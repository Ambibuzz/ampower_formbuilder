<template>
	<div class="afb-library-grid">
		<button
			v-for="item in layoutItems"
			:key="item.fieldtype"
			class="afb-library-item"
			type="button"
			draggable="true"
			@dragstart="onDragStart($event, item)"
			@click="store.addLibraryItem(item, {})"
		>
			<span>{{ item.label }}</span>
		</button>
	</div>
</template>

<script setup>
import { useFormBuilderStore } from "../store.js";

const store = useFormBuilderStore();
const layoutItems = [
	{ kind: "layout-section", fieldtype: "Section Break", label: "Section Break" },
	{ kind: "layout-section", fieldtype: "Tab Break", label: "Tab Break" },
	{ kind: "layout-column", fieldtype: "Column Break", label: "Column Break" },
];

function onDragStart(event, item) {
	event.dataTransfer?.setData("application/json", JSON.stringify(item));
}
</script>
