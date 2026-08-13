<template>
	<div class="afb-shell">
		<header class="afb-header">
			<div class="afb-header-main">
				<div class="afb-header-title">
										<p class="afb-kicker">Ampower Form Builder</p>
					<nav class="afb-breadcrumb" aria-label="Breadcrumb">
						<span class="afb-breadcrumb-item">Home</span>
						<span class="afb-breadcrumb-separator">/</span>
						<span class="afb-breadcrumb-item">Ampower Form Builder</span>
						<template v-if="store.currentTemplate.name || store.currentTemplate.form_name">
							<span class="afb-breadcrumb-separator">/</span>
							<span class="afb-breadcrumb-item is-current">{{ store.currentTemplate.form_name || store.currentTemplate.name }}</span>
						</template>
					</nav>
					<div v-if="showVersionMeta" class="afb-version-row">
						<span class="afb-version-pill">{{ `${t("Version")} ${store.currentTemplate.version_label || "1.0"}` }}</span>
						<span v-if="store.currentTemplate.base_form_name" class="afb-version-copy">
							{{ `${t("Family")}: ${store.currentTemplate.base_form_name}` }}
						</span>
					</div>
					<input
						v-model="title"
						class="afb-title-input"
						type="text"
						placeholder="Untitled Form"
						:disabled="store.isSaving || !isNewForm"
					>
					<textarea
						v-model="description"
						class="afb-description-input"
						rows="2"
						placeholder="Describe this form template"
						:disabled="store.isSaving"
					></textarea>
				</div>
				<div class="afb-form-meta">
					<div class="afb-meta-field">
						<span class="afb-meta-label">{{ t("Form Type") }}</span>
						<select
							class="form-control afb-meta-select"
							:disabled="store.isSaving"
							:value="store.currentTemplate.form_type || 'Form'"
							@change="setFormType($event.target.value)"
						>
							<option value="Form">{{ t("Form") }}</option>
							<option value="Doctype Integration">{{ t("Doctype Integration") }}</option>
						</select>
					</div>
					<div v-if="isIntegrationForm" class="afb-meta-field">
						<span class="afb-meta-label">{{ t("Target DocType") }}</span>
						<LinkControl
							:df="targetDoctypeDf"
							:model-value="store.currentTemplate.target_doctype"
							:no_label="true"
							@update:modelValue="setTargetDoctype"
						/>
					</div>
				</div>
			</div>
			<div class="afb-header-actions">
				<div class="menu-btn-group">
					<button
						type="button"
						class="btn btn-default icon-btn"
						data-toggle="dropdown"
						aria-expanded="false"
						aria-label="Menu"
						:title="t('Menu')"
					>
						<span>
							<span class="menu-btn-group-label" data-label="">
								<svg class="icon icon-sm">
									<use href="#icon-dot-horizontal"></use>
								</svg>
							</span>
						</span>
					</button>
					<ul class="dropdown-menu dropdown-menu-right" role="menu">
						<li>
							<a class="grey-link dropdown-item" href="#" @click.prevent="loadTemplate">
								<span class="menu-item-label">{{ t("Load Form") }}</span>
							</a>
						</li>
						<li>
							<a class="grey-link dropdown-item" href="#" @click.prevent="loadDoctype">
								<span class="menu-item-label">{{ t("Load Doctype Form") }}</span>
							</a>
						</li>
						<li>
							<a class="grey-link dropdown-item" href="#" @click.prevent="openAiAgent">
								<span class="menu-item-label">{{ t("Add via AI Agent") }}</span>
							</a>
						</li>
						<li class="dropdown-divider user-action"></li>
						<li>
							<a class="grey-link dropdown-item" href="#" @click.prevent="newForm">
								<span class="menu-item-label">{{ t("New Form") }}</span>
							</a>
						</li>
						<li>
							<a class="grey-link dropdown-item" href="#" @click.prevent="duplicateExistingForm">
								<span class="menu-item-label">{{ t("Duplicate Existing Form") }}</span>
							</a>
						</li>
						<li v-if="canCreateVersion">
							<a class="grey-link dropdown-item" href="#" @click.prevent="createVersion">
								<span class="menu-item-label">{{ t("Create New Version") }}</span>
							</a>
						</li>
						<li>
							<a class="grey-link dropdown-item" href="#" @click.prevent="previewForm">
								<span class="menu-item-label">{{ t("Preview") }}</span>
							</a>
						</li>
						<li class="dropdown-divider user-action"></li>
						<li>
							<a class="grey-link dropdown-item" href="#" @click.prevent="reloadBuilder">
								<span class="menu-item-label">{{ t("Reload") }}</span>
							</a>
						</li>
					</ul>
				</div>
				<button
					v-if="canCreateDoctype"
					class="btn btn-default btn-sm"
					:disabled="store.isSaving"
					@click="createDoctype"
				>
					{{ t("Create DocType") }}
				</button>
				<div class="afb-save-status">
					<button class="btn btn-primary btn-sm" :disabled="store.isSaving" @click="saveTemplate">
						{{ store.isSaving ? "Saving..." : (store.dirty ? "Save Changes" : "Saved") }}
					</button>
					<div v-if="store.dirty && store.dirtyReason" class="afb-dirty-reason">{{ store.dirtyReason }}</div>
				</div>
			</div>
		</header>

		<div class="afb-workspace">
			<Canvas />
			<PropertiesPanel />
		</div>

		<PreviewModal />
		<AiFormImportModal
			:open="aiImportOpen"
			@close="aiImportOpen = false"
			@applied="handleAiDraftApplied"
		/>
	</div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useFormBuilderStore } from "./store.js";
