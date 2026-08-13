<template>
	<div class="fv-layout-container" :class="{ 'is-embedded': embeddedMode, 'is-directory-view': isFormsDirectoryView, 'is-form-view': !isFormsDirectoryView }">
		<div class="fv-main-form">
			<div class="fv-container fv-view-shell" :class="{ 'is-embedded': embeddedMode, 'is-directory-view': isFormsDirectoryView, 'is-form-view': !isFormsDirectoryView }">
				<FormViewerHeader
					v-if="!embeddedMode"
					:page-title="pageTitle"
					:header-description="headerDescription"
					:breadcrumb-label="breadcrumbLabel"
					:report-preview-open="reportPreviewOpen"
					:is-forms-directory-view="isFormsDirectoryView"
					:is-submission-detail-view="isSubmissionDetailView"
					:directory-menu-items="directoryMenuItems"
					:view-menu-items="viewMenuItems"
					:can-create-report="canCreateReport"
					:report-loading="reportLoading"
					:primary-action-label="primaryActionLabel"
					:primary-action-disabled="primaryActionDisabled"
					:secondary-action-label="secondaryActionLabel"
					@print-report="printReport('fv-print-report-preview')"
					@refresh-report="createReport"
					@refresh-directory="refreshDirectory"
					@open-builder="openBuilder"
					@directory-menu-select="handleDirectoryMenuSelect"
					@view-menu-select="handleViewMenuSelect"
					@primary-action="handlePrimaryAction"
					@secondary-action="handleSecondaryAction"
				/>

				<FormViewerBody
					:report-preview-open="reportPreviewOpen"
					:print-render-context="printRenderContext"
					:is-forms-directory-view="isFormsDirectoryView"
					:is-reports-list-view="isReportsListView"
					:form-render-key="formRenderKey"
					:tabs="tabs"
					:current-tab="currentTab"
					:loading-template="loadingTemplate"
					:loading-templates="loadingTemplates"
					:selector-mode="selectorMode"
					:active-templates="activeTemplates"
					:active-sections="activeSections"
					:values="values"
					:field-visibility="fieldVisibility"
					:empty-state-message="emptyStateMessage"
					:is-read-only="isReadOnly"
					:loading-submissions="loadingSubmissions"
					:filtered-submissions="filteredSubmissions"
					:paginated-submissions="paginatedSubmissions"
					:submission-search="submissionSearch"
					:report-group-by-items="reportGroupByItems"
					:report-list-count-label="reportListCountLabel"
					:submission-pagination-label="submissionPaginationLabel"
					:submission-page="submissionPage"
					:submission-total-pages="submissionTotalPages"
					:list-id-label="__('ID')"
					:list-status-label="__('Status')"
					:submission-list-columns="submissionListColumns"
					:get-submission-status-tone="getSubmissionStatusTone"
					:get-submission-status-label="getSubmissionStatusLabel"
					:get-submission-column-value="getSubmissionColumnValue"
					@update:current-tab="currentTab = $event"
					@open-template="openTemplate"
					@update-field="setFieldValue"
					@update:search-value="handleSubmissionSearchUpdate"
					@previous-page="goToPreviousSubmissionPage"
					@next-page="goToNextSubmissionPage"
					@go-to-page="goToSubmissionPage"
					@group-by-select="handleSubmissionGroupBySelect"
					@open-submission="viewSubmission"
				/>
			</div>
		</div>
	</div>

	<AiFormAutofillModal
		:open="autofillModalOpen"
		:template-name="templateDocName"
		@close="autofillModalOpen = false"
		@applied="handleAutofillApplied"
	/>
</template>
<script setup>
import { computed, nextTick, reactive, ref, watch } from "vue";
import AiFormAutofillModal from "../../components/AiFormAutofillModal.vue";
import FormViewerHeader from "./components/FormViewerHeader.vue";
import FormViewerBody from "./components/FormViewerBody.vue";
import { getCachedTemplateSchema } from "../../templateCache.js";
import { NEW_SUBMISSION_ROUTE_TOKEN, buildViewerListRoute, buildViewerNewRoute, buildViewerSubmissionRoute } from "./utils/navigation.js";
import { buildSubmissionListColumns } from "./utils/submissionColumns.js";

import {
	buildTabs,
	evaluateFormulaExpression,
	formatSubmissionValue,
	flattenFields,
	getDynamicLinkSourceFieldname,
	getEmptyValue,
	getInitialValue,
	normalizeFetchedFieldValue,
	getResolvedLinkDoctype,
	getVisibleState,
	normalizeTableValue,
	schemaToSections,
} from "../../viewerUtils.js";

const props = defineProps({
	templateName: { type: String, default: "" },
	page: { type: Object, default: null },
	builderRoute: { type: String, default: "form_builder" },
	embedded: { type: Boolean, default: false },
	frm: { type: Object, default: null },
	parentDoctype: { type: String, default: "" },
	parentDocname: { type: String, default: "" },
	submissionName: { type: String, default: "" },
	submissionFieldname: { type: String, default: "" },
	autofillSubmissionStatus: { type: String, default: "" },
	beforeSubmit: { type: Function, default: null },
	onSubmissionSaved: { type: Function, default: null },
});
const isHydrating = ref(false);
const templateDocName = ref("");
const templateLabel = ref("");
const templateDescription = ref("");
const sections = ref([]);
const currentTab = ref(0);
const loadingTemplate = ref(false);
const loadingSubmissions = ref(false);
const loadingTemplates = ref(false);
const savingSubmission = ref(false);
const selectorMode = ref(false);
const activeTemplates = ref([]);
const submissions = ref([]);
const submissionColumns = ref([]);
const submissionTotal = ref(0);
const loadedSubmissionName = ref("");
const creatingNewEntry = ref(false);
const submissionSearch = ref("");
const submissionPage = ref(1);
const submissionPageSize = ref(20);
const submissionSortMode = ref("modified_desc");
const autofillModalOpen = ref(false);
const printFormats = ref([]);
const selectedPrintFormatName = ref("");
const printRenderContext = ref(null);
const reportPreviewOpen = ref(false);
const printFormatsLoading = ref(false);
const reportLoading = ref(false);
const values = reactive({});
const fetchRequestTokens = reactive({});
const pendingFetches = reactive({});
const fetchDebounceTimers = reactive({});
const formContextVersion = ref(0);
const embeddedMode = computed(() => Boolean(props.embedded));
const isReadOnly = computed(() => embeddedMode.value && [1, 2].includes(Number(props.frm?.doc?.docstatus || 0)));
const FETCH_FROM_DEBOUNCE_MS = 150;


const viewMenuItems = computed(() => {
	const items = [];
	if (loadedSubmissionName.value) {
		items.push({ key: "add_new", label: __("Add New") });
		items.push({ key: "print_report", label: __("Print") });
	}
	items.push({ key: "build_new_form", label: __("Build New Form") });
	if (templateDocName.value) {
		items.push({ key: "autofill_with_ai", label: __("Autofill with AI") });
	}
	return items;
});

const directoryMenuItems = computed(() => ([
	{ key: "directory_group", label: __("Directory"), items: [
		{ key: "open_builder", label: __("Open Builder") },
		{ key: "refresh_directory", label: __("Refresh List") },
	] },
	{ key: "page_group", label: __("Page"), items: [
		{ key: "reload_page", label: __("Reload Page") },
	] },
]));

const reportAddMenuItems = computed(() => ([
	{ key: "add_new", label: __("Add Entry") },
]));


const reportGroupByItems = computed(() => ([
	{ key: "modified_desc", label: __("Last Updated On") },
	{ key: "modified_asc", label: __("Oldest First") },
	{ key: "status_asc", label: __("Status") },
]));


