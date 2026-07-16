<template>
	<div class="table-cell" :class="{ 'is-link-cell': isLinkField }">
		<div v-if="!isEditable" class="static-area ellipsis" :class="{ 'is-link-value': isLinkField }">
			<span v-if="column.fieldtype === 'Check'">{{ value ? "Yes" : "No" }}</span>
			<template v-else-if="column.fieldtype === 'Color' && displayValue">
				<span class="table-color-preview" :style="{ backgroundColor: displayValue }"></span>
				<span>{{ displayValue }}</span>
			</template>
			<span v-else-if="displayValue">{{ displayValue }}</span>
			<span v-else>-</span>
		</div>
		<LinkControl
			v-else-if="usesLinkControl"
			:args="{ dropdown_in_body: true, keep_visible_in_grid: true, dropdown_width: 250 }"
			:df="controlDf"
			:model-value="value ?? ''"
			:read_only="!isEditable || Boolean(column.formula)"
			:no_label="true"
			@update:modelValue="update"
		/>
		<GenericFieldControl
			v-else-if="usesFrappeControl"
			:df="controlDf"
			:model-value="controlValue"
			:read_only="!isEditable || Boolean(column.formula)"
			@update:modelValue="update"
		/>
		<input
			v-else-if="['Data', 'Small Text', 'Text'].includes(column.fieldtype)"
			class="form-control"
			type="text"
			:value="displayValue"
			:placeholder="cellPlaceholder"
			:readonly="!isEditable || Boolean(column.formula)"
			@input="update($event.target.value)"
		>
		<input
			v-else-if="column.fieldtype === 'Number'"
			class="form-control"
			type="number"
			:step="numberStep"
			:value="displayValue"
			:placeholder="cellPlaceholder"
			:readonly="!isEditable || Boolean(column.formula)"
			@input="update($event.target.value)"
		>
		<input
			v-else-if="column.fieldtype === 'Percent'"
			class="form-control"
			type="number"
			step="0.01"
			:value="displayValue"
			:placeholder="cellPlaceholder"
			:readonly="!isEditable || Boolean(column.formula)"
			@input="update($event.target.value)"
		>
		<select
			v-else-if="column.fieldtype === 'Select'"
			class="form-control"
			:value="displayValue"
			:disabled="!isEditable || Boolean(column.formula)"
			@change="update($event.target.value)"
		>
			<option value=""></option>
			<option v-for="option in selectOptions" :key="option" :value="option">{{ option }}</option>
		</select>
		<label v-else-if="column.fieldtype === 'Check'" class="afb-inline-check">
			<input
				type="checkbox"
				:checked="Boolean(value)"
				:disabled="!isEditable || Boolean(column.formula)"
				@change="update($event.target.checked)"
			>
		</label>
		<input
			v-else
			class="form-control"
			type="text"
			:value="displayValue"
			:placeholder="cellPlaceholder"
			:readonly="!isEditable || Boolean(column.formula)"
			@input="update($event.target.value)"
		>
	</div>
</template>

<script setup>
import { computed } from "vue";
import GenericFieldControl from "./controls/GenericFieldControl.vue";
import LinkControl from "./controls/LinkControl.vue";
import { buildViewerControlDf, formatSubmissionValue, getFieldInputStep, getFieldPlaceholder } from "../viewerUtils.js";

const props = defineProps({
	column: { type: Object, required: true },
	value: { type: [String, Number, Boolean], default: "" },
	isEditable: { type: Boolean, default: false },
	compact: { type: Boolean, default: false },
});

const emit = defineEmits(["update"]);

const selectOptions = computed(() => String(props.column.options || "")
	.split(/\n|,/)
	.map((item) => item.trim())
	.filter(Boolean));

const displayValue = computed(() => formatSubmissionValue(props.value, "", props.column.fieldtype));
const controlValue = computed(() => ["Date", "Datetime", "Time"].includes(props.column.fieldtype)
	? props.value
	: displayValue.value);
const isLinkField = computed(() => ["Link", "Dynamic Link"].includes(props.column.fieldtype));
const usesLinkControl = computed(() => ["Link", "Dynamic Link"].includes(props.column.fieldtype));
const cellPlaceholder = computed(() => getFieldPlaceholder(props.column));
const usesFrappeControl = computed(() => ["Attach Image", "Color", "Date", "Datetime", "Time"].includes(props.column.fieldtype));
const numberStep = computed(() => getFieldInputStep(props.column));

const controlDf = computed(() => buildViewerControlDf(props.column, { read_only: !props.isEditable }));

function update(value) {
	if (!props.isEditable) return;
	emit("update", value);
}
</script>


<style scoped>
.table-cell :deep(.afb-link-control),
.table-cell :deep(.frappe-control),
.table-cell :deep(.control-input-wrapper),
.table-cell :deep(.control-input),
.table-cell :deep(.link-field),
.table-cell :deep(.input-with-feedback) {
	width: 100%;
	margin: 0;
	padding: 0;
}

.table-cell :deep(.form-control),
.table-cell :deep(.input-with-feedback) {
	height: 38px;
	min-height: 38px;
	border: 0;
	border-radius: 0;
	padding: 10px;
	background: transparent;
	box-shadow: none;
}

.table-cell :deep(.link-btn) {
	top: 5px;
	right: 4px;
	background-color: var(--bg-color);
}
</style>
