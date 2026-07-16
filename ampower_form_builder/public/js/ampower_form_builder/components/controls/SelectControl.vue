<script setup>
import { computed, onBeforeUnmount, onMounted, ref, useSlots, watch } from "vue";

const props = defineProps({
	df: { type: Object, default: () => ({}) },
	read_only: { type: [Boolean, String], default: false },
	modelValue: { type: [String, Number, Boolean, Object, Array], default: "" },
	no_label: { type: Boolean, default: false },
});
const emit = defineEmits(["update:modelValue"]);
const slots = useSlots();

const select = ref(null);
const control = ref(null);
const syncingFromControl = ref(false);

function getOptions() {
	let options = props.df.options;

	if (typeof options === "string") {
		options = options.split("\n").map((opt) => opt.trim()).filter(Boolean);
		options = options.map((opt) => ({ label: __(opt), value: opt }));
	}

	if (options?.length && typeof options[0] === "string") {
		options = options.map((opt) => String(opt).trim()).filter(Boolean);
		options = options.map((opt) => ({ label: __(opt), value: opt }));
	}

	if (props.df.sort_options) {
		options = [...options].sort((a, b) => a.label.localeCompare(b.label));
	}

	return [{ label: __("") || "", value: "" }, ...(options || [])];
}

const content = computed({
	get: () => props.modelValue,
	set: (value) => emit("update:modelValue", value),
});

function buildControl() {
	if (!select.value) return;
	select.value.innerHTML = "";

	control.value = frappe.ui.form.make_control({
		parent: select.value,
		df: {
			...props.df,
			fieldtype: "Select",
			hidden: 0,
			options: getOptions(),
			read_only: Boolean(slots.label) || props.read_only,
			change: () => {
				if (syncingFromControl.value) return;
				syncingFromControl.value = true;
				content.value = control.value?.get_value?.() ?? "";
			},
		},
		value: content.value,
		render_input: true,
		only_input: Boolean(slots.label) || props.no_label,
	});
	control.value?.refresh?.();
	control.value?.set_value?.(content.value);
}

onMounted(() => {
	buildControl();
});

onBeforeUnmount(() => {
	control.value = null;
});

watch(
	() => content.value,
	(value) => {
		if (!control.value) return;
		if (syncingFromControl.value) {
			syncingFromControl.value = false;
			return;
		}
		control.value.set_value?.(value ?? "");
	}
);

watch(
	() => [props.df.options, props.df.sort_options, props.read_only, props.no_label],
	() => buildControl(),
	{ deep: true }
);
</script>

<template>
	<div v-if="slots.label" class="control frappe-control" :class="{ editable: slots.label }">
		<div class="field-controls">
			<slot name="label" />
			<slot name="actions" />
		</div>
		<div class="select-input">
			<input class="form-control" readonly>
			<div class="select-icon" v-html="frappe.utils.icon('select', 'sm')"></div>
		</div>
		<div v-if="df.description" class="mt-2 description" v-html="df.description"></div>
	</div>
	<div v-else class="control" ref="select"></div>
</template>

<style lang="scss" scoped>
.editable {
	.select-icon {
		top: 3px !important;
	}
}

.select-input {
	position: relative;

	.select-icon {
		position: absolute;
		pointer-events: none;
		top: 5px;
		right: 10px;
	}
}
</style>