const tabs = computed(() => buildTabs(sections.value));
const activeSections = computed(() => tabs.value[Math.min(currentTab.value, Math.max(tabs.value.length - 1, 0))]?.sections || []);
const flattenedFields = computed(() => flattenFields(sections.value).filter((field) => !["Section Break", "Tab Break", "Column Break"].includes(field.fieldtype)));
const activeSubmission = computed(() => submissions.value.find((submission) => submission._name === loadedSubmissionName.value) || null);
const isFormsDirectoryView = computed(() => selectorMode.value || !templateDocName.value);
const isReportsListView = computed(() => !embeddedMode.value && !isFormsDirectoryView.value && !creatingNewEntry.value && !loadedSubmissionName.value);
const isSubmissionDetailView = computed(() => Boolean(templateDocName.value && loadedSubmissionName.value && !creatingNewEntry.value && !reportPreviewOpen.value));
const selectedPrintFormat = computed(() => printFormats.value.find((item) => item.name === selectedPrintFormatName.value) || null);
const canCreateReport = computed(() => Boolean(templateDocName.value && loadedSubmissionName.value));
const submissionListColumns = computed(() => buildSubmissionListColumns(submissionColumns.value));
const submissionTotalItems = computed(() => submissionTotal.value);
const submissionTotalPages = computed(() => Math.max(1, Math.ceil(submissionTotalItems.value / submissionPageSize.value)));
const paginatedSubmissions = computed(() => filteredSubmissions.value);
const submissionPageStart = computed(() => (submissionTotalItems.value ? ((submissionPage.value - 1) * submissionPageSize.value) + 1 : 0));
const submissionPageEnd = computed(() => (submissionTotalItems.value ? Math.min(submissionPageStart.value + paginatedSubmissions.value.length - 1, submissionTotalItems.value) : 0));
const reportListCountLabel = computed(() => (submissionTotalItems.value ? `${submissionPageStart.value}-${submissionPageEnd.value} of ${submissionTotalItems.value}` : `0 of 0`));
const submissionPaginationLabel = computed(() => (submissionTotalItems.value ? __("Showing {0}-{1} of {2}", [submissionPageStart.value, submissionPageEnd.value, submissionTotalItems.value]) : __("No reports found")));

function getSubmissionSortValue(submission, mode) {
	if (!submission) return "";
	if (mode === "owner_asc") return String(submission._owner || submission.owner || "").toLowerCase();
	if (mode === "status_asc") return String(submission._status || "").toLowerCase();
	const timestamp = Date.parse(submission.modified || submission._submitted_on || submission.submitted_on || "") || 0;
	return timestamp;
}

function sortSubmissions(list) {
	const sorted = [...list];
	if (submissionSortMode.value === "modified_asc") {
		return sorted.sort((left, right) => getSubmissionSortValue(left, submissionSortMode.value) - getSubmissionSortValue(right, submissionSortMode.value));
	}
	if (submissionSortMode.value === "owner_asc" || submissionSortMode.value === "status_asc") {
		return sorted.sort((left, right) => getSubmissionSortValue(left, submissionSortMode.value).localeCompare(getSubmissionSortValue(right, submissionSortMode.value)));
	}
	return sorted.sort((left, right) => getSubmissionSortValue(right, submissionSortMode.value) - getSubmissionSortValue(left, submissionSortMode.value));
}

const filteredSubmissions = computed(() => {
	const query = submissionSearch.value.trim().toLowerCase();
	const list = !query ? submissions.value : submissions.value.filter((submission) => {
		return [submission._name, getSubmissionTitle(submission), submission._status, submission._submitted_on]
			.filter(Boolean)
			.some((value) => String(value).toLowerCase().includes(query));
	});
	return sortSubmissions(list);
});

watch([submissionTotalItems, submissionTotalPages], () => {
	if (submissionPage.value > submissionTotalPages.value) {
		submissionPage.value = submissionTotalPages.value;
	}
	if (submissionPage.value < 1) {
		submissionPage.value = 1;
	}
}, { immediate: true });
const fieldVisibility = computed(() => Object.fromEntries(
	flattenedFields.value.map((field) => [field.fieldname, getVisibleState(field, values)])
));
const formRenderKey = computed(() => [
	templateDocName.value || "selector",
	loadedSubmissionName.value || (creatingNewEntry.value ? NEW_SUBMISSION_ROUTE_TOKEN : "list"),
	embeddedMode.value ? "embedded" : "standalone",
	formContextVersion.value,
].join(":"));
const viewKicker = computed(() => {
	if (reportPreviewOpen.value) return __("Report Preview");
	if (isFormsDirectoryView.value) return __("Forms");
	if (isReportsListView.value) return __("Reports");
	return __("Form Viewer");
});
const pageTitle = computed(() => {
	if (reportPreviewOpen.value && selectedPrintFormat.value) {
		return selectedPrintFormat.value.format_name || __("Print Report");
	}
	if (loadingTemplate.value) return __("Loading Form...");
	if (isFormsDirectoryView.value) return __("Dynamic Form Template");
	if (isReportsListView.value) return templateLabel.value || __("Reports");
	if (creatingNewEntry.value) return __("New {0}", [templateLabel.value || __("Form")]);
	if (activeSubmission.value) return getSubmissionTitle(activeSubmission.value);
	return templateLabel.value || __("Form Viewer");
});
const breadcrumbLabel = computed(() => {
	if (reportPreviewOpen.value) return `${__("Reports")} / ${__("Report Preview")}`;
	if (isFormsDirectoryView.value) return `${__("Forms")} / ${__("Dynamic Form Template")}`;
	if (isSubmissionDetailView.value) return `${__("Reports")} / ${templateLabel.value || __("Form Viewer")} / ${pageTitle.value}`;
	if (isReportsListView.value) return `${__("Reports")} / ${templateLabel.value || __("List")}`;
	return `${__("Form Viewer")} / ${pageTitle.value}`;
});
const headerDescription = computed(() => "");
const primaryActionLabel = computed(() => (isReportsListView.value ? __("Add New") : __("Save")));
const primaryActionDisabled = computed(() => loadingTemplate.value || loadingTemplates.value || loadingSubmissions.value || savingSubmission.value || isHydrating.value);
const secondaryActionLabel = computed(() => (isSubmissionDetailView.value ? __("Add New") : ""));
const emptyStateMessage = computed(() => {
	if (isFormsDirectoryView.value || isReportsListView.value) return "";
	if (embeddedMode.value && !templateDocName.value) return __("Select a form to continue.");
	if (!loadedSubmissionName.value && !creatingNewEntry.value) return __("Select a report entry to continue.");
	return __("This form has no fields.");
});


function reportViewerError(title, error, fallbackMessage) {
	const message = error?.message || error?.exc || fallbackMessage || __("Something went wrong.");
	console.error(title, error);
	frappe.msgprint({
		title,
		message,
		indicator: "red",
	});
}

watch(
	pageTitle,
	(title) => {
		if (!embeddedMode.value) {
			props.page?.set_title?.(title);
		}
	},
	{ immediate: true }
);

function handleSubmissionSearchUpdate(value) {
	submissionSearch.value = value;
}

function goToSubmissionPage(pageNumber) {
	const nextPage = Math.min(Math.max(1, Number(pageNumber) || 1), submissionTotalPages.value);
	if (nextPage === submissionPage.value) return;
	fetchSubmissions(nextPage);
}

function goToPreviousSubmissionPage() {
	goToSubmissionPage(submissionPage.value - 1);
}

