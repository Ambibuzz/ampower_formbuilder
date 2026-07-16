<template>
	<div class="afb-field-properties">
		<label class="form-group">
			<span>Label</span>
			<input v-model="form.label" class="form-control" @input="onLabelInput">
		</label>
		<label class="form-group">
			<span>Fieldname</span>
			<input v-model="form.fieldname" class="form-control" @input="emitChange('fieldname', form.fieldname)" @blur="validateFieldnameValue">
		</label>
		<label class="form-group">
			<span>Field Type</span>
			<select v-model="form.fieldtype" class="form-control table-type-select" @change="onFieldTypeChange">
				<option v-for="item in fieldTypes" :key="item.fieldtype" :value="item.fieldtype">{{ item.label }}</option>
			</select>
		</label>
		<label class="form-group">
			<span>Description</span>
			<textarea v-model="form.description" class="form-control" rows="2" @input="emitChange('description', form.description)"></textarea>
		</label>
		<label v-if="caps.placeholder" class="form-group">
			<span>Placeholder</span>
			<input v-model="form.placeholder" class="form-control" @input="emitChange('placeholder', form.placeholder)">
		</label>
		<label v-if="caps.defaultValue" class="form-group">
			<span>Default</span>
			<input v-model="form.default" class="form-control" @input="emitChange('default', form.default)">
		</label>
		<label class="form-group">
			<span>Depends On</span>
			<input v-model="form.depends_on" class="form-control" @input="emitChange('depends_on', form.depends_on)">
		</label>
		<div v-if="showFetchFrom" class="form-group">
			<FetchFromControl
				:df="fetchFromDf"
				:model-value="form.fetch_from"
				:source-fields="availableFetchFields"
				:exclude-fieldname="form.fieldname"
				@update:modelValue="updateFetchFrom"
			/>
		</div>
		<label v-if="showCalculation" class="form-group">
			<span>Calculation</span>
			<input
				v-model="form.formula"
				class="form-control"
				placeholder="f1 + f2"
				@input="emitChange('formula', form.formula)"
			>
		</label>
		<label v-if="caps.options" class="form-group">
			<span>Options</span>
			<textarea v-model="form.options" class="form-control" rows="4" @input="emitChange('options', form.options)"></textarea>
		</label>
		<div v-if="caps.linkOptions" class="form-group">
			<LinkControl
				v-if="form.fieldtype === 'Link'"
				:df="doctypeField"
				:model-value="form._doctype"
				@update:modelValue="updateLinkOptions"
			/>
			<SelectControl
				v-else
				:df="dynamicLinkSourceField"
				:model-value="form.options"
				@update:modelValue="updateDynamicLinkOptions"
			/>
		</div>
		<label v-if="caps.precision" class="form-group">
			<span>Precision</span>
			<input v-model="form.precision" class="form-control" type="number" min="0" @input="emitChange('precision', form.precision)">
		</label>
		<div v-if="['Table', 'Mixed Table'].includes(form.fieldtype)" class="form-group afb-table-properties">
			<div class="table-config-header">
				<span>Table Configuration</span>
				<div class="table-config-badges">
					<span class="afb-type-badge">{{ form.fieldtype }}</span>
					<span class="afb-type-badge">{{ `${form.table_columns?.length || 0} columns${form.fieldtype === 'Mixed Table' ? ` / ${form.table_rows?.length || 0} rows` : ''}` }}</span>
				</div>
			</div>
			<div class="table-config-section">
				<h4>Columns</h4>
				<p class="text-muted small">Open each column card to edit its fields one by one.</p>
				<TableColumnEditor
					:model-value="form.table_columns || []"
					@update:modelValue="updateTableColumns"
				/>
			</div>
			<div v-if="form.fieldtype === 'Mixed Table'" class="table-config-section">
				<label class="form-group">
					<span>Row Heading</span>
					<input
						v-model="form.table_row_title"
						class="form-control"
						placeholder="Row"
						@input="emitChange('table_row_title', form.table_row_title)"
					>
				</label>
				<h4>Row Names</h4>
				<p class="text-muted small">Open each row card to edit its fields one by one.</p>
				<TableRowEditor
					:model-value="form.table_rows || []"
					@update:modelValue="updateTableRows"
				/>
			</div>
			<label v-if="showImageColumnProperty" class="form-group">
				<span>Image Column</span>
				<select v-model="form.image_column" class="form-control" @change="emitChange('image_column', form.image_column)">
					<option value="1">1</option>
					<option value="2">2</option>
				</select>
			</label>
		</div>
		<div class="afb-checkbox-grid">
			<label><input :checked="Boolean(form.reqd)" type="checkbox" @change="toggleFlag('reqd', $event.target.checked)"> Required</label>
			<label><input :checked="Boolean(form.read_only)" type="checkbox" @change="toggleFlag('read_only', $event.target.checked)"> Read Only</label>
			<label><input :checked="Boolean(form.hidden)" type="checkbox" @change="toggleFlag('hidden', $event.target.checked)"> Hidden</label>
		</div>
	</div>
