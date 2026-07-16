import { defineStore } from "pinia";
import {
	buildDefaultColumn,
	buildDefaultField,
	buildDefaultSection,
	buildDefaultTableColumn,
	buildDefaultTableRow,
	buildFlatFieldArray,
	ensureUniqueFieldname,
	FIELD_TYPE_MAP,
	TABLE_COLUMN_FIELD_TYPES,
	clone,
	normalizeOptions,
	normalizeFieldname,
	normalizeTableColumn,
	normalizeTableRow,
	parseTableOptions,
	sanitizeFieldForSchema,
	uid,
	validateFieldDefinition,
	validateTableColumns,
} from "./utils.js";
import { getCachedTemplateSchema, invalidateTemplateSchemaCache } from "./templateCache.js";

const t = window.__ || ((text) => text);
const DEFAULT_TEMPLATE_VERSION_LABEL = "1.0";

function buildTemplateState(overrides = {}) {
	return {
		name: "",
		form_name: "",
		form_type: "Form",
		target_doctype: "",
		loaded_doctype: "",
		description: "",
		version: 0,
		base_form_name: "",
		version_label: DEFAULT_TEMPLATE_VERSION_LABEL,
		version_group: "",
		source_template: "",
		is_latest_version: 1,
		is_active: 1,
		...clone(overrides),
	};
}

function getSectionBaseLabel(itemType = "Section Break") {
	if (itemType === "Tab Break") return "New Tab";
	return "New Section";
}

function getUniqueSectionMeta(sections = [], itemType = "Section Break", preferredLabel = "") {
	const baseLabel = preferredLabel || getSectionBaseLabel(itemType);
	const existingLabels = new Set(sections.map((section) => String(section.section_label || "").toLowerCase()).filter(Boolean));
	const existingKeys = new Set(sections.map((section) => section.section_key).filter(Boolean));

	let label = baseLabel;
	let counter = 2;
	while (existingLabels.has(label.toLowerCase())) {
		label = `${baseLabel} ${counter++}`;
	}

	const baseKey = normalizeFieldname(label, itemType === "Tab Break" ? "tab" : "section");
	let key = baseKey;
	let keyCounter = 2;
	while (existingKeys.has(key)) {
		key = `${baseKey}_${keyCounter++}`;
	}

	return { label, key };
}

function buildUniqueSection(sections = [], itemType = "Section Break", preferredLabel = "") {
	const section = buildDefaultSection(itemType);
	const meta = getUniqueSectionMeta(sections, itemType, preferredLabel);
	section.section_label = meta.label;
	section.section_key = meta.key;
	return section;
}

export function getTabGroups(sections = []) {
	const tabSections = sections.filter((section) => section.item_type === "Tab Break");
	if (!tabSections.length) {
		return [{ id: "default", tab: null, sections }];
	}

	const groups = [];
	let currentGroup = null;
	sections.forEach((section) => {
		if (section.item_type === "Tab Break") {
			currentGroup = { id: section.id, tab: section, sections: [section] };
			groups.push(currentGroup);
			return;
		}
		if (currentGroup) {
			currentGroup.sections.push(section);
			return;
		}
		if (!groups.length) {
			groups.push({ id: "leading", tab: null, sections: [section] });
			return;
		}
		groups[0].sections.push(section);
	});

	if (groups[0]?.id === "leading" && groups[1]) {
		const leadingSections = groups.shift().sections || [];
		groups[0].sections.unshift(...leadingSections);
	}

	return groups;
}

function getTabInsertIndex(sections = [], activeTabId = null) {
	const groups = getTabGroups(sections);
	const group = groups.find((item) => item.id === activeTabId) || groups.at(-1);
	if (!group?.sections?.length) return sections.length;
	const lastSection = group.sections.at(-1);
	return sections.findIndex((section) => section.id === lastSection.id) + 1;
}

function ensureTabbedSections(sections = []) {
	if (!sections.length) return [buildUniqueSection([], "Tab Break", "Details")];
	if (sections.some((section) => section.item_type === "Tab Break")) return sections;
	return [buildUniqueSection(sections, "Tab Break", "Details"), ...sections];
}

function getEmptyTableValue(fieldtype = "Data") {
	return fieldtype === "Check" ? false : "";
}

function buildEmptyTableRow(columns = []) {
	const row = {};
	columns.forEach((column) => {
		row[column.fieldname] = getEmptyTableValue(column.fieldtype);
	});
	return row;
}

function syncTableDataWithColumns(rows = [], previousColumns = [], nextColumns = [], rowDefinitions = []) {
	const previousById = new Map(previousColumns.map((column) => [column.id, column]));
	const normalizedRows = (Array.isArray(rows) ? rows : []).map((row) => {
		const normalizedRow = {};
		nextColumns.forEach((column) => {
			const previousColumn = previousById.get(column.id);
			const previousFieldname = previousColumn?.fieldname;
			if (previousFieldname && Object.prototype.hasOwnProperty.call(row || {}, previousFieldname)) {
				normalizedRow[column.fieldname] = row[previousFieldname];
				return;
			}
			if (Object.prototype.hasOwnProperty.call(row || {}, column.fieldname)) {
				normalizedRow[column.fieldname] = row[column.fieldname];
				return;
			}
			normalizedRow[column.fieldname] = getEmptyTableValue(column.fieldtype);
		});
		return normalizedRow;
	});

	if (!rowDefinitions.length) return normalizedRows;

	return rowDefinitions.map((rowDefinition, index) => {
		const existingRow = normalizedRows[index] || {};
		return {
			...buildEmptyTableRow(nextColumns),
			...existingRow,
		};
	});
}

