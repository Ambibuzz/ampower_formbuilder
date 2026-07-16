<template>
	<aside class="afb-properties">
		<div v-if="!selectedItem" class="afb-empty-state slim">
			<h3>No selection</h3>
			<p>Select a section, column, or field to edit properties.</p>
		</div>
		<div v-else-if="selected.kind === 'field'" class="afb-properties-group">
			<h3>Field Properties</h3>
			<FieldProperties :field="selectedItem" />
		</div>
		<div v-else-if="selected.kind === 'section'" class="afb-properties-group">
			<h3>Section Properties</h3>
			<label class="form-group">
				<span>Label</span>
				<input :value="selectedItem.section_label" class="form-control" @input="updateSection('section_label', $event.target.value)">
			</label>
			<label class="form-group">
				<span>Key</span>
				<input :value="selectedItem.section_key" class="form-control" @input="updateSection('section_key', $event.target.value)">
			</label>
			<label class="form-group">
				<span>Type</span>
				<select :value="selectedItem.item_type" class="form-control" @change="updateSection('item_type', $event.target.value)">
					<option value="Section Break">Section Break</option>
					<option value="Tab Break">Tab Break</option>
				</select>
			</label>
		</div>
		<div v-else class="afb-properties-group">
			<h3>Column</h3>
			<p class="text-muted small">Columns are structural only. Drag fields into this container or remove the column.</p>
		</div>
	</aside>
</template>

<script setup>
import { computed } from "vue";
import { useFormBuilderStore } from "../store.js";
import FieldProperties from "./FieldProperties.vue";

const store = useFormBuilderStore();
const selected = computed(() => store.selected || {});
const selectedItem = computed(() => store.selectedItem);

function updateSection(key, value) {
	if (!store.selectedItem?.id) return;
	store.updateSection(store.selectedItem.id, { [key]: value });
}
</script>
