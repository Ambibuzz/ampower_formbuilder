<template>
	<div class=" afb-form-grid-container">
		<div class="afb-form-grid" :class="{ 'is-mixed-table': fieldType === 'Mixed Table', 'is-editable-table': canMutateRows }">
			<div class="afb-grid-heading-row fv-table-header-row">
				<div class=" afb-grid-row">
					<div class="data-row afb-data-row row fv-table-row">
						<div v-if="canSelectRows" class="row-check sortable-handle col fv-row-check-col">
							<input
								type="checkbox"
								class="grid-row-check"
								:checked="allVisibleRowsSelected"
								:indeterminate.prop="someVisibleRowsSelected && !allVisibleRowsSelected"
								:title="__('Select visible rows')"
								@change="toggleSelectVisibleRows($event.target.checked)"
							>
						</div>
						<div v-if="hasRowDetail" class="col fv-table-action-col fv-table-action-col-mobile"></div>
						<div class="row-index afb-row-index sortable-handle col fv-row-label-col">
							<span :class="{ 'fv-mixed-table-label': fieldType === 'Mixed Table' }">{{ getRowHeaderLabel() }}</span>
						</div>
						<div
							v-for="column in displayedColumns"
							:key="column.id || column.fieldname"
							class="grid-static-col afb-grid-static-col col fv-table-col"
							:data-fieldtype="column.fieldtype"
						>
							<div class="static-area ellipsis">
								{{ column.label || prettifyFieldname(column.fieldname) }}
								<span v-if="column.reqd" class="text-danger">*</span>
							</div>
						</div>
						<div v-if="hasRowDetail" class="col fv-table-action-col fv-table-action-col-desktop"></div>
					</div>
				</div>
			</div>

			<div class=" afb-grid-body fv-table-body">
				<div v-if="!columns.length" class=" afb-grid-empty text-center">Add at least one column to start the table.</div>
				<div v-else-if="!rows.length" class="grid-empty afb-grid-empty text-center">
					{{ fieldType === "Mixed Table" ? "No configured rows." : "No rows yet." }}
				</div>
				<div v-else class="rows">
					<div
						v-for="rowEntry in paginatedRows"
						:key="rowDefinitions[rowEntry.rowIndex]?.key || rowEntry.row.id || rowEntry.rowIndex"
						class="afb-grid-row"
						:class="{ 'is-drag-target': dragOverRowIndex === rowEntry.rowIndex, 'is-selected-row': isRowSelected(rowEntry.rowIndex) }"
						@dragover.prevent="handleRowDragOver(rowEntry.rowIndex)"
						@drop.prevent="handleRowDrop(rowEntry.rowIndex)"
					>
						<div
							class="afb-data-row row fv-table-row"
							:class="{ 'editable-row': isEditable, 'is-dragging-row': draggingRowIndex === rowEntry.rowIndex }"
						>
							<div v-if="canSelectRows" class="row-check sortable-handle col fv-row-check-col">
								<input
									type="checkbox"
									class="grid-row-check"
									:checked="isRowSelected(rowEntry.rowIndex)"
									:title="__('Select row')"
									@change="toggleRowSelection(rowEntry.rowIndex, $event.target.checked)"
								>
							</div>
							<div v-if="hasRowDetail" class="fv-table-action-col fv-table-action-col-mobile">
								<div class="fv-row-actions">
									<button
										class="fv-row-action-trigger"
										type="button"
										:title="__('View')"
										aria-label="View Row"
										@click="openExpandedRow(rowEntry.rowIndex)"
									>
										<svg class="es-icon es-line icon-sm" aria-hidden="true">
											<use href="#icon-view"></use>
										</svg>
									</button>
								</div>
							</div>
							<div
								class=" afb-row-index sortable-handle col fv-row-label-col"
								:draggable="canDragRows"
								:title="canDragRows ? __('Drag to reorder row') : null"
								@dragstart="handleRowDragStart(rowEntry.rowIndex, $event)"
								@dragend="handleRowDragEnd"
							>
								<span :class="{ 'fv-mixed-table-label': fieldType === 'Mixed Table' }">{{ getRowDisplayLabel(rowEntry.rowIndex) }}</span>
							</div>
							<div
								v-for="column in displayedColumns"
								:key="`${rowEntry.row.id || rowEntry.rowIndex}_${column.fieldname}`"
								class="grid-static-col afb-grid-static-col col fv-table-col"
								:data-fieldtype="column.fieldtype"
								:data-label="column.label || prettifyFieldname(column.fieldname)"
							>
								<TableCell
									:column="column"
									:value="rowEntry.row[column.fieldname]"
									:is-editable="isEditable"
									@update="$emit('update-cell', { rowIndex: rowEntry.rowIndex, fieldname: column.fieldname, value: $event })"
								/>
							</div>
							<div v-if="hasRowDetail" class="fv-table-action-col fv-table-action-col-desktop">
								<div class="fv-row-actions">
									<button
										class="fv-row-action-trigger"
										type="button"
										:title="__('View')"
										aria-label="View Row"
										@click="openExpandedRow(rowEntry.rowIndex)"
									>
										<svg class="es-icon es-line icon-sm" aria-hidden="true">
											<use href="#icon-view"></use>
										</svg>
									</button>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>

			<div class="fv-table-toolbar" v-if="pageCount > 1">
				<div v-if="pageCount > 1" class="fv-table-pagination">
					<button
						type="button"
						class="btn btn-xs btn-secondary"
						:disabled="currentPage === 1"
						@click="goToPage(currentPage - 1)"
					>
						{{ __('Previous') }}
					</button>
					<div class="fv-table-pagination-status">
						{{ __('Page {0} of {1}', [currentPage, pageCount]) }}
					</div>
					<button
						type="button"
						class="btn btn-xs btn-secondary"
						:disabled="currentPage === pageCount"
						@click="goToPage(currentPage + 1)"
					>
						{{ __('Next') }}
					</button>
				</div>
			</div>

			<div v-if="canMutateRows" class="small form-clickable-section afb-grid-footer">
				<div class="fv-grid-footer-actions">
					<div class="grid-buttons afb-grid-buttons">
						<button
							type="button"
							class="btn btn-xs btn-secondary grid-add-row afb-grid-add-row"
							:title="__('Add Row')"
							:disabled="!columns.length"
							@click="$emit('add-row')"
						>
							{{ __('Add Row') }}
						</button>
						<button
							v-if="hasSelectedRows"
							type="button"
							class="btn btn-xs btn-danger"
							:title="__('Delete Selected Rows')"
							@click="deleteSelectedRows"
						>
							{{ __('Delete Selected') }}
						</button>
					</div>
				</div>
			</div>
		</div>

		<TableRowSidebar
			:field-type="fieldType"
			:columns="columns"
			:row-definitions="rowDefinitions"
			:row="expandedRow"
			:row-index="expandedRowIndex"
			:is-editable="isEditable"
			:can-add-rows="canMutateRows && columns.length > 0"
			:can-go-previous="hasPreviousExpandedRow"
			:can-go-next="hasNextExpandedRow"
			@add-row="handleSidebarAddRow"
			@close="closeExpandedRow"
			@delete-row="handleDeleteRow(expandedRowIndex)"
			@duplicate-row="handleDuplicateRow(expandedRowIndex)"
			@previous="goToExpandedRow(expandedRowIndex - 1)"
			@next="goToExpandedRow(expandedRowIndex + 1)"
			@update-field="updateExpandedRowField"
		/>
	</div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import TableCell from "./TableCell.vue";
