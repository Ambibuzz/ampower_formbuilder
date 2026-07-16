import { clone, evaluateDependsOn, getControlComponentName, parseTableOptions, uid } from "./utils.js";

const t = window.__ || ((text) => text);
const DATE_FIELD_TYPES = new Set(["Date", "Datetime", "Time"]);

export const VIEWER_LAYOUT_TYPES = ["Section Break", "Tab Break", "Column Break", "HTML", "Heading"];
export const VIEWER_UPLOAD_FIELD_TYPES = ["Attach", "Attach Image", "Image", "Signature"];

function parseJson(value, fallback = {}) {
	if (!value) return fallback;
	if (typeof value === "object") return value;
	try {
		return JSON.parse(value);
	} catch (error) {
		return fallback;
	}
}

export function getOptionsList(value) {
	if (!value) return [];
	if (Array.isArray(value)) return value.filter(Boolean);
	const raw = String(value);
	if (raw.includes("\n")) {
		return raw.split("\n").map((item) => item.trim()).filter(Boolean);
	}
	return raw.split(",").map((item) => item.trim()).filter(Boolean);
}

export function normalizeField(field = {}) {
	const fieldtype = field.fieldtype || field.field_type || "Data";
	const fieldname = field.fieldname || field.field_name || "";
	const label = field.label || field.field_label || fieldname || t("Untitled Field");

	const normalized = {
		...clone(field),
		id: field.id || uid(),
		fieldtype,
		field_type: fieldtype,
		fieldname,
		field_name: fieldname,
		label,
		field_label: label,
		reqd: field.reqd ? 1 : 0,
		read_only: field.read_only ? 1 : 0,
		hidden: field.hidden ? 1 : 0,
		default: field.default !== undefined && field.default !== null
			? field.default
			: (field.default_value !== undefined && field.default_value !== null ? field.default_value : ""),
		default_value: field.default_value !== undefined && field.default_value !== null
			? field.default_value
			: (field.default !== undefined && field.default !== null ? field.default : ""),
		placeholder: field.placeholder || "",
		description: field.description || "",
		depends_on: field.depends_on || "",
		options: field.options || "",
		filters: clone(field.filters || {}),
		precision: field.precision ?? "",
		length: field.length ?? "",
		sort_options: field.sort_options ? 1 : 0,
		max_height: field.max_height ?? "",
		fetch_from: field.fetch_from || "",
		formula: field.formula || "",
		table_row_title: field.table_row_title || "",
		image_column: field.image_column || "",
		read_only_depends_on: field.read_only_depends_on || "",
	};

	normalized._doctype = fieldtype === "Link" ? (field._doctype || field.options || "") : "";

	if (["Table", "Mixed Table"].includes(fieldtype)) {
		const tableConfig = parseJson(field.options, {});
		const tableColumns = (tableConfig.columns && tableConfig.columns.length)
			? tableConfig.columns
			: (field.table_columns || tableConfig.table_columns || field.columns || []);
		normalized.table_columns = clone(tableColumns || []);
		normalized.table_rows = clone(tableConfig.rows || field.table_rows || field.rows || []);
		normalized.table_row_title = field.table_row_title || tableConfig.table_row_title || tableConfig.row_title || "";
		normalized.image_column = field.image_column || tableConfig.image_column || "";
	}

	return normalized;
}

function normalizeColumn(column = {}) {
	return {
		id: column.id || uid(),
		items: (column.items || []).map((item) => normalizeField(item)),
	};
}

function normalizeSection(section = {}) {
	return {
		id: section.id || uid(),
		item_type: section.item_type || section.fieldtype || "Section Break",
		section_label: section.section_label || section.label || "",
		section_key: section.section_key || section.fieldname || "",
		columns: (section.columns || []).map((column) => normalizeColumn(column)),
	};
}

function createColumn() {
	return {
		id: uid(),
		items: [],
	};
}

export function schemaToSections(schema = {}) {
	if (Array.isArray(schema.sections) && schema.sections.length) {
		return schema.sections.map((section) => normalizeSection(section));
	}

	const fields = schema.fields || [];
	const sections = [];
	let currentSection = null;
	let currentColumn = null;

	fields.forEach((rawField) => {
		const field = normalizeField(rawField);

		if (field.fieldtype === "Section Break" || field.fieldtype === "Tab Break") {
			currentSection = normalizeSection({
				id: field.id || uid(),
				item_type: field.fieldtype,
				section_label: field.label,
				section_key: field.fieldname,
				columns: [],
			});
			sections.push(currentSection);
			currentColumn = createColumn();
			currentSection.columns.push(currentColumn);
			return;
		}

		if (!currentSection) {
			currentSection = normalizeSection({
				id: uid(),
				item_type: "Section Break",
				section_label: t("Default Section"),
				section_key: "default_section",
				columns: [],
			});
			sections.push(currentSection);
			currentColumn = createColumn();
			currentSection.columns.push(currentColumn);
		}

		if (field.fieldtype === "Column Break") {
			currentColumn = createColumn();
			currentSection.columns.push(currentColumn);
			return;
		}

		currentColumn.items.push(field);
	});

	return sections;
}

