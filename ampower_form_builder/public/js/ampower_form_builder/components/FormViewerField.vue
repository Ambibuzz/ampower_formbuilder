<template>
	<div
		v-show="isVisible"
		class="fv-field-container"
		:class="{ 'fv-display-field': isDisplayField }"
		:data-fieldname="field.fieldname"
	>
		<template v-if="field.fieldtype === 'Heading'">
			<div class="fv-heading-block">
				<h3 class="fv-heading-title">{{ field.label || __("Heading") }}</h3>
				<p v-if="field.description" class="fv-heading-description">{{ field.description }}</p>
			</div>
		</template>

		<template v-else-if="field.fieldtype === 'HTML'">
			<div class="fv-html-block" v-html="field.options || field.default || field.description || ''" />
		</template>

		<template v-else>
			<label :class="{ reqd: field.reqd }">{{ field.label || field.fieldname }}</label>
			<div v-if="field.description" class="fv-field-description">{{ field.description }}</div>

			<TableRenderer
				v-if="isTableField"
				:field-type="field.fieldtype"
				:columns="tableConfig.columns"
				:row-definitions="tableConfig.rows"
				:initial-data="normalizedTableRows"
				:is-editable="!(field.read_only || isReadOnly)"
				:row-title="tableConfig.table_row_title || field.table_row_title || ''"
				@add-row="emit('update:value', addTableRow(field, normalizedTableRows))"
				@delete-row="handleDeleteRow"
				@delete-selected-rows="handleDeleteSelectedRows"
				@duplicate-row="handleDuplicateRow"
				@reorder-row="handleReorderRow"
				@update-cell="handleUpdateCell"
			/>

			<div v-else-if="isUploadField" class="fv-upload-block">
				<div v-if="value" class="fv-upload-preview" :class="{ 'has-image-preview': showsImagePreview }">
					<img
						v-if="showsImagePreview"
						class="fv-upload-preview-image"
						:src="value"
						:alt="field.label || field.fieldname || __('Uploaded image')"
					>
					<div class="fv-upload-preview-meta">
						<a class="fv-upload-preview-link" :href="value" target="_blank" rel="noopener noreferrer">
							{{ value }}
						</a>
						<button
							v-if="!(field.read_only || isReadOnly)"
							type="button"
							class="btn btn-xs btn-link text-danger"
							@click="emit('update:value', '')"
						>
							{{ __("Clear") }}
						</button>
					</div>
				</div>
				<div v-else class="fv-upload-empty">
					{{ isImageField ? __("No image selected") : __("No file selected") }}
				</div>
				<div v-if="!(field.read_only || isReadOnly)" class="fv-upload-actions">
					<button type="button" class="btn btn-sm btn-secondary" @click="openUploader">
						{{ value ? (isImageField ? __("Change Image") : __("Change File")) : (isImageField ? __("Upload Image") : __("Upload File")) }}
					</button>
				</div>
			</div>

			<div v-else-if="field.fieldtype === 'Radio'" class="radio-list">
				<label v-for="option in radioOptions" :key="option" class="radio-option">
					<input
						type="radio"
						:name="field.fieldname || field.id"
						:value="option"
						:checked="value === option"
						:disabled="Boolean(field.read_only || isReadOnly)"
						@change="emit('update:value', option)"
					>
					<span>{{ option }}</span>
				</label>
				<div v-if="!radioOptions.length" class="text-muted">{{ __("No options configured") }}</div>
			</div>

			<div v-else-if="field.fieldtype === 'Number'" class="fv-field-input">
				<input
					class="form-control"
					type="number"
					:step="numberStep"
					:value="value ?? ''"
					:readonly="Boolean(field.read_only || field.formula || isReadOnly)"
					@input="emit('update:value', $event.target.value)"
				>
			</div>

			<div v-else-if="field.fieldtype === 'Data'" class="fv-field-input">
				<input
					class="form-control"
					type="text"
					:value="value ?? ''"
					:placeholder="field.placeholder || field.label || field.fieldname"
					:readonly="Boolean(field.read_only || field.formula || isReadOnly)"
					@input="emit('update:value', $event.target.value)"
				>
			</div>

			<div v-else-if="field.fieldtype === 'Text Editor'" class="fv-field-input">
				<TextEditorControl
					:df="controlDf"
					:model-value="value ?? ''"
					:read_only="Boolean(field.read_only || field.formula || isReadOnly)"
					@update:modelValue="emit('update:value', $event)"
				/>
			</div>

			<div v-else-if="isTextareaField" class="fv-field-input">
				<textarea
					class="form-control"
					:value="value ?? ''"
					:placeholder="field.placeholder || field.label || field.fieldname"
					:readonly="Boolean(field.read_only || field.formula || isReadOnly)"
					@input="emit('update:value', $event.target.value)"
				/>
			</div>

			<div v-else-if="usesLinkControl" class="fv-field-input">
				<LinkControl
					:df="controlDf"
					:model-value="value ?? ''"
					:read_only="Boolean(field.read_only || field.formula || isReadOnly)"
					:no_label="true"
					@update:modelValue="emit('update:value', $event)"
				/>
			</div>

			<div v-else-if="field.fieldtype === 'Select'" class="fv-field-input">
				<select
					class="form-control"
					:value="value ?? ''"
					:disabled="Boolean(field.read_only || field.formula || isReadOnly)"
					@change="emit('update:value', $event.target.value)"
				>
					<option value=""></option>
					<option v-for="option in selectOptions" :key="option" :value="option">{{ option }}</option>
				</select>
			</div>

			<div v-else class="fv-field-input">
				<GenericFieldControl
					:df="controlDf"
					:model-value="value"
					:read_only="Boolean(field.read_only || field.formula || isReadOnly)"
					@update:modelValue="emit('update:value', $event)"
				/>
			</div>
		</template>
	</div>