import TableRowSidebar from "./TableRowSidebar.vue";

const props = defineProps({
	fieldType: { type: String, default: "Table" },
	columns: { type: Array, default: () => [] },
	rowDefinitions: { type: Array, default: () => [] },
	initialData: { type: Array, default: () => [] },
	isEditable: { type: Boolean, default: false },
	rowTitle: { type: String, default: "" },
});

const emit = defineEmits(["add-row", "delete-row", "delete-selected-rows", "duplicate-row", "update-cell", "reorder-row"]);

const MAX_VISIBLE_COLUMNS = 8;
const MAX_MOBILE_PREVIEW_COLUMNS = 3;
const PAGE_SIZE = 15;
const rows = computed(() => Array.isArray(props.initialData) ? props.initialData : []);
const visibleColumns = computed(() => props.columns.slice(0, MAX_VISIBLE_COLUMNS));
const isMobileView = ref(false);
const displayedColumns = computed(() => isMobileView.value
	? visibleColumns.value.slice(0, MAX_MOBILE_PREVIEW_COLUMNS)
	: visibleColumns.value);
const canMutateRows = computed(() => props.isEditable && props.fieldType !== "Mixed Table");
const canSelectRows = computed(() => canMutateRows.value && rows.value.length > 0);
const canDragRows = computed(() => canMutateRows.value && rows.value.length > 1);
const hasRowDetail = computed(() => props.columns.length > 0);
const expandedRowIndex = ref(null);
const shouldFocusNewRow = ref(false);
const currentPage = ref(1);
const draggingRowIndex = ref(null);
const dragOverRowIndex = ref(null);
const selectedRowIndexes = ref([]);
const pageCount = computed(() => Math.max(1, Math.ceil(rows.value.length / PAGE_SIZE)));
const paginatedRows = computed(() => {
	const start = (currentPage.value - 1) * PAGE_SIZE;
	return rows.value.slice(start, start + PAGE_SIZE).map((row, offset) => ({
		row,
		rowIndex: start + offset,
	}));
});
const visibleRowIndexes = computed(() => paginatedRows.value.map((entry) => entry.rowIndex));
const hasSelectedRows = computed(() => selectedRowIndexes.value.length > 0);
const allVisibleRowsSelected = computed(() => visibleRowIndexes.value.length > 0
	&& visibleRowIndexes.value.every((rowIndex) => selectedRowIndexes.value.includes(rowIndex)));
