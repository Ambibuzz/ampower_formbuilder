<script setup>
import { computed } from "vue";

const props = defineProps({
	df: { type: Object, required: true },
	modelValue: { type: [String, Number, Boolean], default: "" },
	read_only: { type: Boolean, default: false },
});
const emit = defineEmits(["update:modelValue"]);

const options = computed(() => {
	const raw = props.df.options;
	if (Array.isArray(raw)) return raw.filter(Boolean);
	return String(raw || "").split(/\n|,/).map((item) => item.trim()).filter(Boolean);
});

function update(value) {
	if (props.read_only || props.df.read_only) return;
	emit("update:modelValue", value);
}
</script>

<template>
	<div class="control frappe-control">
		<div class="control-label label">{{ df.label }}</div>
		<div class="radio-list">
			<label v-for="option in options" :key="option" class="radio-option">
				<input
					type="radio"
					:name="df.fieldname || df.label"
					:value="option"
					:checked="modelValue === option"
					:disabled="read_only || df.read_only"
					@change="update(option)"
				>
				<span>{{ option }}</span>
			</label>
			<div v-if="!options.length" class="text-muted">No options configured</div>
		</div>
		<div v-if="df.description" class="mt-2 description">{{ df.description }}</div>
	</div>
</template>

<style scoped>
.radio-list {
	display: flex;
	flex-direction: column;
	gap: 8px;
}

.radio-option {
	display: flex;
	align-items: center;
	gap: 8px;
	margin: 0;
	font-weight: 400;
}
</style>
