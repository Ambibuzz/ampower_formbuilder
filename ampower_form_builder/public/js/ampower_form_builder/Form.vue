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
				<div class="fv-state-card">
					<div class="fv-state-title">{{ __("Browse forms") }}</div>
					<div class="fv-state-copy">{{ __("Pick a form below to open its report entries.") }}</div>
				</div>
				<div class="fv-template-list">
					<div
						v-for="template in activeTemplates"
						:key="template.name"
						class="fv-template-card"
						:data-name="template.name"
						@click="$emit('open-template', template.name)"
					>
						<div class="fv-template-card-head">
							<h5>{{ template.display_name || template.form_name }}</h5>
							<div class="fv-template-card-badges">
								<span class="fv-template-card-badge">{{ `${__("Version")} ${template.version_label || "1.0"}` }}</span>
								<span v-if="template.is_latest_version" class="fv-template-card-badge is-latest">{{ __("Latest") }}</span>
								<span class="fv-template-card-badge">{{ template.form_type || __("Form") }}</span>
							</div>
						</div>
						<p v-if="template.description" class="fv-template-card-copy">{{ template.description }}</p>
						<div class="fv-template-card-meta">
							<span>{{ template.base_form_name || template.form_name || __("Open reports") }}</span>
							<small v-if="template.target_doctype">{{ template.target_doctype }}</small>
						</div>
					</div>
					<div v-if="!activeTemplates.length" class="fv-state-card fv-state-empty">
						<div class="fv-state-title">{{ __("No active form templates found.") }}</div>
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
import FormViewerField from "./components/FormViewerField.vue";

defineProps({
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
});

defineEmits(["update:currentTab", "open-template", "update-field"]);
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
	flex-wrap: wrap;
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
	border-radius: 999px;
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
</style>