function goToNextSubmissionPage() {
	goToSubmissionPage(submissionPage.value + 1);
}

function handleSubmissionGroupBySelect(action) {
	submissionSortMode.value = action || "modified_desc";
}
function resetValues(submissionData = null) {
	Object.keys(values).forEach((key) => delete values[key]);
	flattenedFields.value.forEach((field) => {
		values[field.fieldname] = getInitialValue(field, submissionData);
	});
	syncCalculatedFields();
	syncFetchedFields();
	formContextVersion.value += 1;
}

function setFieldValue(field, nextValue) {
	if (!field?.fieldname) return;
	if (isReadOnly.value) return;
	const currentValue = values[field.fieldname];
	if (isFieldValueEqual(field, currentValue, nextValue)) return;
	values[field.fieldname] = nextValue;
	syncCalculatedFields(field?.fieldname);
	syncFetchedFields(field?.fieldname);
	markParentFormDirty();
}

function markParentFormDirty() {
	if (isHydrating.value) return;
	if (!embeddedMode.value || !props.frm?.dirty) return;
	props.frm.dirty();
	props.frm.refresh_save?.();
}

async function withHydrationGuard(task) {
	isHydrating.value = true;
	try {
		return await task();
	} finally {
		isHydrating.value = false;
	}
}

function getFieldByName(fieldname) {
	return flattenedFields.value.find((field) => field.fieldname === fieldname) || null;
}

function isFieldValueEqual(field, currentValue, nextValue) {
	if (["Table", "Mixed Table"].includes(field?.fieldtype)) {
		return JSON.stringify(currentValue ?? []) === JSON.stringify(nextValue ?? []);
	}
	return currentValue === nextValue;
}

function normalizeFetchedValue(field, value) {
	return normalizeFetchedFieldValue(field, value);
}

function normalizeCalculatedValue(field, value) {
	if (value === "") return "";
	const precision = field.precision === "" || field.precision === null || field.precision === undefined
		? null
		: Number(field.precision);
	if (precision === null || !Number.isFinite(precision)) {
		return value;
	}
	const factor = 10 ** precision;
	return Math.round(Number(value) * factor) / factor;
}

function getActiveSubmissionName() {
	const loadedName = String(loadedSubmissionName.value || "").trim();
	if (loadedName) return loadedName;

	const routeSubmissionName = String(props.submissionName || "").trim();
	if (routeSubmissionName && !isNewSubmissionRoute(routeSubmissionName)) {
		return routeSubmissionName;
	}

	return "";
}

function getSubmissionMethod() {
	return getActiveSubmissionName()
		? "ampower_form_builder.api.update_submission"
		: "ampower_form_builder.api.save_submission";
}

function canSyncSubmission() {
	return Boolean(templateDocName.value);
}

function syncCalculatedFields(changedFieldname = "") {
	const sourceFieldname = String(changedFieldname || "").trim();
	for (let iteration = 0; iteration < 5; iteration += 1) {
		let changed = false;
		flattenedFields.value.forEach((field) => {
			if (!field.formula || !field.fieldname) return;
			if (sourceFieldname && iteration === 0 && field.fieldname === sourceFieldname) return;
			const nextValue = normalizeCalculatedValue(field, evaluateFormulaExpression(field.formula, values));
			if (values[field.fieldname] !== nextValue) {
				values[field.fieldname] = nextValue;
				changed = true;
			}
		});
		if (!changed) break;
	}
}

async function fetchLinkedValue({ targetField, sourceDocName, linkedFieldname, linkedDoctype }) {
	if (!targetField?.fieldname || !linkedDoctype || !linkedFieldname) return;

	const requestKey = targetField.fieldname;
	const requestToken = `${sourceDocName}:${linkedDoctype}:${linkedFieldname}:${Date.now()}`;
	fetchRequestTokens[requestKey] = requestToken;
	const fetchPromise = (async () => {
		await new Promise((resolve) => {
			if (fetchDebounceTimers[requestKey]) {
				window.clearTimeout(fetchDebounceTimers[requestKey]);
			}
			fetchDebounceTimers[requestKey] = window.setTimeout(() => {
				delete fetchDebounceTimers[requestKey];
				resolve();
			}, FETCH_FROM_DEBOUNCE_MS);
		});

		if (fetchRequestTokens[requestKey] !== requestToken) return;

		try {
			const response = await frappe.db.get_value(linkedDoctype, sourceDocName, linkedFieldname);
			if (fetchRequestTokens[requestKey] !== requestToken) return;
			const fetchedValue = response?.message?.[linkedFieldname];
			values[targetField.fieldname] = normalizeFetchedValue(targetField, fetchedValue);
			syncCalculatedFields(targetField.fieldname);
		} catch (error) {
			if (fetchRequestTokens[requestKey] !== requestToken) return;
			reportViewerError(__("Fetch From Error"), error, __("Unable to fetch linked value."));
		} finally {
			if (pendingFetches[requestKey] === fetchPromise) {
				delete pendingFetches[requestKey];
			}
		}
	})();
	pendingFetches[requestKey] = fetchPromise;

	await fetchPromise;
}

function syncFetchedFields(changedFieldname = "") {
	const sourceFieldname = String(changedFieldname || "").trim();
	flattenedFields.value.forEach((field) => {
		const fetchFrom = String(field.fetch_from || "").trim();
		if (!fetchFrom || !field.fieldname) return;

		const [linkFieldname, linkedFieldname] = fetchFrom.split(".", 2);
		if (!linkFieldname || !linkedFieldname) return;

		const sourceField = getFieldByName(linkFieldname);
		if (!sourceField) return;
		const dynamicLinkFieldname = getDynamicLinkSourceFieldname(sourceField);
		if (sourceFieldname && sourceFieldname !== linkFieldname && sourceFieldname !== dynamicLinkFieldname) return;

		const sourceDocName = values[linkFieldname];
		if (!sourceDocName) {
			const emptyValue = getEmptyValue(field);
			if (values[field.fieldname] !== emptyValue) {
				values[field.fieldname] = emptyValue;
				syncCalculatedFields(field.fieldname);
			}
			return;
		}

		const linkedDoctype = getResolvedLinkDoctype(sourceField, values);

		if (!linkedDoctype) {
			const emptyValue = getEmptyValue(field);
			if (values[field.fieldname] !== emptyValue) {
				values[field.fieldname] = emptyValue;
				syncCalculatedFields(field.fieldname);
			}
			return;
		}

		fetchLinkedValue({
			targetField: field,
			sourceDocName,
			linkedFieldname,
			linkedDoctype,
		});
	});
}

function isNewSubmissionRoute(name) {
	return String(name || "").trim() === NEW_SUBMISSION_ROUTE_TOKEN;
}

function showSelector() {
	loadingTemplate.value = false;
	templateDocName.value = "";
	templateLabel.value = "";
	templateDescription.value = "";
	sections.value = [];
	currentTab.value = 0;
	loadedSubmissionName.value = "";
	creatingNewEntry.value = false;
	submissions.value = [];
	submissionSearch.value = "";
	submissionPage.value = 1;
	printFormats.value = [];
	selectedPrintFormatName.value = "";
	printRenderContext.value = null;
	reportPreviewOpen.value = false;
	resetValues();

	if (embeddedMode.value) {
		selectorMode.value = false;
		activeTemplates.value = [];
		loadingTemplates.value = false;
		return;
	}

	selectorMode.value = true;
	refreshDirectory();
}

function showSubmissionList({ resetForm = true } = {}) {
	creatingNewEntry.value = false;
	loadedSubmissionName.value = "";
	reportPreviewOpen.value = false;
	printRenderContext.value = null;
	currentTab.value = 0;
	if (resetForm) {
		resetValues();
	}
}

