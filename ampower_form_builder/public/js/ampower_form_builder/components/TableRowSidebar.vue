<template>
	<div
		v-if="rowIndex !== null"
		class="fv-row-sidebar-backdrop"
		style="position: fixed; inset: 56px 0 0 0; background: rgba(15, 23, 42, 0.14); z-index: 40;"
		@click.self="$emit('close')"
	>
		<aside
			class="fv-row-sidebar bg-white d-flex flex-column"
			style="position: absolute; top: 0; right: 0; width: min(400px, calc(100vw - 12px)); height: calc(100vh - 56px); border-left: 1px solid #e5e7eb;"
			aria-label="Expanded row editor"
		>
			<div
				class="fv-row-sidebar-header bg-white"
				style="display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; padding: 8px 8px 6px;"
			>
				<div class="fv-row-sidebar-heading" style="flex: 1; min-width: 0;">
					<h4 class="fv-row-sidebar-title mb-0" style="font-size: 14px; font-weight: 600; line-height: 1.2;">
						{{ title }}
					</h4>
				</div>
				<div class="fv-row-sidebar-nav" style="display: flex; align-items: center; gap: 4px; flex-wrap: wrap; margin-left: auto;">
					<button
						v-if="isEditable"
						type="button"
						class="btn btn-default btn-sm"
						:title="__('Duplicate')"
						aria-label="Duplicate Row"
						style="display: inline-flex; align-items: center; justify-content: center; min-height: 26px; padding: 2px 8px;"
						@click="$emit('duplicate-row')"
					>
						<svg class="es-icon es-line icon-xs" aria-hidden="true">
							<use href="#icon-duplicate"></use>
						</svg>
					</button>
					<button
						v-if="isEditable"
						type="button"
						class="btn btn-default btn-sm text-danger"
						:title="__('Delete')"
						aria-label="Delete Row"
						style="display: inline-flex; align-items: center; justify-content: center; min-height: 26px; padding: 2px 8px;"
						@click="$emit('delete-row')"
					>
						<svg class="icon icon-sm" aria-hidden="true">
							<use href="#icon-delete"></use>
						</svg>
					</button>
					<button
						v-if="canAddRows"
						type="button"
						class="btn btn-default btn-sm"
						:title="__('Add Row')"
						aria-label="Add Row"
						style="display: inline-flex; align-items: center; justify-content: center; min-height: 26px; padding: 2px 8px;"
						@click="$emit('add-row')"
					>
						<svg class="es-icon es-line icon-xs" aria-hidden="true">
							<use href="#icon-add"></use>
						</svg>
					</button>
					<button
						type="button"
						class="btn btn-default btn-sm"
						:title="__('Previous')"
						aria-label="Previous Row"
						style="display: inline-flex; align-items: center; justify-content: center; min-height: 26px; padding: 2px 8px;"
						:disabled="!canGoPrevious"
						@click="$emit('previous')"
					>
						<svg class="es-icon es-line icon-xs" aria-hidden="true">
							<use href="#icon-left"></use>
						</svg>
					</button>
					<button
						type="button"
						class="btn btn-default btn-sm"
						:title="__('Next')"
						aria-label="Next Row"
						style="display: inline-flex; align-items: center; justify-content: center; min-height: 26px; padding: 2px 8px;"
						:disabled="!canGoNext"
						@click="$emit('next')"
					>
						<svg class="es-icon es-line icon-xs" aria-hidden="true">
							<use href="#icon-right"></use>
						</svg>
					</button>
				</div>
				<button type="button" class="btn btn-default btn-sm d-inline-flex align-items-center justify-content-center" :title="__('Close')" style="min-height: 26px; padding: 2px 8px;" @click="$emit('close')">
					<svg class="es-icon es-line icon-xs" aria-hidden="true">
						<use href="#icon-close"></use>
					</svg>
				</button>
			</div>

			<div class="fv-row-sidebar-body flex-grow-1 overflow-auto" style="padding: 4px 8px 8px;">
				<div
					v-for="column in columns"
					:key="`expanded_${rowIndex}_${column.fieldname}`"
					class="fv-row-sidebar-field"
					style="margin: 0 0 6px;"
				>
					<label class="fv-row-sidebar-label d-inline-block" style="margin: 0 0 2px; font-size: 12px; font-weight: 600; line-height: 1.25; color: #425466;" :class="{ reqd: column.reqd }">
						{{ column.label || prettifyFieldname(column.fieldname) }}
					</label>
					<div v-if="column.description" class="fv-row-sidebar-help text-muted" style="margin: 0 0 2px; font-size: 11px; line-height: 1.25;">
						{{ column.description }}
					</div>
					<div class="fv-row-sidebar-input" :class="{ 'fv-row-sidebar-link-input': isLinkType(column) }">
						<LinkControl
							v-if="isLinkType(column)"
							:key="`link_${rowIndex}_${column.fieldname}`"
							:df="getControlDf(column)"
							:model-value="localRow[column.fieldname] ?? ''"
							:read_only="!isEditable || Boolean(column.formula)"
							:no_label="true"
							@update:modelValue="emitLinkFieldUpdate(column.fieldname, $event)"
						/>
						<select
							v-else-if="column.fieldtype === 'Select'"
							class="form-control"
							style="min-height: 26px; padding: 1px 6px; margin: 0; font-size: 12px; line-height: 1.2;"
							:value="localRow[column.fieldname] ?? ''"
							:disabled="!isEditable || Boolean(column.formula)"
							@change="emitFieldUpdate(column.fieldname, $event.target.value)"
						>
							<option value=""></option>
							<option v-for="option in getSelectOptions(column)" :key="option" :value="option">{{ option }}</option>
						</select>
						<label
							v-else-if="column.fieldtype === 'Check'"
							class="d-flex align-items-center"
							style="gap: 6px; margin: 0; min-height: 26px;"
						>
							<input
								type="checkbox"
								:checked="Boolean(localRow[column.fieldname])"
								:disabled="!isEditable || Boolean(column.formula)"
								@change="emitFieldUpdate(column.fieldname, $event.target.checked)"
							>
							<span style="font-size: 12px; line-height: 1.2;">{{ Boolean(localRow[column.fieldname]) ? __("Yes") : __("No") }}</span>
						</label>
						<textarea
							v-else-if="isTextareaType(column)"
							class="form-control"
							style="min-height: 56px; padding: 4px 6px; margin: 0; font-size: 12px; line-height: 1.3; resize: vertical;"
							:value="localRow[column.fieldname] ?? ''"
							:placeholder="getPlaceholder(column)"
							:readonly="!isEditable || Boolean(column.formula)"
							@input="emitFieldUpdate(column.fieldname, $event.target.value)"
						/>
						<input
							v-else-if="getNativeInputType(column)"
							class="form-control"
							style="min-height: 26px; padding: 1px 6px; margin: 0; font-size: 12px; line-height: 1.2;"
							:type="getNativeInputType(column)"
							:step="getNativeInputStep(column)"
							:value="getNativeInputValue(column, localRow[column.fieldname])"
							:placeholder="getNativeInputPlaceholder(column)"
							:readonly="!isEditable || Boolean(column.formula)"
							@input="emitFieldUpdate(column.fieldname, normalizeNativeInputValue(column, $event.target.value))"
						>
						<GenericFieldControl
							v-else-if="usesGenericFieldControl(column)"
							:df="getControlDf(column)"
							:model-value="localRow[column.fieldname] ?? ''"
							:read_only="!isEditable || Boolean(column.formula)"
							:compact="true"
							@update:modelValue="emitFieldUpdate(column.fieldname, $event)"
						/>
						<input
							v-else
							class="form-control"
							style="min-height: 26px; padding: 1px 6px; margin: 0; font-size: 12px; line-height: 1.2;"
							type="text"
							:value="localRow[column.fieldname] ?? ''"
							:placeholder="getPlaceholder(column)"
							:readonly="!isEditable || Boolean(column.formula)"
							@input="emitFieldUpdate(column.fieldname, $event.target.value)"
						>
					</div>
				</div>
			</div>
		</aside>
	</div>
