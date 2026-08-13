<template>
	<div class="fv-preview-surface" :class="{ 'is-selector-mode': selectorMode, 'is-loading': loadingTemplate }">
		<div v-if="tabs.length > 1" class="fiq-preview-tabs">
			<button
				v-for="(tab, index) in tabs"
				:key="`${tab.label}-${index}`"
				type="button"
				class="fiq-preview-tab"
				:class="{ active: currentTab === index }"
				:title="tab.label"
				@click="$emit('update:currentTab', index)"
			>
				{{ tab.label }}
			</button>
		</div>

		<div class="fv-form-wrapper">
			<div v-if="loadingTemplate" class="fv-state-card fv-state-loading">
				<div class="fv-state-title">{{ __("Loading form...") }}</div>
				<div class="fv-state-copy">{{ __("Pulling the form structure into the viewer.") }}</div>
			</div>

			<div v-else-if="selectorMode" class="fv-selector-state">
				<div class="fv-selector-toolbar">
					<div class="fv-selector-filters">
						<input
							v-model="templateSearchId"
							class="form-control fv-selector-input"
							type="text"
							:placeholder="__('ID')"
						>
						<input
							v-model="templateSearchName"
							class="form-control fv-selector-input"
							type="text"
							:placeholder="__('Form Name')"
						>


					</div>
                    <div class="fv-selector-actions">
                        <button type="button" class="fv-selector-pill" @click="clearFilters">
                            <span class="fv-selector-pill-icon">&#10005;</span>
                            <span>{{ __("Clear") }}</span>
                        </button>
                        <button type="button" class="fv-selector-pill" @click="toggleUpdatedSort">
                            <span class="fv-selector-pill-icon" aria-hidden="true">&#8645;</span>
                            <span>{{ sortDirectionLabel }}</span>
                        </button>
                    </div>
					</div>

				<div class="fv-selector-panel">
					<div class="fv-selector-head">


						<span>{{ __("ID") }}</span>
						<span>{{ __("Form Name") }}</span>


						<span>{{ __("Is Active") }}</span>
						<span>{{ __("Target DocType") }}</span>
						<span>{{ __("Name Link") }}</span>
						<span class="fv-selector-head-right">{{ __("Last Updated On") }}</span>
					</div>

					<div v-if="loadingSelectorTemplates" class="fv-state-card fv-state-loading">
						<div class="fv-state-title">{{ __("Loading templates...") }}</div>
						<div class="fv-state-copy">{{ __("Fetching active form templates for the directory view.") }}</div>
					</div>

					<template v-else-if="filteredTemplates.length">
						<div
							v-for="template in filteredTemplates"
							:key="template.name"
							class="fv-selector-row"
							role="button"
							tabindex="0"
							@click="openTemplate(template.name)"
							@keydown.enter.prevent="openTemplate(template.name)"
							@keydown.space.prevent="openTemplate(template.name)"
						>


							<span class="fv-selector-id">{{ template.name }}</span>
							<span class="fv-selector-name">
								<strong>{{ template.display_name || template.form_name || template.name }}</strong>
								<small v-if="template.description">{{ template.description }}</small>
							</span>


							<span class="fv-selector-active">
								<span class="fv-selector-checkmark" aria-hidden="true">&#10003;</span>
							</span>
							<span class="fv-selector-doctype">{{ template.target_doctype || "-" }}</span>
							<span class="fv-selector-link">{{ template.base_form_name || template.form_name || "-" }}</span>
							<span class="fv-selector-updated">{{ formatUpdatedOn(template.modified) }}</span>
						</div>
					</template>

					<div v-else class="fv-state-card fv-state-empty">
						<div class="fv-state-title">{{ __("No active templates found.") }}</div>
						<div class="fv-state-copy">{{ __("Use Add Dynamic Form Template to create the first form viewer record.") }}</div>
					</div>
				</div>
			</div>

			<div v-else-if="activeSections.length" class="fiq-preview-form">
				<section
					v-for="section in activeSections"
					:key="section.id"
					class="fiq-preview-section"
				>
					<h4 v-if="section.section_label" class="fiq-section-head">{{ section.section_label }}</h4>
					<div class="fiq-preview-row">
						<div v-for="column in section.columns" :key="column.id" class="fiq-preview-col">
							<div class="fiq-preview-fields">
								<FormViewerField
									v-for="field in column.items"
									:key="field.id || field.fieldname"
									:field="field"
									:value="values[field.fieldname]"
									:is-visible="fieldVisibility[field.fieldname] !== false"
									:is-read-only="isReadOnly"
									@update:value="$emit('update-field', field, $event)"
								/>
							</div>
						</div>
					</div>
				</section>
			</div>

			<div v-else class="fv-state-card fv-state-empty">
				<div class="fv-state-title">{{ __("Nothing to show") }}</div>
				<div v-if="emptyStateMessage" class="fv-state-copy">{{ emptyStateMessage }}</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, ref } from "vue";