function syncRouteContext(context = {}) {
	const nextTemplateName = String(context.templateName ?? props.templateName ?? "").trim();
	const nextSubmissionName = String(context.submissionName ?? props.submissionName ?? "").trim();

	if (!nextTemplateName) {
		showSelector();
		return;
	}

	if (templateDocName.value !== nextTemplateName) {
		loadTemplate(nextTemplateName, { submissionName: nextSubmissionName });
		return;
	}

	if (!nextSubmissionName) {
		showSubmissionList();
		return;
	}

	if (isNewSubmissionRoute(nextSubmissionName)) {
		resetEntry({ updateRoute: false });
		return;
	}

	if (loadedSubmissionName.value !== nextSubmissionName || creatingNewEntry.value) {
		loadSubmissionByName(nextSubmissionName, { announce: false });
	}
}

function fetchActiveTemplates() {
	loadingTemplates.value = true;
	frappe.call({
		method: "ampower_form_builder.api.get_active_templates",
		callback: (response) => {
			activeTemplates.value = response.message || [];
			loadingTemplates.value = false;
		},
		error: (error) => {
			loadingTemplates.value = false;
			activeTemplates.value = [];
			reportViewerError(__("Load Forms Error"), error, __("Unable to load forms."));
		},
	});
}

function refreshDirectory() {
	if (embeddedMode.value) return;
	selectorMode.value = true;
	fetchActiveTemplates();
}

async function loadTemplate(templateName, { submissionName = "" } = {}) {
	loadingTemplate.value = true;
	selectorMode.value = false;
	currentTab.value = 0;
	loadedSubmissionName.value = "";
	creatingNewEntry.value = false;
	reportPreviewOpen.value = false;
	printRenderContext.value = null;
	printFormats.value = [];
	selectedPrintFormatName.value = "";
	if (!embeddedMode.value) {
		frappe.dom?.freeze?.(__("Loading form..."));
	}
	try {
		await withHydrationGuard(async () => {
			const doc = await getCachedTemplateSchema(templateName);
			if (!doc) {
				templateDocName.value = "";
				templateLabel.value = __("Error");
				templateDescription.value = __("Form not found or inaccessible.");
				sections.value = [];
				submissions.value = [];
				return;
			}

			templateDocName.value = doc.name || templateName;
			templateLabel.value = doc.form_name || doc.name || templateName;
			templateDescription.value = doc.description || "";
			sections.value = schemaToSections(doc.schema || {});
			resetValues();
			await fetchPrintFormats();

			const targetSubmissionName = String(submissionName || "").trim();

			if (embeddedMode.value && !targetSubmissionName) {
				await loadSubmissionForReference({ announce: false });
			}

			if (embeddedMode.value) {
				if (targetSubmissionName) {
					await loadSubmissionByName(targetSubmissionName, { announce: false });
				}
				return;
			}

			fetchSubmissions();
			if (isNewSubmissionRoute(targetSubmissionName)) {
				resetEntry({ updateRoute: false });
			} else if (targetSubmissionName) {
				await loadSubmissionByName(targetSubmissionName, { announce: false });
			} else {
				showSubmissionList({ resetForm: false });
			}
		});
	} catch (error) {
		templateDocName.value = "";
		templateLabel.value = __("Error");
		templateDescription.value = __("Form not found or inaccessible.");
		sections.value = [];
		submissions.value = [];
		reportViewerError(__("Load Form Error"), error, __("Unable to load form."));
	} finally {
		loadingTemplate.value = false;
		if (!embeddedMode.value) {
			frappe.dom?.unfreeze?.();
		}
	}
}

function fetchSubmissions(page = submissionPage.value) {
	if (!templateDocName.value || embeddedMode.value) return;
	loadingSubmissions.value = true;

	const requestPage = Math.min(Math.max(1, Number(page) || 1), Math.max(1, submissionTotalPages.value));

	frappe.call({
		method: "ampower_form_builder.api.get_submissions",
		args: {
			form_template: templateDocName.value,
			page: requestPage,
			page_size: submissionPageSize.value,
		},
		callback: (response) => {
			loadingSubmissions.value = false;
			submissions.value = response.message?.data || [];
			submissionColumns.value = response.message?.columns || [];
			submissionTotal.value = Number(response.message?.total || submissions.value.length || 0);
			submissionPage.value = Number(response.message?.page || requestPage || 1);
			submissionPageSize.value = Number(response.message?.page_size || submissionPageSize.value || 20);
		},
		error: (error) => {
			loadingSubmissions.value = false;
			submissions.value = [];
			submissionColumns.value = [];
			submissionTotal.value = 0;
			reportViewerError(__("Load Reports Error"), error, __("Unable to load reports."));
		},
	});
}
async function fetchPrintFormats() {
	if (!templateDocName.value) {
		printFormats.value = [];
		selectedPrintFormatName.value = "";
		return;
	}

	printFormatsLoading.value = true;
	try {
		const response = await frappe.xcall("ampower_form_builder.print_builder.api.list_print_formats", {
			dynamic_form_template: templateDocName.value,
		});
		printFormats.value = Array.isArray(response) ? response : [];
		const defaultFormat = printFormats.value.find((item) => item.is_default) || printFormats.value[0] || null;
		if (!selectedPrintFormatName.value || !printFormats.value.some((item) => item.name === selectedPrintFormatName.value)) {
			selectedPrintFormatName.value = defaultFormat?.name || "";
		}
	} catch (error) {
		printFormats.value = [];
		selectedPrintFormatName.value = "";
		reportViewerError(__("Load Print Formats Error"), error, __("Unable to load print formats."));
	} finally {
		printFormatsLoading.value = false;
	}
}

function getSubmissionTitle(submission) {
	const firstField = flattenedFields.value.find((field) => !["HTML", "Heading", "Table", "Mixed Table"].includes(field.fieldtype));
	if (firstField?.fieldname) {
		const title = formatSubmissionValue(submission[firstField.fieldname], "", firstField.fieldtype);
		if (title) return title;
	}
	return submission._name;
}

function getSubmissionStatusLabel(submission) {
	return submission?._status || __("Draft");
}

function getSubmissionStatusTone(submission) {
	const status = String(submission?._status || "").toLowerCase();
	if (status === "submitted") return "submitted";
	if (status === "draft") return "draft";
	if (status === "cancelled") return "cancelled";
	return "neutral";
}

function getSubmissionColumnValue(submission, column = null) {
	if (!submission) return "-";
	const fieldname = String(column?.fieldname || "").trim();
	if (!fieldname) {
		return submission.naming_series || submission.series || "-";
	}
	const value = submission[fieldname];
	if (value === null || value === undefined || value === "") {
		return submission.naming_series || submission.series || "-";
	}
	return formatSubmissionValue(value, "", column?.fieldtype || "Data") || "-";
}

function getSubmissionOwnerInitials(submission) {
	const owner = String(submission?._owner || submission?.owner || "").trim();
	if (!owner) return "--";
	const parts = owner.split(/[\s@._-]+/).filter(Boolean);
	const initials = parts.slice(0, 2).map((part) => part.charAt(0)).join("");
	return (initials || owner.slice(0, 2)).toUpperCase();
}

