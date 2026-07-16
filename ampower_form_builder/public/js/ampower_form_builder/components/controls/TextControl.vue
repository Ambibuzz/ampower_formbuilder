<!-- Used as Small Text & Long Text Control -->
<script setup>
import { computed, useSlots } from "vue";

const props = defineProps(["df", "value", "read_only", "modelValue"]);
const slots = useSlots();

const height = computed(() => ["Long Text", "Text"].includes(props.df.fieldtype) ? "300px" : "150px");
</script>

<template>
	<div class="control" :class="{ editable: slots.label }">
		<div v-if="slots.label" class="field-controls">
			<slot name="label" />
			<slot name="actions" />
		</div>
		<div v-else class="control-label label">{{ __(df.label) }}</div>

		<textarea
			v-if="slots.label"
			:style="{ height: height, maxHeight: df.max_height ?? '' }"
			class="form-control"
			type="text"
			readonly
		/>
		<textarea
			v-else
			:style="{ height: height, maxHeight: df.max_height ?? '' }"
			class="form-control"
			type="text"
			:value="value"
			:disabled="read_only || df.read_only"
			@input="(event) => $emit('update:modelValue', event.target.value)"
		/>

		<div v-if="df.description" class="mt-2 description" v-html="df.description"></div>
	</div>
</template>