function sanitizeSectionsForSchema(sections = []) {
	return sanitizeBuilderSections(sections).map((section) => ({
		...section,
		columns: (section.columns || []).map((column) => ({
			...column,
			items: (column.items || []).map((field) => {
				const sanitized = sanitizeFieldForSchema(field);
				delete sanitized.sequence;
				return sanitized;
			}),
		})),
	}));
}

function getConfigurableFields(sections = []) {
	return sections.flatMap((section) =>
		(section.columns || []).flatMap((column) => column.items || [])
	);
}

function notify(message, indicator = "orange") {
	if (window.frappe?.show_alert) {
		window.frappe.show_alert({ message, indicator });
	}
}

function notifyError(message) {
	if (window.frappe?.msgprint) {
		window.frappe.msgprint({ title: t("Validation Error"), message, indicator: "red" });
	}
}

function getSupportedFieldtype(fieldtype = "Data") {
	return FIELD_TYPE_MAP[fieldtype] ? fieldtype : "Data";
}

function getSupportedTableColumnFieldtype(fieldtype = "Data") {
	return TABLE_COLUMN_FIELD_TYPES.includes(fieldtype) ? fieldtype : "Data";
}

function sanitizeTableColumns(columns = []) {
	const usedFieldnames = new Set();
	return (columns || []).map((column, index) => {
		const nextColumn = normalizeTableColumn(column, index);
		nextColumn.fieldname = ensureUniqueFieldname(
			nextColumn.fieldname || nextColumn.label || `column_${index + 1}`,
			usedFieldnames,
			`column_${index + 1}`
		);
		return nextColumn;
	});
}

function sanitizeBuilderField(field = {}, usedFieldnames = new Set()) {
	const item = normalizeHydratedField(field);
	item.fieldname = ensureUniqueFieldname(
		item.fieldname || item.label || item.fieldtype || "field",
		usedFieldnames,
		item.fieldtype || "field"
	);
	item.field_name = item.fieldname;

	if (["Table", "Mixed Table"].includes(item.fieldtype)) {
		item.table_columns = sanitizeTableColumns(item.table_columns || []);
		item.table_rows = (item.table_rows || []).map((row, index) => normalizeTableRow(row, index));
		item.table_data = syncTableDataWithColumns(
			item.table_data || [],
			[],
			item.table_columns || [],
			item.fieldtype === "Mixed Table" ? (item.table_rows || []) : []
		);
	}

	return item;
}

function sanitizeBuilderSections(sections = []) {
	const usedFieldnames = new Set();
	return clone(sections).map((section) => {
		const itemType = section.item_type || section.fieldtype || "Section Break";
		const nextSection = {
			...buildDefaultSection(itemType),
			...clone(section),
		};
		nextSection.id = nextSection.id || uid();
		nextSection.section_key = normalizeFieldname(
			nextSection.section_key || nextSection.fieldname || nextSection.id || nextSection.section_label || "section",
			itemType === "Tab Break" ? "tab" : "section"
		);
		nextSection.columns = (nextSection.columns || []).length
			? (nextSection.columns || []).map((column) => ({
				...buildDefaultColumn(nextSection.id),
				...clone(column),
				id: column.id || uid(),
				section_id: column.section_id || nextSection.id,
				items: (column.items || []).map((field) => sanitizeBuilderField(field, usedFieldnames)),
			}))
			: [buildDefaultColumn(nextSection.id)];
		return nextSection;
	});
}

function buildImportedField(rawField = {}, childTables = {}) {
	const sourceType = rawField.fieldtype || rawField.field_type || "Data";
	const isChildTable = sourceType === "Table";
	const nextType = isChildTable ? "Table" : getSupportedFieldtype(sourceType);
	const label = rawField.label || rawField.fieldname || nextType;
	const fieldname = normalizeFieldname(rawField.fieldname || rawField.field_name || label, nextType || "field");
	const field = {
		...buildDefaultField(nextType),
		label,
		fieldname,
		description: rawField.description || "",
		placeholder: rawField.placeholder || "",
		default: rawField.default ?? "",
		reqd: rawField.reqd ? 1 : 0,
		read_only: rawField.read_only ? 1 : 0,
		hidden: rawField.hidden ? 1 : 0,
		depends_on: rawField.depends_on || "",
		fetch_from: rawField.fetch_from || "",
		precision: rawField.precision || "",
		options: rawField.options || "",
		_doctype: nextType === "Link" ? (rawField.options || "") : "",
	};

	if (["Select", "Radio"].includes(nextType)) {
		field.options = normalizeOptions(rawField.options);
	}

	if (isChildTable) {
		const tableMeta = childTables[rawField.fieldname]
			|| childTables[rawField.field_name]
			|| childTables[fieldname]
			|| { columns: [] };
		field.options = rawField.options || "";
		field._doctype = rawField.options || "";
		field.table_columns = sanitizeTableColumns((tableMeta.columns || []).map((column, index) => ({
			label: column.label || column.fieldname || `Column ${index + 1}`,
			fieldname: column.fieldname || column.field_name || column.label || `column_${index + 1}`,
			fieldtype: getSupportedTableColumnFieldtype(column.fieldtype || "Data"),
			reqd: column.reqd ? 1 : 0,
			options: ["Select", "Radio"].includes(column.fieldtype) ? normalizeOptions(column.options) : (column.options || ""),
			_doctype: column.fieldtype === "Link" ? (column.options || "") : "",
		})));
		field.table_rows = [];
		field.table_data = [];
	}

	return field;
}

