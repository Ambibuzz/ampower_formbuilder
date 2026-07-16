<!-- Used as Link Control -->
<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useSlots, watch } from "vue";

const props = defineProps({
	args: { type: Object, default: null },
	df: { type: Object, default: () => ({}) },
	read_only: { type: [Boolean, String], default: false },
	modelValue: { type: [String, Number, Boolean, Object, Array], default: "" },
	no_label: { type: Boolean, default: false },
});
const emit = defineEmits(["update:modelValue"]);
const slots = useSlots();

const link = ref(null);
const update_control = ref(true);
const control = ref(null);
let inputElement = null;
let focusListener = null;
let autocompleteOpenListener = null;
let autocompleteCloseListener = null;
let dropdownLayer = null;
let dropdownHost = null;
let repositionHandler = null;

const content = computed({
	get: () => props.modelValue,
	set: (value) => emit("update:modelValue", value),
});

function getControlDf() {
	const df = {
		...props.df,
		hidden: 0,
		read_only: Boolean(slots.label) || props.read_only,
		change: () => {
			if (!control.value) return;
			if (update_control.value) {
				content.value = control.value.get_value();
			}
			update_control.value = true;
		},
	};

	if (props.args?.is_table_field) {
		df.filters = { ...(df.filters || {}), istable: 1 };
	} else if (df.filters && "istable" in df.filters) {
		df.filters = { ...df.filters };
		delete df.filters.istable;
	}

	return df;
}

function getDropdownWidth() {
	const width = Number(props.args?.dropdown_width);
	return Number.isFinite(width) && width > 0 ? width : 250;
}

function getDropdownList() {
	return control.value?.awesomplete?.ul || null;
}

function ensureDropdownLayer() {
	if (typeof document === "undefined") return null;
	if (!dropdownLayer || !document.body.contains(dropdownLayer)) {
		dropdownLayer = document.createElement("div");
		dropdownLayer.className = "ampower-link-dropdown-layer";
		document.body.appendChild(dropdownLayer);
	}
	if (!dropdownHost || !dropdownLayer.contains(dropdownHost)) {
		dropdownHost = document.createElement("div");
		dropdownHost.className = "ampower-link-dropdown-host";
		dropdownLayer.appendChild(dropdownHost);
	}
	return dropdownHost;
}

function updateDropdownPosition() {
	if (!props.args?.dropdown_in_body || !inputElement) return;
	const dropdown = getDropdownList();
	if (!dropdown || !dropdownHost) return;

	const rect = inputElement.getBoundingClientRect();
	const width = Math.max(rect.width, getDropdownWidth());
	const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 0;
	const left = Math.max(8, Math.min(rect.left, Math.max(8, viewportWidth - width - 8)));

	dropdown.classList.add("ampower-link-dropdown-list");
	dropdown.style.position = "fixed";
	dropdown.style.left = `${left}px`;
	dropdown.style.top = `${rect.bottom + 4}px`;
	dropdown.style.width = `${width}px`;
	dropdown.style.minWidth = `${width}px`;
	dropdown.style.maxWidth = `${width}px`;
	dropdown.style.maxHeight = "280px";
	dropdown.style.zIndex = "1060";
}

function detachDropdown() {
	const dropdown = getDropdownList();
	if (!dropdown) return;

	if (repositionHandler) {
		window.removeEventListener("resize", repositionHandler);
		window.removeEventListener("scroll", repositionHandler, true);
		repositionHandler = null;
	}

	if (dropdown.classList.contains("ampower-link-dropdown-list")) {
		dropdown.classList.remove("ampower-link-dropdown-list");
	}

	if (dropdownHost && dropdown.parentNode === dropdownHost) {
		link.value?.appendChild?.(dropdown);
	}

	dropdown.style.position = "";
	dropdown.style.left = "";
	dropdown.style.top = "";
	dropdown.style.width = "";
	dropdown.style.minWidth = "";
	dropdown.style.maxWidth = "";
	dropdown.style.maxHeight = "";
	dropdown.style.zIndex = "";
}

