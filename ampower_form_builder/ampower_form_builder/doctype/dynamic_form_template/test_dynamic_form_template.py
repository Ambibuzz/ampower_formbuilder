# Copyright (c) 2026, Ambibuzz Technologies LLP and Contributors
# See license.txt

from __future__ import annotations

import json

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from ampower_form_builder.api import save_form_template, save_submission
from ampower_form_builder.services.template_versioning import DEFAULT_FORM_VERSION_LABEL

TEMPLATE_DOCTYPE = "Dynamic Form Template"
SUBMISSION_DOCTYPE = "Dynamic Form Submission"


class UnitTestDynamicFormTemplate(UnitTestCase):
	pass


class IntegrationTestDynamicFormTemplate(IntegrationTestCase):
	def setUp(self):
		self.created_templates = []
		self.created_submissions = []

	def tearDown(self):
		for submission_name in reversed(self.created_submissions):
			if frappe.db.exists(SUBMISSION_DOCTYPE, submission_name):
				frappe.delete_doc(SUBMISSION_DOCTYPE, submission_name, force=True, ignore_permissions=True)

		for template_name in reversed(self.created_templates):
			if frappe.db.exists(TEMPLATE_DOCTYPE, template_name):
				frappe.delete_doc(TEMPLATE_DOCTYPE, template_name, force=True, ignore_permissions=True)

	def test_new_template_gets_default_version_metadata(self):
		template = self._create_template()

		self.assertEqual(template.base_form_name, template.form_name)
		self.assertEqual(template.version_label, DEFAULT_FORM_VERSION_LABEL)
		self.assertTrue(template.version_group)
		self.assertEqual(template.is_latest_version, 1)

	def test_new_version_creates_separate_template_and_updates_latest_flag(self):
		base_template = self._create_template()

		version_payload = save_form_template(
			form_name=f"{base_template.form_name} v1.1",
			schema_json=self._build_schema(fieldname="customer_email", label="Customer Email"),
			description="Second version",
			base_form_name=base_template.base_form_name,
			version_label="1.1",
			version_group=base_template.version_group,
			source_template=base_template.name,
		)
		self.created_templates.append(version_payload["name"])

		base_template.reload()
		version_template = frappe.get_doc(TEMPLATE_DOCTYPE, version_payload["name"])

		self.assertNotEqual(version_template.name, base_template.name)
		self.assertEqual(version_template.source_template, base_template.name)
		self.assertEqual(version_template.version_group, base_template.version_group)
		self.assertEqual(version_template.version_label, "1.1")
		self.assertEqual(base_template.is_latest_version, 0)
		self.assertEqual(version_template.is_latest_version, 1)

	def test_existing_version_with_submissions_cannot_change_schema(self):
		template = self._create_template()
		submission = save_submission(
			form_template=template.name,
			data=json.dumps({"customer_name": "Alice"}),
			status="Submitted",
		)
		self.created_submissions.append(submission["name"])

		template.reload()
		template.schema_json = json.dumps(self._build_schema(fieldname="customer_email", label="Customer Email"))

		with self.assertRaises(frappe.ValidationError):
			template.save()

	def _create_template(self, form_name: str | None = None):
		next_form_name = form_name or f"Test Form {frappe.generate_hash(length=6)}"
		payload = save_form_template(
			form_name=next_form_name,
			schema_json=self._build_schema(form_name=next_form_name),
			description="Test template",
		)
		self.created_templates.append(payload["name"])
		return frappe.get_doc(TEMPLATE_DOCTYPE, payload["name"])

	@staticmethod
	def _build_schema(form_name: str = "Test Form", fieldname: str = "customer_name", label: str = "Customer Name"):
		return {
			"version": 1,
			"form_name": form_name,
			"description": "Test schema",
			"fields": [
				{
					"fieldname": fieldname,
					"label": label,
					"fieldtype": "Data",
					"reqd": 1,
				}
			],
			"sections": [],
		}