import FormViewerField from "./components/FormViewerField.vue";

const props = defineProps({
	tabs: { type: Array, default: () => [] },
	currentTab: { type: Number, default: 0 },
	loadingTemplate: { type: Boolean, default: false },
	selectorMode: { type: Boolean, default: false },
	activeTemplates: { type: Array, default: () => [] },
	activeSections: { type: Array, default: () => [] },
	values: { type: Object, default: () => ({}) },
	fieldVisibility: { type: Object, default: () => ({}) },
	emptyStateMessage: { type: String, default: "" },
	isReadOnly: { type: Boolean, default: false },
	loadingSelectorTemplates: { type: Boolean, default: false },
});

const emit = defineEmits(["update:currentTab", "open-template", "update-field"]);

const templateSearchId = ref("");
const templateSearchName = ref("");


const templateSortDescending = ref(true);




const filteredTemplates = computed(() => {
	const idQuery = templateSearchId.value.trim().toLowerCase();
	const nameQuery = templateSearchName.value.trim().toLowerCase();


	return [...props.activeTemplates]
		.filter((template) => {
			const templateId = String(template.name || "").toLowerCase();
			const templateName = String(template.display_name || template.form_name || "").toLowerCase();
			return (!idQuery || templateId.includes(idQuery))
				&& (!nameQuery || templateName.includes(nameQuery));
		})
		.sort((left, right) => {
			const leftTime = Date.parse(left.modified || "") || 0;
			const rightTime = Date.parse(right.modified || "") || 0;
			return templateSortDescending.value ? rightTime - leftTime : leftTime - rightTime;
		});
});

const sortDirectionLabel = computed(() => (templateSortDescending.value ? __("Last Updated On") : __("Oldest First")));

function clearFilters() {
	templateSearchId.value = "";
	templateSearchName.value = "";


}

function openTemplate(name) {
	if (!name) return;
	emit("open-template", name);
}

function toggleUpdatedSort() {
	templateSortDescending.value = !templateSortDescending.value;
}

function toggleFilterPanel() {
	frappe.show_alert({
		message: __("Use the search fields above to narrow the list."),
		indicator: "blue",
	});
}

function formatUpdatedOn(value) {
	if (!value) return "-";
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return String(value);
	return new Intl.DateTimeFormat(undefined, {
		month: "short",
		day: "2-digit",
		year: "numeric",
	}).format(date);
}
</script>

<style scoped>
.fv-template-card-head,
.fv-template-card-meta {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 0.75rem;
}

.fv-template-card-badges {
	display: flex;
	align-items: center;
	gap: 0.35rem;
	flex-wrap: nowrap;
	justify-content: flex-end;
}

.fv-template-card-copy {
	margin: 0.7rem 0 0;
	font-size: 0.85rem;
	line-height: 1.5;
	color: var(--text-muted);
}

.fv-template-card-meta {
	margin-top: 1rem;
	font-size: 0.78rem;
	color: var(--text-muted);
}

.fv-template-card-badge {
	display: inline-flex;
	align-items: center;
	padding: 0.25rem 0.6rem;
	border-radius: var(--border-radius-full, 999px);
	background: var(--subtle-fg);
	color: var(--text-muted);
	font-size: 0.72rem;
	font-weight: 700;
	white-space: nowrap;
}

.fv-template-card-badge.is-latest {
	background: rgba(22, 163, 74, 0.12);
	color: #15803d;
}

.fv-selector-state {
	display: flex;
	flex-direction: column;
	gap: 1rem;
}

.fv-selector-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: nowrap;
}

.fv-selector-filters {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: nowrap;
  flex: 1 1 auto;
}

.fv-selector-input {
  min-width: 220px;
  height: 38px;
  border-radius: var(--border-radius-tiny, 4px);
  background: #ffffff;
  border: 1px solid #d1d8dd;
  box-shadow: none;
}

.fv-selector-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: nowrap;
}

.fv-selector-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  min-height: 38px;
  padding: 0.45rem 0.8rem;
  border: 1px solid #d1d8dd;
  border-radius: var(--border-radius-tiny, 4px);
  background: #ffffff;
  color: #111827;
  font-weight: 500;
}