function formatRelativeTime(value) {
	if (!value) return "-";
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return String(value);
	const diffMinutes = Math.max(1, Math.round((Date.now() - date.getTime()) / 60000));
	if (diffMinutes < 60) return `${diffMinutes} m`;
	const diffHours = Math.round(diffMinutes / 60);
	if (diffHours < 24) return `${diffHours} h`;
	const diffDays = Math.round(diffHours / 24);
	if (diffDays < 30) return `${diffDays} d`;
	const diffMonths = Math.round(diffDays / 30);
	if (diffMonths < 12) return `${diffMonths} M`;
	const diffYears = Math.round(diffMonths / 12);
	return `${diffYears} y`;
}

async function waitForPendingFetches() {
	const requests = Object.values(pendingFetches).filter(Boolean);
	if (!requests.length) return;
	await Promise.allSettled(requests);
}

async function loadSubmissionByName(name, { announce = true } = {}) {
	const manageLoading = !loadingTemplate.value;
	if (manageLoading) {
		loadingTemplate.value = true;
	}
	try {
		const response = await frappe.call({
			method: "ampower_form_builder.api.get_submission",
			args: { submission_name: name },
			freeze: !embeddedMode.value,
			freeze_message: !embeddedMode.value ? __("Loading report...") : undefined,
		});
		if (!response.message?.data) return false;
		return await withHydrationGuard(async () => {
			if (
				templateDocName.value
				&& response.message.form_template
				&& response.message.form_template !== templateDocName.value
			) {
				reportViewerError(
					__("Load Report Error"),
					new Error(__("The selected submission does not belong to the current form.")),
					__("Unable to load report."),
				);
				return false;
			}
			creatingNewEntry.value = false;
			loadedSubmissionName.value = name;
			resetValues(response.message.data);
			if (reportPreviewOpen.value && selectedPrintFormatName.value) {
				createReport({ silent: true });
			}
			if (announce) {
				frappe.show_alert({ message: __("Viewing Report: {0}", [name]), indicator: "blue" });
			}
			return true;
		});
	} catch (error) {
		reportViewerError(__("Load Report Error"), error, __("Unable to load report."));
		return false;
	} finally {
		if (manageLoading) {
			loadingTemplate.value = false;
		}
	}
}

async function loadSubmissionForReference({ announce = false } = {}) {
	if (!embeddedMode.value || !templateDocName.value || !props.parentDoctype || !props.parentDocname) {
		return "";
	}

	try {
		const submissionName = await resolveSubmissionNameForReference();
		if (!submissionName) return "";
		await loadSubmissionByName(submissionName, { announce });
		return submissionName;
	} catch (error) {
		reportViewerError(__("Load Report Error"), error, __("Unable to load report."));
		return "";
	}
}

async function resolveSubmissionNameForReference() {
	if (!embeddedMode.value || !templateDocName.value || !props.parentDoctype || !props.parentDocname) {
		return "";
	}

	try {
		const response = await frappe.call({
			method: "ampower_form_builder.api.get_submission_by_reference",
			args: {
				form_template: templateDocName.value,
				reference_doctype: props.parentDoctype,
				reference_name: props.parentDocname,
			},
			freeze: false,
		});
		return response.message?.name || "";
	} catch (error) {
		reportViewerError(__("Load Report Error"), error, __("Unable to load report."));
		return "";
	}
}

function viewSubmission(name) {
	if (!name) return;
	if (templateDocName.value && props.templateName === templateDocName.value && loadedSubmissionName.value === name) {
		loadSubmissionByName(name, { announce: true });
		return;
	}
	if (templateDocName.value) {
		frappe.set_route(...buildViewerRoute(templateDocName.value, name));
	}
}

function resetEntry({ updateRoute = true } = {}) {
	creatingNewEntry.value = true;
	loadedSubmissionName.value = "";
	reportPreviewOpen.value = false;
	printRenderContext.value = null;
	currentTab.value = 0;
	resetValues();
	if (updateRoute && !embeddedMode.value && templateDocName.value) {
		frappe.set_route(...buildViewerNewRoute(templateDocName.value));
	}
}

function openTemplate(name) {
	if (!name) return;
	if (props.templateName !== name) {
		frappe.set_route(...buildViewerRoute(name));
		return;
	}
	loadTemplate(name, { submissionName: props.submissionName });
}

function openDirectory() {
	frappe.set_route(...buildViewerListRoute());
}

function openSubmissionList() {
	if (!embeddedMode.value && templateDocName.value) {
		frappe.set_route(...buildViewerListRoute(templateDocName.value));
	}
}

function openBuilder() {
	if (embeddedMode.value) return;
	if (templateDocName.value) {
		frappe.set_route(props.builderRoute, templateDocName.value);
		return;
	}
	frappe.set_route(props.builderRoute);
}

function openPrintBuilder() {
	if (embeddedMode.value) return;

	const baseUrl = new URL("/app/print_builder", window.location.origin);
	if (templateDocName.value) {
		baseUrl.searchParams.set("template", templateDocName.value);
	}

	window.location.assign(baseUrl.toString());
}

function handleSecondaryAction() {
	resetEntry();
}


function handleDirectoryMenuSelect(action) {
	if (action === "open_builder") {
		openBuilder();
		return;
	}
	if (action === "refresh_directory") {
		refreshDirectory();
		return;
	}
	if (action === "reload_page") {
		window.location.reload();
	}
}

function handleReportAddSelect(action) {
	if (action === "add_new") {
		resetEntry();
	}
}


function handleViewMenuSelect(action) {
	if (action === "add_new") {
		resetEntry();
		return;
	}
	if (action === "print_report") {
		openPrintDialog();
		return;
	}
	if (action === "build_new_form") {
		openBuilder();
		return;
	}
	if (action === "autofill_with_ai") {
		openAutofillModal();
	}
}


async function createReport({ silent = false, autoPrint = false } = {}) {
	if (!loadedSubmissionName.value) {
		frappe.msgprint({
			title: __("Report Unavailable"),
			message: __("Load a saved or submitted form before creating a report."),
			indicator: "orange",
		});
		return;
	}

	if (!printFormats.value.length) {
		frappe.msgprint({
			title: __("No Print Formats"),
			message: __("There are no print formats linked to this form template yet. Open the print builder to create one."),
			indicator: "orange",
			primary_action: {
				label: __("Open Print Builder"),
				action: () => openPrintBuilder(),
			},
		});
		return;
	}

	if (!selectedPrintFormatName.value) {
		const defaultFormat = printFormats.value.find((item) => item.is_default) || printFormats.value[0] || null;
		selectedPrintFormatName.value = defaultFormat?.name || "";
	}

	if (!selectedPrintFormatName.value) {
		frappe.msgprint({
			title: __("Print Format Missing"),
			message: __("Choose a print format before creating a report."),
			indicator: "orange",
		});
		return;
	}

	reportLoading.value = true;
	try {
		const context = await frappe.xcall("ampower_form_builder.print_builder.api.get_print_render_context", {
			format_name: selectedPrintFormatName.value,
			submission_name: loadedSubmissionName.value,
		});
		if (!context?.print_format || !context?.template || !context?.submission) {
			throw new Error(__("The report data was incomplete."));
		}
		printRenderContext.value = context;
		reportPreviewOpen.value = true;
		if (autoPrint) {
			await nextTick();
			await printReport("fv-print-report-preview");
		}
		if (!silent) {
			frappe.show_alert({
				message: __("Report generated successfully."),
				indicator: "green",
			});
		}
	} catch (error) {
		reportViewerError(__("Create Report Error"), error, __("Unable to create the report."));
	} finally {
		reportLoading.value = false;
	}
}

function closeReport() {
	reportPreviewOpen.value = false;
}