function buildSectionsFromDoctype(doctypeMeta = {}) {
	const sections = [];
	const childTables = doctypeMeta.child_tables || {};
	let currentSection = null;
	let currentColumn = null;

	const ensureSection = (itemType = "Section Break", label = "") => {
		currentSection = buildUniqueSection(sections, itemType, label || (itemType === "Tab Break" ? "Details" : ""));
		currentSection.columns = [];
		currentColumn = buildDefaultColumn(currentSection.id);
		currentSection.columns.push(currentColumn);
		sections.push(currentSection);
		return currentSection;
	};

	const ensureColumn = () => {
		if (!currentSection) ensureSection("Tab Break", "Details");
		if (!currentColumn) {
			currentColumn = buildDefaultColumn(currentSection.id);
			currentSection.columns.push(currentColumn);
		}
		return currentColumn;
	};

	(doctypeMeta.fields || []).forEach((field) => {
		const fieldtype = field.fieldtype || field.field_type || "Data";
		if (fieldtype === "Tab Break" || fieldtype === "Section Break") {
			ensureSection(fieldtype, field.label || "");
			return;
		}
		if (fieldtype === "Column Break") {
			if (!currentSection) ensureSection("Section Break", "Details");
			currentColumn = buildDefaultColumn(currentSection.id);
			currentSection.columns.push(currentColumn);
			return;
		}
		const column = ensureColumn();
		column.items.push(buildImportedField(field, childTables));
	});

	return ensureTabbedSections(sections);
}

function normalizeHydratedField(field = {}) {
	const item = { ...buildDefaultField(field.fieldtype || field.field_type || "Data"), ...clone(field) };
	item.id = item.id || uid();
	item.fieldname = normalizeFieldname(item.fieldname || item.field_name || item.label || item.fieldtype || "field", item.fieldtype || "field");
	item.field_name = item.fieldname;
	item._doctype = item.fieldtype === "Link" ? (item._doctype || item.options || "") : "";

	if (["Table", "Mixed Table"].includes(item.fieldtype) && typeof item.options === "string") {
		const tableConfig = parseTableOptions(item.options);
		item.image_column = item.image_column || tableConfig.image_column || "";
		item.table_columns = sanitizeTableColumns(tableConfig.columns || item.table_columns || []);
		item.table_rows = (tableConfig.rows || item.table_rows || []).map((row, index) =>
			normalizeTableRow(row, index));
	}

	item.table_columns = sanitizeTableColumns(item.table_columns || []);
	item.table_rows = (item.table_rows || []).map((tableRow, index) =>
		normalizeTableRow(tableRow, index));
	item.table_data = ["Table", "Mixed Table"].includes(item.fieldtype)
		? syncTableDataWithColumns(
			item.table_data || [],
			[],
			item.table_columns || [],
			item.fieldtype === "Mixed Table" ? (item.table_rows || []) : []
		)
		: (item.table_data || []);

	return item;
}

function hydrateSections(schema = {}) {
	if (Array.isArray(schema.sections) && schema.sections.length) {
		return ensureTabbedSections(sanitizeBuilderSections(schema.sections));
	}

	const sections = [];
	let currentSection = null;
	let currentColumn = null;
	(schema.fields || []).forEach((field) => {
		const fieldtype = field.fieldtype || field.field_type;
		if (fieldtype === "Tab Break" || fieldtype === "Section Break") {
			currentSection = {
				...buildDefaultSection(fieldtype),
				id: field.id || uid(),
				item_type: fieldtype,
				section_label: field.label || field.section_label || "Untitled Section",
				section_key: field.section_key || field.fieldname || normalizeFieldname(field.label || "section", fieldtype === "Tab Break" ? "tab" : "section"),
				columns: [],
			};
			currentColumn = { ...buildDefaultColumn(currentSection.id), items: [] };
			currentSection.columns.push(currentColumn);
			sections.push(currentSection);
			return;
		}
		if (fieldtype === "Column Break") {
			if (!currentSection) {
				currentSection = buildDefaultSection("Section Break");
				sections.push(currentSection);
			}
			currentColumn = { ...buildDefaultColumn(currentSection.id), items: [] };
			currentSection.columns.push(currentColumn);
			return;
		}
		if (!currentSection) {
			currentSection = buildDefaultSection("Section Break");
			sections.push(currentSection);
		}
		if (!currentColumn) {
			currentColumn = { ...buildDefaultColumn(currentSection.id), items: [] };
			currentSection.columns.push(currentColumn);
		}
		currentColumn.items.push(normalizeHydratedField(field));
	});
	return sanitizeBuilderSections(ensureTabbedSections(sections));
}

