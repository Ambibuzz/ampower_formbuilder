<template>
	<div class="fv-view-body">
		<div v-if="reportPreviewOpen && printRenderContext" id="fv-print-report-preview">
			<PrintReportPreview
				:format="printRenderContext.print_format"
				:template="printRenderContext.template"
				:submission="printRenderContext.submission"
			/>
		</div>
		<Form
			v-else-if="isFormsDirectoryView"
			:key="formRenderKey"
			:tabs="tabs"
			:current-tab="currentTab"
			:loading-template="loadingTemplate"
			:loading-selector-templates="loadingTemplates"
			:selector-mode="selectorMode"
			:active-templates="activeTemplates"
			:active-sections="activeSections"
			:values="values"
			:field-visibility="fieldVisibility"
			:empty-state-message="emptyStateMessage"
			:is-read-only="isReadOnly"
			@update:current-tab="$emit('update:current-tab', $event)"
			@open-template="$emit('open-template', $event)"
			@update-field="(field, value) => $emit('update-field', field, value)"
		/>
		<div v-else-if="isReportsListView">
			<FormSubmissionList
				:loading="loadingSubmissions"
				:has-items="filteredSubmissions.length > 0"
				:search-value="submissionSearch"
				:search-placeholder="__('ID')"
				:group-by-label="__('Group By')"
				:group-by-items="reportGroupByItems"
				:loading-title="__('Loading reports...')"
				:loading-copy="__('Fetching saved entries for this form.')"
				:empty-title="__('No reports found')"
				:empty-copy="__('Create the first entry for this form to start collecting reports.')"
				:id-label="listIdLabel"
				:status-label="listStatusLabel"
				:count-label="reportListCountLabel"
				:columns="submissionListColumns"
				:submissions="paginatedSubmissions"
				:show-pagination="submissionTotalPages > 1"
				:current-page="submissionPage"
				:total-pages="submissionTotalPages"
				:pagination-label="submissionPaginationLabel"
				:get-submission-status-tone="getSubmissionStatusTone"
				:get-submission-status-label="getSubmissionStatusLabel"
				:get-submission-column-value="getSubmissionColumnValue"
				@update:search-value="$emit('update:search-value', $event)"
				@group-by-select="$emit('group-by-select', $event)"
				@open-submission="$emit('open-submission', $event)"
				@previous-page="$emit('previous-page')"
				@next-page="$emit('next-page')"
				@go-to-page="$emit('go-to-page', $event)"
			/>
		</div>
		<Form
			v-else
			:key="formRenderKey"
			:tabs="tabs"
			:current-tab="currentTab"
			:loading-template="loadingTemplate"
			:selector-mode="false"
			:active-templates="activeTemplates"
			:active-sections="activeSections"
			:values="values"
			:field-visibility="fieldVisibility"
			:empty-state-message="emptyStateMessage"
			:is-read-only="isReadOnly"
			@update:current-tab="$emit('update:current-tab', $event)"
			@open-template="$emit('open-template', $event)"
			@update-field="(field, value) => $emit('update-field', field, value)"
		/>
	</div>
</template>

<script setup>
import Form from "../../../Form.vue";
import PrintReportPreview from "../../../print_builder/PrintReportPreview.vue";
import FormSubmissionList from "./FormSubmissionList.vue";

defineProps({
	reportPreviewOpen: { type: Boolean, default: false },
	printRenderContext: { type: Object, default: null },
	isFormsDirectoryView: { type: Boolean, default: false },
	isReportsListView: { type: Boolean, default: false },
	formRenderKey: { type: String, default: "" },
	tabs: { type: Array, default: () => [] },
	currentTab: { type: Number, default: 0 },
	loadingTemplate: { type: Boolean, default: false },
	loadingTemplates: { type: Boolean, default: false },
	selectorMode: { type: Boolean, default: false },
	activeTemplates: { type: Array, default: () => [] },
	activeSections: { type: Array, default: () => [] },
	values: { type: Object, default: () => ({}) },
	fieldVisibility: { type: Object, default: () => ({}) },
	emptyStateMessage: { type: String, default: "" },
	isReadOnly: { type: Boolean, default: false },
	loadingSubmissions: { type: Boolean, default: false },
	filteredSubmissions: { type: Array, default: () => [] },
	paginatedSubmissions: { type: Array, default: () => [] },
	submissionSearch: { type: String, default: "" },
	reportGroupByItems: { type: Array, default: () => [] },
	reportListCountLabel: { type: String, default: "" },
	submissionPaginationLabel: { type: String, default: "" },
	submissionPage: { type: Number, default: 1 },
	submissionTotalPages: { type: Number, default: 1 },
	listIdLabel: { type: String, default: "ID" },
	listStatusLabel: { type: String, default: "Status" },
	submissionListColumns: { type: Array, default: () => [] },
	getSubmissionStatusTone: { type: Function, default: () => "neutral" },
	getSubmissionStatusLabel: { type: Function, default: () => "" },
	getSubmissionColumnValue: { type: Function, default: () => "-" },
});

defineEmits([
	"update:current-tab",
	"open-template",
	"update-field",
	"update:search-value",
	"group-by-select",
	"open-submission",
	"previous-page",
	"next-page",
	"go-to-page",
]);
</script>