function openPrintDialog() {
	if (!loadedSubmissionName.value) {
		frappe.msgprint({
			title: __("Print Unavailable"),
			message: __("Load a saved submission before printing."),
			indicator: "orange",
		});
		return;
	}

	if (!printFormats.value.length) {
		frappe.msgprint({
			title: __("No Print Formats"),
			message: __("There are no print formats linked to this form template yet. Open the print builder to create one."),
			indicator: "orange",
			primary_action: {
				label: __("Open Print Builder"),
				action: () => openPrintBuilder(),
			},
		});
		return;
	}

	const defaultFormat = printFormats.value.find((item) => item.name === selectedPrintFormatName.value)
		|| printFormats.value.find((item) => item.is_default)
		|| printFormats.value[0]
		|| null;
	const dialog = new frappe.ui.Dialog({
		title: __("Print Report"),
		fields: [
			{
				fieldname: "print_format",
				fieldtype: "Link",
				label: __("Print Format"),
				options: "Dynamic Print Format",
				reqd: 1,
				default: defaultFormat?.name || "",
				get_query: () => ({
					filters: {
						dynamic_form_template: templateDocName.value,
					},
				}),
			},
		],
		primary_action_label: __("Print"),
		primary_action: async (values) => {
			const formatName = String(values?.print_format || "").trim();
			if (!formatName) return;
			selectedPrintFormatName.value = formatName;
			dialog.hide();
			await createReport({ silent: true, autoPrint: true });
		},
		secondary_action_label: __("Open Print Builder"),
		secondary_action: () => {
			dialog.hide();
			openPrintBuilder();
		},
	});

	dialog.show();
}

function getPrintableStylesHtml() {
	return Array.from(document.querySelectorAll("link[rel='stylesheet'], style"))
		.map((node) => node.outerHTML)
		.join("");
}

function getPrintableReportHtml(target) {
	const pages = target?.querySelectorAll?.(".pb-report-page");
	if (!pages || !pages.length) {
		return target.outerHTML;
	}

	return `
		<div class="pb-print-root">
			${Array.from(pages)
				.map((page) => page.outerHTML)
				.join("")}
		</div>
	`;
}

function getPrintFormatPageOrientation(printFormat = {}) {
	const pageWidth = Number.parseFloat(String(printFormat.page_width || ""));
	const pageHeight = Number.parseFloat(String(printFormat.page_height || ""));
	if (Number.isFinite(pageWidth) && Number.isFinite(pageHeight) && pageWidth > pageHeight) {
		return "Landscape";
	}
	return "Portrait";
}

function measureRepeatableBlockHeight(target, selector) {
	const nodes = Array.from(target?.querySelectorAll?.(selector) || []);
	if (!nodes.length) {
		return 0;
	}

	return nodes.reduce((total, node, index) => {
		const height = Math.max(node.getBoundingClientRect?.().height || 0, 0);
		const spacer = index < nodes.length - 1 ? 5 : 0;
		return total + height + spacer;
	}, 0);
}

function buildPrintableReportHtml(target) {
	const printFormat = printRenderContext.value?.print_format || {};
	const pageWidth = String(printFormat.page_width || "210mm");
	const pageHeight = String(printFormat.page_height || "297mm");
	const baseHref = `${window.location.origin}/`;

	return `<!doctype html>
<html>
<head>
	<meta charset="utf-8">
	<base href="${baseHref}">
	<title>${document.title}</title>
	<style>
		html,
		body {
			margin: 0;
			padding: 0;
			background: #fff;
			width: 100%;
			box-sizing: border-box;
			font-family: Arial, Helvetica, sans-serif;
			color: #111827;
		}

		.print-format {
			box-sizing: border-box;
			padding: 0;
			width: 100%;
			max-width: none !important;
			margin: 0;
		}

		@page {
			size: ${pageWidth} ${pageHeight};
			margin: 0;
		}

		.pb-print-root {
			display: block;
			width: 100%;
			margin: 0;
		}

		.pb-print-root .pb-report-page {
			box-shadow: none;
			border: 0;
			margin: 0;
			page-break-after: always;
			break-after: page;
		}

		.pb-print-root .pb-report-page.is-last-page {
			page-break-after: auto;
			break-after: auto;
		}

		.pb-report-shell {
			display: block;
			width: 100%;
		}

		.pb-report-page {
			position: relative;
			background: #fff;
			box-sizing: border-box;
			overflow: hidden;
		}

		.pb-report-content {
			position: absolute;
			box-sizing: border-box;
		}

		.pb-report-item,
		.pb-report-matrix,
		.pb-report-table-item {
			box-sizing: border-box;
		}

		.pb-report-item {
			position: absolute;
			display: flex;
			flex-direction: column;
			gap: 5px;
			overflow: hidden;
		}

		.pb-report-label {
			font-size: 12px;
			font-weight: 600;
			color: #64748b;
			line-height: 1.2;
		}

		.pb-report-value {
			font-size: 12px;
			font-weight: 500;
			line-height: 1.25;
			word-break: break-word;
			white-space: pre-wrap;
		}

		.pb-report-image-wrap {
			display: flex;
			align-items: flex-start;
			justify-content: flex-start;
		}

		.pb-report-image {
			display: block;
			max-width: 100%;
			max-height: 140px;
			object-fit: contain;
		}

		.pb-report-table-item {
			display: flex;
			flex-direction: column;
			gap: 8px;
		}

		.pb-report-table-wrap {
			max-width: 100%;
			border: 1px solid #000;
			background: #fff;
			overflow: hidden;
		}

		.pb-report-table {
			width: 100%;
			border-collapse: collapse;
			font-size: 12px;
			color: #0f172a;
		}

		.pb-report-table th,
		.pb-report-table td {
			padding: 8px 10px;
			border-right: 1px solid #000;
			border-bottom: 1px solid #000;
			vertical-align: top;
		}

		.pb-report-table th:first-child,
		.pb-report-table td:first-child {
			border-left: 1px solid #000;
		}

		.pb-report-table tr:first-child th,
		.pb-report-table tr:first-child td {
			border-top: 1px solid #000;
		}

		.pb-report-table th {
			font-size: 11px;
			font-weight: 700;
			color: #111;
			background: #f2f2f2;
			text-align: center;
		}

		.pb-report-table tr:last-child td {
			border-bottom: 0;
		}

		.pb-report-table th:last-child,
		.pb-report-table td:last-child {
			border-right: 0;
		}

		.pb-report-matrix {
			position: absolute;
			display: flex;
			flex-direction: column;
			gap: 5px;
			padding: 0;
			color: #0f172a;
			background: #fff;
			overflow: hidden;
		}

		.pb-report-matrix-heading-table,
		.pb-report-matrix-table {
			width: 100%;
			border-collapse: collapse;
			table-layout: fixed;
			font-size: 12px;
			color: #0f172a;
			background: transparent;
		}

		.pb-report-matrix-heading-table th,
		.pb-report-matrix-table th,
		.pb-report-matrix-table td {
			padding: 6px 8px;
			border-right: 1px solid #000;
			border-bottom: 1px solid #000;
			vertical-align: top;
		}

		.pb-report-matrix-heading-table th:first-child,
		.pb-report-matrix-table th:first-child,
		.pb-report-matrix-table td:first-child {
			border-left: 1px solid #000;
		}

		.pb-report-matrix-heading-table tr:first-child th,
		.pb-report-matrix-table tr:first-child th,
		.pb-report-matrix-table tr:first-child td {
			border-top: 1px solid #000;
		}

		.pb-report-matrix-heading-table th,
		.pb-report-matrix-table th {
			font-size: 13px;
			font-weight: 700;
			color: #111;
			background: #f2f2f2;
			text-align: center;
		}

		.pb-report-matrix-cell {
			box-sizing: border-box;
			min-width: 0;
			min-height: 0;
			overflow: hidden;
		}

		.pb-report-shell {
			padding: 0;
			gap: 0;
		}

		.pb-report-page {
			width: 100%;
			background: #fff;
			box-shadow: none;
			border: 0;
			overflow: visible;
			padding: 10px;
			box-sizing: border-box;
		}

		.pb-report-content {
			position: static;
			display: flex;
			flex-direction: column;
			gap: 0;
			width: 100%;
			height: auto;
			box-sizing: border-box;
		}

		.pb-report-block,
		.pb-report-item,
		.pb-report-table-item,
		.pb-report-matrix {
			position: static;
			width: 100%;
			box-sizing: border-box;
			margin: 0;
		}

		.pb-report-item {
			display: flex;
			flex-direction: column;
			gap: 5px;
		}

		.pb-report-table-item {
			display: flex;
			flex-direction: column;
			gap: 5px;
		}

		.pb-report-spacer {
			flex: 0 0 5px;
			width: 100%;
			height: 5px;
		}

		.pb-report-matrix {
			display: flex;
			flex-direction: column;
			gap: 5px;
			padding: 0;
			border: 0;
			border-radius: 0;
			background: #fff;
			overflow: visible;
		}

		#header-html,
		#footer-html,
		.header-html,
		.letter-head,
		.footer-html {
			width: 100% !important;
			max-width: 100% !important;
			box-sizing: border-box;
		}

		.pb-report-table-wrap {
			max-width: 100%;
			border: 1px solid #000;
			background: #fff;
			overflow: visible;
		}

		.pb-report-table {
			width: 100%;
			border-collapse: collapse;
			page-break-inside: auto;
			break-inside: auto;
		}

		.pb-report-table tr,
		.pb-report-matrix-table tr {
			break-inside: avoid;
			page-break-inside: avoid;
		}

		.pb-report-matrix-heading-table,
		.pb-report-matrix-table {
			width: 100%;
			border-collapse: collapse;
			table-layout: fixed;
			background: transparent;
			page-break-inside: auto;
			break-inside: auto;
		}

		.pb-report-table-empty-state {
			padding: 6px 0;
		}
	</style>
</head>
<body>
	<div class="print-format">
		${getPrintableReportHtml(target)}
	</div>
</body>
</html>`;
}

