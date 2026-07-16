const SQL_KEYWORDS = new Set([
	"select", "insert", "update", "delete", "drop", "table", "from", "where", "join",
	"group", "order", "limit", "by", "and", "or", "into", "create", "alter", "index",
	"primary", "key", "constraint", "grant", "revoke", "union", "having", "distinct",
]);

export const LAYOUT_FIELD_TYPES = ["Tab Break", "Section Break", "Column Break", "HTML", "Heading"];

export const FIELD_TYPES = [
	{ fieldtype: "Data", label: "Data" },
	{ fieldtype: "Small Text", label: "Small Text" },
	{ fieldtype: "Long Text", label: "Long Text" },
	{ fieldtype: "Text Editor", label: "Text Editor" },
	{ fieldtype: "Color", label: "Color" },
	{ fieldtype: "Attach", label: "Attach" },
	{ fieldtype: "Attach Image", label: "Attach Image" },
	{ fieldtype: "Check", label: "Check" },
	{ fieldtype: "Number", label: "Number" },
	{ fieldtype: "Date", label: "Date" },
	{ fieldtype: "Datetime", label: "Datetime" },
	{ fieldtype: "Time", label: "Time" },
	{ fieldtype: "Select", label: "Select" },
	{ fieldtype: "Radio", label: "Radio" },
	{ fieldtype: "Link", label: "Link" },
	{ fieldtype: "Dynamic Link", label: "Dynamic Link" },
	{ fieldtype: "Table", label: "Table" },
	{ fieldtype: "Mixed Table", label: "Mixed Table" },
];

export const FIELD_LIBRARY_ITEMS = FIELD_TYPES;

export const FIELD_TYPE_MAP = FIELD_TYPES.reduce((acc, item) => {
	acc[item.fieldtype] = item;
	return acc;
}, {});

export const TABLE_COLUMN_FIELD_TYPES = [
	"Data", "Small Text", "Text", "Color", "Number", "Percent",
	"Select", "Link", "Date", "Datetime", "Time", "Check", "Attach Image"
];

const SCHEMA_FIELD_KEYS = new Set([
	"fieldtype",
	"fieldname",
	"label",
	"description",
	"placeholder",
	"default",
	"reqd",
	"read_only",
	"hidden",
	"depends_on",
	"options",
	"fetch_from",
	"formula",
	"precision",
	"table_row_title",
	"image_column",
]);

export function getControlComponentName(fieldtype = "Data") {
	return String(fieldtype || "Data").replaceAll(" ", "") + "Control";
}

export function uid() {
	return `fb_${Math.random().toString(36).slice(2, 10)}`;
}

export function clone(value) {
	return value == null ? value : JSON.parse(JSON.stringify(value));
}

export function escapeHtml(text) {
	const source = text == null ? "" : String(text);
	const escape = window.frappe?.utils?.escape_html;
	return escape ? escape(source) : source.replace(/[&<>"']/g, (char) => ({
		"&": "&amp;",
		"<": "&lt;",
		">": "&gt;",
		"\"": "&quot;",
		"'": "&#039;",
	}[char]));
}

