<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps({
	df: { type: Object, required: true },
	modelValue: { type: [String, Number], default: "" },
	read_only: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);

const quill = ref(null);
const control = ref(null);
const normalizedValue = computed(() => props.modelValue ?? "");
const isReadOnly = computed(() => Boolean(props.read_only || props.df?.read_only));
const isSyncingFromControl = ref(false);
let quillTextChangeHandler = null;

function cleanupControlListeners() {
	if (control.value?.quill?.off && quillTextChangeHandler) {
		control.value.quill.off("text-change", quillTextChangeHandler);
	}
	quillTextChangeHandler = null;
}

function getControlValue() {
	return control.value?.get_value?.() ?? control.value?.quill?.root?.innerHTML ?? "";
}

function emitControlValue() {
	if (!control.value || isReadOnly.value) return;
	isSyncingFromControl.value = true;
	emit("update:modelValue", getControlValue());
}

function syncRenderedValue(value) {
	if (!control.value) return;
	const nextValue = value ?? "";
	control.value.set_value?.(nextValue);
	control.value.refresh?.();
	control.value.editor?.set_html?.(nextValue);
	if (control.value.quill?.root) {
		control.value.quill.root.innerHTML = nextValue || "<p><br></p>";
	}
}

async function buildControl() {
	if (!quill.value) return;
	cleanupControlListeners();
	quill.value.innerHTML = "";
	control.value = frappe.ui.form.make_control({
		parent: quill.value,
		df: {
			...props.df,
			hidden: 0,
			read_only: isReadOnly.value,
			change: () => emitControlValue(),
		},
		disabled: isReadOnly.value,
		value: normalizedValue.value,
		render_input: true,
		only_input: true,
	});
	await nextTick();
	syncRenderedValue(normalizedValue.value);
	if (control.value?.quill?.on && !isReadOnly.value) {
		quillTextChangeHandler = () => emitControlValue();
		control.value.quill.on("text-change", quillTextChangeHandler);
	}
}

onMounted(buildControl);
onBeforeUnmount(() => {
	cleanupControlListeners();
	control.value = null;
});

watch(
	() => normalizedValue.value,
	(value) => {
		if (isSyncingFromControl.value) {
			isSyncingFromControl.value = false;
			return;
		}
		syncRenderedValue(value);
	}
);

watch(
	() => JSON.stringify(props.df),
	() => buildControl()
);

watch(
	() => isReadOnly.value,
	() => buildControl()
);
</script>

<template>
	<div class="control editable" :class="{ 'is-read-only': isReadOnly }">
		<div class="field-controls">
			<slot name="label" />
			<slot name="actions" />
		</div>
		<div class="quill" ref="quill"></div>
		<div v-if="df.description" class="mt-2 description" v-html="df.description"></div>
	</div>
</template>

<style lang="scss" scoped>
:deep(.quill) {
	.ql-formats {
		margin-right: 12px;
	}
}

.is-read-only :deep(.quill) {
	.ql-toolbar {
		pointer-events: none;
	}

	.ql-container p {
		cursor: pointer;
	}
}
</style>
