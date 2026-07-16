from frappe.model.document import Document


DEFAULT_OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"


class FormBuilderConfig(Document):
	def validate(self):
		self.openai_api_url = (self.openai_api_url or DEFAULT_OPENAI_API_URL).strip()
		self.google_service_account_json = (self.google_service_account_json or "").strip()
		self.form_builder_system_prompt = (self.form_builder_system_prompt or "").strip()
		self.autofill_system_prompt = (self.autofill_system_prompt or "").strip()
