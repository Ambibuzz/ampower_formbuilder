<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps({
	df: { type: Object, required: true },
	modelValue: { type: [String, Number, Boolean, Array, Object], default: "" },
	read_only: { type: Boolean, default: false },
	compact: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);

const root = ref(null);
const control = ref(null);
const syncingFromControl = ref(false);
let inputElement = null;
let inputListener = null;
let changeListener = null;
let blurListener = null;
let autocompleteSelectListener = null;
let autocompleteSelectCompleteListener = null;
let changeFrame = null;

const normalizedValue = computed(() => props.modelValue ?? "");
const fallbackMode = ref(false);
const isDateLikeField = computed(() => ["Date", "Datetime", "Time"].includes(props.df?.fieldtype));

function getSafeFieldtype(fieldtype) {
	const value = String(fieldtype || "Data");
	if (["Text", "Small Text", "Long Text", "Text Editor"].includes(value)) return "Small Text";
	if (["Number", "Percent", "Int", "Float", "Currency"].includes(value)) return "Float";
	if (["Attach", "Attach Image", "Date", "Datetime", "Time", "Color", "Data", "Select", "Check", "Link", "Dynamic Link"].includes(value)) return value;
	return "Data";
}

function emitLiveValue(nextValue = null) {
	if (!control.value && nextValue === null) return;
	syncingFromControl.value = true;
	emit("update:modelValue", nextValue ?? control.value?.get_value?.());
}

function cancelQueuedChange() {
	if (changeFrame !== null) {
		cancelAnimationFrame(changeFrame);
		changeFrame = null;
	}
}

function queueDomValueEmit() {
	cancelQueuedChange();
	changeFrame = requestAnimationFrame(() => {
		changeFrame = null;
		if (isDateLikeField.value) {
			emitLiveValue();
			return;
		}
		emitLiveValue(inputElement?.value ?? null);
	});
}

function detachInputListeners() {
	cancelQueuedChange();
	if (inputElement && inputListener) {
		inputElement.removeEventListener("input", inputListener);
	}
	if (inputElement && changeListener) {
		inputElement.removeEventListener("change", changeListener);
	}
	if (inputElement && blurListener) {
		inputElement.removeEventListener("blur", blurListener);
	}
	if (inputElement && autocompleteSelectListener) {
		inputElement.removeEventListener("awesomplete-select", autocompleteSelectListener);
	}
	if (inputElement && autocompleteSelectCompleteListener) {
		inputElement.removeEventListener("awesomplete-selectcomplete", autocompleteSelectCompleteListener);
	}
	inputElement = null;
	inputListener = null;
	changeListener = null;
	blurListener = null;
	autocompleteSelectListener = null;
	autocompleteSelectCompleteListener = null;
}

function attachInputListeners() {
	detachInputListeners();
	inputElement = root.value?.querySelector?.("input, textarea, select");
	if (!inputElement) return;

	inputElement.classList.add("form-control");
	inputElement.style.margin = "0";

	if (props.compact) {
		inputElement.style.minHeight = "26px";
		inputElement.style.padding = "1px 6px";
		inputElement.style.fontSize = "12px";
		inputElement.style.lineHeight = "1.2";
	}

	const controlWrapper = root.value?.firstElementChild;
	if (controlWrapper?.style) {
		controlWrapper.style.margin = "0";
		controlWrapper.style.padding = "0";
	}

	if (!isDateLikeField.value) {
		inputListener = (event) => emitLiveValue(event?.target?.value);
	}
	changeListener = () => queueDomValueEmit();
	blurListener = () => queueDomValueEmit();
	autocompleteSelectListener = () => queueDomValueEmit();
	autocompleteSelectCompleteListener = () => queueDomValueEmit();

	if (inputListener) {
		inputElement.addEventListener("input", inputListener);
	}
	inputElement.addEventListener("change", changeListener);
	inputElement.addEventListener("blur", blurListener);
	inputElement.addEventListener("awesomplete-select", autocompleteSelectListener);
	inputElement.addEventListener("awesomplete-selectcomplete", autocompleteSelectCompleteListener);
}

function buildControl() {
	if (!root.value) return;
	detachInputListeners();
	root.value.innerHTML = "";
	fallbackMode.value = false;

	try {
		control.value = frappe.ui.form.make_control({
			parent: root.value,
			df: {
				...props.df,
				fieldtype: getSafeFieldtype(props.df?.fieldtype),
				hidden: 0,
				read_only: Boolean(props.read_only || props.df.read_only),
				change: () => emitLiveValue(),
			},
			value: normalizedValue.value,
			render_input: true,
			only_input: true,
		});

		control.value?.refresh?.();
		control.value?.set_value?.(normalizedValue.value);
		attachInputListeners();
	} catch (error) {
		console.error("Ampower generic control failed", error);
		control.value = null;
		fallbackMode.value = true;
	}
}

onMounted(buildControl);
onBeforeUnmount(() => {
	detachInputListeners();
	control.value = null;
});

watch(
	() => normalizedValue.value,
	(value) => {
		if (!control.value) return;
		if (syncingFromControl.value) {
			syncingFromControl.value = false;
			return;
		}
		try {
			control.value.set_value?.(value);
		} catch (error) {
			console.error("Ampower generic control set_value failed", error);
		}
	}
);

watch(
	() => JSON.stringify(props.df),
	() => buildControl()
);
</script>

<template>
	<div v-if="fallbackMode" class="fv-generic-field-fallback">
		<textarea
			v-if="['Text', 'Small Text', 'Long Text', 'Text Editor'].includes(df?.fieldtype)"
			class="form-control"
			:value="normalizedValue"
			:readonly="read_only || df?.read_only"
			@input="$emit('update:modelValue', $event.target.value)"
		/>
		<input
			v-else-if="['Number', 'Percent', 'Int', 'Float', 'Currency'].includes(df?.fieldtype)"
			class="form-control"
			type="number"
			:value="normalizedValue"
			:readonly="read_only || df?.read_only"
			@input="$emit('update:modelValue', $event.target.value)"
		>
		<input
			v-else
			class="form-control"
			type="text"
			:value="normalizedValue"
			:readonly="read_only || df?.read_only"
			@input="$emit('update:modelValue', $event.target.value)"
		>
	</div>
	<div v-else ref="root" class="fv-generic-field-control"></div>
</template>
