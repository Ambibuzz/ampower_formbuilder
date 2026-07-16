<template>
	<section ref="canvasRef" class="afb-canvas">
		<div v-if="tabGroups.length" class="afb-builder-tabs">
			<BuilderTabs
				:tabs="tabHeaders"
				:active-tab-id="activeTabId"
				:disabled="store.isSaving"
				@select="store.setActiveBuilderTab"
			/>
			<div ref="sectionsRef" class="afb-section-list">
				<Section v-for="section in visibleSections" :key="section.id" :section="section" />
			</div>
		</div>
	</section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import Sortable from "sortablejs";
import { getTabGroups, useFormBuilderStore } from "../store.js";
import BuilderTabs from "./BuilderTabs.vue";
import Section from "./Section.vue";

const store = useFormBuilderStore();
const canvasRef = ref(null);
const sectionsRef = ref(null);
const sortables = [];
const tabGroups = computed(() => getTabGroups(store.sections));
const activeTabId = computed(() => store.activeBuilderTabId || tabGroups.value[0]?.id || null);
const tabHeaders = computed(() => tabGroups.value.map((group) => group.tab).filter(Boolean));
const structureKey = computed(() =>
	store.sections
		.map((section) => `${section.id}:${(section.columns || []).map((column) => `${column.id}=${(column.items || []).length}`).join(",")}`)
		.join("|")
);
const visibleSections = computed(() => {
	const group = tabGroups.value.find((item) => item.id === activeTabId.value) || tabGroups.value[0];
	return group?.sections || [];
});

function destroySortables() {
	sortables.splice(0).forEach((sortable) => sortable.destroy());
}

function syncFromDom(type, evt) {
	const toContainerId = type === "column"
		? evt.to.closest("[data-role='section']")?.dataset.id
		: type === "field"
			? evt.to.closest("[data-role='column']")?.dataset.id
			: null;
	const fromContainerId = type === "column"
		? evt.from.closest("[data-role='section']")?.dataset.id
		: type === "field"
			? evt.from.closest("[data-role='column']")?.dataset.id
			: null;
	store.syncTreeFromDOM(type, {
		fromIndex: evt.oldIndex,
		toIndex: evt.newIndex,
		fromContainerId,
		toContainerId,
	});
}

async function initSortables() {
	await nextTick();
	destroySortables();
	if (sectionsRef.value) {
		sortables.push(new Sortable(sectionsRef.value, {
			group: "sections",
			handle: ".afb-drag-handle",
			animation: 150,
			onEnd: (evt) => syncFromDom("section", evt),
		}));
	}
	canvasRef.value?.querySelectorAll(".afb-columns-list").forEach((node) => {
		sortables.push(new Sortable(node, {
			group: "columns",
			handle: ".afb-drag-handle",
			animation: 150,
			onEnd: (evt) => syncFromDom("column", evt),
		}));
	});
	canvasRef.value?.querySelectorAll(".afb-field-list").forEach((node) => {
		sortables.push(new Sortable(node, {
			group: "fields",
			handle: ".afb-drag-handle",
			animation: 150,
			onEnd: (evt) => syncFromDom("field", evt),
		}));
	});
}

watch(structureKey, initSortables);
onMounted(initSortables);
onBeforeUnmount(destroySortables);
</script>