async function printReport(targetId = "") {
	const target = targetId ? document.getElementById(targetId) : null;
	if (!target) {
		window.print();
		return;
	}

	const printFormat = printRenderContext.value?.print_format || {};
	const html = buildPrintableReportHtml(target);
	const orientation = getPrintFormatPageOrientation(printFormat);
	const pageHeight = String(printFormat.page_height || "297mm");
	const printWindow = window.open("", "_blank");
	const pageWidth = String(printFormat.page_width || "210mm");
	const headerHeightPx = measureRepeatableBlockHeight(target, "#header-html, .header-html, .letter-head");
	const footerHeightPx = measureRepeatableBlockHeight(target, "#footer-html, .footer-html");

	if (!printWindow) {
		frappe.msgprint({
			title: __("Popup Blocked"),
			message: __("Please allow pop-ups so the generated PDF can open."),
			indicator: "orange",
		});
		return;
	}

	printWindow.document.write(`<p style="font-family: sans-serif; padding: 16px;">${__("Generating PDF...")}</p>`);
	printWindow.document.close();
	printWindow.focus();

	try {
		const response = await fetch("/api/method/ampower_form_builder.print_builder.api.download_report_pdf", {
			method: "POST",
			credentials: "same-origin",
			headers: {
				"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
				"X-Frappe-CSRF-Token": frappe.csrf_token,
			},
			body: new URLSearchParams({
				html,
				orientation,
				page_width: pageWidth,
				page_height: pageHeight,
				margin_top: "10px",
				margin_right: "10px",
				margin_bottom: "10px",
				margin_left: "10px",
				header_height_px: String(headerHeightPx),
				footer_height_px: String(footerHeightPx),
			}),
		});

		if (!response.ok) {
			throw new Error(await response.text());
		}

		const blob = await response.blob();
		const blobUrl = URL.createObjectURL(blob);
		printWindow.location.replace(blobUrl);
		printWindow.focus();
		window.setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000);
	} catch (error) {
		printWindow.close();
		reportViewerError(__("Print Error"), error, __("Unable to generate the PDF."));
	}
}
function openAutofillModal() {
	if (!templateDocName.value) {
		frappe.msgprint({
			title: __("Autofill Unavailable"),
			message: __("Load a form template before using AI autofill."),
			indicator: "orange",
		});
		return;
	}
	autofillModalOpen.value = true;
}

function normalizeAutofillValue(field, value) {
	if (["Table", "Mixed Table"].includes(field.fieldtype)) {
		return normalizeTableValue(field, Array.isArray(value) ? value : []);
	}
	if (field.fieldtype === "Check") {
		return value ? 1 : 0;
	}
	return normalizeFetchedFieldValue(field, value);
}

async function handleAutofillApplied(payload) {
	const appliedCount = applyAutofillPayload(payload);

	if (!appliedCount || !embeddedMode.value || !props.autofillSubmissionStatus) {
		return;
	}

	if (props.frm) {
		props.frm._afbReloadAfterSubmissionSave = true;
	}

	try {
		const submissionName = await syncSubmission({
			method: getSubmissionMethod(),
			status: props.autofillSubmissionStatus,
			validateRequired: false,
		});
		if (submissionName) {
			try {
				await handleSubmissionSaved(submissionName);
			} catch (error) {
				reportViewerError(
					__("Submission Link Error"),
					error,
					__("Unable to link the submission to the parent document."),
				);
			}
		}
	} catch (error) {
		reportViewerError(
			__("Autofill Draft Error"),
			error,
			__("Unable to create the draft submission."),
		);
	} finally {
		if (props.frm) {
			props.frm._afbReloadAfterSubmissionSave = false;
		}
	}
}

function applyAutofillPayload(payload) {
	const sourceValues = payload?.values || payload || {};
	let appliedCount = 0;

	flattenedFields.value.forEach((field) => {
		if (!field?.fieldname || ["HTML", "Heading"].includes(field.fieldtype)) return;
		if (!Object.prototype.hasOwnProperty.call(sourceValues, field.fieldname)) return;

		const nextValue = normalizeAutofillValue(field, sourceValues[field.fieldname]);
		const isEmptyArray = Array.isArray(nextValue) && nextValue.length === 0;
		const isEmptyString = typeof nextValue === "string" && !nextValue.trim();
		if (nextValue === "" || nextValue === null || nextValue === undefined || isEmptyArray || isEmptyString) {
			return;
		}

		values[field.fieldname] = nextValue;
		appliedCount += 1;
	});

	syncCalculatedFields();
	syncFetchedFields();
	formContextVersion.value += 1;
	if (appliedCount) {
		markParentFormDirty();
	}

	frappe.show_alert({
		message: appliedCount
			? __("Autofilled {0} field(s).", [appliedCount])
			: __("No confident autofill values were detected."),
		indicator: appliedCount ? "green" : "orange",
	});

	return appliedCount;
}

