<template>
	<div ref="triggerRef" class="afb-dropdown">
		<button
			class="btn"
			:class="buttonClass"
			type="button"
			:title="title || label"
			@click.stop="toggle"
		>
			<span v-if="iconOnly" class="afb-dropdown-icon">•••</span>
			<template v-else>
				<span>{{ label }}</span>
				<span class="afb-dropdown-caret">▾</span>
			</template>
		</button>
	</div>

	<Teleport to="body">
		<div ref="menuRef" class="afb-dropdown-menu-wrap">
			<div v-show="open" class="afb-dropdown-menu" @click.stop>
				<div v-for="group in normalizedGroups" :key="group.key" class="afb-dropdown-group">
					<div v-if="group.label" class="afb-dropdown-group-label">{{ group.label }}</div>
					<button
						v-for="item in group.items"
						:key="item.key"
						class="afb-dropdown-item"
						type="button"
						@click="select(item.key)"
					>
						{{ item.label }}
					</button>
				</div>
			</div>
		</div>
	</Teleport>
</template>

<script setup>
import { createPopper } from "@popperjs/core";
import { computed, nextTick, onBeforeUnmount, ref } from "vue";
import { onClickOutside } from "@vueuse/core";

const props = defineProps({
	label: { type: String, default: "Actions" },
	title: { type: String, default: "" },
	iconOnly: { type: Boolean, default: false },
	items: { type: Array, default: () => [] },
	buttonClass: { type: String, default: "btn btn-default btn-sm" },
	placement: { type: String, default: "bottom-end" },
});

const emit = defineEmits(["select"]);

const open = ref(false);
const triggerRef = ref(null);
const menuRef = ref(null);
let popper = null;

const normalizedGroups = computed(() => {
	if (!props.items.length) return [];
	if (props.items[0]?.items) {
		return props.items.map((group, index) => ({
			key: group.key || `group_${index}`,
			label: group.label || "",
			items: group.items || [],
		}));
	}
	return [{ key: "default", label: "", items: props.items }];
});

function setupPopper() {
	if (!triggerRef.value || !menuRef.value) return;
	if (!popper) {
		popper = createPopper(triggerRef.value, menuRef.value, {
			placement: props.placement,
			modifiers: [
				{
					name: "offset",
					options: { offset: [0, 8] },
				},
				{
					name: "preventOverflow",
					options: { padding: 12 },
				},
			],
		});
	} else {
		popper.update();
	}
}

function toggle() {
	open.value = !open.value;
	if (open.value) nextTick(setupPopper);
}

function close() {
	open.value = false;
}

function select(key) {
	emit("select", key);
	close();
}

onClickOutside(triggerRef, close, { ignore: [menuRef] });
onClickOutside(menuRef, close, { ignore: [triggerRef] });

onBeforeUnmount(() => {
	popper?.destroy();
	popper = null;
});
</script>
