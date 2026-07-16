<template>
	<div ref="root" class="afb-picker">
		<button
			class="btn"
			:class="iconOnly ? 'btn btn-default btn-xs afb-add-field-btn afb-add-field-btn-inline' : 'btn btn-default btn-xs afb-add-field-btn'"
			type="button"
			:title="title || label"
			@click.stop="toggle"
		>
			<span v-if="iconOnly">{{ label }}</span>
			<template v-else>
				<span>{{ label }}</span>
			</template>
		</button>
	</div>

	<Teleport to="body">
		<div ref="menuRef" class="afb-picker-menu-wrap">
			<div v-show="open" class="afb-picker-menu" @click.stop>
				<SearchBox
					ref="searchInput"
					v-model="query"
					placeholder="Search field types..."
					@keydown.esc="close"
					@keydown.enter.prevent="selectFirstMatch"
				/>
				<div class="afb-picker-list">
					<button
						v-for="option in filteredOptions"
						:key="option.value"
						class="afb-picker-item"
						type="button"
						@click="choose(option.value)"
					>
						<span class="afb-picker-item-label">{{ option.label }}</span>
					</button>
					<div v-if="!filteredOptions.length" class="afb-picker-empty">No matching field types</div>
				</div>
			</div>
		</div>
	</Teleport>
</template>

<script setup>
import { createPopper } from "@popperjs/core";
import { onClickOutside } from "@vueuse/core";
import { computed, nextTick, onBeforeUnmount, ref } from "vue";
import SearchBox from "./SearchBox.vue";

const props = defineProps({
	label: { type: String, default: "Add Field" },
	title: { type: String, default: "" },
	iconOnly: { type: Boolean, default: false },
	options: { type: Array, default: () => [] },
});

const emit = defineEmits(["select"]);

const open = ref(false);
const query = ref("");
const root = ref(null);
const menuRef = ref(null);
const searchInput = ref(null);
let popper = null;

const filteredOptions = computed(() => {
	const text = query.value.trim().toLowerCase();
	if (!text) return props.options;
	return props.options.filter((option) => {
		return [option.label, option.value].filter(Boolean).some((value) =>
			String(value).toLowerCase().includes(text)
		);
	});
});

function setupPopper() {
	if (!root.value || !menuRef.value) return;
	if (!popper) {
		popper = createPopper(root.value, menuRef.value, {
			placement: "bottom-start",
			modifiers: [
				{
					name: "offset",
					options: { offset: [0, 8] },
				},
				{
					name: "preventOverflow",
					options: { padding: 12 },
				},
				{
					name: "flip",
					options: { fallbackPlacements: ["bottom-end", "top-start", "top-end"] },
				},
			],
		});
	} else {
		popper.update();
	}
}

function toggle() {
	open.value = !open.value;
	if (!open.value) {
		query.value = "";
		return;
	}
	nextTick(() => {
		setupPopper();
		searchInput.value?.focus();
	});
}

function close() {
	open.value = false;
	query.value = "";
}

function choose(value) {
	emit("select", value);
	close();
}

function selectFirstMatch() {
	const firstMatch = filteredOptions.value[0];
	if (firstMatch) choose(firstMatch.value);
}

onClickOutside(root, close, { ignore: [menuRef] });
onClickOutside(menuRef, close, { ignore: [root] });

onBeforeUnmount(() => {
	popper?.destroy();
	popper = null;
});
</script>
