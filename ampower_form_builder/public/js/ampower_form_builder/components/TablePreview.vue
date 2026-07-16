<template>
	<div class="table-preview">
		<div class="table-preview-header">
			<span class="afb-type-badge">{{ fieldType }}</span>
			<span class="afb-type-badge">{{ `${columns.length} columns` }}</span>
			<span v-if="fieldType === 'Mixed Table'" class="afb-type-badge">{{ `${rowDefinitions.length} rows` }}</span>
		</div>
		<div v-if="!columns.length" class="table-preview-empty">No columns configured</div>
		<TableRenderer
			v-else
			:field-type="fieldType"
			:columns="columns"
			:row-definitions="rowDefinitions"
			:initial-data="previewRows"
			:row-title="rowTitle"
		/>
	</div>
</template>

<script setup>
import { computed } from "vue";
import TableRenderer from "./TableRenderer.vue";

const props = defineProps({
	fieldType: { type: String, default: "Table" },
	columns: { type: Array, default: () => [] },
	rowDefinitions: { type: Array, default: () => [] },
	initialData: { type: Array, default: () => [] },
	rowTitle: { type: String, default: "" },
});

const rows = computed(() => Array.isArray(props.initialData) ? props.initialData : []);
const previewRows = computed(() => {
	if (rows.value.length) return rows.value;

	if (props.fieldType === "Mixed Table") {
		const labels = props.rowDefinitions?.length ? props.rowDefinitions : Array.from({ length: 3 }, (_, index) => ({ label: `${index + 1}` }));
		return labels.map((rowDef, rowIndex) => {
			const row = { id: `preview_row_${rowIndex}`, _preview: true };
			(props.columns || []).forEach((column, columnIndex) => {
				row[column.fieldname] = buildPreviewValue(column, rowIndex, columnIndex, rowDef.label);
			});
			return row;
		});
	}

	return Array.from({ length: 3 }, (_, rowIndex) => {
		const row = { id: `preview_row_${rowIndex}`, _preview: true };
		(props.columns || []).forEach((column, columnIndex) => {
			row[column.fieldname] = buildPreviewValue(column, rowIndex, columnIndex);
		});
		return row;
	});
});

function buildPreviewValue(column, rowIndex, columnIndex, rowLabel = "") {
	if (column.fieldtype === "Color") {
		const palette = ["#2490ef", "#16a34a", "#f59e0b", "#ef4444", "#8b5cf6", "#14b8a6"];
		return palette[(rowIndex + columnIndex) % palette.length];
	}
	if (column.fieldtype === "Check") return rowIndex % 2 === 0;
	if (column.fieldtype === "Number") return String(rowIndex + 1);
	if (["Number", "Percent"].includes(column.fieldtype)) return `${rowIndex + 1}.00`;
	if (column.fieldtype === "Date") return "2026-04-22";
	if (column.fieldtype === "Datetime") return "2026-04-22T10:30";
	if (column.fieldtype === "Time") return "10:30";
	if (column.fieldtype === "Select") {
		return String(column.options || "")
			.split(/\n|,/)
			.map((item) => item.trim())
			.filter(Boolean)[0] || "";
	}
	if (column.fieldtype === "Link") return rowLabel ? `${rowLabel}` : `Item ${rowIndex + 1}`;
	return rowLabel ? `${rowLabel}-${columnIndex + 1}` : `Sample ${rowIndex + 1}`;
}
</script>

<style scoped>
.table-preview {
	display: grid;
	gap: 10px;
}

.table-preview-header {
	display: flex;
	gap: 8px;
	flex-wrap: wrap;
}

.table-preview-empty {
	padding: 16px;
	border: 1px dashed var(--border-color);
	border-radius: 12px;
	background: var(--subtle-fg);
	color: var(--text-muted);
	text-align: center;
	font-size: 12px;
}
</style>
