<template>
	<div class="table-column-editor">
		<div v-if="!localColumns.length" class="table-column-empty">No columns added yet.</div>
		<div ref="root" class="table-column-list">
			<div v-for="(column, index) in localColumns" :key="column.id || index" class="table-column-card">
				<div class="table-column-card-header">
					<div class="table-column-card-summary">
						<button class="btn-reset table-column-handle" type="button" title="Drag to reorder">::</button>
						<button class="btn-reset table-column-toggle" type="button" @click="toggleColumn(column.id || index)">
							<div class="table-column-title-wrap">
								<div class="table-column-title">{{ column.label || `Column ${index + 1}` }}</div>
								<div class="table-column-meta">{{ column.fieldtype || "Data" }}</div>
							</div>
							<span class="table-column-chevron">{{ isOpen(column.id || index) ? "−" : "+" }}</span>
						</button>
					</div>
					<button class="btn-reset afb-delete-icon" type="button" @click="removeColumn(index)">✕</button>
				</div>
				<div v-if="isOpen(column.id || index)" class="table-column-card-body">
					<label class="table-column-field">
						<span class="table-column-label">Label</span>
						<input
							v-model="column.label"
							class="form-control"
							placeholder="Label"
							@input="updateLabel(index)"
						>
					</label>
					<label class="table-column-field">
						<span class="table-column-label">Fieldname</span>
						<input
							v-model="column.fieldname"
							class="form-control"
							placeholder="fieldname"
							@input="updateFieldname(index)"
						>
					</label>
					<label class="table-column-field">
						<span class="table-column-label">Field Type</span>
						<select v-model="column.fieldtype" class="form-control" @change="updateColumn(index, { fieldtype: column.fieldtype })">
							<option v-for="item in fieldTypes" :key="item.fieldtype" :value="item.fieldtype">{{ item.label }}</option>
						</select>
					</label>
					<label v-if="column.fieldtype === 'Select'" class="table-column-field">
						<span class="table-column-label">Options</span>
						<textarea
							v-model="column.options"
							class="form-control"
							rows="3"
							placeholder="Options, one per line"
							@input="updateColumn(index, { options: column.options })"
						></textarea>
					</label>
					<div v-if="column.fieldtype === 'Link'" class="table-column-field">
						<span class="table-column-label">DocType</span>
						<LinkControl
							:df="buildDoctypeField(index)"
							:model-value="column._doctype"
							@update:modelValue="updateColumn(index, { _doctype: $event || '', options: $event || '' })"
						/>
					</div>
					<div v-if="showFetchFrom(column)" class="table-column-field">
						<span class="table-column-label">Fetch From</span>
						<FetchFromControl
							:df="fetchFromDf"
							:model-value="column.fetch_from"
							:source-fields="localColumns"
							:exclude-fieldname="column.fieldname"
							@update:modelValue="updateColumn(index, { fetch_from: $event || '' })"
						/>
					</div>
					<label v-if="showFormula(column)" class="table-column-field">
						<span class="table-column-label">Calculation</span>
						<input
							v-model="column.formula"
							class="form-control"
							placeholder="qty * rate"
							@input="updateColumn(index, { formula: column.formula })"
						>
					</label>
					<label v-if="['Number', 'Percent'].includes(column.fieldtype)" class="table-column-field">
						<span class="table-column-label">Precision</span>
						<input
							v-model="column.precision"
							class="form-control"
							type="number"
							min="0"
							placeholder="Precision"
							@input="updateColumn(index, { precision: column.precision })"
						>
					</label>
					<div v-if="errors[index]?.length" class="table-column-errors">
						<div v-for="error in errors[index]" :key="error">{{ error }}</div>
					</div>
				</div>
			</div>
		</div>
		<div class="table-column-editor-actions">
			<button class="btn btn-default btn-xs" type="button" @click="addColumn">Add Column</button>
		</div>
	</div>
</template>

<script setup>
import Sortable from "sortablejs";
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import {
	TABLE_COLUMN_FIELD_TYPES,
	buildDefaultTableColumn,
	clone,
	normalizeFieldname,
	normalizeTableColumn,
	validateFieldname,
} from "../utils.js";
import FetchFromControl from "./controls/FetchFromControl.vue";
import LinkControl from "./controls/LinkControl.vue";

const props = defineProps({
	modelValue: { type: Array, default: () => [] },
});

const emit = defineEmits(["update:modelValue"]);

const root = ref(null);
const localColumns = reactive([]);
const openItems = ref([]);
let sortable = null;

const fieldTypes = computed(() => TABLE_COLUMN_FIELD_TYPES.map((fieldtype) => ({ fieldtype, label: fieldtype })));
const fetchFromDf = computed(() => ({
	fieldtype: "Data",
	label: "Fetch From",
}));