</template>

<script setup>
import { computed, reactive, watch } from "vue";
import {
	FIELD_TYPES,
	buildDefaultTableColumn,
	buildDefaultTableRow,
	clone,
	getFieldTypeCapabilities,
	normalizeFieldname,
	validateFieldname,
} from "../utils.js";
import { useFormBuilderStore } from "../store.js";
import FetchFromControl from "./controls/FetchFromControl.vue";
import LinkControl from "./controls/LinkControl.vue";
import SelectControl from "./controls/SelectControl.vue";
import TableColumnEditor from "./TableColumnEditor.vue";
import TableRowEditor from "./TableRowEditor.vue";

const props = defineProps({
	field: { type: Object, required: true },
});

const store = useFormBuilderStore();
const form = reactive(clone(props.field));
const fieldTypes = FIELD_TYPES;
const caps = computed(() => getFieldTypeCapabilities(form.fieldtype));
const showFetchFrom = computed(() => !["Table", "Mixed Table", "HTML", "Heading", "Section Break", "Column Break", "Tab Break"].includes(form.fieldtype));
const showCalculation = computed(() => !["Table", "Mixed Table", "HTML", "Heading", "Section Break", "Column Break", "Tab Break", "Attach", "Attach Image"].includes(form.fieldtype));
const showImageColumnProperty = computed(() => ["Table", "Mixed Table"].includes(form.fieldtype)
	&& (form.table_columns || []).some((column) => column.fieldtype === "Attach Image"));
const availableFetchFields = computed(() => store.sections.flatMap((section) =>
	(section.columns || []).flatMap((column) => column.items || [])
));
const fetchFromDf = computed(() => ({
	fieldtype: "Data",
	label: "Fetch From",
}));
const doctypeField = computed(() => ({
	fieldtype: "Link",
	fieldname: "_doctype",
	label: "Options / DocType",
	options: "DocType",
	placeholder: "Select DocType",
	description: "",
	reqd: 0,
	read_only: 0,
	hidden: 0,
}));
const dynamicLinkSourceField = computed(() => ({
	fieldtype: "Select",
	fieldname: "options",
	label: "Options / Source Field",
	options: availableFetchFields.value
		.filter((item) => item.id !== props.field.id && item.fieldname)
		.map((item) => ({
			label: `${item.label || item.fieldname} (${item.fieldname})`,
			value: item.fieldname,
		})),
	description: "Dynamic Link options should point to the fieldname that stores the target DocType.",
}));
const t = window.__ || ((text) => text);

watch(() => props.field, (value) => Object.assign(form, clone(value)), { deep: true, immediate: true });

function emitChange(key, value) {
	store.updateField(props.field.id, { [key]: value });
}

