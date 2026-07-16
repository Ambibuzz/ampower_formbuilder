<template>
	<div class="table-row-editor">
		<div v-if="!localRows.length" class="table-row-empty">No rows added yet.</div>
		<div class="table-row-list">
			<div v-for="(row, index) in localRows" :key="row.id || index" class="table-row-card">
				<div class="table-row-card-header">
					<button class="btn-reset table-row-toggle" type="button" @click="toggleRow(row.id || index)">
						<div class="table-row-title-wrap">
							<div class="table-row-title">{{ row.label || `Row ${index + 1}` }}</div>
							<div class="table-row-meta">{{ row.key || `row_${index + 1}` }}</div>
						</div>
						<span class="table-row-chevron">{{ isOpen(row.id || index) ? "−" : "+" }}</span>
					</button>
					<button class="btn-reset afb-delete-icon" type="button" @click="removeRow(index)">✕</button>
				</div>
				<div v-if="isOpen(row.id || index)" class="table-row-card-body">
					<label class="table-row-field">
						<span class="table-row-field-label">Row Name</span>
						<input
							v-model="row.label"
							class="form-control"
							placeholder="Enter row name"
							@input="updateLabel(index)"
						>
					</label>
					<label class="table-row-field">
						<span class="table-row-field-label">Row Key</span>
						<input
							v-model="row.key"
							class="form-control"
							placeholder="row_key"
							@input="updateKey(index)"
						>
					</label>
				</div>
			</div>
		</div>
		<div class="table-row-editor-actions">
			<button class="btn btn-default btn-xs" type="button" @click="addRow">Add Row</button>
		</div>
	</div>
</template>

<script setup>
import { reactive, ref, watch } from "vue";
import { buildDefaultTableRow, clone, normalizeFieldname, normalizeTableRow } from "../utils.js";

const props = defineProps({
	modelValue: { type: Array, default: () => [] },
});

const emit = defineEmits(["update:modelValue"]);

const localRows = reactive([]);
const openItems = ref([]);

function syncLocal(value) {
	localRows.splice(0, localRows.length, ...(value || []).map((row, index) => normalizeTableRow(row, index)));
	const availableIds = localRows.map((row, index) => row.id || index);
	openItems.value = openItems.value.filter((id) => availableIds.includes(id));
	if (!openItems.value.length && availableIds.length) {
		openItems.value = [availableIds[0]];
	}
}

watch(() => props.modelValue, syncLocal, { deep: true, immediate: true });

function emitRows() {
	emit("update:modelValue", clone(localRows));
}

function updateLabel(index) {
	const row = localRows[index];
	if (!row._manualKey) {
		row.key = normalizeFieldname(row.label, `row_${index + 1}`);
	}
	emitRows();
}

function updateKey(index) {
	localRows[index]._manualKey = true;
	localRows[index].key = normalizeFieldname(localRows[index].key, `row_${index + 1}`);
	emitRows();
}

function addRow() {
	localRows.push(buildDefaultTableRow(localRows.length));
	const newRow = localRows.at(-1);
	openItems.value = [...openItems.value, newRow.id];
	emitRows();
}

function removeRow(index) {
	const removedId = localRows[index]?.id || index;
	localRows.splice(index, 1);
	openItems.value = openItems.value.filter((id) => id !== removedId);
	emitRows();
}

function isOpen(id) {
	return openItems.value.includes(id);
}

function toggleRow(id) {
	openItems.value = isOpen(id)
		? openItems.value.filter((item) => item !== id)
		: [...openItems.value, id];
}
</script>

<style scoped>
.table-row-editor {
	display: grid;
	gap: 10px;
}

.table-row-list {
	display: grid;
	gap: 10px;
}

.table-row-card {
	border: 1px solid rgba(0, 0, 0, 0.08);
	border-radius: 12px;
	background: #fff;
	overflow: hidden;
}

.table-row-card-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 8px;
	padding: 10px 12px;
	background: rgba(248, 250, 252, 0.9);
}

.table-row-toggle {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 12px;
	flex: 1;
	min-width: 0;
	text-align: left;
}

.table-row-title-wrap {
	min-width: 0;
}

.table-row-title {
	font-weight: 600;
	color: var(--text-color);
}

.table-row-meta {
	font-size: 12px;
	color: var(--text-muted);
}

.table-row-chevron {
	font-size: 20px;
	line-height: 1;
	color: var(--text-muted);
}

.table-row-card-body {
	display: grid;
	gap: 10px;
	padding: 12px;
	border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.table-row-field {
	display: grid;
	gap: 4px;
	margin: 0;
}

.table-row-field-label {
	font-size: 12px;
	font-weight: 600;
	color: var(--text-muted);
}

.table-row-editor-actions {
	display: flex;
	justify-content: flex-end;
}
</style>