</template>

<script setup>
import { computed, reactive, watch } from "vue";
import GenericFieldControl from "./controls/GenericFieldControl.vue";
import LinkControl from "./controls/LinkControl.vue";
import { buildViewerControlDf, getFieldInputStep, getFieldPlaceholder, getOptionsList, prettifyFieldname } from "../viewerUtils.js";

const props = defineProps({
	fieldType: { type: String, default: "Table" },
	columns: { type: Array, default: () => [] },
	rowDefinitions: { type: Array, default: () => [] },
	row: { type: Object, default: null },
	rowIndex: { type: Number, default: null },
	isEditable: { type: Boolean, default: false },
	canAddRows: { type: Boolean, default: false },
	canGoPrevious: { type: Boolean, default: false },
	canGoNext: { type: Boolean, default: false },
});

const emit = defineEmits(["close", "add-row", "duplicate-row", "delete-row", "previous", "next", "update-field"]);
const localRow = reactive({});

const title = computed(() => {
	if (props.rowIndex === null) return "";
	const rowNumber = props.rowIndex + 1;
	if (props.fieldType === "Mixed Table") {
		return props.rowDefinitions[props.rowIndex]?.label || `${__("Row")} ${rowNumber}`;
	}
	return `${__("Row")} ${rowNumber}`;
});

