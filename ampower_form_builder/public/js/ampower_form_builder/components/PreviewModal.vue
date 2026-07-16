<template>
	<div v-if="store.preview.open" class="afb-preview-modal">
		<div class="afb-preview-backdrop" @click="store.closePreview()" />
		<div class="afb-preview-shell">
			<header class="afb-preview-header">
				<div class="afb-preview-heading">
					<div class="afb-preview-kicker">Live Preview</div>
					<h2>{{ store.currentTemplate.form_name || "Form Preview" }}</h2>
					<p>{{ store.currentTemplate.description || "Review the form layout and table experience before saving." }}</p>
				</div>
				<div class="afb-preview-actions">
					<button class="btn btn-primary btn-sm" @click="store.closePreview()">Close</button>
				</div>
			</header>
			<div class="afb-preview-body">
				<Form
					:tabs="tabs"
					:current-tab="store.previewTabIndex"
					:active-sections="activeSections"
					:values="values"
					:field-visibility="fieldVisibility"
					:empty-state-message="emptyStateMessage"
					@update:current-tab="store.setPreviewTab($event)"
					@update-field="setFieldValue"
				/>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, reactive, watch } from "vue";
import Form from "../Form.vue";
import {
	VIEWER_LAYOUT_TYPES,
	buildTabs,
	flattenFields,
	getInitialValue,
	getVisibleState,
} from "../viewerUtils.js";
import { useFormBuilderStore } from "../store.js";

const store = useFormBuilderStore();
const values = reactive({});

const tabs = computed(() => buildTabs(store.sections));
const activeSections = computed(() => tabs.value[store.previewTabIndex]?.sections || []);
const editableFields = computed(() => flattenFields(store.sections)
	.filter((field) => field.fieldname && !VIEWER_LAYOUT_TYPES.includes(field.fieldtype)));
const fieldVisibility = computed(() => Object.fromEntries(
	editableFields.value.map((field) => [field.fieldname, getVisibleState(field, values)])
));
const emptyStateMessage = computed(() => "This form has no fields.");

watch(editableFields, (fields) => {
	syncValues(fields, false);
}, { immediate: true, deep: true });

watch(() => store.preview.open, (isOpen) => {
	if (isOpen) {
		syncValues(editableFields.value, true);
		if (store.previewTabIndex >= tabs.value.length) {
			store.setPreviewTab(0);
		}
	}
});

function syncValues(fields, reset = false) {
	const nextFieldnames = new Set(fields.map((field) => field.fieldname));

	Object.keys(values).forEach((fieldname) => {
		if (!nextFieldnames.has(fieldname)) {
			delete values[fieldname];
		}
	});

	fields.forEach((field) => {
		if (reset || !Object.prototype.hasOwnProperty.call(values, field.fieldname)) {
			values[field.fieldname] = getInitialValue(field);
		}
	});
}

function setFieldValue(field, value) {
	values[field.fieldname] = value;
}
</script>