function attachDropdownToBody() {
	if (!props.args?.dropdown_in_body) return;
	const dropdown = getDropdownList();
	const host = ensureDropdownLayer();
	if (!dropdown || !host) return;

	if (dropdown.parentNode !== host) {
		host.appendChild(dropdown);
	}

	if (!repositionHandler) {
		repositionHandler = () => updateDropdownPosition();
		window.addEventListener("resize", repositionHandler);
		window.addEventListener("scroll", repositionHandler, true);
	}

	updateDropdownPosition();
}

function keepInputVisible() {
	if (!props.args?.keep_visible_in_grid || !inputElement) return;

	const scrollContainer = link.value?.closest?.(".afb-form-grid-container");
	if (!scrollContainer) return;

	const containerRect = scrollContainer.getBoundingClientRect();
	const inputRect = inputElement.getBoundingClientRect();
	const requiredRightSpace = getDropdownWidth();
	const rightSpace = containerRect.right - inputRect.left;

	if (inputRect.left < containerRect.left) {
		scrollContainer.scrollLeft -= containerRect.left - inputRect.left;
		return;
	}

	if (rightSpace < requiredRightSpace) {
		scrollContainer.scrollLeft += requiredRightSpace - rightSpace;
	}
}

function detachInputListeners() {
	if (inputElement && focusListener) {
		inputElement.removeEventListener("focus", focusListener);
	}
	if (inputElement && autocompleteOpenListener) {
		inputElement.removeEventListener("awesomplete-open", autocompleteOpenListener);
	}
	if (inputElement && autocompleteCloseListener) {
		inputElement.removeEventListener("awesomplete-close", autocompleteCloseListener);
	}
	detachDropdown();
	inputElement = null;
	focusListener = null;
	autocompleteOpenListener = null;
	autocompleteCloseListener = null;
}

function attachInputListeners() {
	detachInputListeners();
	inputElement = link.value?.querySelector?.("input");
	if (!inputElement) return;

	focusListener = () => nextTick(() => keepInputVisible());
	autocompleteOpenListener = () => nextTick(() => {
		keepInputVisible();
		attachDropdownToBody();
	});
	autocompleteCloseListener = () => nextTick(() => detachDropdown());

	inputElement.addEventListener("focus", focusListener);
	inputElement.addEventListener("awesomplete-open", autocompleteOpenListener);
	inputElement.addEventListener("awesomplete-close", autocompleteCloseListener);
}

function buildControl() {
	detachInputListeners();
	link.value.innerHTML = "";
	control.value = frappe.ui.form.make_control({
		parent: link.value,
		df: getControlDf(),
		value: content.value,
		render_input: true,
		only_input: Boolean(slots.label) || props.no_label,
	});
	control.value?.refresh?.();
	control.value?.set_value?.(content.value);
	attachInputListeners();
}

onMounted(() => {
	if (link.value) buildControl();
});

onBeforeUnmount(() => {
	detachInputListeners();
	if (dropdownHost?.parentNode) {
		dropdownHost.parentNode.removeChild(dropdownHost);
	}
	if (dropdownLayer?.parentNode && dropdownLayer.childElementCount === 0) {
		dropdownLayer.parentNode.removeChild(dropdownLayer);
	}
	dropdownHost = null;
	dropdownLayer = null;
	control.value = null;
});

watch(
	() => content.value,
	(value) => {
		update_control.value = false;
		control.value?.set_value?.(value);
	}
);

watch(
	() => JSON.stringify({
		df: props.df,
		read_only: props.read_only,
		is_table_field: props.args?.is_table_field,
		has_label_slot: Boolean(slots.label),
		no_label: Boolean(props.no_label),
	}),
	() => {
		if (link.value) buildControl();
	}
);
</script>

<template>
	<div
		v-if="slots.label"
		class="control frappe-control afb-link-control"
		:data-fieldtype="df.fieldtype"
		:class="{ editable: slots.label }"
	>
		<div class="field-controls">
			<slot name="label" />
			<slot name="actions" />
		</div>
		<input class="form-control" type="text" readonly>
		<div v-if="df.description" class="mt-2 description" v-html="df.description" />
	</div>
	<div v-else ref="link" class="afb-link-control"></div>
</template>