import Canvas from "./components/Canvas.vue";
import PropertiesPanel from "./components/PropertiesPanel.vue";
import PreviewModal from "./components/PreviewModal.vue";
import LinkControl from "./components/controls/LinkControl.vue";
import AiFormImportModal from "./components/AiFormImportModal.vue";

const store = useFormBuilderStore();
const t = window.__ || ((text) => text);
const aiImportOpen = ref(false);
const isNewForm = computed(() => !store.currentTemplate.name);
const canCreateVersion = computed(() => Boolean(store.currentTemplate.name));
const showVersionMeta = computed(() => Boolean(
	store.currentTemplate.name
	|| store.currentTemplate.form_name
	|| store.currentTemplate.base_form_name
));
const isIntegrationForm = computed(() => (
	store.currentTemplate.form_type === "Doctype Integration"
	|| Boolean(store.currentTemplate.target_doctype)
));
const canCreateDoctype = computed(() => Boolean(window.frappe?.user?.has_role?.("System Manager")));

const targetDoctypeDf = computed(() => ({
	fieldtype: "Link",
	label: "",
	options: "DocType",
}));

const title = computed({
	get: () => store.currentTemplate.form_name,
	set: (value) => {
		if ((store.currentTemplate.form_name || "") === (value || "")) return;
		store.currentTemplate.form_name = value;
		store.setDirty("form_name_changed");
	},
});

const description = computed({
	get: () => store.currentTemplate.description,
	set: (value) => {
		if ((store.currentTemplate.description || "") === (value || "")) return;
		store.currentTemplate.description = value;
		store.setDirty("description_changed");
	},
});

function setFormType(value) {
	const nextValue = value || "Form";
	const nextTargetDoctype = nextValue === "Doctype Integration"
		? (store.currentTemplate.target_doctype || store.currentTemplate.loaded_doctype || "")
		: "";
	if (
		(store.currentTemplate.form_type || "Form") === nextValue
		&& (store.currentTemplate.target_doctype || "") === nextTargetDoctype
	) {
		return;
	}
	store.currentTemplate.form_type = nextValue;
	store.currentTemplate.target_doctype = nextTargetDoctype;
	store.setDirty("form_type_changed");
}

function setTargetDoctype(value) {
	const nextValue = value || "";
	if ((store.currentTemplate.target_doctype || "") === nextValue) return;
	store.currentTemplate.target_doctype = nextValue;
	store.setDirty("target_doctype_changed");
}

function loadTemplate() {
	frappe.prompt(
		[{ fieldname: "template", fieldtype: "Link", options: "Dynamic Form Template", label: "Template", reqd: 1 }],
		(values) => store.loadTemplate(values.template),
		t("Load Form"),
		t("Load"),
	);
}

function loadDoctype() {
	frappe.prompt(
		[{ fieldname: "doctype", fieldtype: "Link", options: "DocType", label: "DocType", reqd: 1 }],
		(values) => store.loadDoctype(values.doctype),
		t("Load DocType Form"),
		t("Load"),
	);
}

function openAiAgent() {
	const openModal = () => {
		aiImportOpen.value = true;
	};

	if (store.dirty || store.hasContent) {
		frappe.confirm(
			t("This will replace the current builder draft when the AI result is applied. Continue?"),
			openModal,
		);
		return;
	}

	openModal();
}