</template>

<script setup>
import { computed, watch } from "vue";
import TableRenderer from "./TableRenderer.vue";
import GenericFieldControl from "./controls/GenericFieldControl.vue";
import TextEditorControl from "./controls/TextEditorControl.vue";
import LinkControl from "./controls/LinkControl.vue";
import {
	addTableRow,
	buildViewerControlDf,
	getFieldInputStep,
	getOptionsList,
	getTableConfig,
	normalizeTableCellValue,
	normalizeTableValue,
	syncTableFetchColumns,
	syncTableFormulaColumns,
	VIEWER_UPLOAD_FIELD_TYPES,
} from "../viewerUtils.js";

const props = defineProps({
	field: { type: Object, required: true },
	value: { type: [String, Number, Array, Object, Boolean], default: "" },
	isVisible: { type: Boolean, default: true },
	isReadOnly: { type: Boolean, default: false },
});

const emit = defineEmits(["update:value"]);

const isDisplayField = computed(() => ["HTML", "Heading"].includes(props.field.fieldtype));
const isTableField = computed(() => ["Table", "Mixed Table"].includes(props.field.fieldtype));
const isUploadField = computed(() => VIEWER_UPLOAD_FIELD_TYPES.includes(props.field.fieldtype));
const isTextareaField = computed(() => ['Small Text', 'Text', 'Long Text'].includes(props.field.fieldtype));
const isImageField = computed(() => ["Attach Image", "Image"].includes(props.field.fieldtype));
const showsImagePreview = computed(() => isImageField.value || props.field.fieldtype === "Signature");
const tableConfig = computed(() => getTableConfig(props.field));
const normalizedTableRows = computed(() => normalizeTableValue(props.field, props.value));
const radioOptions = computed(() => getOptionsList(props.field.options));
const selectOptions = computed(() => getOptionsList(props.field.options));
const numberStep = computed(() => getFieldInputStep(props.field));
const usesLinkControl = computed(() => ["Link", "Dynamic Link"].includes(props.field.fieldtype));
const controlDf = computed(() => buildViewerControlDf(props.field, {
	read_only: Boolean(props.field.read_only || props.field.formula || props.isReadOnly),
}));
let tableSyncToken = 0;

