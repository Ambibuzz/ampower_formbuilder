# Copyright (c) 2026, Ambibuzz Technologies LLP and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document
from frappe.utils import cint, now_datetime


class DynamicFormSubmission(Document):
    """Stores filled-form data as JSON against a Dynamic Form Template.

    Validates submitted data against the template's schema to ensure
    required fields are present and data types are compatible.
    """

    def validate(self):
        """Run all validations before saving."""
        self._validate_data_json()
        self._validate_reference_link()
        self._validate_against_schema()

    def before_insert(self):
        """Auto-set the submission timestamp on first save."""
        if not self.submitted_on:
            self.submitted_on = now_datetime()

    # ── Data validation ────────────────────────────────────────────

    def _validate_data_json(self):
        """Ensure data_json is valid JSON and a dict."""
        try:
            data = json.loads(self.data_json) if isinstance(self.data_json, str) else self.data_json
        except (json.JSONDecodeError, TypeError) as exc:
            frappe.throw(
                frappe._("Invalid JSON in submission data: {0}").format(str(exc)),
                title=frappe._("Data Error"),
            )

        if not isinstance(data, dict):
            frappe.throw(
                frappe._("Submission data must be a JSON object."),
                title=frappe._("Data Error"),
            )

    def _validate_against_schema(self):
        """Check submitted data against the linked template's schema.

        - Ensures all required fields are present and non-empty.
        - Supports both flat and nested section schemas.
        - Skips layout-only fields.
        """
        template = frappe.get_doc("Dynamic Form Template", self.form_template)
        schema = json.loads(template.schema_json)
        data = json.loads(self.data_json) if isinstance(self.data_json, str) else self.data_json

        layout_types = {"Section Break", "Tab Break", "Column Break", "HTML", "Heading"}

        for field_def in self._iter_schema_fields(schema):
            fieldtype = field_def.get("fieldtype", "")
            if fieldtype in layout_types:
                continue

            fieldname = field_def.get("fieldname", "")
            is_required = field_def.get("reqd") or field_def.get("required")

            if is_required and self._is_missing_required_value(data.get(fieldname), fieldtype):
                frappe.throw(
                    frappe._("Required field '{0}' is missing or empty.").format(
                        field_def.get("label", fieldname)
                    ),
                    title=frappe._("Validation Error"),
                )

    def _validate_reference_link(self):
        """Keep parent references consistent when present."""
        reference_doctype = (self.reference_doctype or "").strip()
        reference_name = (self.reference_name or "").strip()

        if bool(reference_doctype) ^ bool(reference_name):
            frappe.throw(
                frappe._("Parent DocType and Parent Document must be provided together."),
                title=frappe._("Validation Error"),
            )

    @staticmethod
    def _iter_schema_fields(schema):
        fields = schema.get("fields", [])
        if isinstance(fields, list) and fields:
            for field in fields:
                yield field or {}
            return

        for section in schema.get("sections", []) or []:
            section = dict(section or {})
            yield {
                "fieldtype": section.get("item_type") or section.get("type") or "Section Break",
                "fieldname": section.get("section_key") or section.get("id"),
                "label": section.get("section_label") or section.get("label"),
            }
            for column in section.get("columns", []) or []:
                for field in column.get("items", []) or []:
                    yield field or {}

    @staticmethod
    def _is_missing_required_value(value, fieldtype):
        if fieldtype == "Check":
            return not cint(value)
        if value is None:
            return True
        if isinstance(value, str):
            return not value.strip()
        if isinstance(value, (list, tuple, set)):
            return len(value) == 0
        if isinstance(value, dict):
            return len(value) == 0
        return False