function handleAiDraftApplied(payload) {
	store.applyAiDraft(payload || {});
	aiImportOpen.value = false;

	const warnings = Array.isArray(payload?.warnings) ? payload.warnings : [];
	frappe.show_alert({
		message: warnings.length
			? t("AI draft applied with warnings. Review the canvas before saving.")
			: t("AI draft applied to the builder."),
		indicator: warnings.length ? "orange" : "green",
	});
}

async function flushActiveFieldInput() {
	if (typeof document === "undefined") return;
	const activeElement = document.activeElement;
	if (activeElement && typeof activeElement.blur === "function") {
		activeElement.blur();
	}
	await Promise.resolve();
}

async function saveTemplate() {
	await flushActiveFieldInput();
	await store.saveTemplate();
}

async function createVersion() {
	if (!store.currentTemplate.name) {
		frappe.msgprint({
			title: t("Versioning Unavailable"),
			message: t("Load or save a form before creating a new version."),
			indicator: "orange",
		});
		return;
	}

	let context = null;
	window.frappe?.dom?.freeze?.(t("Preparing version details..."));
	try {
		const { message } = await frappe.call({
			method: "ampower_form_builder.api.get_template_version_context",
			args: { template_name: store.currentTemplate.name },
		});
		context = message || null;
	} catch (error) {
		frappe.msgprint({
			title: t("Versioning Error"),
			message: error?.message || t("Unable to prepare a new form version."),
			indicator: "red",
		});
		return;
	} finally {
		window.frappe?.dom?.unfreeze?.();
	}

	if (!context) {
		frappe.msgprint({
			title: t("Versioning Error"),
			message: t("Unable to prepare a new form version."),
			indicator: "red",
		});
		return;
	}

	frappe.prompt(
		[
			{
				fieldname: "version_label",
				fieldtype: "Data",
				label: t("New Version"),
				reqd: 1,
				default: context.next_version_label || "1.1",
				description: t("Use dotted numeric versions like 1.1 or 2.0."),
			},
			{
				fieldname: "form_name",
				fieldtype: "Data",
				label: t("New Form Name"),
				reqd: 1,
				default: context.suggested_form_name || "",
			},
		],
		(values) => {
			store.createVersionDraft({
				...context,
				version_label: String(values.version_label || "").trim(),
				form_name: String(values.form_name || "").trim(),
			});
			frappe.show_alert({
				message: t("New version draft created in the builder."),
				indicator: "green",
			});
		},
		t("Create New Version"),
		t("Create"),
	);
}

async function createDoctype() {
	if (store.isSaving || !canCreateDoctype.value) return;

	try {
		if (store.dirty || !store.currentTemplate.name) {
			await saveTemplate();
		}
	} catch {
		return;
	}

	const defaultDoctypeName = store.currentTemplate.form_name || store.currentTemplate.name || t("New DocType");
	const defaultModule = store.currentTemplate.module || "Ampower Form Builder";

	frappe.prompt(
		[
			{
				fieldname: "doctype_name",
				fieldtype: "Data",
				label: t("DocType Name"),
				reqd: 1,
				default: defaultDoctypeName,
			},
			{
				fieldname: "module",
				fieldtype: "Link",
				options: "Module Def",
				label: t("Module"),
				reqd: 1,
				default: defaultModule,
			},
		],
		async (values) => {
			const doctypeName = String(values.doctype_name || "").trim();
			const moduleName = String(values.module || "").trim();
			if (!doctypeName) {
				return;
			}

			window.frappe?.dom?.freeze?.(t("Creating DocType..."));
			try {
				const response = await frappe.call({
					method: "ampower_form_builder.api.create_doctype_from_template",
					args: {
						template_name: store.currentTemplate.name,
						doctype_name: doctypeName,
						module: moduleName,
					},
				});
				const createdName = response?.message?.doctype_name || doctypeName;
				frappe.show_alert({
					message: t("DocType created successfully."),
					indicator: "green",
				});
				frappe.set_route("Form", "DocType", createdName);
			} catch (error) {
				frappe.msgprint({
					title: t("Create DocType Error"),
					message: error?.message || t("Unable to create DocType."),
					indicator: "red",
				});
			} finally {
				window.frappe?.dom?.unfreeze?.();
			}
		},
		t("Create DocType"),
		t("Create"),
	);
}

function handleSaveShortcut(event) {
	if (!(event.ctrlKey || event.metaKey) || String(event.key).toLowerCase() !== "s") {
		return;
	}

	event.preventDefault();

	if (store.isSaving) {
		return;
	}

	saveTemplate();
}