function reportFieldError(title, error, fallbackMessage) {
	console.error(title, error);
	if (window.frappe?.show_alert) {
		window.frappe.show_alert({
			message: error?.message || fallbackMessage || title,
			indicator: "red",
		});
	}
}

function openUploader() {
	new frappe.ui.FileUploader({
		restrictions: getUploadRestrictions(),
		on_success: (file) => emit("update:value", file.file_url || ""),
	});
}

function getUploadRestrictions() {
	if (props.field.fieldtype === "Signature") {
		return { allowed_file_types: ["image/*"] };
	}
	if (isImageField.value) {
		return { allowed_file_types: ["image/*"] };
	}
	const fileTypes = getOptionsList(props.field.options);
	return fileTypes.length ? { allowed_file_types: fileTypes } : undefined;
}

function handleDeleteRow(rowIndex) {
	const rows = [...normalizedTableRows.value];
	rows.splice(rowIndex, 1);
	emit("update:value", rows);
}

function handleDeleteSelectedRows(rowIndexes) {
	if (!Array.isArray(rowIndexes) || !rowIndexes.length) return;
	const indexes = [...rowIndexes].sort((left, right) => right - left);
	const rows = [...normalizedTableRows.value];
	indexes.forEach((rowIndex) => {
		if (rowIndex >= 0 && rowIndex < rows.length) {
			rows.splice(rowIndex, 1);
		}
	});
	emit("update:value", rows);
}

function handleDuplicateRow(rowIndex) {
	const rows = normalizedTableRows.value.map((row) => ({ ...row }));
	if (!rows[rowIndex]) return;
	rows.splice(rowIndex + 1, 0, { ...rows[rowIndex] });
	emit("update:value", rows);
}

function handleReorderRow({ fromIndex, toIndex }) {
	if (fromIndex === toIndex) return;
	const rows = normalizedTableRows.value.map((row) => ({ ...row }));
	const [movedRow] = rows.splice(fromIndex, 1);
	if (!movedRow) return;
	rows.splice(toIndex, 0, movedRow);
	emit("update:value", rows);
}

function handleUpdateCell({ rowIndex, fieldname, value }) {
	const rows = normalizedTableRows.value.map((row) => ({ ...row }));
	if (!rows[rowIndex]) return;
	const column = tableConfig.value.columns.find((item) => item.fieldname === fieldname);
	if (!column) return;

	rows[rowIndex][fieldname] = normalizeTableCellValue(column, value);
	emit("update:value", rows);
	syncTableRow(tableConfig.value.columns, rows, rowIndex)
		.then((nextRows) => {
			if (JSON.stringify(nextRows) !== JSON.stringify(rows)) {
				emit("update:value", nextRows);
			}
		})
		.catch((error) => {
			reportFieldError("Ampower table sync failed", error, __("Unable to update table row."));
		});
}

async function syncTableRow(columns, rows, rowIndex) {
	const nextRows = rows.map((row) => ({ ...row }));
	const row = await syncTableFetchColumns(
		columns,
		nextRows[rowIndex] || {},
		(error) => reportFieldError("Ampower table fetch_from failed", error, __("Unable to fetch table value."))
	);

	nextRows[rowIndex] = syncTableFormulaColumns(columns, row);
	return nextRows;
}

async function syncAllTableRows(rows = normalizedTableRows.value) {
	if (!isTableField.value) return;

	const syncToken = ++tableSyncToken;
	let nextRows = rows.map((row) => ({ ...row }));

	for (let rowIndex = 0; rowIndex < nextRows.length; rowIndex += 1) {
		nextRows = await syncTableRow(tableConfig.value.columns, nextRows, rowIndex);
		if (syncToken !== tableSyncToken) {
			return;
		}
	}

	if (syncToken !== tableSyncToken) return;
	if (JSON.stringify(nextRows) !== JSON.stringify(rows)) {
		emit("update:value", nextRows);
	}
}

watch(
	() => [props.field, props.value],
	() => {
		if (!isTableField.value) return;
		syncAllTableRows();
	},
	{ deep: true, immediate: true }
);
</script>
