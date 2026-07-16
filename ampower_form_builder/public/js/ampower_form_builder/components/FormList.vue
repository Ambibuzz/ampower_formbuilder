<template>
	<div class="afb-template-list">
		<div v-if="loading" class="text-muted small">Loading templates...</div>
		<button
			v-for="template in templates"
			:key="template.name"
			class="afb-template-item"
			:class="{ 'is-active': template.name === store.currentTemplate.name || template.form_name === store.currentTemplate.form_name }"
			type="button"
			@click="store.loadTemplate(template.name)"
		>
			<strong>{{ template.display_name || template.form_name }}</strong>
			<small>{{ `${t("Version")} ${template.version_label || "1.0"}` }}</small>
			<span>{{ template.description || "No description" }}</span>
		</button>
	</div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useFormBuilderStore } from "../store.js";

const store = useFormBuilderStore();
const loading = ref(false);
const templates = ref([]);
const t = window.__ || ((text) => text);

async function fetchTemplates() {
	loading.value = true;
	try {
		const { message } = await frappe.call({ method: "ampower_form_builder.api.get_active_templates" });
		templates.value = message || [];
	} catch (error) {
		frappe.msgprint({ title: t("Error"), message: error?.message || t("Unable to load templates."), indicator: "red" });
	} finally {
		loading.value = false;
	}
}

onMounted(fetchTemplates);
</script>