function previewForm() {
	store.openPreview();
}

function newForm() {
	store.newForm();
}

function duplicateExistingForm() {
	const openDuplicatePrompt = () => {
		frappe.prompt(
			[
				{
					fieldname: "source_template",
					fieldtype: "Link",
					options: "Dynamic Form Template",
					label: t("Source Form"),
					reqd: 1,
					default: store.currentTemplate.name || "",
				},
				{
					fieldname: "amended",
					fieldtype: "Check",
					label: t("Amended"),
					default: 0,
				},
				{
					fieldname: "amended_template",
					fieldtype: "Link",
					options: "Dynamic Form Template",
					label: t("Amend For Form"),
					depends_on: "eval:doc.amended",
					mandatory_depends_on: "eval:doc.amended",
				},
			],
			async (values) => {
				const sourceTemplate = String(values.source_template || "").trim();
				const isAmended = Boolean(Number(values.amended || 0));
				const amendedTemplate = String(values.amended_template || "").trim();

				if (!sourceTemplate) {
					return;
				}
				if (isAmended && !amendedTemplate) {
					frappe.msgprint({
						title: t("Validation Error"),
						message: t("Select the form for which the amended version should be created."),
						indicator: "red",
					});
					return;
				}

				let sourceDoc = null;
				let amendedContext = null;

				window.frappe?.dom?.freeze?.(t("Preparing duplicate form..."));
				try {
					const sourceResponse = await frappe.call({
						method: "ampower_form_builder.api.get_form_schema",
						args: { form_template: sourceTemplate },
					});
					sourceDoc = sourceResponse?.message || null;

					if (isAmended) {
						const amendedResponse = await frappe.call({
							method: "ampower_form_builder.api.get_template_version_context",
							args: { template_name: amendedTemplate },
						});
						amendedContext = amendedResponse?.message || null;
					}
				} catch (error) {
					frappe.msgprint({
						title: t("Duplicate Error"),
						message: error?.message || t("Unable to prepare the duplicate form."),
						indicator: "red",
					});
					return;
				} finally {
					window.frappe?.dom?.unfreeze?.();
				}

				if (!sourceDoc) {
					frappe.msgprint({
						title: t("Duplicate Error"),
						message: t("Unable to load the source form."),
						indicator: "red",
					});
					return;
				}

				const defaultFormName = isAmended
					? (amendedContext?.suggested_form_name || "")
					: `${sourceDoc.form_name || sourceTemplate} ${t("Copy")}`;

				frappe.prompt(
					[
						{
							fieldname: "form_name",
							fieldtype: "Data",
							label: t("New Form Name"),
							reqd: 1,
							default: defaultFormName,
						},
						...(isAmended
							? [{
								fieldname: "version_label",
								fieldtype: "Data",
								label: t("Version"),
								reqd: 1,
								default: amendedContext?.next_version_label || "1.1",
								description: t("Use dotted numeric versions like 1.1 or 2.0."),
							}]
							: []),
					],
					(duplicateValues) => {
						const formName = String(duplicateValues.form_name || "").trim();
						const versionLabel = String(
							duplicateValues.version_label
							|| amendedContext?.next_version_label
							|| "1.0"
						).trim();

						store.createDuplicatedDraft(
							sourceDoc,
							isAmended
								? {
									form_name: formName,
									form_type: amendedContext?.form_type || sourceDoc.form_type || "Form",
									target_doctype: amendedContext?.target_doctype ?? sourceDoc.target_doctype ?? "",
									description: sourceDoc.description || amendedContext?.description || "",
									base_form_name: amendedContext?.base_form_name || amendedContext?.form_name || formName,
									version_label: versionLabel,
									version_group: amendedContext?.version_group || "",
									source_template: amendedTemplate,
									dirtyReason: "template_amended_from_duplicate",
								}
								: {
									form_name: formName,
									form_type: sourceDoc.form_type || "Form",
									target_doctype: sourceDoc.target_doctype || "",
									description: sourceDoc.description || "",
									base_form_name: formName,
									version_label: "1.0",
									version_group: "",
									source_template: "",
									dirtyReason: "template_duplicated",
								}
						);

						frappe.show_alert({
							message: isAmended
								? t("Amended form draft created from the selected source form.")
								: t("Duplicate form draft created successfully."),
							indicator: "green",
						});
					},
					isAmended ? t("Create Amended Form") : t("Duplicate Form"),
					t("Create"),
				);
			},
			t("Duplicate Existing Form"),
			t("Next"),
		);
	};

	if (store.dirty || store.hasContent) {
		frappe.confirm(
			t("This will replace the current builder draft. Continue?"),
			openDuplicatePrompt,
		);
		return;
	}

	openDuplicatePrompt();
}

