<script setup>
import { computed, ref, watch } from "vue";
import { computedAsync } from "@vueuse/core";

const props = defineProps({
	df: { type: Object, default: () => ({}) },
	modelValue: { type: String, default: "" },
	read_only: { type: Boolean, default: false },
	sourceFields: { type: Array, default: () => [] },
	excludeFieldname: { type: String, default: "" },
});

const emit = defineEmits(["update:modelValue"]);

const sourceFieldname = ref("");
const targetFieldname = ref("");
const helpMessage = computed(() => {
	if (!linkFieldOptions.value.length) {
		return __("Add a Link field first, then choose which field to fetch from it.");
	}
	if (!sourceFieldname.value) {
		return __("Step 1: choose the source Link field.");
	}
	if (!targetOptions.value.length) {
		return __("No fetchable fields were found for the selected DocType.");
	}
	return __("Step 2: choose the field to fetch from the linked document.");
});
const fetchExpression = computed(() => (
	sourceFieldname.value && targetFieldname.value
		? `${sourceFieldname.value}.${targetFieldname.value}`
		: ""
));

function loadDoctypeModel(doctype) {
	return frappe.call("frappe.desk.form.load.getdoctype", { doctype });
}

const linkFieldOptions = computed(() => {
	return (props.sourceFields || [])
		.filter((field) => field.fieldtype === "Link")
		.filter((field) => field.options)
		.filter((field) => field.fieldname !== props.excludeFieldname)
		.sort((a, b) => String(a.options || "").localeCompare(String(b.options || "")))
		.map((field) => ({
			label: `${field.label || field.fieldname} (${field.options})`,
			value: field.fieldname,
			doctype_name: field.options,
		}));
});
const targetOptions = computedAsync(async () => {
	if (!sourceFieldname.value) {
		return [];
	}

	const linkField = linkFieldOptions.value.find((item) => item.value === sourceFieldname.value);
	const doctypeName = String(linkField?.doctype_name || "").trim();
	if (!doctypeName) {
		return [];
	}

	if ((props.modelValue || "").split(".")[0] !== sourceFieldname.value) {
		targetFieldname.value = "";
	}

	try {
		await loadDoctypeModel(doctypeName);
		return frappe.meta
			.get_docfields(doctypeName, null, {
				fieldtype: ["not in", frappe.model.no_value_type],
			})
			.sort((a, b) => {
				if (a.label && b.label) {
					return a.label.localeCompare(b.label);
				}
				return 0;
			})
			.map((field) => ({
				label: `${field.label || __("No Label")} (${field.fieldtype})`,
				value: field.fieldname,
			}));
	} catch (error) {
		console.error("Ampower FetchFromControl doctype load failed", error);
		return [];
	}
}, []);

watch(
	() => props.modelValue,
	(value) => {
		if (value) {
			[sourceFieldname.value, targetFieldname.value] = value.split(".") || ["", ""];
			return;
		}
		sourceFieldname.value = "";
		targetFieldname.value = "";
	},
	{ immediate: true }
);

watch([sourceFieldname, targetFieldname], ([sourceValue, targetValue]) => {
	const currentValue = props.modelValue || "";
	const nextValue = sourceValue && targetValue ? `${sourceValue}.${targetValue}` : "";
	if (nextValue !== currentValue) {
		emit("update:modelValue", nextValue);
	}
});
</script>

<template>
	<div class="afb-fetch-from-control">
		<label class="form-group">
			<span>{{ __("Source Link Field") }}</span>
			<select
				class="form-control"
				:value="sourceFieldname"
				:disabled="read_only"
				@change="sourceFieldname = $event.target.value"
			>
				<option value="">{{ __("Select Link Field") }}</option>
				<option v-for="option in linkFieldOptions" :key="option.value" :value="option.value">
					{{ option.label }}
				</option>
			</select>
		</label>
		<label v-if="sourceFieldname" class="form-group">
			<span>{{ __("Field To Fetch") }}</span>
			<select
				class="form-control"
				:value="targetFieldname"
				:disabled="read_only || !targetOptions.length"
				@change="targetFieldname = $event.target.value"
			>
				<option value="">{{ __("Select Field") }}</option>
				<option v-for="option in targetOptions" :key="option.value" :value="option.value">
					{{ option.label }}
				</option>
			</select>
		</label>
		<div class="help-box small text-muted">{{ helpMessage }}</div>
		<div v-if="fetchExpression" class="help-box small">
			{{ __("Saved as: {0}", [fetchExpression]) }}
		</div>
	</div>
</template>