function emitFieldUpdate(fieldname, value) {
	if (!props.isEditable) return;
	localRow[fieldname] = value;
	emit("update-field", { fieldname, value });
}

function emitLinkFieldUpdate(fieldname, value) {
	if (!props.isEditable) return;
	localRow[fieldname] = value;
	emit("update-field", { fieldname, value });
}

function isLinkType(column) {
	return ["Link", "Dynamic Link"].includes(column?.fieldtype);
}

function isNumberType(column) {
	return ["Number", "Percent"].includes(column?.fieldtype);
}

function getNativeInputType(column) {
	if (isNumberType(column)) return "number";
	return "";
}

function getNativeInputStep(column) {
	return isNumberType(column) ? getInputStep(column) : undefined;
}

function getNativeInputValue(column, value) {
	const raw = String(value || "").trim();
	return raw;
}

function normalizeNativeInputValue(column, value) {
	return String(value || "").trim();
}

function getNativeInputPlaceholder(column) {
	return getPlaceholder(column);
}

function usesGenericFieldControl(column) {
	return ["Attach Image", "Date", "Datetime", "Time", "Color"].includes(column?.fieldtype);
}

function isTextareaType(column) {
	return ["Small Text", "Text"].includes(column?.fieldtype);
}

function getPlaceholder(column) {
	return getFieldPlaceholder(column);
}

function getInputStep(column) {
	return getFieldInputStep(column);
}

function getSelectOptions(column) {
	return getOptionsList(column?.options);
}

function getControlDf(column) {
	return buildViewerControlDf(column, {
		read_only: !props.isEditable || Boolean(column?.formula),
	});
}

watch(
	() => props.rowIndex,
	() => {
		Object.keys(localRow).forEach((key) => delete localRow[key]);
		Object.assign(localRow, props.row || {});
	},
	{ immediate: true }
);

watch(
	() => props.row,
	(nextRow) => {
		Object.keys(localRow).forEach((key) => {
			if (!nextRow || !Object.prototype.hasOwnProperty.call(nextRow, key)) {
				delete localRow[key];
			}
		});
		if (!nextRow) return;
		Object.entries(nextRow).forEach(([key, value]) => {
			if (localRow[key] !== value) {
				localRow[key] = value;
			}
		});
	}
);
</script>

<style scoped>
.fv-row-sidebar-link-input :deep(.control-label),
.fv-row-sidebar-link-input :deep(.label),
.fv-row-sidebar-link-input :deep(label[data-fieldtype]) {
	display: none !important;
}

.fv-row-sidebar-link-input :deep(.frappe-control),
.fv-row-sidebar-link-input :deep(.control-input-wrapper),
.fv-row-sidebar-link-input :deep(.link-field) {
	margin: 0 !important;
	padding: 0 !important;
}

.fv-row-sidebar-link-input :deep(input),
.fv-row-sidebar-link-input :deep(.form-control) {
	min-height: 26px;
	padding: 1px 6px;
	margin: 0;
	font-size: 12px;
	line-height: 1.2;
}
</style>