function reloadBuilder() {
	window.location.reload();
}

onMounted(() => {
	if (!store.sections.length) {
		store.newForm();
	}

	window.addEventListener("keydown", handleSaveShortcut);
});

onBeforeUnmount(() => {
	window.removeEventListener("keydown", handleSaveShortcut);
});
</script>

<style scoped lang="scss">
.afb-header {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 24px;
}

.afb-header-main {
	flex: 1 1 auto;
	min-width: 0;
	display: flex;
	align-items: flex-start;
	gap: 32px;
}

.afb-header-title {
	flex: 1 1 420px;
	min-width: 280px;
}

.afb-version-row {
	display: flex;
	align-items: center;
	gap: 10px;
	margin-bottom: 10px;
	flex-wrap: wrap;
}

.afb-version-pill {
	display: inline-flex;
	align-items: center;
	padding: 4px 10px;
	border-radius: 999px;
	background: #eef2ff;
	color: #3730a3;
	font-size: 12px;
	font-weight: 700;
}

.afb-version-copy {
	font-size: 12px;
	font-weight: 600;
	color: var(--text-muted, #6c7680);
}

.afb-form-meta {
	flex: 0 1 620px;
	display: grid;
	grid-template-columns: repeat(2, minmax(240px, 1fr));
	gap: 12px 16px;
	margin-top: 24px;
}

.afb-meta-field {
	display: flex;
	flex-direction: column;
	gap: 4px;
}

.afb-meta-label {
	font-size: 12px;
	font-weight: 600;
	color: var(--text-muted, #6c7680);
}

.afb-meta-field :deep(.control),
.afb-meta-field :deep(.control.frappe-control),
.afb-meta-field :deep(.control-label),
.afb-meta-field :deep(.form-control),
.afb-meta-field :deep(.link-input) {
	width: 100%;
}

.afb-meta-field :deep(.form-group),
.afb-meta-field :deep(.frappe-control) {
	margin-bottom: 0 !important;
}

.afb-save-status {
	display: flex;
	flex-direction: column;
	align-items: flex-end;
	gap: 4px;
}

.afb-dirty-reason {
	font-size: 11px;
	line-height: 1.2;
	color: var(--text-muted, #6c7680);
	max-width: 180px;
	text-align: right;
}

.afb-header-actions {
	flex: 0 0 auto;
	margin-left: auto;
	padding-top: 10px;
	display: flex;
	align-items: center;
	gap: 8px;
}

@media (max-width: 1200px) {
	.afb-header {
		flex-direction: column;
	}

	.afb-header-main {
		width: 100%;
		flex-direction: column;
		gap: 16px;
	}

	.afb-form-meta {
		width: 100%;
		grid-template-columns: minmax(240px, 1fr);
		margin-top: 0;
	}

	.afb-header-actions {
		width: 100%;
		padding-top: 0;
		margin-left: 0;
		display: flex;
		justify-content: flex-end;
	}
}

@media (max-width: 768px) {
	.afb-shell {
		height: auto;
		min-height: calc(100vh - 72px);
	}

	.afb-header {
		gap: 16px;
		padding: 12px;
	}

	.afb-header-main {
		gap: 12px;
	}

	.afb-title-input {
		font-size: 20px;
	}

	.afb-description-input {
		min-height: 56px;
	}

	.afb-form-meta {
		grid-template-columns: 1fr;
		gap: 10px;
	}

	.afb-meta-field {
		min-width: 0;
	}

	.afb-header-actions {
		width: 100%;
		flex-wrap: wrap;
		justify-content: stretch;
	}

	.afb-header-actions :deep(.menu-btn-group),
	.afb-header-actions :deep(.btn) {
		flex: 1 1 0;
		min-width: 0;
	}

	.afb-header-actions :deep(.btn) {
		width: 100%;
	}

	.afb-workspace {
		display: flex;
		flex-direction: column;
	}

	.afb-sidebar-wrap,
	.afb-canvas,
	.afb-properties {
		width: 100%;
		overflow: visible;
	}

	.afb-sidebar-wrap {
		padding: 0;
	}

	.afb-canvas {
		padding: 12px;
	}

	.afb-properties {
		border-top: 1px solid var(--afb-border);
		border-left: none;
		padding: 12px;
	}
}
</style>
