<template>
	<div
		class="afb-field-card"
		:class="{ 'is-selected': isSelected }"
		data-role="field"
		:data-id="field.id"
		@click.stop="store.selectItem(field.id)"
	>
		<header class="afb-field-header">
			<div class="afb-field-title">
				<button class="afb-drag-handle btn-reset" type="button">⋮⋮</button>
				<div>
					<strong>{{ field.label || "Untitled Field" }}</strong>
					<div class="afb-field-meta">
						{{ field.fieldtype }}
						<span v-if="['Table', 'Mixed Table'].includes(field.fieldtype)">· {{ `${field.table_columns?.length || 0} columns` }}</span>
						<span v-if="field.fieldtype === 'Mixed Table'">· {{ `${field.table_rows?.length || 0} rows` }}</span>
					</div>
				</div>
			</div>
			<div class="afb-card-actions">
				<span v-if="field.reqd" class="afb-required">*</span>
				<button class="btn-reset afb-delete-icon" type="button" @click.stop="store.deleteField(field.id)">✕</button>
			</div>
		</header>
		<div class="afb-field-preview">
			<TablePreview
				v-if="['Table', 'Mixed Table'].includes(field.fieldtype)"
				:field-type="field.fieldtype"
				:columns="field.table_columns || []"
				:row-definitions="field.table_rows || []"
				:initial-data="field.table_data || []"
				:row-title="field.table_row_title || ''"
			/>
			<component v-else :is="controlComponent" :df="field" :read-only="true" />
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { getControlComponentName } from "../utils.js";
import { useFormBuilderStore } from "../store.js";
import TablePreview from "./TablePreview.vue";

const props = defineProps({
	field: { type: Object, required: true },
});

const store = useFormBuilderStore();
const isSelected = computed(() => store.selected?.id === props.field.id);
const controlComponent = computed(() => getControlComponentName(props.field.fieldtype));
</script>