export function buildTabs(sections = []) {
	const tabs = [];
	let current = { label: t("Details"), sections: [] };

	sections.forEach((section) => {
		const isTab = section.item_type === "Tab Break" || section.item_type === "Tab";
		if (isTab) {
			if (current.sections.length) {
				tabs.push(current);
			}
			current = { label: section.section_label || t("Untitled Tab"), sections: [] };
			if ((section.columns || []).some((column) => (column.items || []).length > 0)) {
				current.sections.push(section);
			}
			return;
		}

		current.sections.push(section);
	});

	if (current.sections.length || !tabs.length) {
		tabs.push(current);
	}

	return tabs;
}

export function flattenFields(sections = []) {
	const fields = [];
	sections.forEach((section) => {
		fields.push({
			fieldtype: section.item_type,
			fieldname: section.section_key,
			label: section.section_label,
		});

		(section.columns || []).forEach((column) => {
			(column.items || []).forEach((field) => fields.push(field));
		});
	});
	return fields;
}

export function getInitialValue(field = {}, submissionData = null) {
	if (submissionData && Object.prototype.hasOwnProperty.call(submissionData, field.fieldname)) {
		if (["Table", "Mixed Table"].includes(field.fieldtype)) {
			return normalizeTableValue(
				field,
				Array.isArray(submissionData[field.fieldname]) ? clone(submissionData[field.fieldname]) : []
			);
		}
		return normalizeFetchedFieldValue(field, submissionData[field.fieldname]);
	}

	if (field.default !== undefined && field.default !== null && field.default !== "") {
		if (["Table", "Mixed Table"].includes(field.fieldtype)) {
			return normalizeTableValue(field, Array.isArray(field.default) ? clone(field.default) : []);
		}
		return normalizeFetchedFieldValue(field, field.default);
	}
	if (field.default_value !== undefined && field.default_value !== null && field.default_value !== "") {
		return normalizeFetchedFieldValue(field, field.default_value);
	}
	if (field.fieldtype === "Check") return 0;
	if (["Table", "Mixed Table"].includes(field.fieldtype)) {
		return Array.isArray(field.default) ? clone(field.default) : [];
	}
	return "";
}

export function formatSubmissionValue(value, fallback = "", fieldtype = "") {
	if (value === null || value === undefined || value === "") return fallback;
	if (DATE_FIELD_TYPES.has(fieldtype)) {
		if (fieldtype === "Date") return frappe.datetime.str_to_user(value, false, true);
		if (fieldtype === "Datetime") return frappe.datetime.str_to_user(value, false);
		return frappe.datetime.str_to_user(value, true);
	}
	if (Array.isArray(value)) return value.length ? `${value.length} item${value.length === 1 ? "" : "s"}` : fallback;
	if (typeof value === "object") {
		const name = value.name || value.label || value.value;
		return name ? String(name) : fallback;
	}
	if (typeof value === "boolean") return value ? "Yes" : "No";
	return String(value);
}

export function normalizeDateFieldValue(fieldtype = "", value) {
	if (!DATE_FIELD_TYPES.has(fieldtype)) return value;
	if (value === null || value === undefined || value === "") return "";

	const rawValue = String(value).trim();
	if (!rawValue) return "";

	const lowerValue = rawValue.toLowerCase();
	if (fieldtype === "Date" && lowerValue === "today") {
		return frappe.datetime.nowdate();
	}
	if (fieldtype === "Datetime" && lowerValue === "now") {
		return frappe.datetime.now_datetime();
	}
	if (fieldtype === "Time" && lowerValue === "now") {
		return frappe.datetime.now_time();
	}

	if (frappe.datetime.validate(rawValue)) {
		return rawValue;
	}

	if (fieldtype === "Date") {
		const normalized = frappe.datetime.user_to_str(rawValue, false, true);
		return normalized === "Invalid date" ? rawValue : normalized;
	}

	if (fieldtype === "Datetime") {
		const normalized = frappe.datetime.user_to_str(rawValue, false);
		return normalized === "Invalid date" ? rawValue : normalized;
	}

	const normalized = frappe.datetime.user_to_str(rawValue, true);
	return normalized === "Invalid date" ? rawValue : normalized;
}

export function getResolvedLinkDoctype(field = {}, values = {}) {
	if (field.fieldtype === "Link") {
		return String(field.options || field._doctype || "").trim();
	}
	if (field.fieldtype === "Dynamic Link") {
		return String(values[field.options] || "").trim();
	}
	return "";
}

