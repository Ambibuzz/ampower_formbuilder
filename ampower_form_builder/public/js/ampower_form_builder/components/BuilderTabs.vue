<script setup>
const props = defineProps({
	tabs: { type: Array, default: () => [] },
	activeTabId: { type: String, default: "" },
	disabled: { type: Boolean, default: false },
});

const emit = defineEmits(["select"]);
</script>

<template>
	<div class="afb-tabs" v-if="tabs.length">
		<ul class="nav nav-tabs">
			<li v-for="tab in tabs" :key="tab.id" class="nav-item">
				<button
					type="button"
					class="nav-link"
					:class="{ active: activeTabId === tab.id }"
					:title="tab.section_key || tab.id"
					:disabled="disabled"
					@click="emit('select', tab.id)"
				>
					{{ tab.section_label || "New Tab" }}
				</button>
			</li>
		</ul>
	</div>
</template>

<style lang="scss" scoped>
.afb-tabs {
	margin-bottom: 14px;
	overflow-x: auto;
	padding-bottom: 1px;
}

.nav {
	flex-wrap: nowrap;
	gap: 4px;
	border-bottom: 1px solid var(--border-color);
}

.nav-item {
	flex: 0 0 auto;
}

.nav-link {
	min-width: max-content;
	border: 1px solid transparent;
	border-bottom: none;
	border-radius: var(--border-radius-md) var(--border-radius-md) 0 0;
	background: transparent;
	color: var(--text-muted);
	padding: 8px 14px;
	font-size: 13px;
	font-weight: 500;
	transition: color 0.15s ease, background-color 0.15s ease, border-color 0.15s ease;

	&:hover:not(:disabled) {
		color: var(--text-color);
		background: var(--subtle-fg);
	}

	&.active {
		color: var(--text-color);
		background: var(--fg-color);
		border-color: var(--border-color);
		font-weight: 600;
	}

	&:disabled {
		cursor: not-allowed;
		opacity: 0.6;
	}
}
</style>