export function slugify(text) {
	return String(text || "")
		.toLowerCase()
		.trim()
		.replace(/['"]/g, "")
		.replace(/[^a-z0-9]+/g, "_")
		.replace(/^_+|_+$/g, "")
		.replace(/_{2,}/g, "_");
}

export function normalizeFieldname(text, fallback = "field") {
	let value = slugify(text);
	if (!value) value = slugify(fallback) || "field";
	if (!/^[a-z]/.test(value)) value = `field_${value}`;
	value = value.replace(/^_+|_+$/g, "");
	if (SQL_KEYWORDS.has(value)) value = `${value}_field`;
	if (value.endsWith("_")) value = value.replace(/_+$/g, "");
	return value || "field";
}

export function ensureUniqueFieldname(name, existingNames = new Set(), fallback = "field") {
	const usedNames = existingNames instanceof Set ? existingNames : new Set(existingNames || []);
	const baseName = normalizeFieldname(name, fallback);
	let candidate = baseName;
	let counter = 2;
	while (usedNames.has(candidate)) {
		candidate = `${baseName}_${counter++}`;
	}
	usedNames.add(candidate);
	return candidate;
}

export function validateFieldname(name) {
	const value = String(name || "").trim();
	if (!value) return { valid: false, message: "Fieldname is required." };
	if (!/^[a-z][a-z0-9_]*$/.test(value)) {
		return { valid: false, message: "Fieldname must start with a letter and use lowercase letters, numbers, and underscores only." };
	}
	if (SQL_KEYWORDS.has(value)) {
		return { valid: false, message: "Fieldname cannot be a SQL keyword." };
	}
	if (value.endsWith("_")) {
		return { valid: false, message: "Fieldname cannot end with an underscore." };
	}
	return { valid: true, message: "" };
}

export function validateDependsOn(expr) {
	const value = String(expr || "").trim();
	if (!value) return { valid: true, message: "" };
	if (value.startsWith("eval:")) {
		try {
			// eslint-disable-next-line no-new-func
			new Function("doc", `return (${value.slice(5)});`);
			return { valid: true, message: "" };
		} catch (error) {
			return { valid: false, message: `Invalid eval expression: ${error.message}` };
		}
	}
	if (/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(value)) {
		return { valid: true, message: "" };
	}
	if (/^doc\.[a-zA-Z_][a-zA-Z0-9_]*\s*(==|!=|>|<|>=|<=).+/.test(value)) {
		return { valid: true, message: "" };
	}
	return { valid: false, message: "Depends On must be a fieldname, `doc.field == value`, or `eval:` expression." };
}

export function evaluateDependsOn(expr, doc = {}) {
	const value = String(expr || "").trim();
	if (!value) return true;
	if (value.startsWith("eval:")) {
		try {
			// eslint-disable-next-line no-new-func
			return Boolean(new Function("doc", `return (${value.slice(5)});`)(doc));
		} catch (error) {
			return false;
		}
	}
	if (/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(value)) {
		return Boolean(doc[value]);
	}
	try {
		// eslint-disable-next-line no-new-func
		return Boolean(new Function("doc", `return (${value.replace(/^doc\./, "doc.")});`)(doc));
	} catch (error) {
		return false;
	}
}

export function getFieldTypeCapabilities(type) {
	const fieldtype = type || "Data";
	const caps = {
		placeholder: !["Check", "Button", "HTML", "Heading", "Image", "Section Break", "Column Break", "Tab Break"].includes(fieldtype),
		description: true,
		required: canBeRequired(fieldtype),
		options: ["Select", "Radio"].includes(fieldtype),
		linkOptions: ["Link", "Dynamic Link"].includes(fieldtype),
		tableColumns: ["Table", "Mixed Table"].includes(fieldtype),
		tableRows: fieldtype === "Mixed Table",
		precision: ["Number", "Percent"].includes(fieldtype),
		styles: ["Small Text", "Long Text"].includes(fieldtype),
		defaultValue: !["Attach", "Attach Image", "Table", "Mixed Table"].includes(fieldtype),
		dependsOn: !["Section Break", "Column Break", "Tab Break"].includes(fieldtype),
	};
	return caps;
}

export function canBeInTable(type) {
	return TABLE_COLUMN_FIELD_TYPES.includes(type);
}

export function canBeRequired(type) {
	return !["Button", "HTML", "Heading", "Section Break", "Column Break", "Tab Break", "Read Only"].includes(type);
}

export function normalizeOptions(value) {
	if (Array.isArray(value)) return value.join("\n");
	return String(value || "").trim();
}

export function buildDefaultField(fieldtype = "Data") {
	const meta = FIELD_TYPE_MAP[fieldtype] || FIELD_TYPE_MAP.Data;
	return {
		id: uid(),
		type: "field",
		fieldtype: meta.fieldtype,
		label: meta.label,
		fieldname: normalizeFieldname(meta.label, meta.fieldtype || "field"),
		description: "",
		placeholder: "",
		default: "",
		reqd: 0,
		read_only: 0,
		hidden: 0,
		depends_on: "",
		options: ["Select", "Radio"].includes(fieldtype) ? "Option 1\nOption 2" : "",
		fetch_from: "",
		formula: "",
		precision: ["Number", "Percent"].includes(fieldtype) ? 2 : "",
		table_row_title: fieldtype === "Mixed Table" ? "Row" : "",
		image_column: "",
		table_columns: [],
		table_rows: [],
		table_data: [],
		_doctype: "",
	};
}

export function buildDefaultTableColumn(index = 0) {
	return {
		id: uid(),
		label: `Column ${index + 1}`,
		fieldname: `column_${index + 1}`,
		fieldtype: "Data",
		reqd: 0,
		options: "",
		placeholder: "",
		fetch_from: "",
		formula: "",
		precision: "",
		_doctype: "",
		_manualFieldname: false,
	};
}

export function buildDefaultTableRow(index = 0) {
	return {
		id: uid(),
		label: `Row ${index + 1}`,
		key: `row_${index + 1}`,
	};
}

export function normalizeTableColumn(column = {}, index = 0) {
	const nextFieldtype = column.fieldtype;
	return {
		...buildDefaultTableColumn(index),
		...clone(column),
		label: column.label || `Column ${index + 1}`,
		fieldname: normalizeFieldname(column.fieldname || column.label || `column_${index + 1}`, `column_${index + 1}`),
		fieldtype: TABLE_COLUMN_FIELD_TYPES.includes(nextFieldtype) ? nextFieldtype : "Data",
		reqd: column.reqd ? 1 : 0,
		options: column.options || "",
		placeholder: column.placeholder || "",
		fetch_from: column.fetch_from || "",
		formula: column.formula || "",
		precision: column.precision ?? (["Number", "Percent"].includes(nextFieldtype) ? 2 : ""),
		_doctype: column._doctype || (nextFieldtype === "Link" ? (column.options || "") : ""),
	};
}

export function normalizeTableRow(row = {}, index = 0) {
	return {
		...buildDefaultTableRow(index),
		...clone(row),
		label: String(row.label || `${index + 1}`),
		key: normalizeFieldname(row.key || row.label || `row_${index + 1}`, `row_${index + 1}`),
	};
}

export function parseTableOptions(value) {
	if (!value) return {};
	if (typeof value === "object") return clone(value);
	try {
		return JSON.parse(value);
	} catch (error) {
		return {};
	}
}

export function buildTableOptions(field = {}) {
	return JSON.stringify({
		mode: field.fieldtype === "Mixed Table" ? "mixed" : "table",
		table_row_title: field.table_row_title || "",
		image_column: field.image_column || "",
		columns: clone(field.table_columns || []).map((column, index) => {
			const normalized = normalizeTableColumn(column, index);
			return {
				label: normalized.label,
				fieldname: normalized.fieldname,
				fieldtype: normalized.fieldtype,
				reqd: normalized.reqd ? 1 : 0,
				placeholder: normalized.placeholder || "",
				fetch_from: normalized.fetch_from || "",
				formula: normalized.formula || "",
				precision: normalized.precision ?? "",
				options: normalized.fieldtype === "Link" ? (normalized._doctype || normalized.options || "") : (normalized.options || ""),
			};
		}),
		rows: clone(field.table_rows || []).map((row) => ({
			label: row.label,
			key: normalizeFieldname(row.key || row.label || "row", row.label || "row"),
		})),
	});
}

export function validateTableColumns(columns = []) {
	const errors = [];
	const seen = new Set();

	if (!columns.length) {
		errors.push("Table fields require at least one column.");
		return errors;
	}

	columns.forEach((column) => {
		const fieldnameCheck = validateFieldname(column.fieldname);
		if (!fieldnameCheck.valid) errors.push(fieldnameCheck.message);
		if (seen.has(column.fieldname)) errors.push(`Duplicate table column fieldname: ${column.fieldname}`);
		seen.add(column.fieldname);
		if (!TABLE_COLUMN_FIELD_TYPES.includes(column.fieldtype)) {
			errors.push(`Unsupported table column fieldtype: ${column.fieldtype}`);
		}
		if (column.fieldtype === "Select" && !normalizeOptions(column.options)) {
			errors.push(`Select column "${column.label || column.fieldname}" requires options.`);
		}
		if (column.fieldtype === "Link" && !(column._doctype || column.options)) {
			errors.push(`Link column "${column.label || column.fieldname}" requires a DocType.`);
		}
	});

	return [...new Set(errors)];
}

export function buildDefaultColumn(sectionId = "") {
	return {
		id: uid(),
		type: "column",
		section_id: sectionId,
		items: [],
	};
}

export function buildDefaultSection(itemType = "Section Break") {
	const label = itemType === "Tab Break" ? "New Tab" : "New Section";
	return {
		id: uid(),
		type: "section",
		item_type: itemType,
		section_label: label,
		section_key: normalizeFieldname(label, itemType === "Tab Break" ? "tab" : "section"),
		columns: [buildDefaultColumn()],
	};
}

export function buildFlatFieldArray(sections = []) {
	const fields = [];
	let sequence = 1;
	sections.forEach((section) => {
		const sectionFieldname = normalizeFieldname(
			section.section_key || section.fieldname || section.id || section.section_label || "section",
			section.item_type === "Tab Break" ? "tab" : "section"
		);
		fields.push({
			fieldtype: section.item_type || "Section Break",
			fieldname: sectionFieldname,
			label: section.section_label || "",
			section_key: sectionFieldname,
			section_label: section.section_label || "",
			sequence: sequence++,
		});
		(section.columns || []).forEach((column, index) => {
			if (index > 0) {
				fields.push({
					fieldtype: "Column Break",
					fieldname: normalizeFieldname(
						`${sectionFieldname}_column_${index + 1}`,
						`column_${index + 1}`
					),
					label: "Column Break",
					section_key: sectionFieldname,
					section_label: section.section_label || "",
					sequence: sequence++,
				});
			}
			(column.items || []).forEach((field) => {
				const docfield = sanitizeFieldForSchema(field);
				docfield.fieldname = normalizeFieldname(
					docfield.fieldname || docfield.label || docfield.fieldtype || "field",
					docfield.fieldtype || "field"
				);
				docfield.sequence = sequence++;
				fields.push(docfield);
			});
		});
	});
	return fields;
}

export function sanitizeFieldForSchema(field = {}) {
	const source = clone(field);
	const docfield = {};

	SCHEMA_FIELD_KEYS.forEach((key) => {
		if (source[key] !== undefined) {
			docfield[key] = source[key];
		}
	});

	docfield.fieldname = normalizeFieldname(
		docfield.fieldname || source.fieldname || source.field_name || source.label || docfield.fieldtype || "field",
		docfield.fieldtype || "field"
	);

	if (docfield.fieldtype === "Link" || docfield.fieldtype === "Dynamic Link") {
		docfield.options = source.options || source._doctype || "";
	}

	if (["Table", "Mixed Table"].includes(docfield.fieldtype)) {
		docfield.options = buildTableOptions(source);
	}

	return docfield;
}

export function validateFieldDefinition(field, seen = new Set()) {
	const messages = [];
	const fieldtype = field.fieldtype || "Data";
	if (!LAYOUT_FIELD_TYPES.includes(fieldtype)) {
		const fieldnameCheck = validateFieldname(field.fieldname);
		if (!fieldnameCheck.valid) messages.push(fieldnameCheck.message);
		if (seen.has(field.fieldname)) messages.push(`Duplicate fieldname: ${field.fieldname}`);
		seen.add(field.fieldname);
	}
	if (field.reqd && field.hidden) messages.push("Required fields cannot be hidden.");
	if (["Select", "Radio"].includes(fieldtype) && !normalizeOptions(field.options)) messages.push(`${fieldtype} fields require options.`);
	if (fieldtype === "Link" && !(field.options || field._doctype)) {
		messages.push("Link fields require an Options / DocType value.");
	}
	if (fieldtype === "Dynamic Link" && !field.options) {
		messages.push("Dynamic Link fields require an Options / Source Field value.");
	}
	if (field.formula) {
		const formula = String(field.formula).trim();
		if (!/^[\d\s+\-*/%().,_a-zA-Z]+$/.test(formula)) {
			messages.push("Calculation formula supports only fieldnames, numbers, parentheses, and basic math operators.");
		}
	}
	if (["Table", "Mixed Table"].includes(fieldtype) && !(field.table_columns || []).length) {
		messages.push(`${fieldtype} fields require at least one table column.`);
	}
	if (["Table", "Mixed Table"].includes(fieldtype)) {
		messages.push(...validateTableColumns(field.table_columns || []));
	}
	if (fieldtype === "Mixed Table" && !(field.table_rows || []).length) {
		messages.push("Mixed Table fields require at least one row.");
	}
	const dependsOnCheck = validateDependsOn(field.depends_on);
	if (!dependsOnCheck.valid) messages.push(dependsOnCheck.message);
	return messages;
}
