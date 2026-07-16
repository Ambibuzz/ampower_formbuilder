<template>
	<article
		class="afb-section-card"
		:class="{ 'is-selected': isSelected, 'is-tab-section': isTabSection }"
		data-role="section"
		:data-id="section.id"
		@click="store.selectItem(section.id)"
		@dragover.prevent
		@drop="onDrop"
	>
		<header class="afb-section-header">
			<div class="afb-section-meta">
				<button class="afb-drag-handle btn-reset" type="button">⋮⋮</button>
				<div>
					<h3>{{ section.section_label || "Untitled Section" }}</h3>
					<span class="afb-type-badge">{{ isTabSection ? "Tab" : section.item_type }}</span>
				</div>
			</div>
			<div class="afb-card-actions">
				<AddFieldPicker
					label="Add field"
					title="Add Field"
					:options="fieldOptions"
					@select="addField"
				/>
				<AddActionMenu :items="actionItems" icon-only label="Section actions" @select="handleAction" />
			</div>
		</header>

		<div class="afb-columns-list">
			<Column v-for="column in section.columns" :key="column.id" :section-id="section.id" :column="column" />
		</div>
	</article>
</template>

<script setup>
import { computed } from "vue";
import { useFormBuilderStore } from "../store.js";
import { FIELD_LIBRARY_ITEMS } from "../utils.js";
import AddActionMenu from "./AddActionMenu.vue";
import AddFieldPicker from "./AddFieldPicker.vue";
import Column from "./Column.vue";

const props = defineProps({
	section: { type: Object, required: true },
});

const store = useFormBuilderStore();
const isSelected = computed(() => store.selected?.id === props.section.id);
const isTabSection = computed(() => props.section.item_type === "Tab Break");
const fieldOptions = FIELD_LIBRARY_ITEMS.map((item) => ({
	label: item.label,
	value: item.key || item.fieldtype,
	fieldtype: item.fieldtype,
}));
const actionItems = computed(() => ([
	...(isTabSection.value ? [{
		key: "tab_group",
		label: "Tab",
		items: [
			{ key: "tab_below", label: "Add tab below" },
		],
	}] : []),
	{
		key: "section_group",
		label: "Section",
		items: [
			{ key: "section_below", label: "Add section below" },
			{ key: "delete_section", label: "Remove section" },
		],
	},
	{
		key: "column_group",
		label: "Column",
		items: [
			{ key: "add_column", label: "Add column" },
			{ key: "remove_column", label: "Remove last column" },
		],
	},
]));

function onDrop(event) {
	const raw = event.dataTransfer?.getData("application/json");
	if (!raw) return;
	store.addLibraryItem(JSON.parse(raw), { sectionId: props.section.id });
}

function addField(value) {
	const firstColumn = props.section.columns[0] || store.createColumn(props.section.id);
	const option = fieldOptions.find((item) => item.value === value);
	if (!option) return;
	store.addLibraryItem(
		{ kind: "field", fieldtype: option.fieldtype },
		{ sectionId: props.section.id, columnId: firstColumn.id }
	);
}

function handleAction(action) {
	if (action === "tab_below") {
		const currentIndex = store.sections.findIndex((item) => item.id === props.section.id);
		let insertIndex = currentIndex + 1;
		for (let i = currentIndex + 1; i < store.sections.length; i++) {
			if (store.sections[i].item_type === "Tab Break") break;
			insertIndex = i + 1;
		}
		store.createSection("Tab Break", insertIndex);
		return;
	}
	if (action === "section_below") {
		const index = store.sections.findIndex((item) => item.id === props.section.id);
		store.createSection("Section Break", index + 1);
		return;
	}
	if (action === "delete_section") {
		store.deleteSection(props.section.id);
		return;
	}
	if (action === "add_column") {
		store.createColumn(props.section.id);
		return;
	}
	if (action === "remove_column" && props.section.columns.length > 1) {
		store.deleteColumn(props.section.columns.at(-1).id);
	}
}
</script>
