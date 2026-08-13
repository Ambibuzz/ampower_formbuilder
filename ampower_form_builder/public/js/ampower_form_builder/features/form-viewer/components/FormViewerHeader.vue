<template>
	<header class="fv-view-header fv-page-header">
		<div class="fv-view-heading fv-page-heading">
			<div class="fv-page-title-copy">
				<p v-if="breadcrumbLabel" class="fv-breadcrumb">{{ breadcrumbLabel }}</p>
				<h2 class="fv-view-title fv-page-title">{{ pageTitle }}</h2>
				<p v-if="headerDescription" class="fv-view-description fv-page-description">{{ headerDescription }}</p>
			</div>
		</div>
		<div class="fv-view-actions fv-page-actions">
			<template v-if="reportPreviewOpen">
				<button type="button" class="fv-action-btn secondary icon-btn" :title="__('Print')" @click="$emit('print-report')">
					<span v-html="frappe.utils.icon('printer', 'sm')" aria-hidden="true"></span>
				</button>
				<button type="button" class="fv-action-btn primary" :title="__('Refresh Report')" @click="$emit('refresh-report')">
					{{ __('Refresh Report') }}
				</button>
			</template>
			<template v-else-if="isFormsDirectoryView">
				<button type="button" class="fv-action-btn secondary icon-btn" :title="__('Refresh list')" @click="$emit('refresh-directory')">
					<span v-html="frappe.utils.icon('refresh', 'sm')" aria-hidden="true"></span>
				</button>
				<BuilderDropdown
					:icon-only="true"
					:title="__('More actions')"
					:items="directoryMenuItems"
					button-class="fv-action-btn secondary fv-view-menu-btn"
					@select="$emit('directory-menu-select', $event)"
				/>
				<button type="button" class="fv-action-btn primary" :title="__('Add Dynamic Form Template')" @click="$emit('open-builder')">
					{{ __('Add Dynamic Form Template') }}
				</button>
			</template>
			<template v-else-if="isReportsListView">
				<BuilderDropdown
					:icon-only="true"
					:title="__('View actions')"
					:items="viewMenuItems"
					button-class="fv-action-btn secondary fv-view-menu-btn"
					@select="$emit('view-menu-select', $event)"
				/>
				<button type="button" class="fv-action-btn primary" :disabled="primaryActionDisabled" :title="primaryActionLabel" @click="$emit('primary-action')">
					{{ primaryActionLabel }}
				</button>
			</template>
			<template v-else-if="isSubmissionDetailView">
				<BuilderDropdown
					:icon-only="true"
					:title="__('View actions')"
					:items="viewMenuItems"
					button-class="fv-action-btn secondary fv-view-menu-btn"
					@select="$emit('view-menu-select', $event)"
				/>
				<button
					v-if="secondaryActionLabel"
					type="button"
					class="fv-action-btn secondary"
					:title="secondaryActionLabel"
					@click="$emit('secondary-action')"
				>
					{{ secondaryActionLabel }}
				</button>
				<button type="button" class="fv-action-btn primary" :disabled="primaryActionDisabled" :title="primaryActionLabel" @click="$emit('primary-action')">
					{{ primaryActionLabel }}
				</button>
			</template>
			<template v-else>
				<BuilderDropdown
					:icon-only="true"
					:title="__('View actions')"
					:items="viewMenuItems"
					button-class="fv-action-btn secondary fv-view-menu-btn"
					@select="$emit('view-menu-select', $event)"
				/>
				<button type="button" class="fv-action-btn primary" :disabled="primaryActionDisabled" :title="primaryActionLabel" @click="$emit('primary-action')">
					{{ primaryActionLabel }}
				</button>
			</template>
		</div>
	</header>
</template>

<script setup>
import BuilderDropdown from "../../../components/BuilderDropdown.vue";

defineProps({
	pageTitle: { type: String, default: "" },
	headerDescription: { type: String, default: "" },
	breadcrumbLabel: { type: String, default: "" },
	reportPreviewOpen: { type: Boolean, default: false },
	isFormsDirectoryView: { type: Boolean, default: false },
	isReportsListView: { type: Boolean, default: false },
	isSubmissionDetailView: { type: Boolean, default: false },
	directoryMenuItems: { type: Array, default: () => [] },
	viewMenuItems: { type: Array, default: () => [] },
	canCreateReport: { type: Boolean, default: false },
	reportLoading: { type: Boolean, default: false },
	primaryActionLabel: { type: String, default: "Save" },
	primaryActionDisabled: { type: Boolean, default: false },
	secondaryActionLabel: { type: String, default: "" },
});

defineEmits([
	"print-report",
	"refresh-report",
	"refresh-directory",
	"open-builder",
	"directory-menu-select",
	"view-menu-select",
	"primary-action",
	"secondary-action",
]);
</script>

<style scoped>
.fv-view-header {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 16px;
	padding: 18px 0 14px;
	border-bottom: 1px solid var(--fv-border);
	background: var(--fv-surface);
}

.fv-view-heading {
	display: flex;
	align-items: flex-start;
	gap: 8px;
	min-width: 0;
	flex: 1 1 auto;
}

.fv-page-title-copy {
	min-width: 0;
}

.fv-breadcrumb {
	margin: 0 0 6px;
	font-size: 0.75rem;
	font-weight: 700;
	letter-spacing: 0.08em;
	text-transform: uppercase;
	color: var(--fv-text-muted);
}

.fv-page-title {
	margin: 0;
	font-size: clamp(24px, 2.2vw, 32px);
	line-height: 1.1;
	font-weight: 700;
	letter-spacing: 0;
	color: var(--fv-text-main);
}

.fv-page-description {
	margin: 4px 0 0;
	max-width: 62rem;
	color: var(--fv-text-muted);
}

.fv-page-actions {
	display: flex;
	align-items: center;
	justify-content: flex-end;
	gap: 8px;
	flex-wrap: wrap;
	margin-left: auto;
}

:deep(.fv-action-btn) {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	gap: 8px;
	min-height: 38px;
	padding: 0.45rem 0.8rem;
	border: 1px solid var(--fv-border);
	border-radius: 4px;
	background: var(--fv-surface);
	color: var(--fv-text-main);
	font-weight: 500;
	box-shadow: none;
}

:deep(.fv-action-btn:hover) {
	background: var(--subtle-fg);
}

:deep(.fv-action-btn.primary) {
	border-color: var(--primary);
	background: var(--primary);
	color: #ffffff;
}

:deep(.fv-action-btn.primary:hover) {
	background: var(--color-theme-2, var(--primary));
	border-color: var(--color-theme-2, var(--primary));
}

:deep(.fv-action-btn.secondary) {
	background: var(--fv-surface);
	color: var(--fv-text-main);
}

:deep(.fv-action-btn.icon-btn) {
	min-width: 38px;
	padding-inline: 0.6rem;
}

:deep(.fv-action-btn.icon-btn svg) {
	width: 14px;
	height: 14px;
	display: block;
}

:deep(.fv-list-dropdown),
:deep(.fv-view-menu-btn) {
	min-height: 38px;
	border-radius: 4px;
}

@media (max-width: 768px) {
	.fv-view-header {
		flex-direction: column;
	}

	.fv-page-actions {
		width: 100%;
		justify-content: flex-start;
	}
}
</style>
