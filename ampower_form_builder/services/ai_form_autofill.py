"""AI-assisted form viewer autofill pipeline."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import frappe
import requests
from frappe import _
from frappe.realtime import publish_progress
from frappe.utils.background_jobs import enqueue, get_job_status
from rq import get_current_job

from ampower_form_builder.services.ai_form_builder import (
	AiFormBuilderError,
	AiFormBuilderProcessingError,
	AiFormBuilderValidationError,
	FormBuilderConfigRepository,
	GoogleVisionClient,
	OcrPage,
	OcrTableDetector,
	PdfPageRasterizer,
	TableHint,
	_normalize_text,
)


TEMPLATE_DOCTYPE = "Dynamic Form Template"
AI_AUTOFILL_STATUS_TTL = 7 * 24 * 60 * 60
AI_AUTOFILL_REASONING_EFFORT = "minimal"
AI_AUTOFILL_MAX_COMPLETION_TOKENS = 8000
DEFAULT_AI_AUTOFILL_SYSTEM_PROMPT = (
	"You are an expert Frappe/ERPNext form autofill assistant. "
	"Map OCR text into the provided form template fieldnames. "
	"Use only values supported by the OCR. "
	"Leave uncertain fields blank instead of guessing. "
	"Return clean JSON only."
)
LAYOUT_FIELD_TYPES = {"Section Break", "Column Break", "Tab Break", "HTML", "Heading"}
TABLE_FIELD_TYPES = {"Table", "Mixed Table"}


@dataclass(slots=True)
class AutofillProgressReporter:
	job_id: str
	owner: str
	status_store: "AutofillStatusStore"

	def update(self, percent: int, stage: str, message: str, **extra: Any) -> None:
		payload = {
			"job_id": self.job_id,
			"owner": self.owner,
			"status": "processing",
			"stage": stage,
			"message": message,
			"progress": max(0, min(int(percent), 100)),
			"updated_at": _utc_now_iso(),
		}
		payload.update(extra)
		self.status_store.update(self.job_id, payload)
		publish_progress(payload["progress"], title=_("Ampower AI Autofill"), description=message, task_id=self.job_id)

	def complete(self, result: dict[str, Any]) -> None:
		payload = {
			"job_id": self.job_id,
			"owner": self.owner,
			"status": "completed",
			"stage": "complete",
			"message": _("AI autofill completed successfully."),
			"progress": 100,
			"result": result,
			"error": "",
			"updated_at": _utc_now_iso(),
		}
		self.status_store.update(self.job_id, payload)
		publish_progress(100, title=_("Ampower AI Autofill"), description=payload["message"], task_id=self.job_id)

	def fail(self, message: str, *, stage: str = "failed") -> None:
		payload = {
			"job_id": self.job_id,
			"owner": self.owner,
			"status": "failed",
			"stage": stage,
			"message": message,
			"progress": 100,
			"error": message,
			"updated_at": _utc_now_iso(),
		}
		self.status_store.update(self.job_id, payload)
		publish_progress(100, title=_("Ampower AI Autofill"), description=message, task_id=self.job_id)


class AutofillStatusStore:
	"""Stores the latest autofill state in Redis so the UI can poll it."""

	def __init__(self, prefix: str = "ampower_form_builder:ai_autofill") -> None:
		self.prefix = prefix

	def key(self, job_id: str) -> str:
		return f"{self.prefix}:{job_id}"

	def create(self, job_id: str, owner: str, file_docname: str, file_name: str, template_name: str) -> dict[str, Any]:
		payload = {
			"job_id": job_id,
			"owner": owner,
			"file_docname": file_docname,
			"file_name": file_name,
			"template_name": template_name,
			"status": "queued",
			"stage": "queued",
			"message": _("Queued for AI autofill."),
			"progress": 0,
			"result": None,
			"error": "",
			"updated_at": _utc_now_iso(),
		}
		frappe.cache.set_value(self.key(job_id), payload, expires_in_sec=AI_AUTOFILL_STATUS_TTL)
		return payload

	def update(self, job_id: str, patch: dict[str, Any]) -> dict[str, Any]:
		current = self.get(job_id) or {"job_id": job_id}
		current.update(patch)
		current.setdefault("updated_at", _utc_now_iso())
		frappe.cache.set_value(self.key(job_id), current, expires_in_sec=AI_AUTOFILL_STATUS_TTL)
		return current

	def get(self, job_id: str) -> dict[str, Any] | None:
		return frappe.cache.get_value(self.key(job_id))


class OpenAiFormAutofillClient:
	"""Transform OCR text into a form-value payload using OpenAI."""

	def __init__(self, config, timeout_seconds: int = 600) -> None:
		self.config = config
		self.timeout_seconds = timeout_seconds
		self.session = requests.Session()

	def generate(
		self,
		ocr_pages: list[OcrPage],
		template_name: str,
		template_fields: list[dict[str, Any]],
		table_hints: list[TableHint] | None = None,
	) -> dict[str, Any]:
		messages = self._build_messages(ocr_pages, template_name, template_fields, table_hints or [])
		payload = {
			"model": self.config.model,
			"messages": messages,
			"reasoning_effort": AI_AUTOFILL_REASONING_EFFORT,
			"max_completion_tokens": AI_AUTOFILL_MAX_COMPLETION_TOKENS,
			"response_format": {"type": "json_object"},
		}

		response = self.session.post(
			self.config.openai_api_url,
			headers={
				"Authorization": f"Bearer {self.config.openai_api_key}",
				"Content-Type": "application/json",
			},
			json=payload,
			timeout=self.timeout_seconds,
		)
		self._raise_for_http_error(response, _("OpenAI autofill request failed."))
		data = response.json()
		choice = (data.get("choices") or [{}])[0]
		message = choice.get("message") or {}

		if message.get("refusal"):
			raise AiFormBuilderProcessingError(message["refusal"])

		content = message.get("content") or ""
		if not content.strip():
			raise AiFormBuilderProcessingError(_("OpenAI returned an empty autofill response."))

		try:
			draft = json.loads(content)
		except json.JSONDecodeError as exc:
			raise AiFormBuilderProcessingError(_("OpenAI returned invalid autofill JSON. {0}").format(str(exc))) from exc

		if not isinstance(draft, dict):
			raise AiFormBuilderProcessingError(_("OpenAI autofill response must be a JSON object."))

		return draft

	def _build_messages(
		self,
		ocr_pages: list[OcrPage],
		template_name: str,
		template_fields: list[dict[str, Any]],
		table_hints: list[TableHint],
	) -> list[dict[str, str]]:
		source_summary = "\n".join(
			f"Page {page.page_number}:\n{page.text or '[No text detected]'}".strip()
			for page in ocr_pages
		)
		template_summary = self._render_template_fields(template_fields)
		table_hint_summary = self._render_table_hints(table_hints)

		system_prompt = (
			getattr(self.config, "autofill_system_prompt", "")
			or ""
		).strip() or DEFAULT_AI_AUTOFILL_SYSTEM_PROMPT

		user_prompt = (
			f"Form template: {template_name}\n\n"
			"Template fields:\n"
			f"{template_summary}\n\n"
			"OCR text by page:\n"
			f"{source_summary}\n\n"
			"Return JSON with:\n"
			"- field_values: an array of {fieldname, value} objects\n"
			"- warnings: an array of short notes\n"
			"- unmapped_fields: fieldnames that could not be confidently filled\n\n"
			"Rules:\n"
			"- Use template fieldnames exactly as provided.\n"
			"- Do not invent new keys.\n"
			"- Use YYYY-MM-DD for Date fields.\n"
			"- Use YYYY-MM-DD HH:MM:SS for Datetime fields.\n"
			"- Use HH:MM:SS for Time fields.\n"
			"- Keep table values as arrays of row objects keyed by table column fieldname.\n"
			"- For Select/Radio fields, use one of the documented options when possible.\n"
		)

		if table_hint_summary:
			user_prompt += (
				"\nDetected structural hints from OCR:\n"
				f"{table_hint_summary}\n"
			)

		return [
			{"role": "system", "content": system_prompt},
			{"role": "user", "content": user_prompt},
		]

	def _render_template_fields(self, template_fields: list[dict[str, Any]]) -> str:
		if not template_fields:
			return "[No fields found]"

		lines: list[str] = []
		for field in template_fields[:120]:
			label = field.get("label") or field.get("fieldname") or "Field"
			fieldtype = field.get("fieldtype") or "Data"
			fieldname = field.get("fieldname") or ""
			line = f"- {fieldname} [{fieldtype}] {label}"
			options = _normalize_text(field.get("options") or "")
			if fieldtype in {"Select", "Radio"} and options:
				line += f" | options: {options}"
			if fieldtype in TABLE_FIELD_TYPES:
				columns = field.get("table_columns") or []
				column_bits = []
				for column in columns:
					column_bits.append(
						f"{column.get('fieldname') or column.get('label') or 'column'}:{column.get('fieldtype') or 'Data'}"
					)
				if column_bits:
					line += f" | columns: {'; '.join(column_bits)}"
			lines.append(line)
		return "\n".join(lines)

	def _render_table_hints(self, table_hints: list[TableHint]) -> str:
		if not table_hints:
			return ""

		lines: list[str] = []
		for hint in table_hints[:8]:
			lines.append(f"- Page {hint.page_number}: {hint.title} ({hint.kind})")
			if hint.columns:
				lines.append(f"  Columns: {' | '.join(hint.columns[:10])}")
		return "\n".join(lines)

	def _raise_for_http_error(self, response: requests.Response, fallback_message: str) -> None:
		if response.ok:
			return
		message = _parse_http_error(response, fallback_message)
		raise AiFormBuilderProcessingError(message)


def build_template_field_specs(template_doc) -> list[dict[str, Any]]:
	schema = _parse_schema_json(getattr(template_doc, "schema_json", None))
	fields = schema.get("fields") or []
	if not fields and schema.get("sections"):
		fields = []
		for section in schema.get("sections", []):
			for column in (section or {}).get("columns", []) or []:
				fields.extend((column or {}).get("items", []) or [])
	specs: list[dict[str, Any]] = []

	for field in fields:
		normalized = _normalize_field(field)
		fieldtype = normalized.get("fieldtype") or "Data"
		if fieldtype in LAYOUT_FIELD_TYPES:
			continue

		spec = {
			"fieldtype": fieldtype,
			"fieldname": normalized.get("fieldname") or "",
			"label": normalized.get("label") or normalized.get("fieldname") or "",
			"options": normalized.get("options") or "",
			"reqd": 1 if normalized.get("reqd") in (True, 1, "1") else 0,
			"description": normalized.get("description") or "",
			"placeholder": normalized.get("placeholder") or "",
			"precision": normalized.get("precision") or "",
		}

		if fieldtype in TABLE_FIELD_TYPES:
			spec["table_columns"] = _parse_table_columns(normalized.get("options") or normalized.get("table_columns") or [])
			spec["table_rows"] = _parse_table_rows(normalized.get("options") or normalized.get("table_rows") or [])

		specs.append(spec)

	return specs


def normalize_autofill_values(template_fields: list[dict[str, Any]], raw_values: Any) -> dict[str, Any]:
	values = _extract_autofill_value_map(raw_values)
	normalized: dict[str, Any] = {}

	for field in template_fields:
		fieldname = (field.get("fieldname") or "").strip()
		if not fieldname or fieldname not in values:
			continue

		next_value = _normalize_field_value(field, values[fieldname])
		if _should_keep_value(field, next_value):
			normalized[fieldname] = next_value

	return normalized


def _extract_autofill_value_map(raw_values: Any) -> dict[str, Any]:
	if isinstance(raw_values, dict):
		field_values = raw_values.get("field_values")
		if isinstance(field_values, list):
			values: dict[str, Any] = {}
			for item in field_values:
				if not isinstance(item, dict):
					continue
				fieldname = (item.get("fieldname") or "").strip()
				if not fieldname:
					continue
				values[fieldname] = item.get("value")
			return values
		return raw_values

	if isinstance(raw_values, list):
		values: dict[str, Any] = {}
		for item in raw_values:
			if not isinstance(item, dict):
				continue
			fieldname = (item.get("fieldname") or "").strip()
			if not fieldname:
				continue
			values[fieldname] = item.get("value")
		return values

	return {}


def _normalize_field(field: dict[str, Any]) -> dict[str, Any]:
	normalized = dict(field or {})

	field_type = normalized.get("fieldtype") or normalized.get("field_type")
	if field_type:
		normalized["fieldtype"] = field_type
		normalized["field_type"] = field_type

	fieldname = normalized.get("fieldname") or normalized.get("field_name")
	if fieldname:
		normalized["fieldname"] = fieldname
		normalized["field_name"] = fieldname

	label = normalized.get("label") or normalized.get("field_label")
	if label:
		normalized["label"] = label
		normalized["field_label"] = label

	if normalized.get("reqd") in (True, "1", 1):
		normalized["reqd"] = 1

	return normalized


def _parse_schema_json(schema_json):
	if isinstance(schema_json, str):
		return json.loads(schema_json)
	if isinstance(schema_json, dict):
		return schema_json
	return {}


def _parse_table_columns(options: Any) -> list[dict[str, Any]]:
	parsed = _parse_table_options(options)
	columns = parsed.get("columns") or parsed.get("table_columns") or []
	result: list[dict[str, Any]] = []
	for column in columns if isinstance(columns, list) else []:
		column = dict(column or {})
		result.append(
			{
				"label": column.get("label") or column.get("fieldname") or _("Column"),
				"fieldname": column.get("fieldname") or "",
				"fieldtype": column.get("fieldtype") or "Data",
				"options": column.get("options") or "",
				"reqd": 1 if column.get("reqd") in (True, 1, "1") else 0,
			}
		)
	return result


def _parse_table_rows(options: Any) -> list[dict[str, Any]]:
	parsed = _parse_table_options(options)
	rows = parsed.get("rows") or []
	result: list[dict[str, Any]] = []
	for row in rows if isinstance(rows, list) else []:
		row = dict(row or {})
		result.append(
			{
				"label": row.get("label") or "",
				"key": row.get("key") or row.get("label") or "",
			}
		)
	return result


def _parse_table_options(options: Any) -> dict[str, Any]:
	if isinstance(options, dict):
		return options
	if not options:
		return {}
	if isinstance(options, str):
		try:
			parsed = json.loads(options)
		except Exception:
			return {}
		return parsed if isinstance(parsed, dict) else {}
	return {}


def _normalize_field_value(field: dict[str, Any], value: Any) -> Any:
	fieldtype = (field.get("fieldtype") or "").strip()
	if value is None:
		return _empty_value(fieldtype)

	if fieldtype in TABLE_FIELD_TYPES:
		return _normalize_table_value(field, value)
	if fieldtype == "Check":
		return _normalize_check_value(value)
	if fieldtype in {"Number", "Percent", "Int", "Float", "Currency"}:
		return _normalize_number_value(value)
	if fieldtype in {"Date", "Datetime", "Time"}:
		return _normalize_date_value(fieldtype, value)

	if isinstance(value, str):
		return value.strip()
	return value


def _normalize_table_value(field: dict[str, Any], value: Any) -> list[dict[str, Any]]:
	rows = value if isinstance(value, list) else []
	columns = field.get("table_columns") or []
	if not isinstance(columns, list):
		columns = []

	normalized_rows: list[dict[str, Any]] = []
	for row in rows:
		if not isinstance(row, dict):
			continue
		normalized_row: dict[str, Any] = {}
		for column in columns:
			column_name = (column.get("fieldname") or "").strip()
			if not column_name:
				continue
			normalized_row[column_name] = _normalize_column_value(column, row.get(column_name))
		if any(_has_meaningful_value(item) for item in normalized_row.values()):
			normalized_rows.append(normalized_row)
	return normalized_rows


def _normalize_column_value(column: dict[str, Any], value: Any) -> Any:
	fieldtype = (column.get("fieldtype") or "Data").strip()
	if value is None:
		return _empty_value(fieldtype)
	if fieldtype == "Check":
		return _normalize_check_value(value)
	if fieldtype in {"Number", "Percent", "Int", "Float", "Currency"}:
		return _normalize_number_value(value)
	if fieldtype in {"Date", "Datetime", "Time"}:
		return _normalize_date_value(fieldtype, value)
	if isinstance(value, str):
		return value.strip()
	return value


def _normalize_check_value(value: Any) -> int:
	if isinstance(value, bool):
		return 1 if value else 0
	if isinstance(value, (int, float)):
		return 1 if value else 0
	text = str(value).strip().lower()
	return 1 if text in {"1", "true", "yes", "y", "on"} else 0


def _normalize_number_value(value: Any) -> Any:
	if isinstance(value, (int, float)) and not isinstance(value, bool):
		return value
	text = str(value).strip()
	if not text:
		return ""
	try:
		number = float(text)
	except Exception:
		return ""
	if number.is_integer():
		return int(number)
	return number


def _normalize_date_value(fieldtype: str, value: Any) -> str:
	text = str(value).strip()
	if not text:
		return ""

	formats = {
		"Date": ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d %b %Y", "%d %B %Y"),
		"Datetime": ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d-%m-%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S"),
		"Time": ("%H:%M:%S", "%H:%M"),
	}
	for fmt in formats.get(fieldtype, ()):
		try:
			dt = datetime.strptime(text, fmt)
		except Exception:
			continue
		if fieldtype == "Date":
			return dt.strftime("%Y-%m-%d")
		if fieldtype == "Datetime":
			return dt.strftime("%Y-%m-%d %H:%M:%S")
		return dt.strftime("%H:%M:%S")
	return text


def _empty_value(fieldtype: str) -> Any:
	if fieldtype == "Check":
		return 0
	if fieldtype in TABLE_FIELD_TYPES:
		return []
	return ""


def _has_meaningful_value(value: Any) -> bool:
	if value is None:
		return False
	if isinstance(value, bool):
		return True
	if isinstance(value, (int, float)):
		return True
	if isinstance(value, str):
		return bool(value.strip())
	if isinstance(value, list):
		return len(value) > 0
	if isinstance(value, dict):
		return bool(value)
	return True


def _should_keep_value(field: dict[str, Any], value: Any) -> bool:
	fieldtype = (field.get("fieldtype") or "").strip()
	if fieldtype == "Check":
		return True
	if fieldtype in TABLE_FIELD_TYPES:
		return isinstance(value, list) and len(value) > 0
	return _has_meaningful_value(value)


def _build_openai_schema() -> dict[str, Any]:
	return {
		"type": "object",
		"additionalProperties": False,
		"required": ["field_values", "warnings", "unmapped_fields"],
		"properties": {
			"field_values": {
				"type": "array",
				"items": {
					"type": "object",
					"additionalProperties": False,
					"required": ["fieldname", "value"],
					"properties": {
						"fieldname": {"type": "string"},
						"value": {
							"anyOf": [
								{"type": "string"},
								{"type": "number"},
								{"type": "boolean"},
								{"type": "null"},
								{"type": "array"},
							],
						},
					},
				},
			},
			"warnings": {
				"type": "array",
				"items": {"type": "string"},
			},
			"unmapped_fields": {
				"type": "array",
				"items": {"type": "string"},
			},
		},
	}


def _parse_http_error(response: requests.Response, fallback_message: str) -> str:
	try:
		data = response.json()
	except Exception:
		data = {}

	message_parts = []
	if isinstance(data, dict):
		if data.get("error"):
			error = data["error"]
			if isinstance(error, dict):
				if error.get("message"):
					message_parts.append(str(error["message"]))
				details = error.get("details")
				if details:
					message_parts.append(str(details))
			elif error:
				message_parts.append(str(error))

		if data.get("message"):
			message_parts.append(str(data["message"]))

	text = response.text.strip()
	if text and text not in message_parts:
		message_parts.append(text)

	if not message_parts:
		message_parts.append(fallback_message)

	status_bits = [f"HTTP {response.status_code}"]
	if response.reason:
		status_bits.append(response.reason)
	return f"{' '.join(status_bits)}: {' '.join(message_parts)}"


def _utc_now_iso() -> str:
	return datetime.now(timezone.utc).isoformat()


def _current_background_job_id() -> str:
	job = get_current_job()
	if not job or not job.id:
		return ""

	job_id = str(job.id)
	if "::" in job_id:
		return job_id.rsplit("::", 1)[-1]
	return job_id


def _job_status_text(status: Any) -> str:
	if not status:
		return ""
	text = str(status)
	if "." in text:
		text = text.rsplit(".", 1)[-1]
	return text.lower()


def _normalize_job_status(status_text: str) -> str:
	mapping = {
		"finished": "completed",
		"success": "completed",
		"started": "processing",
		"queued": "queued",
		"deferred": "queued",
	}
	return mapping.get(status_text, status_text)


class AiFormAutofillService:
	"""Orchestrates the OCR + field mapping workflow."""

	def __init__(self) -> None:
		self.config_repository = FormBuilderConfigRepository()
		self.status_store = AutofillStatusStore()
		self.rasterizer = PdfPageRasterizer()
		self.table_detector = OcrTableDetector()

	def enqueue_autofill(self, file_docname: str, template_name: str) -> dict[str, Any]:
		file_doc = self._load_file_doc(file_docname)
		template_doc = self._load_template_doc(template_name)
		self._validate_template(template_doc)

		job_id = frappe.generate_hash(length=16)
		self.status_store.create(job_id, frappe.session.user, file_doc.name, file_doc.file_name, template_doc.name)

		enqueue(
			"ampower_form_builder.services.ai_form_autofill.process_ai_form_autofill",
			queue="long",
			timeout=1800,
			enqueue_after_commit=True,
			job_id=job_id,
			file_docname=file_doc.name,
			template_name=template_doc.name,
			owner=frappe.session.user,
		)

		return {
			"job_id": job_id,
			"status": "queued",
			"file_docname": file_doc.name,
			"file_name": file_doc.file_name,
			"template_name": template_doc.name,
		}

	def get_status(self, job_id: str) -> dict[str, Any]:
		if not job_id:
			raise AiFormBuilderValidationError(_("Job ID is required."))

		status = self.status_store.get(job_id) or {}
		rq_status = get_job_status(job_id)
		rq_status_text = _normalize_job_status(_job_status_text(rq_status))

		if not status:
			if rq_status_text:
				status = {
					"job_id": job_id,
					"status": rq_status_text,
					"stage": rq_status_text,
					"message": _("Job status: {0}").format(rq_status_text),
					"progress": 0 if rq_status_text in {"queued", "processing"} else 100,
					"result": None,
					"error": "",
					"updated_at": _utc_now_iso(),
				}
			else:
				raise AiFormBuilderValidationError(_("AI autofill job was not found."))

		if status.get("owner") and status.get("owner") != frappe.session.user:
			raise AiFormBuilderValidationError(_("You are not allowed to access this AI autofill job."))

		if rq_status_text and status.get("status") in {"queued", "processing"} and rq_status_text == "failed":
			status["status"] = "failed"
			status["stage"] = "failed"
			status["progress"] = 100
			status.setdefault("error", _("The background job failed."))

		status["rq_status"] = rq_status_text
		status["finished"] = status.get("status") in {"completed", "failed"}
		return status

	def process_autofill(self, file_docname: str, template_name: str, owner: str, job_id: str | None = None) -> dict[str, Any]:
		resolved_job_id = job_id or _current_background_job_id()
		if not resolved_job_id:
			raise AiFormBuilderProcessingError(_("Unable to determine the AI autofill job ID."))

		progress = AutofillProgressReporter(job_id=resolved_job_id, owner=owner, status_store=self.status_store)
		previous_user = getattr(getattr(frappe, "session", None), "user", None)
		restore_user = bool(owner) and previous_user != owner

		try:
			if restore_user:
				frappe.set_user(owner)

			progress.update(5, "loading", _("Loading uploaded file and form template..."))
			file_doc = self._load_file_doc(file_docname)
			template_doc = self._load_template_doc(template_name)
			template_fields = build_template_field_specs(template_doc)

			if not template_fields:
				raise AiFormBuilderProcessingError(_("The selected form template does not contain any fillable fields."))

			pages = self.rasterizer.render(file_doc)
			progress.update(20, "rendering", _("Rendered {0} page(s) for OCR.").format(len(pages)))

			config = self.config_repository.load()
			vision_client = GoogleVisionClient(config)
			ocr_pages = vision_client.detect_text(pages)
			table_hints = self.table_detector.detect(ocr_pages)
			progress.update(
				55,
				"ocr",
				_("OCR completed for {0} page(s).").format(len(ocr_pages)),
				table_candidates=len(table_hints),
			)

			openai_client = OpenAiFormAutofillClient(config)
			progress.update(75, "mapping", _("Mapping OCR text to form fields..."))
			draft = openai_client.generate(ocr_pages, template_doc.form_name or template_doc.name, template_fields, table_hints=table_hints)

			raw_values = draft.get("field_values") or draft.get("values") or []
			values = normalize_autofill_values(template_fields, raw_values)
			warnings = _dedupe_strings([str(item).strip() for item in (draft.get("warnings") or []) if str(item).strip()])
			result = {
				"job_id": resolved_job_id,
				"template_name": template_doc.name,
				"template_label": template_doc.form_name or template_doc.name,
				"file_name": file_doc.file_name,
				"page_count": len(pages),
				"values": values,
				"warnings": warnings,
				"unmapped_fields": [
					field.get("fieldname")
					for field in template_fields
					if field.get("fieldname") and field.get("fieldname") not in values
				],
			}

			progress.complete(result)
			return result
		except AiFormBuilderError as exc:
			progress.fail(str(exc), stage="failed")
			raise
		except Exception as exc:
			message = _("AI autofill failed: {0}").format(str(exc))
			progress.fail(message, stage="failed")
			raise AiFormBuilderProcessingError(message) from exc
		finally:
			if restore_user:
				try:
					frappe.set_user(previous_user or "Administrator")
				except Exception:
					pass

	def _load_file_doc(self, file_docname: str):
		if not file_docname:
			raise AiFormBuilderValidationError(_("File is required."))

		file_doc = frappe.get_doc("File", file_docname)
		file_doc.check_permission("read")

		if not file_doc.file_name:
			raise AiFormBuilderValidationError(_("Uploaded file is missing a filename."))

		return file_doc

	def _load_template_doc(self, template_name: str):
		if not template_name:
			raise AiFormBuilderValidationError(_("Form template is required."))

		template_doc = frappe.get_doc(TEMPLATE_DOCTYPE, template_name)
		template_doc.check_permission("read")
		return template_doc

	def _validate_template(self, template_doc) -> None:
		form_type = _normalize_text(getattr(template_doc, "form_type", "") or "")
		if form_type and form_type not in {"Form", "Doctype Integration"}:
			raise AiFormBuilderValidationError(_("Unsupported form type for autofill."))


def _dedupe_strings(items: list[str]) -> list[str]:
	seen: set[str] = set()
	result: list[str] = []
	for item in items:
		if item and item not in seen:
			seen.add(item)
			result.append(item)
	return result


def queue_ai_form_autofill(file_docname: str, template_name: str) -> dict[str, Any]:
	return AiFormAutofillService().enqueue_autofill(file_docname, template_name)


def get_ai_form_autofill_status(job_id: str) -> dict[str, Any]:
	return AiFormAutofillService().get_status(job_id)


def process_ai_form_autofill(file_docname: str, template_name: str, owner: str, job_id: str | None = None) -> dict[str, Any]:
	return AiFormAutofillService().process_autofill(
		file_docname=file_docname,
		template_name=template_name,
		owner=owner,
		job_id=job_id,
	)
