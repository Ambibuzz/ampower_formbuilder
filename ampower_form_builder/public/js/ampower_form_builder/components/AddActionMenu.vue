<template>
	<BuilderDropdown
		:label="label"
		:title="label"
		:items="items"
		:icon-only="iconOnly"
		:button-class="iconOnly ? 'afb-icon-btn afb-picker-trigger' : 'btn btn-default btn-sm afb-layout-trigger'"
		@select="$emit('select', $event)"
	/>
</template>

<script setup>
import BuilderDropdown from "./BuilderDropdown.vue";

defineProps({
	label: { type: String, default: "Add" },
	iconOnly: { type: Boolean, default: false },
	items: { type: Array, default: () => [] },
});

defineEmits(["select"]);
</script>