export const useFormBuilderStore = defineStore("ampowerFormBuilder", {
	state: () => ({
		sections: [],
		selected: null,
		currentTemplate: buildTemplateState(),
		registry: {},
		dirty: false,
		dirtyReason: "",
		isSaving: false,
		activeBuilderTabId: null,
		preview: { open: false },
		previewTabIndex: 0,
	}),
	getters: {
		hasContent: (state) => state.sections.some((section) => section.columns.some((column) => column.items.length)),
		selectedItem(state) {
			if (!state.selected?.id) return null;
			const entry = state.registry[state.selected.id];
			if (!entry) return null;
			if (entry.kind === "section") return state.sections.find((section) => section.id === entry.sectionId) || null;
			if (entry.kind === "column") {
				const section = state.sections.find((item) => item.id === entry.sectionId);
				return section?.columns.find((column) => column.id === entry.columnId) || null;
			}
			const section = state.sections.find((item) => item.id === entry.sectionId);
			const column = section?.columns.find((item) => item.id === entry.columnId);
			return column?.items.find((field) => field.id === entry.fieldId) || null;
		},
	},
	actions: {
		_register() {
			const registry = {};
			this.sections.forEach((section) => {
				registry[section.id] = { kind: "section", id: section.id, sectionId: section.id };
				(section.columns || []).forEach((column) => {
					registry[column.id] = { kind: "column", id: column.id, sectionId: section.id, columnId: column.id };
					(column.items || []).forEach((field) => {
						registry[field.id] = {
							kind: "field",
							id: field.id,
							sectionId: section.id,
							columnId: column.id,
							fieldId: field.id,
						};
					});
				});
			});
			this.registry = registry;
		},
		setDirty(reason = "builder_state_changed") {
			const nextReason = String(reason || "builder_state_changed");
			if (!this.dirty && typeof window !== "undefined") {
				console.warn("[AFB dirty]", nextReason);
				console.trace();
			}
			this.dirty = true;
			this.dirtyReason = nextReason;
		},
		setClean(reason = "") {
			this.dirty = false;
			this.dirtyReason = String(reason || "");
		},
		markDirty(reason = "builder_state_changed") {
			this.setDirty(reason);
			this._register();
		},
		newForm() {
			this.sections = [buildUniqueSection([], "Tab Break", "Details")];
			this.selected = null;
			this.currentTemplate = buildTemplateState();
			this.isSaving = false;
			this.activeBuilderTabId = this.sections[0].id;
			this.preview = { open: false };
			this.previewTabIndex = 0;
			this.setClean();
			this._register();
		},
		createSection(itemType = "Section Break", index = null) {
			const insertIndex = typeof index === "number"
				? index
				: (itemType === "Tab Break"
					? getTabInsertIndex(this.sections, this.activeBuilderTabId)
					: (this.activeBuilderTabId ? getTabInsertIndex(this.sections, this.activeBuilderTabId) : this.sections.length));
			const section = buildUniqueSection(this.sections, itemType);
			this.sections.splice(insertIndex, 0, section);
			if (itemType === "Tab Break") this.activeBuilderTabId = section.id;
			this.markDirty("section_created");
			this.selectItem(section.id);
			return section;
		},
		createColumn(sectionId, index = null) {
			const section = this.sections.find((item) => item.id === sectionId);
			if (!section) return null;
			const column = buildDefaultColumn(sectionId);
			if (typeof index === "number") section.columns.splice(index, 0, column);
			else section.columns.push(column);
			this.markDirty("column_created");
			this.selectItem(column.id);
			return column;
		},
		createField(columnId, fieldtype = "Data", index = null, preset = {}) {
			const section = this.sections.find((item) => item.columns.some((column) => column.id === columnId));
			const column = section?.columns.find((item) => item.id === columnId);
			if (!column) return null;
			const field = buildDefaultField(fieldtype);
			Object.assign(field, clone(preset));
			field.fieldname = normalizeFieldname(field.fieldname || field.label, field.fieldtype || "field");
			field.field_name = field.fieldname;
			field._manualFieldname = Boolean(field._manualFieldname || preset.fieldname);
			if (typeof index === "number") column.items.splice(index, 0, field);
			else column.items.push(field);
			this.sections = sanitizeBuilderSections(this.sections);
			this.markDirty("field_created");
			this.selectItem(field.id);
			return this._getField(field.id);
		},
		deleteSection(sectionId) {
			this.sections = this.sections.filter((section) => section.id !== sectionId);
			this.sections = ensureTabbedSections(this.sections);
			if (this.activeBuilderTabId === sectionId) {
				this.activeBuilderTabId = this.sections.find((section) => section.item_type === "Tab Break")?.id || null;
			}
			if (this.selected?.id === sectionId) this.clearSelection();
			this.markDirty();
		},
		setActiveBuilderTab(sectionId) {
			this.activeBuilderTabId = sectionId || null;
		},
		deleteColumn(columnId) {
			this.sections = this.sections.map((section) => ({
				...section,
				columns: section.columns.filter((column) => column.id !== columnId),
			})).filter((section) => section.columns.length);
			if (this.selected?.id === columnId) this.clearSelection();
			this.markDirty();
		},
		deleteField(fieldId) {
			this.sections = this.sections.map((section) => ({
				...section,
				columns: section.columns.map((column) => ({
					...column,
					items: column.items.filter((field) => field.id !== fieldId),
				})),
			}));
			if (this.selected?.id === fieldId) this.clearSelection();
			this.markDirty();
		},
		selectItem(id) {
			const entry = this.registry[id];
			if (!entry) {
				this.clearSelection();
				return;
			}
			this.selected = { id, kind: entry.kind };
		},
		clearSelection() {
			this.selected = null;
		},
		updateSection(sectionId, patch) {
			const section = this.sections.find((item) => item.id === sectionId);
			if (!section) return;
			Object.assign(section, clone(patch));
			if (patch.section_label && !patch.section_key) {
				const otherSections = this.sections.filter((item) => item.id !== sectionId);
				const meta = getUniqueSectionMeta(otherSections, section.item_type, patch.section_label);
				section.section_label = meta.label;
				section.section_key = meta.key;
			}
			if (patch.section_key) {
				const otherKeys = new Set(this.sections.filter((item) => item.id !== sectionId).map((item) => item.section_key));
				let key = normalizeFieldname(patch.section_key, section.item_type === "Tab Break" ? "tab" : "section");
				const baseKey = key;
				let counter = 2;
				while (otherKeys.has(key)) {
					key = `${baseKey}_${counter++}`;
				}
				section.section_key = key;
			}
			this.markDirty();
		},
		updateField(fieldId, patch) {
			for (const section of this.sections) {
				for (const column of section.columns) {
					const field = column.items.find((item) => item.id === fieldId);
					if (!field) continue;
					Object.assign(field, clone(patch));
					if (patch.fieldname) {
						field.fieldname = normalizeFieldname(patch.fieldname, field.fieldtype || "field");
						field._manualFieldname = true;
					} else if (patch.label && !field._manualFieldname) {
						field.fieldname = normalizeFieldname(patch.label, field.fieldtype || "field") || field.fieldname;
					}
					if (["Table", "Mixed Table"].includes(field.fieldtype)) {
						field.table_columns = sanitizeTableColumns(field.table_columns || []);
						field.table_rows = (field.table_rows || []).map((row, index) =>
							normalizeTableRow(row, index));
						field.table_data = syncTableDataWithColumns(
							field.table_data || [],
							[],
							field.table_columns || [],
							field.fieldtype === "Mixed Table" ? (field.table_rows || []) : []
						);
					}
					this.sections = sanitizeBuilderSections(this.sections);
					this.markDirty();
					return this._getField(fieldId);
				}
			}
			return null;
		},
		_getField(fieldId) {
			for (const section of this.sections) {
				for (const column of section.columns) {
					const field = column.items.find((item) => item.id === fieldId);
					if (field) return field;
				}
			}
			return null;
		},
		addLibraryItem(payload, target = {}) {
			if (payload.kind === "layout-section") {
				return this.createSection(payload.fieldtype || "Section Break");
			}
			if (payload.kind === "layout-column") {
				return this.createColumn(target.sectionId || this.sections.at(-1)?.id || this.createSection().id);
			}
			if (!this.sections.length) {
				this.createSection("Section Break");
			}
			const section = target.sectionId
				? this.sections.find((item) => item.id === target.sectionId)
				: (this.sections.find((item) => item.id === this.activeBuilderTabId) || this.sections.at(-1));
			const column = target.columnId
				? section?.columns.find((item) => item.id === target.columnId)
				: section?.columns.at(-1);
			if (!column) return null;
			return this.createField(column.id, payload.fieldtype || "Data", null, {});
		},
		async loadTemplate(templateName) {
			if (!templateName) return;
			try {
				const message = await getCachedTemplateSchema(templateName);
				if (!message) {
					throw new Error(t("Unable to load form."));
				}
				this.sections = hydrateSections(message.schema || {});
				if (!this.sections.length) this.sections = [buildUniqueSection([], "Tab Break", "Details")];
				this.currentTemplate = buildTemplateState({
					name: templateName,
					form_name: message.form_name || templateName,
					form_type: message.form_type || "Form",
					target_doctype: message.target_doctype || "",
					loaded_doctype: message.target_doctype || "",
					description: message.description || "",
					version: message.version || 0,
					base_form_name: message.base_form_name || message.form_name || templateName,
					version_label: message.version_label || DEFAULT_TEMPLATE_VERSION_LABEL,
					version_group: message.version_group || "",
					source_template: message.source_template || "",
					is_latest_version: message.is_latest_version ?? 0,
					is_active: message.is_active ?? 1,
				});
				this.setClean();
				this.activeBuilderTabId = this.sections.find((section) => section.item_type === "Tab Break")?.id || null;
				this.previewTabIndex = 0;
				this._register();
				this.clearSelection();
			} catch (error) {
				notifyError(error?.message || t("Unable to load form."));
			}
		},
		async loadDoctype(doctypeName) {
			if (!doctypeName) return;
			try {
				const { message } = await frappe.call({
					method: "ampower_form_builder.api.get_doctype_fields",
					args: { doctype_name: doctypeName },
				});
				const nextFormType = this.currentTemplate.form_type === "Doctype Integration"
					? "Doctype Integration"
					: "Form";
				this.sections = buildSectionsFromDoctype(message || {});
				if (!this.sections.length) this.sections = [buildUniqueSection([], "Tab Break", "Details")];
				this.currentTemplate = buildTemplateState({
					form_name: message.title || message.doctype || doctypeName,
					form_type: nextFormType,
					target_doctype: nextFormType === "Doctype Integration" ? doctypeName : "",
					loaded_doctype: doctypeName,
					description: this.currentTemplate.description || "",
					version: 0,
					base_form_name: message.title || message.doctype || doctypeName,
					is_active: 1,
				});
				this.setClean("doctype_loaded");
				this.isSaving = false;
				this.activeBuilderTabId = this.sections.find((section) => section.item_type === "Tab Break")?.id || null;
				this.previewTabIndex = 0;
				this.preview = { open: false };
				this._register();
				this.clearSelection();
				notify(t("DocType form loaded successfully"), "green");
			} catch (error) {
				notifyError(error?.message || t("Unable to load DocType form."));
			}
		},
		applyAiDraft(payload = {}) {
			const source = clone(payload.schema || payload || {});
			const draft = {
				sections: Array.isArray(source.sections) ? source.sections : [],
				form_name: source.form_name || payload.form_name || "",
				description: source.description || payload.description || "",
			};

			this.sections = hydrateSections(draft);
			if (!this.sections.length) {
				this.sections = [buildUniqueSection([], "Tab Break", "Details")];
			}
			this.currentTemplate = buildTemplateState({
				form_name: draft.form_name || "",
				form_type: "Form",
				description: draft.description || "",
				base_form_name: draft.form_name || "",
				version: 0,
				is_active: 1,
			});
			this.setDirty("ai_draft_applied");
			this.isSaving = false;
			this.activeBuilderTabId = this.sections.find((section) => section.item_type === "Tab Break")?.id || null;
			this.previewTabIndex = 0;
			this.preview = { open: false };
			this.clearSelection();
			this._register();
			return this.sections;
		},
		buildSchema() {
			this.sections = sanitizeBuilderSections(this.sections);
			const fields = buildFlatFieldArray(this.sections);
			const seen = new Set();
			const errors = [];
			getConfigurableFields(this.sections).forEach((field) => {
				errors.push(...validateFieldDefinition(field, seen));
			});
			if (!this.currentTemplate.form_name?.trim()) {
				errors.push("Form title is required.");
			}
			if (errors.length) {
				const message = [...new Set(errors)].join("<br>");
				notifyError(message);
				throw new Error(message);
			}
			return {
				version: 1,
				form_name: this.currentTemplate.form_name,
				description: this.currentTemplate.description || "",
				fields,
				sections: sanitizeSectionsForSchema(this.sections),
			};
		},
		createVersionDraft(payload = {}) {
			const baseFormName = payload.base_form_name
				|| this.currentTemplate.base_form_name
				|| this.currentTemplate.form_name
				|| "";
			const targetDoctype = payload.target_doctype !== undefined
				? payload.target_doctype
				: (this.currentTemplate.target_doctype || "");

			this.currentTemplate = buildTemplateState({
				form_name: payload.form_name || "",
				form_type: payload.form_type || this.currentTemplate.form_type || "Form",
				target_doctype: targetDoctype,
				loaded_doctype: this.currentTemplate.loaded_doctype || targetDoctype || "",
				description: payload.description ?? this.currentTemplate.description ?? "",
				base_form_name: baseFormName,
				version_label: payload.version_label || payload.next_version_label || DEFAULT_TEMPLATE_VERSION_LABEL,
				version_group: payload.version_group || this.currentTemplate.version_group || "",
				source_template: payload.source_template || this.currentTemplate.name || this.currentTemplate.source_template || "",
				is_latest_version: 1,
				is_active: 1,
			});
			this.preview = { open: false };
			this.previewTabIndex = 0;
			this.isSaving = false;
			this.setDirty("template_version_created");
			this._register();
			return this.currentTemplate;
		},
		createDuplicatedDraft(sourceTemplate = {}, payload = {}) {
			this.sections = hydrateSections(sourceTemplate.schema || {});
			if (!this.sections.length) {
				this.sections = [buildUniqueSection([], "Tab Break", "Details")];
			}

			const targetDoctype = payload.target_doctype !== undefined
				? payload.target_doctype
				: (sourceTemplate.target_doctype || "");
			const formType = payload.form_type || sourceTemplate.form_type || "Form";
			const formName = payload.form_name || "";
			const baseFormName = payload.base_form_name
				|| formName
				|| sourceTemplate.base_form_name
				|| sourceTemplate.form_name
				|| "";

			this.currentTemplate = buildTemplateState({
				form_name: formName,
				form_type: formType,
				target_doctype: targetDoctype,
				loaded_doctype: targetDoctype || "",
				description: payload.description ?? sourceTemplate.description ?? "",
				base_form_name: baseFormName,
				version_label: payload.version_label || DEFAULT_TEMPLATE_VERSION_LABEL,
				version_group: payload.version_group || "",
				source_template: payload.source_template || "",
				is_latest_version: 1,
				is_active: payload.is_active ?? 1,
			});
			this.isSaving = false;
			this.activeBuilderTabId = this.sections.find((section) => section.item_type === "Tab Break")?.id || null;
			this.preview = { open: false };
			this.previewTabIndex = 0;
			this.clearSelection();
			this.setDirty(payload.dirtyReason || "template_duplicated");
			this._register();
			return this.currentTemplate;
		},
		async saveTemplate() {
			if (this.isSaving) return null;
			const schema = this.buildSchema();
			const previousTemplateName = this.currentTemplate.name || "";
			this.isSaving = true;
			window.frappe?.dom?.freeze?.(t("Saving form..."));
			try {
				if (
					this.currentTemplate.form_type === "Doctype Integration"
					&& !this.currentTemplate.target_doctype
					&& this.currentTemplate.loaded_doctype
				) {
					this.currentTemplate.target_doctype = this.currentTemplate.loaded_doctype;
				}
				const { message } = await frappe.call({
					method: "ampower_form_builder.api.save_form_template",
					args: {
						template_name: this.currentTemplate.name || "",
						form_name: this.currentTemplate.form_name,
						description: this.currentTemplate.description || "",
						is_active: this.currentTemplate.is_active ?? 1,
						form_type: this.currentTemplate.form_type || "Form",
						target_doctype: this.currentTemplate.target_doctype || "",
						base_form_name: this.currentTemplate.base_form_name || this.currentTemplate.form_name,
						version_label: this.currentTemplate.version_label || DEFAULT_TEMPLATE_VERSION_LABEL,
						version_group: this.currentTemplate.version_group || "",
						source_template: this.currentTemplate.source_template || "",
						schema_json: JSON.stringify(schema),
					},
				});
				this.currentTemplate.name = message.name || this.currentTemplate.form_name;
				this.currentTemplate.form_name = message.form_name || this.currentTemplate.form_name;
				this.currentTemplate.form_type = message.form_type || this.currentTemplate.form_type || "Form";
				this.currentTemplate.target_doctype = message.target_doctype || "";
				this.currentTemplate.loaded_doctype = this.currentTemplate.loaded_doctype || this.currentTemplate.target_doctype || "";
				this.currentTemplate.description = message.description ?? this.currentTemplate.description;
				this.currentTemplate.base_form_name = message.base_form_name || this.currentTemplate.base_form_name || this.currentTemplate.form_name;
				this.currentTemplate.version_label = message.version_label || this.currentTemplate.version_label || DEFAULT_TEMPLATE_VERSION_LABEL;
				this.currentTemplate.version_group = message.version_group || this.currentTemplate.version_group || "";
				this.currentTemplate.source_template = message.source_template || this.currentTemplate.source_template || "";
				this.currentTemplate.is_latest_version = message.is_latest_version ?? this.currentTemplate.is_latest_version;
				this.currentTemplate.is_active = message.is_active ?? this.currentTemplate.is_active;
				this.currentTemplate.version = message.version || this.currentTemplate.version;
				invalidateTemplateSchemaCache(previousTemplateName);
				invalidateTemplateSchemaCache(this.currentTemplate.name);
				this.setClean("template_saved");
				notify(t("Form saved successfully"), "green");
				return message;
			} catch (error) {
				notifyError(error?.message || t("Unable to save form."));
				throw error;
			} finally {
				window.frappe?.dom?.unfreeze?.();
				this.isSaving = false;
			}
		},
		syncTreeFromDOM(type, payload = {}) {
			const {
				fromIndex = -1,
				toIndex = -1,
				fromContainerId = null,
				toContainerId = null,
			} = payload || {};
			if (fromIndex < 0 || toIndex < 0) return;

			const moveWithin = (items) => {
				if (!Array.isArray(items) || fromIndex >= items.length || toIndex > items.length) return false;
				if (fromIndex === toIndex) return false;
				const [item] = items.splice(fromIndex, 1);
				if (!item) return false;
				items.splice(toIndex, 0, item);
				return true;
			};

			const moveAcross = (fromItems, toItems) => {
				if (!Array.isArray(fromItems) || !Array.isArray(toItems)) return false;
				if (fromIndex >= fromItems.length || toIndex > toItems.length) return false;
				const [item] = fromItems.splice(fromIndex, 1);
				if (!item) return false;
				toItems.splice(toIndex, 0, item);
				return true;
			};

			let changed = false;
			if (type === "section") {
				changed = moveWithin(this.sections);
			} else if (type === "column") {
				const fromSection = this.sections.find((item) => item.id === fromContainerId);
				const toSection = this.sections.find((item) => item.id === toContainerId);
				if (!fromSection || !toSection) return;
				changed = fromContainerId === toContainerId
					? moveWithin(toSection.columns)
					: moveAcross(fromSection.columns, toSection.columns);
				if (changed && fromContainerId !== toContainerId) {
					(toSection.columns || []).forEach((column) => {
						column.section_id = toSection.id;
					});
					(fromSection.columns || []).forEach((column) => {
						column.section_id = fromSection.id;
					});
				}
			} else if (type === "field") {
				const fromSection = this.sections.find((item) =>
					item.columns.some((column) => column.id === fromContainerId)
				);
				const toSection = this.sections.find((item) =>
					item.columns.some((column) => column.id === toContainerId)
				);
				const fromColumn = fromSection?.columns.find((item) => item.id === fromContainerId);
				const toColumn = toSection?.columns.find((item) => item.id === toContainerId);
				if (!fromColumn || !toColumn) return;
				changed = fromContainerId === toContainerId
					? moveWithin(toColumn.items)
					: moveAcross(fromColumn.items, toColumn.items);
			}

			if (!changed) return;
			if (this.activeBuilderTabId && !this.sections.some((section) => section.id === this.activeBuilderTabId)) {
				this.activeBuilderTabId = this.sections.find((section) => section.item_type === "Tab Break")?.id || null;
			}
			this.markDirty(`${type}_moved`);
		},
		openPreview() {
			this.preview.open = true;
		},
		closePreview() {
			this.preview.open = false;
		},
		setPreviewTab(index) {
			this.previewTabIndex = index;
		},
		addTableColumn(fieldId, columnDef = null) {
			const field = this._getField(fieldId);
			if (!field) return null;
			const previousColumns = clone(field.table_columns || []);
			field.table_columns = previousColumns.concat([
				normalizeTableColumn(columnDef || buildDefaultTableColumn(previousColumns.length), previousColumns.length),
			]);
			field.table_data = syncTableDataWithColumns(
				field.table_data || [],
				previousColumns,
				field.table_columns,
				field.fieldtype === "Mixed Table" ? (field.table_rows || []) : []
			);
			this.markDirty();
			return field.table_columns.at(-1);
		},
		setTableColumns(fieldId, columns = []) {
			const field = this._getField(fieldId);
			if (!field) return [];
			const previousColumns = clone(field.table_columns || []);
			field.table_columns = (columns || []).map((column, index) => normalizeTableColumn(column, index));
			field.table_data = syncTableDataWithColumns(
				field.table_data || [],
				previousColumns,
				field.table_columns,
				field.fieldtype === "Mixed Table" ? (field.table_rows || []) : []
			);
			this.markDirty();
			return field.table_columns;
		},
		setTableRows(fieldId, rows = []) {
			const field = this._getField(fieldId);
			if (!field) return [];
			field.table_rows = (rows || []).map((row, index) => normalizeTableRow(row, index));
			field.table_data = syncTableDataWithColumns(
				field.table_data || [],
				field.table_columns || [],
				field.table_columns || [],
				field.fieldtype === "Mixed Table" ? field.table_rows : []
			);
			this.markDirty();
			return field.table_rows;
		},
		removeTableColumn(fieldId, columnIndex) {
			const field = this._getField(fieldId);
			if (!field?.table_columns) return;
			const nextColumns = clone(field.table_columns);
			nextColumns.splice(columnIndex, 1);
			field.table_data = syncTableDataWithColumns(
				field.table_data || [],
				field.table_columns,
				nextColumns,
				field.fieldtype === "Mixed Table" ? (field.table_rows || []) : []
			);
			field.table_columns = nextColumns;
			this.markDirty();
		},
		updateTableColumn(fieldId, columnIndex, updates) {
			const field = this._getField(fieldId);
			if (!field?.table_columns?.[columnIndex]) return;
			const previousColumns = clone(field.table_columns);
			const nextColumns = clone(field.table_columns);
			Object.assign(nextColumns[columnIndex], clone(updates));
			field.table_columns = nextColumns.map((column, index) => normalizeTableColumn(column, index));
			field.table_data = syncTableDataWithColumns(
				field.table_data || [],
				previousColumns,
				field.table_columns,
				field.fieldtype === "Mixed Table" ? (field.table_rows || []) : []
			);
			this.markDirty();
		},
		validateTableField(field) {
			return validateTableColumns(field.table_columns || []);
		},
		addTableRow(fieldId) {
			const field = this._getField(fieldId);
			if (!field || !["Table", "Mixed Table"].includes(field.fieldtype)) return null;
			field.table_data = Array.isArray(field.table_data) ? field.table_data : [];
			if (field.fieldtype === "Mixed Table" && Array.isArray(field.table_rows) && field.table_rows.length) {
				const nextRows = clone(field.table_rows).concat([
					normalizeTableRow(buildDefaultTableRow(field.table_rows.length), field.table_rows.length),
				]);
				field.table_rows = nextRows;
				field.table_data = syncTableDataWithColumns(
					field.table_data,
					field.table_columns || [],
					field.table_columns || [],
					nextRows
				);
			} else {
				field.table_data.push(buildEmptyTableRow(field.table_columns || []));
			}
			this.markDirty();
			return field.table_data.at(-1);
		},
		removeTableRow(fieldId, rowIndex) {
			const field = this._getField(fieldId);
			if (!field || !Array.isArray(field.table_data)) return;
			if (field.fieldtype === "Mixed Table" && Array.isArray(field.table_rows) && field.table_rows.length) {
				const nextRows = clone(field.table_rows);
				nextRows.splice(rowIndex, 1);
				field.table_rows = nextRows;
				field.table_data = syncTableDataWithColumns(
					field.table_data,
					field.table_columns || [],
					field.table_columns || [],
					nextRows
				);
			} else {
				field.table_data.splice(rowIndex, 1);
			}
			this.markDirty();
		},
		updateTableCell(fieldId, { rowIndex, fieldname, value }) {
			const field = this._getField(fieldId);
			if (!field) return;
			field.table_data = Array.isArray(field.table_data) ? field.table_data : [];
			field.table_data[rowIndex] = field.table_data[rowIndex] || {};
			field.table_data[rowIndex][fieldname] = value;
			this.markDirty();
		},
	},
});