const someVisibleRowsSelected = computed(() => visibleRowIndexes.value.some((rowIndex) => selectedRowIndexes.value.includes(rowIndex)));
const expandedRow = computed(() => {
	if (expandedRowIndex.value === null) return null;
	return rows.value[expandedRowIndex.value] || null;
});
const hasPreviousExpandedRow = computed(() => expandedRowIndex.value !== null && expandedRowIndex.value > 0);
const hasNextExpandedRow = computed(() => expandedRowIndex.value !== null && expandedRowIndex.value < rows.value.length - 1);

function openExpandedRow(rowIndex) {
	expandedRowIndex.value = rowIndex;
}

function closeExpandedRow() {
	expandedRowIndex.value = null;
}

function updateExpandedRowField({ fieldname, value }) {
	if (expandedRowIndex.value === null) return;
	emit("update-cell", { rowIndex: expandedRowIndex.value, fieldname, value });
}

function handleSidebarAddRow() {
	shouldFocusNewRow.value = true;
	emit("add-row");
}

function goToExpandedRow(rowIndex) {
	if (rowIndex < 0 || rowIndex >= rows.value.length) return;
	expandedRowIndex.value = rowIndex;
}

function goToPage(pageNumber) {
	if (pageNumber < 1 || pageNumber > pageCount.value) return;
	currentPage.value = pageNumber;
}

function isRowSelected(rowIndex) {
	return selectedRowIndexes.value.includes(rowIndex);
}

function toggleRowSelection(rowIndex, checked) {
	const next = new Set(selectedRowIndexes.value);
	if (checked) {
		next.add(rowIndex);
	} else {
		next.delete(rowIndex);
	}
	selectedRowIndexes.value = Array.from(next).sort((left, right) => left - right);
}

function toggleSelectVisibleRows(checked) {
	const next = new Set(selectedRowIndexes.value);
	visibleRowIndexes.value.forEach((rowIndex) => {
		if (checked) {
			next.add(rowIndex);
		} else {
			next.delete(rowIndex);
		}
	});
	selectedRowIndexes.value = Array.from(next).sort((left, right) => left - right);
}

function deleteSelectedRows() {
	if (!selectedRowIndexes.value.length) return;
	const indexes = [...selectedRowIndexes.value].sort((left, right) => left - right);
	selectedRowIndexes.value = [];
	closeExpandedRow();
	emit("delete-selected-rows", indexes);
}

function handleRowDragStart(rowIndex, event) {
	if (!canDragRows.value) return;
	draggingRowIndex.value = rowIndex;
	dragOverRowIndex.value = rowIndex;
	if (event?.dataTransfer) {
		event.dataTransfer.effectAllowed = "move";
		event.dataTransfer.setData("text/plain", String(rowIndex));
	}
}

function handleRowDragOver(rowIndex) {
	if (!canDragRows.value || draggingRowIndex.value === null) return;
	dragOverRowIndex.value = rowIndex;
}

function remapSelectionAfterReorder(fromIndex, toIndex) {
	selectedRowIndexes.value = selectedRowIndexes.value.map((rowIndex) => {
		if (rowIndex === fromIndex) return toIndex;
		if (fromIndex < toIndex && rowIndex > fromIndex && rowIndex <= toIndex) return rowIndex - 1;
		if (fromIndex > toIndex && rowIndex >= toIndex && rowIndex < fromIndex) return rowIndex + 1;
		return rowIndex;
	}).sort((left, right) => left - right);
}

