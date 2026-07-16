function clonePayload(payload) {
	return payload ? JSON.parse(JSON.stringify(payload)) : payload;
}

const templateSchemaCache = new Map();
const templateSchemaRequests = new Map();

export async function getCachedTemplateSchema(templateName, options = {}) {
	const normalizedTemplateName = String(templateName || "").trim();
	if (!normalizedTemplateName) return null;

	const force = Boolean(options.force);
	if (!force && templateSchemaCache.has(normalizedTemplateName)) {
		return clonePayload(templateSchemaCache.get(normalizedTemplateName));
	}

	if (!force && templateSchemaRequests.has(normalizedTemplateName)) {
		return clonePayload(await templateSchemaRequests.get(normalizedTemplateName));
	}

	const request = (async () => {
		const response = await frappe.call({
			method: "ampower_form_builder.api.get_form_schema",
			args: { form_template: normalizedTemplateName },
		});

		const payload = response?.message || null;
		if (payload) {
			templateSchemaCache.set(normalizedTemplateName, clonePayload(payload));
		}

		return payload;
	})();

	templateSchemaRequests.set(normalizedTemplateName, request);

	try {
		return clonePayload(await request);
	} finally {
		templateSchemaRequests.delete(normalizedTemplateName);
	}
}

export function invalidateTemplateSchemaCache(templateName) {
	const normalizedTemplateName = String(templateName || "").trim();
	if (!normalizedTemplateName) return;
	templateSchemaCache.delete(normalizedTemplateName);
	templateSchemaRequests.delete(normalizedTemplateName);
}