.fv-selector-pill:hover {
	background: var(--subtle-fg);
}

.fv-selector-pill-icon {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 1rem;
	font-size: 0.95rem;
	line-height: 1;
}

.fv-selector-panel {
  border: 1px solid #d1d8dd;
  border-radius: var(--border-radius-tiny, 4px);
  background: #ffffff;
  overflow: auto;
}

.fv-selector-head,
.fv-selector-row {
  display: grid;
  grid-template-columns:
    minmax(140px, 1.1fr) minmax(220px, 1.6fr) minmax(120px, 0.85fr)
    minmax(110px, 0.7fr) minmax(150px, 1fr) minmax(160px, 1fr);
  gap: 8px;
  align-items: center;
}

.fv-selector-head {
  padding: 0.8rem 1rem;
  border-bottom: 1px solid #d1d8dd;
  background: var(--subtle-fg);
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.fv-selector-head-right {
  text-align: right;
}

.fv-selector-row {
  padding: 0.85rem 1rem;
  border: 0;
  border-bottom: 1px solid #e5e7eb;
  background: transparent;
  transition: background-color 0.16s ease, box-shadow 0.16s ease;
  text-align: left;
}

.fv-selector-row:last-of-type {
  border-bottom: 0;
}

.fv-selector-row:hover {
  background: var(--subtle-fg);
}

.fv-selector-row:focus {
  outline: 2px solid rgba(249, 115, 22, 0.35);
  outline-offset: -2px;
}

.fv-selector-id,
.fv-selector-doctype,
.fv-selector-link,
.fv-selector-updated {
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.fv-selector-name {
	display: flex;
	flex-direction: column;
	gap: 0.2rem;
	min-width: 0;
}

.fv-selector-name strong {
	font-size: 0.93rem;
	font-weight: 700;
	color: var(--text-color);
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.fv-selector-name small {
	font-size: 0.79rem;
	color: var(--text-muted);
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.fv-selector-active {
	display: flex;
	align-items: center;
}

.fv-selector-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.28rem 0.65rem;
  border-radius: var(--border-radius-tiny, 4px);
  border: 1px solid #d1d8dd;
  background: var(--subtle-fg);
  color: #334155;
  font-size: 0.75rem;
  font-weight: 700;
  white-space: nowrap;
}

.fv-selector-checkmark {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 22px;
	height: 22px;
	border-radius: 50%;
	background: rgba(22, 163, 74, 0.12);
	color: #15803d;
	font-size: 0.8rem;
	font-weight: 700;
}

@media (max-width: 1200px) {
	.fv-selector-toolbar {
		flex-wrap: wrap;
		align-items: stretch;
	}

	.fv-selector-filters,
	.fv-selector-actions {
		width: 100%;
		flex-wrap: wrap;
	}

	.fv-selector-filters {
		gap: 0.5rem;
	}

	.fv-selector-input {
		flex: 1 1 220px;
		min-width: 0;
	}

	.fv-selector-head {
		display: none;
	}

	.fv-selector-row {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-start;
		gap: 0.35rem 0.75rem;
	}


	.fv-selector-row > * {
		flex: 1 1 100%;
		min-width: 0;
	}

	.fv-selector-name,
	.fv-selector-id,
	.fv-selector-doctype,
	.fv-selector-link,
	.fv-selector-updated,
	.fv-selector-active {
		width: 100%;
		min-width: 0;
		white-space: normal;
	}

	.fv-selector-name {
		gap: 0.15rem;
	}

	.fv-selector-id::before {
		content: "ID: ";
		font-weight: 700;
		color: var(--text-muted);
	}

	.fv-selector-active::before {
		content: "Active: ";
		font-weight: 700;
		color: var(--text-muted);
	}

	.fv-selector-doctype::before {
		content: "DocType: ";
		font-weight: 700;
		color: var(--text-muted);
	}

	.fv-selector-link::before {
		content: "Link: ";
		font-weight: 700;
		color: var(--text-muted);
	}

	.fv-selector-updated::before {
		content: "Updated: ";
		font-weight: 700;
		color: var(--text-muted);
	}
}

@media (max-width: 768px) {
	.fv-selector-panel {
		border-radius: 0.5rem;
	}

	.fv-selector-row {
		padding: 0.8rem 0.85rem;
	}

	.fv-selector-name strong,
	.fv-selector-name small {
		white-space: normal;
	}

	.fv-selector-checkmark {
		max-width: 100%;
	}
}
</style>
