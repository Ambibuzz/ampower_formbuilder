<template>
	<div ref="triggerRef" class="afb-dropdown">
		<button
			class="btn"
			:class="buttonClass"
			type="button"
			:title="title || label"
			@click.stop="toggle"
		>
			<span v-if="iconOnly" class="afb-dropdown-icon" aria-hidden="true">&#8942;</span>
			<template v-else>
				<span>{{ label }}</span>
				<span class="afb-dropdown-caret" aria-hidden="true">&#9662;</span>
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

<style scoped>
.afb-dropdown {
	display: inline-flex;
}

.afb-dropdown-menu-wrap {
	z-index: 1050;
}

.afb-dropdown-menu {
	min-width: 220px;
	padding: 4px;
	border: 1px solid #d1d8dd;
	border-radius: 4px;
	background: #ffffff;
	box-shadow: 0 2px 6px rgba(15, 23, 42, 0.06);
}

.afb-dropdown-group + .afb-dropdown-group {
	margin-top: 4px;
	padding-top: 4px;
	border-top: 1px solid #e5e7eb;
}

.afb-dropdown-group-label {
	padding: 6px 10px;
	font-size: 0.76rem;
	font-weight: 700;
	letter-spacing: 0.04em;
	text-transform: uppercase;
	color: #6b7280;
}

.afb-dropdown-item {
	display: flex;
	width: 100%;
	align-items: center;
	padding: 7px 10px;
	border: 0;
	border-radius: 4px;
	background: transparent;
	text-align: left;
	color: #1f2937;
}

.afb-dropdown-item:hover {
	background: #f8f9fa;
}
</style>