const errors = computed(() => localColumns.map((column) => {
	const columnErrors = [];
	const validation = validateFieldname(column.fieldname);
	if (!validation.valid) columnErrors.push(validation.message);
	if (localColumns.filter((item) => item.fieldname === column.fieldname).length > 1) {
		columnErrors.push("Fieldname must be unique within the table.");
	}
	if (column.fieldtype === "Select" && !String(column.options || "").trim()) {
		columnErrors.push("Select columns require options.");
	}
	if (column.formula && !/^[\d\s+\-*/%().,_a-zA-Z]+$/.test(String(column.formula).trim())) {
		columnErrors.push("Formula supports only fieldnames, numbers, parentheses, and basic math operators.");
	}
	return columnErrors;
}));

function syncLocal(value) {
	localColumns.splice(0, localColumns.length, ...(value || []).map((column, index) => normalizeTableColumn(column, index)));
	const availableIds = localColumns.map((column, index) => column.id || index);
	openItems.value = openItems.value.filter((id) => availableIds.includes(id));
	if (!openItems.value.length && availableIds.length) {
		openItems.value = [availableIds[0]];
	}
}

watch(() => props.modelValue, syncLocal, { deep: true, immediate: true });

function emitColumns() {
	emit("update:modelValue", clone(localColumns));
}

function updateColumn(index, updates) {
	Object.assign(localColumns[index], updates);
	emitColumns();
}

function updateLabel(index) {
	const column = localColumns[index];
	if (!column._manualFieldname) {
		column.fieldname = normalizeFieldname(column.label, `column_${index + 1}`);
	}
	emitColumns();
}

function updateFieldname(index) {
	localColumns[index]._manualFieldname = true;
	localColumns[index].fieldname = normalizeFieldname(localColumns[index].fieldname, `column_${index + 1}`);
	emitColumns();
}

function addColumn() {
	localColumns.push(buildDefaultTableColumn(localColumns.length));
	const newColumn = localColumns.at(-1);
	openItems.value = [...openItems.value, newColumn.id];
	emitColumns();
	nextTick(initSortable);
}

function removeColumn(index) {
	const removedId = localColumns[index]?.id || index;
	localColumns.splice(index, 1);
	openItems.value = openItems.value.filter((id) => id !== removedId);
	emitColumns();
}

function buildDoctypeField(index) {
	return {
		fieldtype: "Link",
		fieldname: `table_column_doctype_${index}`,
		label: "DocType",
		options: "DocType",
		placeholder: "Select DocType",
	};
}

function showFetchFrom(column) {
	return !["Check"].includes(column.fieldtype);
}

function showFormula(column) {
	return !["Link", "Dynamic Link", "Date", "Datetime", "Time", "Check"].includes(column.fieldtype);
}

function isOpen(id) {
	return openItems.value.includes(id);
}

function toggleColumn(id) {
	openItems.value = isOpen(id)
		? openItems.value.filter((item) => item !== id)
		: [...openItems.value, id];
}

function initSortable() {
	sortable?.destroy();
	if (!root.value) return;
	sortable = new Sortable(root.value, {
		handle: ".table-column-handle",
		animation: 150,
		onEnd(event) {
			const [moved] = localColumns.splice(event.oldIndex, 1);
			localColumns.splice(event.newIndex, 0, moved);
			emitColumns();
		},
	});
}

onMounted(initSortable);
onBeforeUnmount(() => sortable?.destroy());
</script>

<style scoped>
.table-column-editor {
	display: grid;
	gap: 10px;
}

.table-column-list {
	display: grid;
	gap: 10px;
}

.table-column-card {
	border: 1px solid rgba(0, 0, 0, 0.08);
	border-radius: 12px;
	background: #fff;
	overflow: hidden;
}

.table-column-card-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 8px;
	padding: 10px 12px;
	background: rgba(248, 250, 252, 0.9);
}

.table-column-card-summary {
	display: flex;
	align-items: center;
	gap: 8px;
	flex: 1;
	min-width: 0;
}

.table-column-handle {
	flex: 0 0 auto;
	cursor: grab;
	color: var(--text-muted);
	font-weight: 700;
}

.table-column-toggle {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 12px;
	flex: 1;
	min-width: 0;
	text-align: left;
}

.table-column-title-wrap {
	min-width: 0;
}

.table-column-title {
	font-weight: 600;
	color: var(--text-color);
}

.table-column-meta {
	font-size: 12px;
	color: var(--text-muted);
}

.table-column-chevron {
	font-size: 20px;
	line-height: 1;
	color: var(--text-muted);
}

.table-column-card-body {
	display: grid;
	gap: 10px;
	padding: 12px;
	border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.table-column-field {
	display: grid;
	gap: 4px;
	margin: 0;
}

.table-column-label {
	font-size: 12px;
	font-weight: 600;
	color: var(--text-muted);
}

.table-column-errors {
	display: grid;
	gap: 4px;
	padding: 8px 10px;
	border-radius: 8px;
	background: rgba(220, 38, 38, 0.08);
	color: #b91c1c;
	font-size: 12px;
}

.table-column-editor-actions {
	display: flex;
	justify-content: flex-end;
}
</style>