function handleRowDrop(targetRowIndex) {
	if (!canDragRows.value || draggingRowIndex.value === null) return;
	const fromIndex = draggingRowIndex.value;
	resetDragState();
	if (fromIndex === targetRowIndex) return;
	remapSelectionAfterReorder(fromIndex, targetRowIndex);
	emit("reorder-row", { fromIndex, toIndex: targetRowIndex });
	if (expandedRowIndex.value === fromIndex) {
		expandedRowIndex.value = targetRowIndex;
	} else if (expandedRowIndex.value !== null) {
		if (fromIndex < expandedRowIndex.value && targetRowIndex >= expandedRowIndex.value) {
			expandedRowIndex.value -= 1;
		} else if (fromIndex > expandedRowIndex.value && targetRowIndex <= expandedRowIndex.value) {
			expandedRowIndex.value += 1;
		}
	}
}

function handleRowDragEnd() {
	resetDragState();
}

function resetDragState() {
	draggingRowIndex.value = null;
	dragOverRowIndex.value = null;
}

function handleDuplicateRow(rowIndex) {
	if (rowIndex === null || rowIndex === undefined) return;
	selectedRowIndexes.value = selectedRowIndexes.value.map((selectedIndex) => selectedIndex > rowIndex ? selectedIndex + 1 : selectedIndex);
	emit("duplicate-row", rowIndex);
}

function handleDeleteRow(rowIndex) {
	if (rowIndex === null || rowIndex === undefined) return;
	selectedRowIndexes.value = selectedRowIndexes.value
		.filter((selectedIndex) => selectedIndex !== rowIndex)
		.map((selectedIndex) => selectedIndex > rowIndex ? selectedIndex - 1 : selectedIndex);
	if (expandedRowIndex.value === rowIndex) {
		closeExpandedRow();
	} else if (expandedRowIndex.value !== null && expandedRowIndex.value > rowIndex) {
		expandedRowIndex.value -= 1;
	}
	emit("delete-row", rowIndex);
}

function prettifyFieldname(value) {
	return String(value || "")
		.replace(/_/g, " ")
		.replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function getRowHeaderLabel() {
	return props.fieldType === "Mixed Table" ? (props.rowTitle || __("Row")) : "No.";
}

function getRowDisplayLabel(rowIndex) {
	if (props.fieldType === "Mixed Table") {
		return props.rowDefinitions[rowIndex]?.label || rowIndex + 1;
	}
	return rowIndex + 1;
}

function updateViewportState() {
	if (typeof window === "undefined") return;
	isMobileView.value = window.innerWidth <= 768;
}

watch(
	() => rows.value.length,
	(nextLength, previousLength) => {
		selectedRowIndexes.value = selectedRowIndexes.value.filter((rowIndex) => rowIndex < nextLength);
		if (currentPage.value > pageCount.value) {
			currentPage.value = pageCount.value;
		}
		if (!shouldFocusNewRow.value) return;
		if (nextLength <= previousLength) return;
		currentPage.value = pageCount.value;
		expandedRowIndex.value = nextLength - 1;
		shouldFocusNewRow.value = false;
	}
);

onMounted(() => {
	updateViewportState();
	window.addEventListener("resize", updateViewportState);
});

onBeforeUnmount(() => {
	if (typeof window === "undefined") return;
	window.removeEventListener("resize", updateViewportState);
});
</script>

<style scoped>
.fv-mixed-table-label {
	font-weight: 700;
}

.fv-row-check-col {
	flex: 0 0 40px;
	width: 40px;
	min-width: 40px;
	max-width: 40px;
	display: flex;
	align-items: center;
	justify-content: center;
	padding: 0 6px !important;
}

.fv-row-check-col .grid-row-check {
	margin: 0;
}

.is-selected-row .fv-table-row {
	background: rgba(59, 130, 246, 0.06);
}

.fv-table-toolbar {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 12px;
	padding: 0.5rem 0.75rem;
	border-top: 1px solid var(--table-border-color);
	background: var(--subtle-fg);
}


.fv-grid-footer-actions {
	display: flex;
	align-items: center;
	justify-content: space-between;
}

.fv-grid-footer-actions .afb-grid-buttons {
	display: flex;
	align-items: center;
	gap: 0.5rem;
}
</style>
