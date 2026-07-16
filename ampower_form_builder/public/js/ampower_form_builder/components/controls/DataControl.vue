<!-- Used as Color, Data, Date, Datetime, Dynamic Link, Number, Time Control -->
<script setup>
import { computed, ref, useSlots } from "vue";

const props = defineProps(["df", "value", "read_only"]);
const slots = useSlots();
const time_zone = ref("");
const placeholder = ref("");

if (props.df.fieldtype === "Datetime") {
	const time_zone_text = frappe.boot.time_zone
		? frappe.boot.time_zone.user
		: frappe.sys_defaults.time_zone;
	time_zone.value = time_zone_text;
}

if (props.df.fieldtype === "Color") {
	placeholder.value = __("Choose a color");
}

const inputType = computed(() => props.df.fieldtype === "Number" ? "number" : "text");
const inputStep = computed(() => {
	if (props.df.fieldtype !== "Number") return undefined;
	const precision = Number(props.df.precision);
	if (!Number.isFinite(precision) || precision <= 0) return "1";
	return (1 / (10 ** precision)).toString();
});
</script>

<template>
	<div class="control frappe-control" :class="{ editable: slots.label }">
		<div v-if="slots.label" class="field-controls">
			<slot name="label" />
			<slot name="actions" />
		</div>
		<div v-else class="control-label label" :class="{ reqd: df.reqd }">{{ __(df.label) }}</div>

		<input
			v-if="slots.label"
			class="form-control"
			:type="inputType"
			:placeholder="__(placeholder)"
			readonly
		>
		<input
			v-else
			class="form-control"
			:type="inputType"
			:step="inputStep"
			:value="value"
			:disabled="read_only || df.read_only"
			@input="(event) => $emit('update:modelValue', event.target.value)"
		>

		<div v-if="df.description" class="mt-2 description" v-html="__(df.description)" />
		<div v-if="time_zone" :class="['time-zone', !df.description ? 'mt-2' : '']" v-html="time_zone" />
		<div v-if="df.fieldtype === 'Color'" class="selected-color no-value" />
	</div>
</template>

<style lang="scss" scoped>
.selected-color {
	background-color: transparent;
	top: 30px !important;
}
</style>