export function getDynamicLinkSourceFieldname(field = {}) {
	return field.fieldtype === "Dynamic Link" ? String(field.options || "").trim() : "";
}

export function prettifyFieldname(value) {
	return String(value || "")
		.replace(/_/g, " ")
		.replace(/\b\w/g, (letter) => letter.toUpperCase())
		.trim();
}

export function getFieldPlaceholder(field = {}) {
	if (field.placeholder) return field.placeholder;
	if (field.label) return field.label;
	return prettifyFieldname(field.fieldname || "");
}

export function getFieldInputStep(field = {}) {
	if (field.fieldtype === "Percent") return "0.01";
	const precision = Number(field.precision);
	if (!Number.isFinite(precision) || precision <= 0) return "1";
	return (1 / (10 ** precision)).toString();
}

export function buildViewerControlDf(field = {}, overrides = {}) {
	return {
		...field,
		label: field.label || field.fieldname || "",
		fieldname: field.fieldname || "",
		fieldtype: field.fieldtype || "Data",
		options: field.options || "",
		placeholder: getFieldPlaceholder(field),
		hidden: 0,
		...overrides,
	};
}

export function getVisibleState(field = {}, doc = {}) {
	if (field.hidden) return false;
	if (!field.depends_on) return true;
	return evaluateDependsOn(field.depends_on, doc);
}

export function getEmptyValue(field = {}) {
	if (field.fieldtype === "Check") return 0;
	if (["Table", "Mixed Table"].includes(field.fieldtype)) return [];
	return "";
}

export function normalizeFetchedFieldValue(field = {}, value) {
	if (value === null || value === undefined) {
		return getEmptyValue(field);
	}
	if (field.fieldtype === "Check") {
		return value ? 1 : 0;
	}
	if (DATE_FIELD_TYPES.has(field.fieldtype)) {
		return normalizeDateFieldValue(field.fieldtype, value);
	}
	if (["Number", "Percent", "Int", "Float", "Currency"].includes(field.fieldtype)) {
		const next = Number(value);
		return Number.isFinite(next) ? next : getEmptyValue(field);
	}
	return value;
}

export function getNumericValue(value) {
	if (value === null || value === undefined || value === "") return 0;
	if (typeof value === "boolean") return value ? 1 : 0;
	const next = Number(value);
	return Number.isFinite(next) ? next : 0;
}

export function evaluateFormulaExpression(formula = "", values = {}) {
	const expression = String(formula || "").trim();
	if (!expression) return "";
	if (!/^[\d\s+\-*/%().,_a-zA-Z]+$/.test(expression)) return "";

	const parsed = expression.replace(/\b[a-zA-Z_][a-zA-Z0-9_]*\b/g, (token) => String(getNumericValue(values[token])));

	try {
		// eslint-disable-next-line no-new-func
		const result = new Function(`return (${parsed});`)();
		return Number.isFinite(result) ? result : "";
	} catch (error) {
		return "";
	}
}

export function getTableConfig(field = {}, selectedColumns = null) {
	if (!["Table", "Mixed Table"].includes(field.fieldtype)) {
		return { mode: "table", table_row_title: "", image_column: "", columns: [], rows: [] };
	}

	const normalizeColumns = (columns = []) =>
		columns.map((column) => {
			const fieldtype = column.fieldtype || column.field_type || "Data";
			const fieldname = column.fieldname || column.field_name || frappe.scrub(column.label || column.field_label || "column");

			return {
				...clone(column),
				id: column.id || uid(),
				label: column.label || column.field_label || fieldname || t("Column"),
				fieldname,
				fieldtype,
				field_type: fieldtype,
				field_name: fieldname,
				options: column.options || "",
				placeholder: column.placeholder || "",
				description: column.description || "",
				fetch_from: column.fetch_from || "",
				formula: column.formula || "",
				precision: column.precision ?? "",
				reqd: column.reqd ? 1 : 0,
				read_only: column.read_only ? 1 : 0,
				hidden: column.hidden ? 1 : 0,
				default: column.default !== undefined && column.default !== null ? column.default : "",
				_doctype: column._doctype || (fieldtype === "Link" ? (column.options || "") : ""),
				filters: clone(column.filters || {}),
			};
		});

	const config = parseTableOptions(field.options);
	const fallbackColumns = (config.columns && config.columns.length)
		? config.columns
		: (config.table_columns || config.fields || field.table_columns || field.columns || []);
	const normalizedFallbackColumns = normalizeColumns(fallbackColumns);
	const selectedFieldnames = Array.isArray(selectedColumns) && selectedColumns.length
		? new Set(selectedColumns.map((value) => String(value || "").trim()).filter(Boolean))
		: null;
	const nextColumns = selectedFieldnames
		? normalizedFallbackColumns.filter((column) => selectedFieldnames.has(column.fieldname))
		: normalizedFallbackColumns;
	const resolvedColumns = nextColumns.length ? nextColumns : normalizedFallbackColumns;

	return {
		mode: config.mode || (field.fieldtype === "Mixed Table" ? "mixed" : "table"),
		table_row_title: field.table_row_title || config.table_row_title || config.row_title || "",
		image_column: field.image_column || config.image_column || "",
		columns: resolvedColumns,
		rows: clone(config.rows || field.table_rows || []),
	};
}