function onFieldTypeChange() {
	const nextType = form.fieldtype;
	const previousType = props.field.fieldtype || "";
	const patch = { fieldtype: nextType };

	if (nextType === "Link") {
		patch._doctype = form._doctype || form.options || "";
		patch.options = patch._doctype;
	} else if (nextType === "Dynamic Link") {
		patch._doctype = "";
		patch.options = previousType === "Dynamic Link" ? (form.options || "") : "";
	} else {
		patch._doctype = "";
	}

	if (["Table", "Mixed Table"].includes(nextType)) {
		patch.table_columns = (form.table_columns && form.table_columns.length)
			? clone(form.table_columns)
			: [buildDefaultTableColumn(0)];
		patch.table_rows = nextType === "Mixed Table"
			? ((form.table_rows && form.table_rows.length) ? clone(form.table_rows) : [buildDefaultTableRow(0)])
			: [];
		patch.table_row_title = nextType === "Mixed Table" ? (form.table_row_title || "Row") : "";
		patch.image_column = form.image_column || "1";
		patch.table_data = Array.isArray(form.table_data) ? clone(form.table_data) : [];
	} else {
		patch.table_rows = [];
		patch.table_row_title = "";
		patch.image_column = "";
	}

	store.updateField(props.field.id, patch);
}

function onLabelInput() {
	if (!props.field._manualFieldname) {
		form.fieldname = normalizeFieldname(form.label, form.fieldtype || "field");
		emitChange("fieldname", form.fieldname);
	}
	emitChange("label", form.label);
}

function validateFieldnameValue() {
	const check = validateFieldname(form.fieldname);
	if (!check.valid) {
		frappe.msgprint({ title: t("Invalid Fieldname"), message: check.message, indicator: "red" });
		return;
	}
	emitChange("fieldname", form.fieldname);
}

function emitLinkOptions() {
	emitChange("_doctype", form._doctype);
	emitChange("options", form._doctype);
}

function updateLinkOptions(value) {
	form._doctype = value || "";
	emitLinkOptions();
}

function updateDynamicLinkOptions(value) {
	form.options = value || "";
	form._doctype = "";
	emitChange("options", form.options);
	emitChange("_doctype", "");
}

function updateFetchFrom(value) {
	form.fetch_from = value || "";
	emitChange("fetch_from", form.fetch_from);
}

function updateTableColumns(columns) {
	form.table_columns = clone(columns);
	store.setTableColumns(props.field.id, form.table_columns);
	const hasImageColumn = form.table_columns.some((column) => column.fieldtype === "Attach Image");
	if (hasImageColumn && !form.image_column) {
		form.image_column = "1";
		emitChange("image_column", form.image_column);
	}
	if (!hasImageColumn && form.image_column) {
		form.image_column = "";
		emitChange("image_column", "");
	}
}

function updateTableRows(rows) {
	form.table_rows = clone(rows);
	store.setTableRows(props.field.id, form.table_rows);
}

function toggleFlag(key, checked) {
	form[key] = checked ? 1 : 0;
	emitChange(key, form[key]);
}
</script>

<style scoped>
.afb-field-properties {
	display: grid;
	gap: 8px;
}

.afb-field-properties :deep(.form-group) {
	display: grid;
	gap: 4px;
	margin-bottom: 0;
}

.afb-field-properties :deep(.form-group > span) {
	margin-bottom: 0;
	font-size: 12px;
}

.afb-table-properties {
	display: grid;
	gap: 10px;
	padding: 12px;
	border: 1px solid var(--border-color);
	border-radius: var(--border-radius-md);
	background: linear-gradient(180deg, var(--subtle-fg) 0%, rgba(255, 255, 255, 0.98) 100%);
}

.table-config-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 8px;
	padding-bottom: 6px;
	border-bottom: 1px solid var(--border-color);
}

.table-config-badges {
	display: flex;
	gap: 8px;
	flex-wrap: wrap;
}

.table-config-section {
	display: grid;
	gap: 6px;
	padding: 10px;
	border: 1px solid rgba(0, 0, 0, 0.06);
	border-radius: 12px;
	background: rgba(255, 255, 255, 0.85);
}

.table-config-section h4,
.table-config-section p {
	margin: 0;
}

.table-type-select {
	font-weight: 500;
}
</style>
