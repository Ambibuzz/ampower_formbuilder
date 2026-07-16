<template>
	<div class="afb-library-grid">
		<button
			v-for="field in fieldTypes"
			:key="field.key || field.label"
			class="afb-library-item"
			type="button"
			draggable="true"
			@dragstart="onDragStart($event, field)"
			@click="store.addLibraryItem({ kind: 'field', fieldtype: field.fieldtype }, {})"
		>
			<span>{{ field.label }}</span>
		</button>
	</div>
</template>

<script setup>
import { FIELD_LIBRARY_ITEMS } from "../utils.js";
import { useFormBuilderStore } from "../store.js";

const store = useFormBuilderStore();
const fieldTypes = FIELD_LIBRARY_ITEMS;

function onDragStart(event, field) {
	event.dataTransfer?.setData("application/json", JSON.stringify({
		kind: "field",
		fieldtype: field.fieldtype,
	}));
}
</script>