function getPayload({ validateRequired = true } = {}) {
	const payload = {};
	const missing = [];

	flattenedFields.value.forEach((field) => {
		if (["HTML", "Heading"].includes(field.fieldtype)) return;
		if (fieldVisibility.value[field.fieldname] === false) return;

		const value = values[field.fieldname];
		payload[field.fieldname] = value;

		const isEmpty = value === null || value === undefined || value === "" || (Array.isArray(value) && value.length === 0);
		if (validateRequired && field.reqd && isEmpty) {
			missing.push(field.label || field.fieldname);
		}
	});

	if (missing.length) {
		let message = __("Please fill the following mandatory fields:") + "<br><ul>";
		missing.slice(0, 5).forEach((label) => {
			message += `<li>${frappe.utils.escape_html(label)}</li>`;
		});
		if (missing.length > 5) {
			message += `<li>${__("and {0} more", [missing.length - 5])}</li>`;
		}
		message += "</ul>";

		frappe.msgprint({
			title: __("Missing Values"),
			message,
			indicator: "red",
		});
		return null;
	}

	return payload;
}

async function handleSubmissionSaved(submissionName) {
	if (!submissionName) return;
	loadedSubmissionName.value = submissionName;

	if (templateDocName.value) {
		await loadSubmissionByName(submissionName, { announce: false });
	}

	if (!embeddedMode.value && templateDocName.value) {
		frappe.set_route(...buildViewerSubmissionRoute(templateDocName.value, submissionName));
	}

	if (embeddedMode.value && typeof props.onSubmissionSaved === "function") {
		await props.onSubmissionSaved(submissionName);
	}
}

async function handlePrimaryAction() {
	if (isReportsListView.value) {
		resetEntry();
		return;
	}

	await waitForPendingFetches();
	try {
		if (typeof props.beforeSubmit === "function") {
			await props.beforeSubmit();
		}
	} catch (error) {
		reportViewerError(__("Submit Error"), error, __("Unable to submit form."));
		return;
	}
	if (getActiveSubmissionName()) {
		await updateForm();
		return;
	}
	await submitForm();
}

async function flushActiveFieldInput() {
	if (typeof document === "undefined" || typeof window === "undefined") return;
	const activeElement = document.activeElement;
	if (activeElement && typeof activeElement.blur === "function") {
		activeElement.blur();
	}
	await new Promise((resolve) => window.requestAnimationFrame(resolve));
}

async function submitForm() {
	if (savingSubmission.value) return;
	savingSubmission.value = true;
	try {
		await flushActiveFieldInput();
		await waitForPendingFetches();
		const payload = getPayload();
		if (!payload || !templateDocName.value) return;

		const response = await frappe.call({
			method: "ampower_form_builder.api.save_submission",
			args: {
				form_template: templateDocName.value,
				data: JSON.stringify(payload),
				reference_doctype: embeddedMode.value ? (props.parentDoctype || "") : "",
				reference_name: embeddedMode.value ? (props.parentDocname || "") : "",
			},
			freeze: true,
			freeze_message: __("Submitting..."),
		});
		if (!response.message) return;

		frappe.msgprint({
			title: __("Success"),
			message: __("Form submitted successfully."),
			indicator: "green",
		});

		try {
			await handleSubmissionSaved(response.message.name);
		} catch (error) {
			reportViewerError(__("Submission Link Error"), error, __("Unable to link the submission to the parent document."));
		}
		if (embeddedMode.value) return;
		fetchSubmissions();
	} catch (error) {
		reportViewerError(__("Submit Error"), error, __("Unable to submit form."));
	} finally {
		savingSubmission.value = false;
	}
}

async function updateForm() {
	if (savingSubmission.value) return;
	savingSubmission.value = true;
	try {
		await flushActiveFieldInput();
		await waitForPendingFetches();
		const payload = getPayload();
		const activeSubmissionName = getActiveSubmissionName();
		if (!payload || !activeSubmissionName) return;

		if (loadedSubmissionName.value !== activeSubmissionName) {
			loadedSubmissionName.value = activeSubmissionName;
		}

		const response = await frappe.call({
			method: "ampower_form_builder.api.update_submission",
			args: {
				submission_name: activeSubmissionName,
				data: JSON.stringify(payload),
				reference_doctype: embeddedMode.value ? (props.parentDoctype || "") : "",
				reference_name: embeddedMode.value ? (props.parentDocname || "") : "",
			},
			freeze: true,
			freeze_message: __("Updating..."),
		});
		if (!response.message) return;

		frappe.msgprint({
			title: __("Success"),
			message: __("Form updated successfully."),
			indicator: "green",
		});

		try {
			await handleSubmissionSaved(response.message.name || activeSubmissionName);
		} catch (error) {
			reportViewerError(__("Submission Link Error"), error, __("Unable to link the submission to the parent document."));
		}
		if (embeddedMode.value) return;
		fetchSubmissions();
	} catch (error) {
		reportViewerError(__("Update Error"), error, __("Unable to update form."));
	} finally {
		savingSubmission.value = false;
	}
}

async function syncSubmission(options = {}) {
	if (isReadOnly.value) {
		return getActiveSubmissionName();
	}
	if (embeddedMode.value && !templateDocName.value) {
		return getActiveSubmissionName();
	}
	await flushActiveFieldInput();
	await waitForPendingFetches();

	try {
		if (typeof props.beforeSubmit === "function") {
			await props.beforeSubmit();
		}
	} catch (error) {
		throw error;
	}

	const payload = getPayload({ validateRequired: options.validateRequired !== false });
	if (!payload || !templateDocName.value) {
		throw new Error(__("Unable to prepare form submission."));
	}

	if (embeddedMode.value && !getActiveSubmissionName()) {
		const resolvedName = await resolveSubmissionNameForReference();
		if (resolvedName) {
			loadedSubmissionName.value = resolvedName;
		}
	}

	const activeSubmissionName = getActiveSubmissionName();
	const method = options.method || getSubmissionMethod();
	const hasExistingSubmission = method === "ampower_form_builder.api.update_submission";

	const args = {
		form_template: templateDocName.value,
		data: JSON.stringify(payload),
		reference_doctype: embeddedMode.value ? (props.parentDoctype || "") : "",
		reference_name: embeddedMode.value ? (props.parentDocname || "") : "",
	};

	if (hasExistingSubmission) {
		args.submission_name = activeSubmissionName;
	}
	if (options.status) {
		args.status = options.status;
	}

	try {
		const response = await frappe.call({
			method,
			args,
		});

		const submissionName = response.message?.name || activeSubmissionName || "";
		if (submissionName) {
			loadedSubmissionName.value = submissionName;
		}
		return submissionName;
	} catch (error) {
		reportViewerError(__("Sync Error"), error, __("Unable to sync the embedded form before saving."));
		throw error;
	}
}

defineExpose({
	syncSubmission,
	getSubmissionMethod,
	openAutofillModal,
	syncRouteContext,
	isReadOnly: () => isReadOnly.value,
	canSyncSubmission,
});

watch(
	() => sections.value,
	() => {
		flattenedFields.value.forEach((field) => {
			if (!(field.fieldname in values)) {
				values[field.fieldname] = getEmptyValue(field);
			}
		});
		syncCalculatedFields();
	},
	{ deep: true }
);
</script>

<style scoped>
.fv-layout-container {
	min-height: calc(100vh - 72px);
	color: var(--fv-text-main);
}

.fv-main-form {
	min-height: inherit;
}

.fv-container.fv-view-shell {
	display: flex;
	flex-direction: column;
	gap: 16px;
	padding: 18px 18px 24px;
	background: var(--fv-surface);
	border: 1px solid var(--fv-border);
	border-radius: var(--fv-radius);
	box-shadow: var(--fv-shadow-sm);
}

.fv-view-body {
	display: flex;
	flex-direction: column;
	gap: 16px;
}

.fv-print-controls {
	display: flex;
	align-items: center;
	gap: 8px;
	flex-wrap: wrap;
}

.fv-print-format-select {
	min-width: 220px;
}

</style>
