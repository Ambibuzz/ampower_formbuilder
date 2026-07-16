from __future__ import annotations

import os
import tempfile

import frappe
import pdfkit
from bs4 import BeautifulSoup

from frappe.utils.pdf import cleanup, get_cookie_options, inline_private_images, scrub_urls

from .services.print_format_service import DynamicPrintFormatService


@frappe.whitelist()
def list_print_formats(dynamic_form_template):
	service = DynamicPrintFormatService(template_name=dynamic_form_template)
	return service.list_for_template()


@frappe.whitelist()
def get_print_format(format_name):
	service = DynamicPrintFormatService()
	return service.get(format_name)


@frappe.whitelist()
def save_print_format(**payload):
	service = DynamicPrintFormatService()
	return service.save(payload)


@frappe.whitelist()
def get_print_render_context(format_name, submission_name):
	service = DynamicPrintFormatService()
	return service.get_render_context(format_name, submission_name)


def _pixel_value(value, fallback=0):
	try:
		text = str(value or "").strip().lower()
		if text.endswith("px"):
			text = text[:-2]
		return max(float(text), 0)
	except Exception:
		return float(fallback)


def _px_to_option(value):
	return f"{max(int(round(value)), 0)}px"


def _extract_repeatable_blocks(html):
	soup = BeautifulSoup(html or "", "lxml")
	style_html = "".join(str(style) for style in soup.find_all("style"))
	content_root = soup.select_one(".pb-report-content") or soup.body or soup

	header_nodes = list(content_root.select("#header-html, .header-html, .letter-head"))
	footer_nodes = list(content_root.select("#footer-html, .footer-html"))

	for node in header_nodes + footer_nodes:
		node.extract()

	for node in list(content_root.select(".pb-report-spacer")):
		prev_node = node.find_previous_sibling()
		next_node = node.find_next_sibling()
		if prev_node is None or next_node is None:
			node.extract()

	body_html = str(soup)
	spacer = '<div class="pb-report-spacer" aria-hidden="true"></div>'
	header_html = spacer.join(str(node) for node in header_nodes)
	footer_html = spacer.join(str(node) for node in footer_nodes)
	return body_html, header_html, footer_html, style_html


def _build_fragment_document(fragment_html, style_html="", page_padding="10px"):
	return f"""<!doctype html>
<html>
<head>
	<meta charset="utf-8">
	{style_html}
	<style>
		html, body {{
			margin: 0;
			background: #fff;
			box-sizing: border-box;
			width: 100%;
			max-width: 100%;
		}}
		.print-format {{
			width: 100%;
			max-width: 100%;
			box-sizing: border-box;
			margin: 0;
			padding: 0;
		}}
		.pb-report-page {{
			position: relative;
			width: 100%;
			box-sizing: border-box;
			background: #fff;
			overflow: hidden;
			padding: {page_padding};
		}}
		.pb-report-content {{
			position: static;
			display: flex;
			flex-direction: column;
			gap: 0;
			width: 100%;
			height: auto;
			box-sizing: border-box;
		}}
		.pb-report-block,
		.pb-report-item,
		.pb-report-table-item,
		.pb-report-matrix {{
			position: static;
			width: 100%;
			box-sizing: border-box;
			margin: 0;
		}}
		#header-html,
		#footer-html,
		.header-html,
		.letter-head,
		.footer-html {{
			width: 100% !important;
			max-width: 100% !important;
			box-sizing: border-box;
		}}
		.pb-report-spacer {{
			height: 5px;
		}}
	</style>
</head>
<body>
	<div class="print-format">
		<div class="pb-report-page">
			<div class="pb-report-content">{fragment_html}</div>
		</div>
	</div>
</body>
</html>"""


@frappe.whitelist()
def download_report_pdf(
	html,
	page_width="210mm",
	page_height="297mm",
	margin_top="0mm",
	margin_right="0mm",
	margin_bottom="0mm",
	margin_left="0mm",
	orientation="Portrait",
	header_height_px="0",
	footer_height_px="0",
):
	html = inline_private_images(scrub_urls(html))
	body_html, header_html, footer_html, style_html = _extract_repeatable_blocks(html)

	header_temp = None
	footer_temp = None
	options = {
		"disable-javascript": "",
		"disable-local-file-access": "",
		"encoding": "UTF-8",
		"load-error-handling": "ignore",
		"load-media-error-handling": "ignore",
		"quiet": "",
		"page-width": page_width,
		"page-height": page_height,
		"margin-top": _px_to_option(_pixel_value(margin_top, 0) + _pixel_value(header_height_px, 0) + 10),
		"margin-right": margin_right,
		"margin-bottom": _px_to_option(_pixel_value(margin_bottom, 0) + _pixel_value(footer_height_px, 0) + 10),
		"margin-left": margin_left,
		"orientation": orientation or "Portrait",
	}

	if header_html.strip():
		header_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
		header_temp.write(_build_fragment_document(header_html, style_html).encode("utf-8"))
		header_temp.flush()
		header_temp.close()
		options["header-html"] = header_temp.name
		options["header-spacing"] = "0"

	if footer_html.strip():
		footer_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
		footer_temp.write(_build_fragment_document(footer_html, style_html).encode("utf-8"))
		footer_temp.flush()
		footer_temp.close()
		options["footer-html"] = footer_temp.name
		options["footer-spacing"] = "0"

	options.update(get_cookie_options())

	try:
		pdf_file = pdfkit.from_string(body_html, options=options, verbose=True)
	finally:
		cleanup(options)
		for temp_file in (header_temp, footer_temp):
			if temp_file and os.path.exists(temp_file.name):
				os.unlink(temp_file.name)

	frappe.local.response.filename = "report.pdf"
	frappe.local.response.filecontent = pdf_file
	frappe.local.response.type = "pdf"
