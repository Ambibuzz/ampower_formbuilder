<template>
	<div class="afb-search-box">
		<input
			ref="inputRef"
			:value="modelValue"
			class="afb-search-input form-control"
			type="text"
			:placeholder="placeholder"
			@input="$emit('update:modelValue', $event.target.value)"
			@keydown="$emit('keydown', $event)"
		>
		<span class="afb-search-icon">
			<div v-html="frappe.utils.icon('search', 'sm')"></div>
		</span>
	</div>
</template>

<script setup>
import { ref } from "vue";

defineProps({
	modelValue: { type: String, default: "" },
	placeholder: { type: String, default: "Search..." },
});

defineEmits(["update:modelValue", "keydown"]);

const inputRef = ref(null);

defineExpose({
	focus: () => inputRef.value?.focus(),
});
</script>