export function addTableRow(field = {}, rows = []) {
	const config = getTableConfig(field);
	const row = {};
	config.columns.forEach((column) => {
		row[column.fieldname] = column.default !== undefined && column.default !== null
			? column.default
			: (column.fieldtype === "Check" ? 0 : "");
	});
	return [...rows, row];
}

export function normalizeTableValue(field = {}, rows = []) {
	const config = getTableConfig(field);
	const normalizedRows = (Array.isArray(rows) ? rows : []).map((row) => {
		const next = { ...(row || {}) };
		config.columns.forEach((column) => {
			if (next[column.fieldname] === undefined) {
				next[column.fieldname] = column.fieldtype === "Check" ? 0 : "";
			} else {
				next[column.fieldname] = normalizeTableCellValue(column, next[column.fieldname]);
			}
		});
		return next;
	});

	if (field.fieldtype !== "Mixed Table" || !config.rows.length) {
		return normalizedRows;
	}

	return config.rows.map((rowDefinition, index) => ({
		...config.columns.reduce((acc, column) => {
			acc[column.fieldname] = column.fieldtype === "Check" ? 0 : "";
			return acc;
		}, {}),
		...(normalizedRows[index] || {}),
	}));
}

export function getEmptyTableCellValue(column = {}) {
	return column.fieldtype === "Check" ? false : "";
}

export function normalizeTableCellValue(column = {}, value) {
	if (value === null || value === undefined) return getEmptyTableCellValue(column);
	if (column.fieldtype === "Check") return Boolean(value);
	if (DATE_FIELD_TYPES.has(column.fieldtype)) {
		return normalizeDateFieldValue(column.fieldtype, value);
	}
	if (["Number", "Percent", "Int", "Float", "Currency"].includes(column.fieldtype)) {
		const next = Number(value);
		return Number.isFinite(next) ? next : getEmptyTableCellValue(column);
	}
	return value;
}

export async function syncTableFetchColumns(columns = [], row = {}, reportError = null) {
	const nextRow = { ...(row || {}) };

	for (const column of columns) {
		const fetchFrom = String(column.fetch_from || "").trim();
		if (!fetchFrom) continue;

		const [linkFieldname, linkedFieldname] = fetchFrom.split(".", 2);
		if (!linkFieldname || !linkedFieldname) continue;

		const sourceColumn = columns.find((item) => item.fieldname === linkFieldname);
		if (!sourceColumn) continue;

		const sourceDocName = nextRow[linkFieldname];
		if (!sourceDocName) {
			nextRow[column.fieldname] = getEmptyTableCellValue(column);
			continue;
		}

		const linkedDoctype = getResolvedLinkDoctype(sourceColumn, nextRow);
		if (!linkedDoctype) {
			nextRow[column.fieldname] = getEmptyTableCellValue(column);
			continue;
		}

		try {
			const response = await frappe.db.get_value(linkedDoctype, sourceDocName, linkedFieldname);
			nextRow[column.fieldname] = normalizeTableCellValue(column, response?.message?.[linkedFieldname]);
		} catch (error) {
			if (typeof reportError === "function") {
				reportError(error);
			}
		}
	}

	return nextRow;
}

export function normalizeCalculatedTableValue(column = {}, value) {
	if (value === "") return "";
	const precision = column.precision === "" || column.precision === null || column.precision === undefined
		? null
		: Number(column.precision);
	if (precision === null || !Number.isFinite(precision)) {
		return value;
	}
	const factor = 10 ** precision;
	return Math.round(Number(value) * factor) / factor;
}

export function syncTableFormulaColumns(columns = [], row = {}) {
	const nextRow = { ...(row || {}) };
	for (let iteration = 0; iteration < 5; iteration += 1) {
		let changed = false;
		columns.forEach((column) => {
			if (!column.formula || !column.fieldname) return;
			const nextValue = normalizeCalculatedTableValue(column, evaluateFormulaExpression(column.formula, nextRow));
			if (nextRow[column.fieldname] !== nextValue) {
				nextRow[column.fieldname] = nextValue;
				changed = true;
			}
		});
		if (!changed) break;
	}
	return nextRow;
}

export { getControlComponentName };
