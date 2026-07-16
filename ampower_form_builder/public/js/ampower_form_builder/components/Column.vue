<template>
	<div
		class="afb-column-card"
		:class="{ 'is-selected': isSelected }"
		data-role="column"
		:data-id="column.id"
		@click.stop="store.selectItem(column.id)"
		@dragover.prevent
		@drop="onDrop"
	>
		<header class="afb-column-header">
			<div class="afb-column-title">
				<button class="afb-drag-handle btn-reset" type="button">⋮⋮</button>
				<span>Column</span>
			</div>
			<div class="afb-card-actions">
				<AddFieldPicker
					label="Add field"
					title="Add Field"
					:options="fieldOptions"
					@select="addField"
				/>
				<button class="btn-reset afb-delete-icon" type="button" @click.stop="store.deleteColumn(column.id)">✕</button>
			</div>
		</header>

		<div class="afb-field-list">
			<Field v-for="field in column.items" :key="field.id" :field="field" />
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { useFormBuilderStore } from "../store.js";
import { FIELD_LIBRARY_ITEMS } from "../utils.js";
import AddFieldPicker from "./AddFieldPicker.vue";
import Field from "./Field.vue";

const props = defineProps({
	column: { type: Object, required: true },
	sectionId: { type: String, required: true },
});

const store = useFormBuilderStore();
const isSelected = computed(() => store.selected?.id === props.column.id);
const fieldOptions = FIELD_LIBRARY_ITEMS.map((item) => ({
	label: item.label,
	value: item.key || item.fieldtype,
	fieldtype: item.fieldtype,
}));

function onDrop(event) {
	const raw = event.dataTransfer?.getData("application/json");
	if (!raw) return;
	store.addLibraryItem(JSON.parse(raw), { sectionId: props.sectionId, columnId: props.column.id });
}

function addField(value) {
	const option = fieldOptions.find((item) => item.value === value);
	if (!option) return;
	store.addLibraryItem(
		{ kind: "field", fieldtype: option.fieldtype },
		{ sectionId: props.sectionId, columnId: props.column.id }
	);
}
</script>
