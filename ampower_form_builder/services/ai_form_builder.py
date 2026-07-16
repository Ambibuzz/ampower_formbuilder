"""AI-assisted form builder import pipeline.

This module keeps the AI workflow isolated from the rest of the builder:
- upload file validation
- Google Vision OCR
- OpenAI structured output generation
- background job status tracking
- schema normalization
"""

from __future__ import annotations

import base64
import json
import re
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import frappe
import requests
from rq import get_current_job
from frappe import _
from frappe.realtime import publish_progress
from frappe.utils.background_jobs import enqueue, get_job_status


AI_IMPORT_MODEL = "gpt-5-mini"
AI_IMPORT_MAX_PAGES = 5
AI_IMPORT_STATUS_TTL = 7 * 24 * 60 * 60
AI_IMPORT_REASONING_EFFORT = "minimal"
AI_IMPORT_MAX_COMPLETION_TOKENS = 12000
DEFAULT_AI_IMPORT_SYSTEM_PROMPT = (
	"You are an expert Frappe/ERPNext form analyst. "
	"Convert OCR text from scanned forms and report-style documents into a builder-ready draft. "
	"Use only the supported field types from the schema. "
	"Prefer conservative guesses over hallucinations. "
	"Use only headings, keys, and column labels from the OCR to build the schema. "
	"Ignore the data values when deciding labels or field names. "
	"If a field is not obvious, use Data rather than inventing unsupported structure. "
	"Detect tabs or sections only when the layout strongly suggests them. "
	"Treat key/value detail blocks under a heading as ordinary form fields. "
	"Treat repeated row grids or columnar report blocks as Table or Mixed Table fields. "
	"Do not flatten a detected table into standalone fields. "
	"If the OCR shows a report-like layout, keep root-level fields separate from table regions. "
	"Always return valid structured JSON that matches the schema."
)
DEFAULT_OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
DEFAULT_GOOGLE_VISION_URL = "https://vision.googleapis.com/v1/images:annotate"
DEFAULT_VISION_SCOPE = "https://www.googleapis.com/auth/cloud-vision"
VISION_DOCUMENT_FEATURE = "DOCUMENT_TEXT_DETECTION"
OPENAI_TIMEOUT_SECONDS = 600
GOOGLE_TIMEOUT_SECONDS = 120

SUPPORTED_FIELD_TYPES = (
    "Data",
    "Small Text",
    "Long Text",
    "Text Editor",
    "Color",
    "Attach",
    "Attach Image",
    "Check",
    "Number",
    "Date",
    "Datetime",
    "Time",
    "Select",
    "Radio",
    "Link",
    "Dynamic Link",
    "Table",
    "Mixed Table",
)

SUPPORTED_TABLE_COLUMN_FIELD_TYPES = (
    "Data",
    "Small Text",
    "Text",
    "Color",
    "Number",
    "Percent",
    "Select",
    "Link",
    "Date",
    "Datetime",
    "Time",
    "Check",
)

SQL_KEYWORDS = {
    "select",
    "insert",
    "update",
    "delete",
    "drop",
    "table",
    "from",
    "where",
    "join",
    "group",
    "order",
    "limit",
    "by",
    "and",
    "or",
    "into",
    "create",
    "alter",
    "index",
    "primary",
    "key",
    "constraint",
    "grant",
    "revoke",
    "union",
    "having",
    "distinct",
}


class AiFormBuilderError(Exception):
    """Base exception for the AI import pipeline."""


class AiFormBuilderConfigurationError(AiFormBuilderError):
    """Raised when the form builder config is incomplete or invalid."""


class AiFormBuilderValidationError(AiFormBuilderError):
    """Raised when the uploaded asset is not supported."""


class AiFormBuilderProcessingError(AiFormBuilderError):
    """Raised when OCR or model inference fails."""


@dataclass(slots=True)
class AiImportConfig:
	openai_api_key: str
	openai_api_url: str
	google_service_account: dict[str, Any]
	form_builder_system_prompt: str = ""
	google_token_url: str = DEFAULT_GOOGLE_TOKEN_URL
	google_vision_url: str = DEFAULT_GOOGLE_VISION_URL
	model: str = AI_IMPORT_MODEL


@dataclass(slots=True)
class RenderedPage:
    page_number: int
    content: bytes
    mime_type: str
    file_name: str


@dataclass(slots=True)
class OcrPage:
    page_number: int
    text: str


@dataclass(slots=True)
class TableHint:
    page_number: int
    title: str
    kind: str
    columns: list[str]
    rows: list[list[str]]
    evidence: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_number": self.page_number,
            "title": self.title,
            "kind": self.kind,
            "columns": list(self.columns),
            "rows": [list(row) for row in self.rows],
            "evidence": list(self.evidence),
        }

    def to_prompt_lines(self) -> list[str]:
        lines = [f"- Page {self.page_number}: {self.title} ({self.kind})"]
        if self.kind == "detail_block":
            lines.append("  Type: key-value detail block")
            keys = [row[0] for row in self.rows[:5] if row and row[0]]
            if keys:
                lines.append(f"  Keys: {' | '.join(keys)}")
            if len(self.rows) > 5:
                lines.append("  Keys: ...")
        else:
            lines.append(f"  Columns: {' | '.join(self.columns) if self.columns else '[none]'}")
            lines.append(f"  Row count: {len(self.rows)}")
        if self.evidence:
            lines.append("  Evidence:")
            for item in self.evidence[:4]:
                clean_item = _normalize_ocr_line(item)
                if len(clean_item) > 140:
                    clean_item = clean_item[:137].rstrip() + "..."
                lines.append(f"    - {clean_item}")
        return lines


class OcrTableDetector:
    """Detect table-like blocks in OCR text so they are preserved in the draft."""

    def __init__(self, max_block_lines: int = 40) -> None:
        self.max_block_lines = max_block_lines

    def detect(self, pages: list[OcrPage]) -> list[TableHint]:
        hints: list[TableHint] = []
        for page in pages:
            hints.extend(self._detect_page(page))
        return hints

    def _detect_page(self, page: OcrPage) -> list[TableHint]:
        lines = self._normalize_lines(page.text)
        if not lines:
            return []

        hints: list[TableHint] = []
        index = 0
        while index < len(lines):
            line = lines[index]
            if not self._is_heading_candidate(line):
                index += 1
                continue

            block_lines, next_index = self._collect_block(lines, index + 1)
            hint = self._build_hint(page.page_number, line, block_lines)
            if hint:
                hints.append(hint)
            index = max(next_index, index + 1)

        return hints

    def _build_hint(self, page_number: int, title: str, block_lines: list[str]) -> TableHint | None:
        key_value_rows: list[list[str]] = []
        grid_rows: list[list[str]] = []

        for line in block_lines:
            key_value = self._split_key_value_line(line)
            if key_value:
                key_value_rows.append(key_value)
                continue

            grid_cells = self._split_grid_cells(line)
            if grid_cells:
                grid_rows.append(grid_cells)

        if len(key_value_rows) >= 2 and len(key_value_rows) >= len(grid_rows):
            evidence = []
            for row in key_value_rows[:6]:
                if not row or not row[0]:
                    continue
                if len(row) > 1:
                    evidence.append(f"{row[0]}: {row[1]}")
                else:
                    evidence.append(row[0])
            return TableHint(
                page_number=page_number,
                title=title,
                kind="detail_block",
                columns=[],
                rows=[[row[0]] for row in key_value_rows if row and row[0]],
                evidence=evidence,
            )

        if len(grid_rows) >= 3 and self._looks_like_consistent_grid(grid_rows):
            header_index = self._pick_grid_header_index(grid_rows)
            header = self._clean_cells(grid_rows[header_index])
            rows = [self._clean_cells(row) for row_index, row in enumerate(grid_rows) if row_index != header_index]
            rows = [row for row in rows if row]
            if len(header) >= 2 and len(rows) >= 2:
                evidence = []
                if title:
                    evidence.append(title)
                if header:
                    evidence.append(f"Header: {' | '.join(header[:10])}")
                for row in rows[:3]:
                    if row:
                        evidence.append(f"Row: {' | '.join(row[:10])}")
                return TableHint(
                    page_number=page_number,
                    title=title,
                    kind="child_table",
                    columns=header,
                    rows=rows,
                    evidence=evidence,
                )

        return None

    def _collect_block(self, lines: list[str], start_index: int) -> tuple[list[str], int]:
        block_lines: list[str] = []
        index = start_index
        while index < len(lines):
            line = lines[index]
            if self._is_heading_candidate(line):
                break
            if line:
                block_lines.append(line)
            index += 1
            if len(block_lines) >= self.max_block_lines:
                break
        return block_lines, index

    def _normalize_lines(self, text: str) -> list[str]:
        lines: list[str] = []
        for line in str(text or "").splitlines():
            normalized = _normalize_ocr_line(line)
            if normalized:
                lines.append(normalized)
        return lines

    def _is_heading_candidate(self, line: str) -> bool:
        text = _normalize_ocr_line(line)
        if not text or len(text) > 90:
            return False
        if ":" in text or "|" in text or "\t" in text or "/" in text:
            return False

        words = [word for word in text.split() if word]
        if len(words) < 2 or len(words) > 10:
            return False

        alpha_chars = [char for char in text if char.isalpha()]
        if len(alpha_chars) < 4:
            return False

        if text.isupper():
            return True

        if len(words) < 4:
            return False

        upper_ratio = sum(1 for char in alpha_chars if char.isupper()) / len(alpha_chars)
        title_ratio = sum(
            1
            for word in words
            if word[:1].isupper() and (len(word) == 1 or word[1:].islower())
        ) / len(words)
        return upper_ratio >= 0.7 or title_ratio >= 0.8

    def _split_key_value_line(self, line: str) -> list[str]:
        text = _normalize_ocr_line(line)
        if not text:
            return []
        if "|" in text or "\t" in text:
            return []

        if ":" in text:
            left, right = text.split(":", 1)
            left = _normalize_ocr_line(left)
            right = _normalize_ocr_line(right)
            if left and right:
                return [left, right]

        if re.search(r"\s{2,}", text):
            cells = self._clean_cells(re.split(r"\s{2,}", text))
            if len(cells) == 2 and self._looks_like_label_value_pair(cells[0], cells[1]):
                return cells

        implicit = self._split_implicit_key_value_line(text)
        if implicit:
            return implicit

        return []

    def _split_implicit_key_value_line(self, text: str) -> list[str]:
        words = [word for word in _normalize_ocr_line(text).split() if word]
        if len(words) < 2 or len(words) > 8:
            return []

        stopwords = {
            "a",
            "an",
            "and",
            "as",
            "at",
            "by",
            "for",
            "from",
            "if",
            "in",
            "is",
            "it",
            "of",
            "on",
            "or",
            "the",
            "to",
            "up",
            "via",
            "with",
        }

        best_candidate: list[str] = []
        best_score = float("-inf")
        for split_index in range(1, min(4, len(words))):
            left = " ".join(words[:split_index]).strip()
            right = " ".join(words[split_index:]).strip()
            if not left or not right:
                continue
            if len(right.split()) > 6 or len(right) > 80:
                continue
            if not self._looks_like_implicit_label(left, stopwords):
                continue
            if self._looks_like_label_value_pair(left, right):
                score = self._score_implicit_key_value_candidate(left, right)
                if score > best_score:
                    best_score = score
                    best_candidate = [left, right]

        return best_candidate

    def _score_implicit_key_value_candidate(self, left: str, right: str) -> float:
        left_words = [word for word in _normalize_ocr_line(left).split() if word]
        right_words = [word for word in _normalize_ocr_line(right).split() if word]
        left_text = _normalize_ocr_line(left)
        right_text = _normalize_ocr_line(right)
        left_title_ratio = self._titlecase_ratio(left_words)
        right_title_ratio = self._titlecase_ratio(right_words)
        left_alpha_ratio = self._alpha_ratio(left_text)
        right_alpha_ratio = self._alpha_ratio(right_text)
        right_has_value_markers = bool(
            re.search(r"\d", right_text)
            or re.search(r"[%/\\\-]", right_text)
            or re.search(r"\b(?:N/?A|NA|YES|NO|Y|N)\b", right_text, re.I)
            or re.search(r"[A-Z]{2,}\d+[A-Z0-9]*", right_text)
        )

        score = 0.0
        score += max(0.0, 2.0 - (len(left_words) * 0.2))
        score += max(0.0, 1.8 - (len(right_words) * 0.15))
        if len(left_words) == 1:
            score += 0.6
        elif len(left_words) == 2:
            score += 0.9
        elif len(left_words) == 3:
            score += 0.7

        if len(right_words) <= 2:
            score += 0.8
        elif len(right_words) <= 4:
            score += 0.5

        if left.isupper():
            score += 0.7
        elif left_title_ratio >= 0.8:
            score += 0.5
        elif left_title_ratio >= 0.6:
            score += 0.2

        if right.isupper():
            score += 0.4
        elif right_title_ratio >= 0.8:
            score += 0.2

        if right_has_value_markers:
            score += 1.2

        if len(left_text) > 40:
            score -= 0.8
        if len(right_text) > 80:
            score -= 0.6
        if len(left_words) > len(right_words) + 1:
            score -= 0.5
        if left_alpha_ratio < 0.5 or right_alpha_ratio < 0.5:
            score -= 0.25
        if left_text.endswith((".", "!", "?")) or right_text.endswith((".", "!", "?")):
            score -= 0.5

        return score

    def _looks_like_implicit_label(
        self,
        left: str,
        stopwords: set[str],
    ) -> bool:
        words = [word for word in _normalize_ocr_line(left).split() if word]
        if not words or len(words) > 4:
            return False

        normalized_first_word = re.sub(r"[^a-z0-9]+", "", words[0].lower())
        if normalized_first_word in stopwords:
            return False

        if len(words) == 1:
            normalized_word = re.sub(r"[^a-z0-9]+", "", left.lower())
            if left.isupper() and len(normalized_word) <= 4:
                return True
            return left[:1].isupper() and len(normalized_word) <= 12

        if left.isupper():
            return True

        alpha_chars = [char for char in left if char.isalpha()]
        if len(alpha_chars) < 3:
            return False

        connector_words = {"of", "and", "for", "to", "from", "with", "by", "in", "on", "before", "after"}
        upper_ratio = sum(1 for char in alpha_chars if char.isupper()) / len(alpha_chars)
        title_ratio = sum(
            1
            for word in words
            if word[:1].isupper() and (len(word) == 1 or word[1:].islower())
        ) / len(words)
        if upper_ratio >= 0.7 or title_ratio >= 0.8:
            return True

        if len(words) == 3:
            middle_words = {re.sub(r"[^a-z0-9]+", "", word.lower()) for word in words[1:-1]}
            if middle_words & connector_words and title_ratio >= 0.65:
                return True

        return False

    def _alpha_ratio(self, text: str) -> float:
        if not text:
            return 0.0
        alpha_count = sum(1 for char in text if char.isalpha())
        return alpha_count / len(text)

    def _titlecase_ratio(self, words: list[str]) -> float:
        if not words:
            return 0.0
        return sum(
            1
            for word in words
            if word[:1].isupper() and (len(word) == 1 or word[1:].islower())
        ) / len(words)

    def _split_grid_cells(self, line: str) -> list[str]:
        text = _normalize_ocr_line(line)
        if not text:
            return []

        separators = None
        if "|" in text:
            separators = r"\s*\|\s*"
        elif "\t" in text:
            separators = r"\t+"
        elif re.search(r"\s{2,}", text):
            separators = r"\s{2,}"

        if not separators:
            return []

        cells = self._clean_cells(re.split(separators, text))
        return cells if len(cells) >= 2 else []

    def _clean_cells(self, cells: list[str]) -> list[str]:
        return [
            _normalize_ocr_line(cell)
            for cell in cells
            if _normalize_ocr_line(cell)
        ]

    def _looks_like_label_value_pair(self, left: str, right: str) -> bool:
        if not left or not right:
            return False
        if len(left) > 60 or len(right) > 160:
            return False
        if len(left.split()) > 8:
            return False
        return True

    def _looks_like_consistent_grid(self, rows: list[list[str]]) -> bool:
        counts: dict[int, int] = {}
        for row in rows:
            counts[len(row)] = counts.get(len(row), 0) + 1
        if not counts:
            return False
        cell_count, frequency = max(counts.items(), key=lambda item: item[1])
        return cell_count >= 2 and frequency >= 2

    def _pick_grid_header_index(self, rows: list[list[str]]) -> int:
        best_index = 0
        best_score = float("-inf")
        for index, row in enumerate(rows[:3]):
            score = self._row_text_score(row) - (index * 0.05)
            if score > best_score:
                best_score = score
                best_index = index
        return best_index

    def _row_text_score(self, row: list[str]) -> float:
        if not row:
            return 0.0

        score = 0.0
        for cell in row:
            letters = sum(1 for char in cell if char.isalpha())
            digits = sum(1 for char in cell if char.isdigit())
            if letters >= digits:
                score += 1.0
            if len(cell.split()) <= 4:
                score += 0.25
        return score / len(row)


@dataclass(slots=True)
class ProgressReporter:
    job_id: str
    owner: str
    progress_store: "AiImportStatusStore"

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
        self.progress_store.update(self.job_id, payload)
        publish_progress(payload["progress"], title=_("Ampower AI Import"), description=message, task_id=self.job_id)

    def complete(self, result: dict[str, Any]) -> None:
        payload = {
            "job_id": self.job_id,
            "owner": self.owner,
            "status": "completed",
            "stage": "complete",
            "message": _("AI draft generated successfully."),
            "progress": 100,
            "result": result,
            "error": "",
            "updated_at": _utc_now_iso(),
        }
        self.progress_store.update(self.job_id, payload)
        publish_progress(100, title=_("Ampower AI Import"), description=payload["message"], task_id=self.job_id)

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
        self.progress_store.update(self.job_id, payload)
        publish_progress(100, title=_("Ampower AI Import"), description=message, task_id=self.job_id)


class AiImportStatusStore:
    """Stores the latest import state in Redis so the UI can poll it."""

    def __init__(self, prefix: str = "ampower_form_builder:ai_import") -> None:
        self.prefix = prefix

    def key(self, job_id: str) -> str:
        return f"{self.prefix}:{job_id}"

    def create(self, job_id: str, owner: str, file_docname: str, file_name: str) -> dict[str, Any]:
        payload = {
            "job_id": job_id,
            "owner": owner,
            "file_docname": file_docname,
            "file_name": file_name,
            "status": "queued",
            "stage": "queued",
            "message": _("Queued for AI processing."),
            "progress": 0,
            "result": None,
            "error": "",
            "updated_at": _utc_now_iso(),
        }
        frappe.cache.set_value(self.key(job_id), payload, expires_in_sec=AI_IMPORT_STATUS_TTL)
        return payload

    def update(self, job_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        current = self.get(job_id) or {"job_id": job_id}
        current.update(patch)
        current.setdefault("updated_at", _utc_now_iso())
        frappe.cache.set_value(self.key(job_id), current, expires_in_sec=AI_IMPORT_STATUS_TTL)
        return current

    def get(self, job_id: str) -> dict[str, Any] | None:
        return frappe.cache.get_value(self.key(job_id))


class AiImportArtifactStore:
    """Stores intermediate OCR artifacts between background jobs."""

    def __init__(self, prefix: str = "ampower_form_builder:ai_import_artifact") -> None:
        self.prefix = prefix

    def key(self, job_id: str) -> str:
        return f"{self.prefix}:{job_id}"

    def create(self, job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        frappe.cache.set_value(self.key(job_id), payload, expires_in_sec=AI_IMPORT_STATUS_TTL)
        return payload

    def get(self, job_id: str) -> dict[str, Any] | None:
        return frappe.cache.get_value(self.key(job_id))

    def delete(self, job_id: str) -> None:
        frappe.cache.delete_value(self.key(job_id))


class FormBuilderConfigRepository:
    """Read and validate the single Form Builder Config document."""

    def load(self) -> AiImportConfig:
        doc = frappe.get_single("Form Builder Config")

        openai_api_key = (doc.get_password("openai_api_key", raise_exception=False) or "").strip()
        openai_api_url = (getattr(doc, "openai_api_url", "") or DEFAULT_OPENAI_API_URL).strip()
        form_builder_system_prompt = (
            getattr(doc, "form_builder_system_prompt", "")
            or ""
        ).strip()
        google_service_account_raw = (getattr(doc, "google_service_account_json", "") or "").strip()

        if not openai_api_key:
            raise AiFormBuilderConfigurationError(_("OpenAI API key is missing in Form Builder Config."))
        if not openai_api_url:
            raise AiFormBuilderConfigurationError(_("OpenAI API URL is missing in Form Builder Config."))
        if not google_service_account_raw:
            raise AiFormBuilderConfigurationError(_("Google service account JSON is missing in Form Builder Config."))

        try:
            google_service_account = json.loads(google_service_account_raw)
        except json.JSONDecodeError as exc:
            raise AiFormBuilderConfigurationError(
                _("Google service account JSON is invalid: {0}").format(str(exc))
            ) from exc

        if not isinstance(google_service_account, dict):
            raise AiFormBuilderConfigurationError(_("Google service account JSON must be a JSON object."))

        for key in ("client_email", "private_key"):
            if not google_service_account.get(key):
                raise AiFormBuilderConfigurationError(
                    _("Google service account JSON is missing required field '{0}'.").format(key)
                )

        return AiImportConfig(
            openai_api_key=openai_api_key,
            openai_api_url=openai_api_url,
            form_builder_system_prompt=form_builder_system_prompt,
            google_service_account=google_service_account,
            google_token_url=str(google_service_account.get("token_uri") or DEFAULT_GOOGLE_TOKEN_URL),
        )


class PdfPageRasterizer:
    """Render PDFs to page images and normalize image uploads."""

    def __init__(self, max_pages: int = AI_IMPORT_MAX_PAGES, dpi: int = 180) -> None:
        self.max_pages = max_pages
        self.dpi = dpi

    def render(self, file_doc) -> list[RenderedPage]:
        content = file_doc.get_content()
        if isinstance(content, str):
            content = content.encode()

        if self._looks_like_pdf(file_doc, content):
            return self._render_pdf(file_doc, content)

        if self._looks_like_image(file_doc):
            return [RenderedPage(page_number=1, content=content, mime_type=self._guess_mime(file_doc), file_name=file_doc.file_name)]

        raise AiFormBuilderValidationError(
            _("Only PDF and image files are supported for AI form import.")
        )

    def _render_pdf(self, file_doc, content: bytes) -> list[RenderedPage]:
        try:
            import fitz
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise AiFormBuilderProcessingError(
                _("PyMuPDF is required to render PDF pages for AI form import.")
            ) from exc

        try:
            pdf = fitz.open(stream=content, filetype="pdf")
        except Exception as exc:
            raise AiFormBuilderValidationError(
                _("The uploaded file could not be opened as a PDF.")
            ) from exc

        try:
            page_count = pdf.page_count
            if page_count > self.max_pages:
                raise AiFormBuilderValidationError(
                    _("PDF contains {0} pages. The current limit is {1} pages.").format(page_count, self.max_pages)
                )

            rendered_pages: list[RenderedPage] = []
            zoom = self.dpi / 72.0
            matrix = fitz.Matrix(zoom, zoom)
            for page_index in range(page_count):
                page = pdf.load_page(page_index)
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                rendered_pages.append(
                    RenderedPage(
                        page_number=page_index + 1,
                        content=pixmap.tobytes("png"),
                        mime_type="image/png",
                        file_name=f"{self._stem(file_doc.file_name)}_page_{page_index + 1}.png",
                    )
                )
            return rendered_pages
        finally:
            pdf.close()

    def _looks_like_pdf(self, file_doc, content: bytes) -> bool:
        file_name = (file_doc.file_name or "").lower()
        file_type = (getattr(file_doc, "file_type", "") or "").lower()
        return content.startswith(b"%PDF") or file_name.endswith(".pdf") or file_type == "pdf"

    def _looks_like_image(self, file_doc) -> bool:
        file_name = (file_doc.file_name or "").lower()
        file_type = (getattr(file_doc, "file_type", "") or "").lower()
        image_extensions = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff")
        image_types = {"png", "jpg", "jpeg", "webp", "gif", "bmp", "tif", "tiff"}
        return file_name.endswith(image_extensions) or file_type in image_types or file_type.startswith("image/")

    def _guess_mime(self, file_doc) -> str:
        file_name = (file_doc.file_name or "").lower()
        if file_name.endswith(".png"):
            return "image/png"
        if file_name.endswith(".jpg") or file_name.endswith(".jpeg"):
            return "image/jpeg"
        if file_name.endswith(".webp"):
            return "image/webp"
        if file_name.endswith(".gif"):
            return "image/gif"
        if file_name.endswith(".bmp"):
            return "image/bmp"
        if file_name.endswith(".tif") or file_name.endswith(".tiff"):
            return "image/tiff"
        return "application/octet-stream"

    def _stem(self, file_name: str) -> str:
        if not file_name:
            return "page"
        name = file_name.rsplit("/", 1)[-1]
        if "." in name:
            name = name.rsplit(".", 1)[0]
        return _slugify(name) or "page"


class GoogleVisionClient:
    """Perform OCR against Google Vision with a service account."""

    def __init__(self, config: AiImportConfig, timeout_seconds: int = GOOGLE_TIMEOUT_SECONDS) -> None:
        self.config = config
        self.timeout_seconds = timeout_seconds
        self._access_token: str | None = None
        self._token_expiry: int = 0
        self.session = requests.Session()

    def detect_text(self, pages: list[RenderedPage]) -> list[OcrPage]:
        if not pages:
            return []

        token = self._get_access_token()
        payload = {
            "requests": [
                {
                    "image": {"content": base64.b64encode(page.content).decode()},
                    "features": [{"type": VISION_DOCUMENT_FEATURE}],
                }
                for page in pages
            ]
        }
        response = self.session.post(
            self.config.google_vision_url,
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
            timeout=self.timeout_seconds,
        )
        self._raise_for_http_error(response, _("Google Vision OCR request failed."))
        data = response.json()
        responses = data.get("responses") or []

        ocr_pages: list[OcrPage] = []
        for index, page in enumerate(pages):
            response_item = responses[index] if index < len(responses) else {}
            if response_item.get("error"):
                raise AiFormBuilderProcessingError(
                    _("Google Vision failed on page {0}: {1}").format(
                        page.page_number,
                        response_item["error"].get("message") or _("Unknown error"),
                    )
                )

            full_text = (
                (response_item.get("fullTextAnnotation") or {}).get("text")
                or (response_item.get("textAnnotations") or [{}])[0].get("description")
                or ""
            )
            ocr_pages.append(
                OcrPage(
                    page_number=page.page_number,
                    text=_normalize_text(full_text),
                )
            )

        return ocr_pages

    def _get_access_token(self) -> str:
        now = int(time.time())
        if self._access_token and now < self._token_expiry - 60:
            return self._access_token

        header = {"alg": "RS256", "typ": "JWT"}
        claims = {
            "iss": self.config.google_service_account["client_email"],
            "scope": DEFAULT_VISION_SCOPE,
            "aud": self.config.google_token_url,
            "iat": now,
            "exp": now + 3600,
        }

        assertion = _sign_jwt(header, claims, self.config.google_service_account["private_key"])
        response = self.session.post(
            self.config.google_token_url,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            },
            timeout=60,
        )
        self._raise_for_http_error(response, _("Google OAuth token exchange failed."))
        token_data = response.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise AiFormBuilderProcessingError(_("Google OAuth token exchange did not return an access token."))

        self._access_token = access_token
        self._token_expiry = int(token_data.get("expires_in") or 3600) + now
        return access_token

    def _raise_for_http_error(self, response: requests.Response, fallback_message: str) -> None:
        if response.ok:
            return
        message = _parse_http_error(response, fallback_message)
        raise AiFormBuilderProcessingError(message)


class OpenAiFormGenerator:
    """Transform OCR text into a builder-ready schema using OpenAI."""

    def __init__(self, config: AiImportConfig, timeout_seconds: int = OPENAI_TIMEOUT_SECONDS) -> None:
        self.config = config
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()

    def generate(
        self,
        ocr_pages: list[OcrPage],
        source_file_name: str,
        table_hints: list[TableHint] | None = None,
    ) -> dict[str, Any]:
        messages = self._build_messages(ocr_pages, source_file_name, table_hints or [])
        payload = {
            "model": self.config.model,
            "messages": messages,
            "reasoning_effort": AI_IMPORT_REASONING_EFFORT,
            "max_completion_tokens": AI_IMPORT_MAX_COMPLETION_TOKENS,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "ampower_form_builder_ai_draft",
                    "strict": True,
                    "schema": _build_openai_schema(),
                },
            },
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
        self._raise_for_http_error(response, _("OpenAI request failed."))
        data = response.json()
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}

        if message.get("refusal"):
            raise AiFormBuilderProcessingError(message["refusal"])

        content = message.get("content") or ""
        if not content.strip():
            raise AiFormBuilderProcessingError(_("OpenAI returned an empty response."))

        try:
            draft = json.loads(content)
        except json.JSONDecodeError as exc:
            raise AiFormBuilderProcessingError(_("OpenAI returned invalid JSON. {0}").format(str(exc))) from exc

        if not isinstance(draft, dict):
            raise AiFormBuilderProcessingError(_("OpenAI response must be a JSON object."))

        return draft

    def _build_messages(
        self,
        ocr_pages: list[OcrPage],
        source_file_name: str,
        table_hints: list[TableHint],
    ) -> list[dict[str, str]]:
        source_summary = "\n".join(
            f"Page {page.page_number}:\n{page.text or '[No text detected]'}".strip()
            for page in ocr_pages
        )
        table_hint_summary = self._render_table_hints(table_hints)

        system_prompt = (
            getattr(self.config, "form_builder_system_prompt", "")
            or ""
        ).strip() or DEFAULT_AI_IMPORT_SYSTEM_PROMPT

        user_prompt = (
            f"Source file: {source_file_name}\n\n"
            "OCR text by page:\n"
            f"{source_summary}\n\n"
            "Create a draft form schema with:\n"
            "- form_name\n"
            "- description\n"
            "- warnings\n"
            "- sections\n\n"
            "Use warnings for ambiguous or inferred items, or return an empty array when there are no notes.\n\n"
            "Structure guidance:\n"
            "- Key/value blocks under a heading represent ordinary fields in a section. Use only the keys/labels, never the values.\n"
            "- Repeated row groups with clear headers or repeated columns should become Table or Mixed Table fields.\n"
            "- Columnar blocks under a heading should become a Table or Mixed Table with the header row as table_columns.\n"
            "- Do not flatten a detected child table into unrelated standalone fields.\n"
            "- Prefer Table over Mixed Table for report-style grids unless the row labels are part of the document structure itself.\n"
            "- Do not use OCR values to invent labels, fieldnames, or table headers.\n\n"
            "Section guidance:\n"
            "- Use Tab Break for major groups when the document clearly separates parts.\n"
            "- Use Section Break for sub-groups within a tab.\n"
            "- Each section must contain one or more columns.\n"
            "- Each column must contain only actual form fields.\n"
            "- Do not include HTML or Heading placeholders.\n\n"
            "Field guidance:\n"
            "- Keep fieldnames lowercase snake_case and unique.\n"
            "- For Link fields, include the target DocType in options only when it is obvious from the OCR.\n"
            "- For Select and Radio fields, include newline-separated options.\n"
            "- For Table and Mixed Table fields, include table_columns and, for Mixed Table, table_rows.\n"
            "- If a table cannot be reconstructed, fall back to a regular field instead of guessing.\n"
        )

        if table_hint_summary:
            table_hint_json = self._render_table_hints_json(table_hints)
            user_prompt += (
                "\nDetected structural candidates from OCR:\n"
                f"{table_hint_json}\n\n"
                f"{table_hint_summary}\n"
                "Use detail blocks as signals for ordinary fields, and child table candidates as signals for Table or Mixed Table fields.\n"
                "When a child table candidate is present, keep its columns and repeated rows inside one table field instead of converting them into standalone fields.\n"
            )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _render_table_hints(self, table_hints: list[TableHint]) -> str:
        if not table_hints:
            return ""

        lines: list[str] = []
        for hint in table_hints[:8]:
            lines.extend(hint.to_prompt_lines())
        return "\n".join(lines)

    def _render_table_hints_json(self, table_hints: list[TableHint]) -> str:
        if not table_hints:
            return ""

        payload = [hint.to_dict() for hint in table_hints[:8]]
        return json.dumps(payload, indent=2, ensure_ascii=True)

    def _raise_for_http_error(self, response: requests.Response, fallback_message: str) -> None:
        if response.ok:
            return
        message = _parse_http_error(response, fallback_message)
        raise AiFormBuilderProcessingError(message)


class AiFormDraftNormalizer:
    """Normalize model output into a stable schema for the Vue builder."""

    def normalize(self, draft: dict[str, Any], source_file_name: str) -> dict[str, Any]:
        warnings = self._dedupe_strings([str(item) for item in (draft.get("warnings") or []) if str(item).strip()])
        form_name = _normalize_text(draft.get("form_name") or self._fallback_form_name(source_file_name))
        description = _normalize_text(draft.get("description") or "")
        sections = draft.get("sections") or []

        if not isinstance(sections, list) or not sections:
            raise AiFormBuilderProcessingError(_("OpenAI did not return any form sections."))

        normalized_sections: list[dict[str, Any]] = []
        seen_section_keys: set[str] = set()
        seen_fieldnames: set[str] = set()

        for index, section in enumerate(sections):
            normalized_section = self._normalize_section(
                section,
                index=index,
                seen_section_keys=seen_section_keys,
                seen_fieldnames=seen_fieldnames,
                warnings=warnings,
            )
            normalized_sections.append(normalized_section)

        return {
            "version": 1,
            "form_name": form_name,
            "description": description,
            "sections": normalized_sections,
            "warnings": self._dedupe_strings(warnings),
        }

    def ensure_table_hints(
        self,
        draft: dict[str, Any],
        table_hints: list[TableHint],
    ) -> dict[str, Any]:
        if not table_hints or not isinstance(draft, dict):
            return draft

        sections = draft.get("sections") or []
        if not isinstance(sections, list) or not sections:
            return draft

        injected = False
        warnings = [str(item) for item in (draft.get("warnings") or []) if str(item).strip()]
        used_fieldnames = self._collect_fieldnames(sections)
        existing_field_keys = self._collect_field_keys(sections)

        for hint in table_hints[:5]:
            if hint.kind == "detail_block":
                fields = self._build_detail_fields_from_hint(hint, used_fieldnames, existing_field_keys)
                if not fields:
                    continue

                target_section = self._find_target_section(sections, hint.title) or sections[0]
                target_columns = target_section.setdefault("columns", [])
                if not target_columns:
                    target_columns.append({"items": []})
                target_columns[0].setdefault("items", []).extend(fields)
                warnings.append(_("Detail block auto-expanded into fields from OCR: {0}").format(hint.title))
                injected = True
                continue

            if hint.kind != "child_table":
                continue
            if self._hint_has_matching_table_field(sections, hint.title):
                continue
            field = self._build_table_field_from_hint(hint, used_fieldnames)
            if not field:
                continue

            target_section = self._find_target_section(sections, hint.title) or sections[0]
            target_columns = target_section.setdefault("columns", [])
            if not target_columns:
                target_columns.append({"items": []})
            target_columns[0].setdefault("items", []).append(field)
            warnings.append(_("Table structure auto-added from OCR: {0}").format(hint.title))
            injected = True

        if injected:
            draft["warnings"] = self._dedupe_strings(warnings)
        return draft

    def _collect_field_keys(self, sections: list[dict[str, Any]]) -> set[str]:
        keys: set[str] = set()
        for section in sections:
            for column in section.get("columns", []) or []:
                for field in column.get("items", []) or []:
                    fieldtype = _normalize_text(field.get("fieldtype") or field.get("field_type") or "")
                    if fieldtype in {"Table", "Mixed Table"}:
                        continue
                    label_match = _slugify(field.get("label") or field.get("field_label") or "")
                    name_match = _slugify(field.get("fieldname") or field.get("field_name") or "")
                    if label_match:
                        keys.add(label_match)
                    if name_match:
                        keys.add(name_match)
        return keys

    def _normalize_section(
        self,
        section: dict[str, Any],
        *,
        index: int,
        seen_section_keys: set[str],
        seen_fieldnames: set[str],
        warnings: list[str],
    ) -> dict[str, Any]:
        if not isinstance(section, dict):
            raise AiFormBuilderProcessingError(_("Section at index {0} must be an object.").format(index))

        item_type = section.get("item_type") or section.get("type") or section.get("section_type")
        if item_type not in {"Tab Break", "Section Break"}:
            item_type = "Tab Break" if index == 0 else "Section Break"

        section_label = _normalize_text(section.get("section_label") or section.get("label") or "")
        if not section_label:
            section_label = "Details" if item_type == "Tab Break" and index == 0 else _("Section {0}").format(index + 1)

        section_key_source = section.get("section_key") or section.get("fieldname") or section_label
        section_key = self._unique_name(_slugify(section_key_source), seen_section_keys, fallback=f"section_{index + 1}")

        raw_columns = section.get("columns") or []
        if not isinstance(raw_columns, list) or not raw_columns:
            raw_columns = [{"items": []}]

        columns: list[dict[str, Any]] = []
        for column_index, column in enumerate(raw_columns):
            columns.append(
                self._normalize_column(
                    column,
                    section_label=section_label,
                    section_key=section_key,
                    column_index=column_index,
                    seen_fieldnames=seen_fieldnames,
                    warnings=warnings,
                )
            )

        return {
            "item_type": item_type,
            "section_label": section_label,
            "section_key": section_key,
            "columns": columns,
        }

    def _normalize_column(
        self,
        column: dict[str, Any],
        *,
        section_label: str,
        section_key: str,
        column_index: int,
        seen_fieldnames: set[str],
        warnings: list[str],
    ) -> dict[str, Any]:
        if not isinstance(column, dict):
            column = {}

        raw_items = column.get("items") or []
        if not isinstance(raw_items, list):
            raw_items = []

        normalized_items: list[dict[str, Any]] = []
        for item_index, field in enumerate(raw_items):
            normalized_items.append(
                self._normalize_field(
                    field,
                    section_label=section_label,
                    section_key=section_key,
                    column_index=column_index,
                    item_index=item_index,
                    seen_fieldnames=seen_fieldnames,
                    warnings=warnings,
                )
            )

        return {
            "items": normalized_items,
        }

    def _normalize_field(
        self,
        field: dict[str, Any],
        *,
        section_label: str,
        section_key: str,
        column_index: int,
        item_index: int,
        seen_fieldnames: set[str],
        warnings: list[str],
    ) -> dict[str, Any]:
        if not isinstance(field, dict):
            raise AiFormBuilderProcessingError(_("Field at index {0} must be an object.").format(item_index))

        fieldtype = field.get("fieldtype") or field.get("field_type") or "Data"
        fieldtype = self._normalize_fieldtype(fieldtype)

        label = _normalize_text(field.get("label") or field.get("field_label") or "")
        if not label:
            label = field.get("fieldname") or fieldtype

        fieldname_source = field.get("fieldname") or field.get("field_name") or label
        fieldname = self._unique_name(_slugify(fieldname_source), seen_fieldnames, fallback=f"field_{item_index + 1}")

        description = _normalize_text(field.get("description") or "")
        placeholder = _normalize_text(field.get("placeholder") or "")
        default_value = field.get("default")
        if default_value is None:
            default_value = ""
        depends_on = _normalize_text(field.get("depends_on") or "")
        fetch_from = _normalize_text(field.get("fetch_from") or "")
        table_row_title = _normalize_text(field.get("table_row_title") or "")
        read_only = 1 if field.get("read_only") in (True, 1, "1") else 0
        hidden = 1 if field.get("hidden") in (True, 1, "1") else 0
        reqd = 1 if field.get("reqd") in (True, 1, "1") else 0
        precision = field.get("precision")
        options = field.get("options") or ""

        if fieldtype in {"Select", "Radio"}:
            options = _normalize_options(options)
            if not options:
                warnings.append(f"{label}: missing options, converted to Data.")
                fieldtype = "Data"

        if fieldtype == "Link":
            options = _normalize_text(options or field.get("_doctype") or "")
            if not options:
                warnings.append(f"{label}: missing link target, converted to Data.")
                fieldtype = "Data"

        if fieldtype == "Dynamic Link" and not _normalize_text(options):
            warnings.append(f"{label}: missing dynamic link source, converted to Data.")
            fieldtype = "Data"

        table_columns: list[dict[str, Any]] = []
        table_rows: list[dict[str, Any]] = []
        if fieldtype in {"Table", "Mixed Table"}:
            raw_columns = field.get("table_columns") or field.get("columns") or []
            if not isinstance(raw_columns, list):
                raw_columns = []
            table_columns = self._normalize_table_columns(raw_columns, label, warnings)

            raw_rows = field.get("table_rows") or field.get("rows") or []
            if not isinstance(raw_rows, list):
                raw_rows = []
            table_rows = self._normalize_table_rows(raw_rows, label)

            if fieldtype == "Mixed Table" and not table_rows:
                warnings.append(f"{label}: mixed table rows were missing, converted to Table.")
                fieldtype = "Table"

            if not table_columns:
                warnings.append(f"{label}: table columns were missing, added a generic column.")
                table_columns = [
                    {
                        "label": "Value",
                        "fieldname": "value",
                        "fieldtype": "Data",
                        "reqd": 0,
                        "placeholder": "",
                        "fetch_from": "",
                        "formula": "",
                        "precision": "",
                        "options": "",
                    }
                ]

        return {
            "fieldtype": fieldtype,
            "fieldname": fieldname,
            "label": label,
            "description": description,
            "placeholder": placeholder,
            "default": default_value,
            "reqd": reqd,
            "read_only": read_only,
            "hidden": hidden,
            "depends_on": depends_on,
            "options": options if fieldtype not in {"Table", "Mixed Table"} else "",
            "fetch_from": fetch_from,
            "precision": precision if precision is not None else "",
            "table_row_title": table_row_title,
            "table_columns": table_columns,
            "table_rows": table_rows,
            "_meta": {
                "section_key": section_key,
                "section_label": section_label,
                "column_index": column_index,
            },
        }

    def _normalize_table_columns(self, columns: list[dict[str, Any]], parent_label: str, warnings: list[str]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        normalized: list[dict[str, Any]] = []
        for index, column in enumerate(columns):
            if not isinstance(column, dict):
                column = {}

            label = _normalize_text(column.get("label") or column.get("fieldname") or f"Column {index + 1}")
            fieldtype = self._normalize_table_column_fieldtype(column.get("fieldtype") or "Data")
            fieldname = self._unique_name(_slugify(column.get("fieldname") or label), seen, fallback=f"column_{index + 1}")
            options = _normalize_text(column.get("options") or "")
            if fieldtype == "Select" and not options:
                warnings.append(f"{parent_label}: table column {label} is a Select field without options, converted to Data.")
                fieldtype = "Data"
            if fieldtype == "Link" and not options and not _normalize_text(column.get("_doctype")):
                warnings.append(f"{parent_label}: table column {label} is a Link field without target, converted to Data.")
                fieldtype = "Data"

            normalized.append(
                {
                    "label": label,
                    "fieldname": fieldname,
                    "fieldtype": fieldtype,
                    "reqd": 1 if column.get("reqd") in (True, 1, "1") else 0,
                    "placeholder": _normalize_text(column.get("placeholder") or ""),
                    "fetch_from": _normalize_text(column.get("fetch_from") or ""),
                    "formula": _normalize_text(column.get("formula") or ""),
                    "precision": column.get("precision") if column.get("precision") is not None else "",
                    "options": options,
                    "_doctype": _normalize_text(column.get("_doctype") or ""),
                }
            )
        return normalized

    def _normalize_table_rows(self, rows: list[dict[str, Any]], parent_label: str) -> list[dict[str, Any]]:
        seen: set[str] = set()
        normalized: list[dict[str, Any]] = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                row = {}
            label = _normalize_text(row.get("label") or row.get("key") or f"Row {index + 1}")
            key = self._unique_name(_slugify(row.get("key") or label), seen, fallback=f"row_{index + 1}")
            normalized.append({"label": label, "key": key})
        return normalized

    def _normalize_fieldtype(self, fieldtype: str) -> str:
        value = _normalize_text(fieldtype)
        if value not in SUPPORTED_FIELD_TYPES:
            return "Data"
        return value

    def _normalize_table_column_fieldtype(self, fieldtype: str) -> str:
        value = _normalize_text(fieldtype)
        if value not in SUPPORTED_TABLE_COLUMN_FIELD_TYPES:
            return "Data"
        return value

    def _has_table_field(self, sections: list[dict[str, Any]]) -> bool:
        for section in sections:
            for column in section.get("columns", []) or []:
                for field in column.get("items", []) or []:
                    fieldtype = _normalize_text(field.get("fieldtype") or field.get("field_type") or "")
                    if fieldtype in {"Table", "Mixed Table"}:
                        return True
        return False

    def _hint_has_matching_table_field(self, sections: list[dict[str, Any]], title: str) -> bool:
        normalized_title = _slugify(title)
        if not normalized_title:
            return False

        for section in sections:
            for column in section.get("columns", []) or []:
                for field in column.get("items", []) or []:
                    fieldtype = _normalize_text(field.get("fieldtype") or field.get("field_type") or "")
                    if fieldtype not in {"Table", "Mixed Table"}:
                        continue
                    label_match = _slugify(field.get("label") or field.get("field_label") or "")
                    name_match = _slugify(field.get("fieldname") or field.get("field_name") or "")
                    if normalized_title == label_match or normalized_title == name_match:
                        return True
        return False

    def _collect_fieldnames(self, sections: list[dict[str, Any]]) -> set[str]:
        names: set[str] = set()
        for section in sections:
            for column in section.get("columns", []) or []:
                for field in column.get("items", []) or []:
                    fieldname = _normalize_text(field.get("fieldname") or field.get("field_name") or "")
                    if fieldname:
                        names.add(fieldname)
        return names

    def _find_target_section(self, sections: list[dict[str, Any]], title: str) -> dict[str, Any] | None:
        normalized_title = _normalize_text(title).lower()
        if not normalized_title:
            return sections[0] if sections else None

        for section in sections:
            section_label = _normalize_text(section.get("section_label") or section.get("label") or "").lower()
            if section_label and (normalized_title in section_label or section_label in normalized_title):
                return section
        return sections[0] if sections else None

    def _build_table_field_from_hint(self, hint: TableHint, used_fieldnames: set[str]) -> dict[str, Any]:
        label = _normalize_text(hint.title) or _("Detected Table")
        fieldname = self._unique_name(_slugify(label), used_fieldnames, fallback="table")
        columns_source = hint.columns or []
        if len(columns_source) < 2:
            columns_source = ["Column 1", "Column 2"]

        table_columns = []
        for index, column_label in enumerate(columns_source):
            clean_label = _normalize_text(column_label) or f"Column {index + 1}"
            table_columns.append(
                {
                    "label": clean_label,
                    "fieldname": self._unique_name(_slugify(clean_label), used_fieldnames, fallback=f"column_{index + 1}"),
                    "fieldtype": "Data",
                    "reqd": 0,
                    "placeholder": "",
                    "fetch_from": "",
                    "formula": "",
                    "precision": "",
                    "options": "",
                }
            )

        return {
            "fieldtype": "Table",
            "fieldname": fieldname,
            "label": label,
            "description": _(""),
            "placeholder": "",
            "default": "",
            "reqd": 0,
            "read_only": 0,
            "hidden": 0,
            "depends_on": "",
            "options": "",
            "fetch_from": "",
            "precision": "",
            "table_row_title": "",
            "table_columns": table_columns,
            "table_rows": [],
        }

    def _build_detail_fields_from_hint(
        self,
        hint: TableHint,
        used_fieldnames: set[str],
        existing_field_keys: set[str],
    ) -> list[dict[str, Any]]:
        fields: list[dict[str, Any]] = []
        for index, row in enumerate(hint.rows):
            if not row:
                continue

            label = _normalize_text(row[0]) if row else ""
            if not label:
                continue

            label_key = _slugify(label)
            if label_key and label_key in existing_field_keys:
                continue

            fieldtype = self._infer_detail_fieldtype(label)
            fieldname = self._unique_name(_slugify(label), used_fieldnames, fallback=f"field_{index + 1}")

            fields.append(
                {
                    "fieldtype": fieldtype,
                    "fieldname": fieldname,
                    "label": label,
                    "description": _(""),
                    "placeholder": "",
                    "default": "",
                    "reqd": 0,
                    "read_only": 0,
                    "hidden": 0,
                    "depends_on": "",
                    "options": "",
                    "fetch_from": "",
                    "precision": "",
                    "table_row_title": "",
                    "table_columns": [],
                    "table_rows": [],
                }
            )
            if label_key:
                existing_field_keys.add(label_key)
            existing_field_keys.add(_slugify(fieldname))

        return fields

    def _infer_detail_fieldtype(self, label: str) -> str:
        compact_label = re.sub(r"\s+", " ", _normalize_text(label).lower()).strip()

        if not compact_label:
            return "Data"

        if re.search(r"\b(date|dob)\b", compact_label) and re.search(r"\btime\b", compact_label):
            return "Datetime"

        if re.search(r"\b(date|dob)\b", compact_label):
            return "Date"

        if re.search(r"\btime\b", compact_label):
            return "Time"

        return "Data"

    def _unique_name(self, base_name: str, seen: set[str], *, fallback: str) -> str:
        candidate = _slugify(base_name) or _slugify(fallback) or "field"
        if not candidate:
            candidate = "field"
        if not candidate[0].isalpha():
            candidate = f"field_{candidate}"
        if candidate in SQL_KEYWORDS:
            candidate = f"{candidate}_field"

        unique = candidate
        counter = 2
        while unique in seen:
            unique = f"{candidate}_{counter}"
            counter += 1
        seen.add(unique)
        return unique

    def _dedupe_strings(self, items: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for item in items:
            if item and item not in seen:
                seen.add(item)
                result.append(item)
        return result

    def _fallback_form_name(self, source_file_name: str) -> str:
        base = source_file_name.rsplit("/", 1)[-1]
        if "." in base:
            base = base.rsplit(".", 1)[0]
        base = _normalize_text(base).replace("_", " ").strip()
        return base.title() if base else _("AI Draft Form")


class AiFormBuilderImportService:
    """Orchestrates the import workflow."""

    def __init__(self) -> None:
        self.config_repository = FormBuilderConfigRepository()
        self.status_store = AiImportStatusStore()
        self.artifact_store = AiImportArtifactStore()
        self.rasterizer = PdfPageRasterizer()
        self.table_detector = OcrTableDetector()
        self.normalizer = AiFormDraftNormalizer()

    def enqueue_import(self, file_docname: str) -> dict[str, Any]:
        file_doc = self._load_file_doc(file_docname)
        config = self.config_repository.load()

        job_id = frappe.generate_hash(length=16)
        self.status_store.create(job_id, frappe.session.user, file_doc.name, file_doc.file_name)

        enqueue(
            "ampower_form_builder.services.ai_form_builder.process_ai_form_builder_import",
            queue="long",
            timeout=1800,
            enqueue_after_commit=True,
            job_id=job_id,
            file_docname=file_doc.name,
            owner=frappe.session.user,
        )

        return {
            "job_id": job_id,
            "status": "queued",
            "file_docname": file_doc.name,
            "file_name": file_doc.file_name,
            "model": config.model,
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
                raise AiFormBuilderValidationError(_("AI import job was not found."))

        if status.get("owner") and status.get("owner") != frappe.session.user:
            raise AiFormBuilderValidationError(_("You are not allowed to access this AI import job."))

        if rq_status_text and status.get("status") in {"queued", "processing"} and rq_status_text == "failed":
            status["status"] = "failed"
            status["stage"] = "failed"
            status["progress"] = 100
            status.setdefault("error", _("The background job failed."))

        status["rq_status"] = rq_status_text
        status["finished"] = status.get("status") in {"completed", "failed"}
        return status

    def process_import(self, file_docname: str, owner: str, job_id: str | None = None) -> dict[str, Any]:
        resolved_job_id = job_id or _current_background_job_id()
        if not resolved_job_id:
            raise AiFormBuilderProcessingError(_("Unable to determine the AI import job ID."))

        progress = ProgressReporter(job_id=resolved_job_id, owner=owner, progress_store=self.status_store)
        previous_user = getattr(getattr(frappe, "session", None), "user", None)
        restore_user = bool(owner) and previous_user != owner

        try:
            if restore_user:
                frappe.set_user(owner)

            progress.update(5, "loading", _("Loading uploaded file..."))
            file_doc = self._load_file_doc(file_docname)

            pages = self.rasterizer.render(file_doc)
            progress.update(20, "rendering", _("Rendered {0} page(s) for OCR.").format(len(pages)))

            config = self.config_repository.load()
            vision_client = GoogleVisionClient(config)
            ocr_pages = vision_client.detect_text(pages)
            table_hints = self.table_detector.detect(ocr_pages)
            detail_block_count = sum(1 for hint in table_hints if hint.kind == "detail_block")
            child_table_count = sum(1 for hint in table_hints if hint.kind == "child_table")
            non_empty_pages = sum(1 for page in ocr_pages if page.text.strip())
            progress.update(
                55,
                "ocr",
                _("Google Vision OCR completed for {0} page(s). Detected {1} detail block(s) and {2} child table candidate(s).").format(
                    len(ocr_pages),
                    detail_block_count,
                    child_table_count,
                ),
                ocr_pages=len(ocr_pages),
                non_empty_pages=non_empty_pages,
                detail_block_candidates=detail_block_count,
                child_table_candidates=child_table_count,
            )

            self.artifact_store.create(
                resolved_job_id,
                {
                    "source_file_name": file_doc.file_name,
                    "page_count": len(pages),
                    "ocr_pages": [
                        {
                            "page_number": page.page_number,
                            "text": page.text,
                        }
                        for page in ocr_pages
                    ],
                    "table_hints": [hint.to_dict() for hint in table_hints],
                },
            )

            enqueue(
                "ampower_form_builder.services.ai_form_builder.finalize_ai_form_builder_import",
                queue="long",
                timeout=3600,
                import_job_id=resolved_job_id,
                owner=owner,
            )

            progress.update(
                65,
                "queued_generation",
                _("OCR completed. OpenAI generation job has been queued."),
                table_candidates=len(table_hints),
            )

            result = {
                "job_id": resolved_job_id,
                "source_file_name": file_doc.file_name,
                "page_count": len(pages),
                "status": "queued_for_generation",
                "schema": None,
                "warnings": [],
                "form_name": "",
                "description": "",
            }
            return result
        except AiFormBuilderError as exc:
            progress.fail(str(exc), stage="failed")
            raise
        except Exception as exc:
            message = _("AI form import failed: {0}").format(str(exc))
            progress.fail(message, stage="failed")
            raise AiFormBuilderProcessingError(message) from exc
        finally:
            if restore_user:
                try:
                    frappe.set_user(previous_user or "Administrator")
                except Exception:
                    pass

    def finalize_import(self, import_job_id: str, owner: str) -> dict[str, Any]:
        if not import_job_id:
            raise AiFormBuilderProcessingError(_("Unable to determine the AI import job ID."))

        progress = ProgressReporter(job_id=import_job_id, owner=owner, progress_store=self.status_store)
        previous_user = getattr(getattr(frappe, "session", None), "user", None)
        restore_user = bool(owner) and previous_user != owner

        try:
            if restore_user:
                frappe.set_user(owner)

            artifact = self.artifact_store.get(import_job_id)
            if not artifact:
                raise AiFormBuilderProcessingError(_("The AI import payload expired before generation could finish."))

            source_file_name = _normalize_text(artifact.get("source_file_name") or "")
            ocr_pages = [
                OcrPage(
                    page_number=int(page.get("page_number") or index + 1),
                    text=_normalize_text(page.get("text") or ""),
                )
                for index, page in enumerate(artifact.get("ocr_pages") or [])
                if isinstance(page, dict)
            ]
            table_hints = [
                TableHint(
                    page_number=int(hint.get("page_number") or 1),
                    title=_normalize_text(hint.get("title") or ""),
                    kind=_normalize_text(hint.get("kind") or ""),
                    columns=[_normalize_text(column) for column in (hint.get("columns") or []) if _normalize_text(column)],
                    rows=[
                        [_normalize_text(cell) for cell in row if _normalize_text(cell)]
                        for row in (hint.get("rows") or [])
                        if isinstance(row, list)
                    ],
                    evidence=[_normalize_text(item) for item in (hint.get("evidence") or []) if _normalize_text(item)],
                )
                for hint in artifact.get("table_hints") or []
                if isinstance(hint, dict)
            ]

            config = self.config_repository.load()
            openai_client = OpenAiFormGenerator(config)
            progress.update(80, "reasoning", _("OpenAI generation in progress..."))

            draft = openai_client.generate(ocr_pages, source_file_name, table_hints=table_hints)
            progress.update(90, "normalizing", _("OpenAI draft generated, normalizing schema..."))

            normalized = self.normalizer.normalize(draft, source_file_name)
            normalized = self.normalizer.ensure_table_hints(normalized, table_hints)
            result = {
                "job_id": import_job_id,
                "source_file_name": source_file_name,
                "page_count": int(artifact.get("page_count") or len(ocr_pages)),
                "schema": normalized,
                "warnings": normalized.get("warnings") or [],
                "form_name": normalized.get("form_name") or "",
                "description": normalized.get("description") or "",
            }
            progress.complete(result)
            self.artifact_store.delete(import_job_id)
            return result
        except AiFormBuilderError as exc:
            progress.fail(str(exc), stage="failed")
            raise
        except Exception as exc:
            message = _("AI form generation failed: {0}").format(str(exc))
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


def queue_ai_form_builder_import(file_docname: str) -> dict[str, Any]:
    return AiFormBuilderImportService().enqueue_import(file_docname)


def get_ai_form_builder_import_status(job_id: str) -> dict[str, Any]:
    return AiFormBuilderImportService().get_status(job_id)


def process_ai_form_builder_import(file_docname: str, owner: str, job_id: str | None = None) -> dict[str, Any]:
    return AiFormBuilderImportService().process_import(file_docname=file_docname, owner=owner, job_id=job_id)


def finalize_ai_form_builder_import(import_job_id: str, owner: str) -> dict[str, Any]:
    return AiFormBuilderImportService().finalize_import(import_job_id=import_job_id, owner=owner)


def _build_openai_schema() -> dict[str, Any]:
    field_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "fieldtype",
            "fieldname",
            "label",
            "description",
            "placeholder",
            "default",
            "reqd",
            "read_only",
            "hidden",
            "depends_on",
            "options",
            "fetch_from",
            "precision",
            "table_row_title",
            "table_columns",
            "table_rows",
        ],
        "properties": {
            "fieldtype": {"type": "string", "enum": list(SUPPORTED_FIELD_TYPES)},
            "fieldname": {"type": "string"},
            "label": {"type": "string"},
            "description": {"type": "string"},
            "placeholder": {"type": "string"},
            "default": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "number"},
                    {"type": "boolean"},
                    {"type": "null"},
                ],
            },
            "reqd": {"type": "boolean"},
            "read_only": {"type": "boolean"},
            "hidden": {"type": "boolean"},
            "depends_on": {"type": "string"},
            "options": {"type": "string"},
            "fetch_from": {"type": "string"},
            "precision": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "number"},
                    {"type": "null"},
                ],
            },
            "table_row_title": {"type": "string"},
            "table_columns": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "label",
                        "fieldname",
                        "fieldtype",
                        "reqd",
                        "placeholder",
                        "fetch_from",
                        "formula",
                        "precision",
                        "options",
                    ],
                    "properties": {
                        "label": {"type": "string"},
                        "fieldname": {"type": "string"},
                        "fieldtype": {
                            "type": "string",
                            "enum": list(SUPPORTED_TABLE_COLUMN_FIELD_TYPES),
                        },
                        "reqd": {"type": "boolean"},
                        "placeholder": {"type": "string"},
                        "fetch_from": {"type": "string"},
                        "formula": {"type": "string"},
                        "precision": {
                            "anyOf": [
                                {"type": "string"},
                                {"type": "number"},
                                {"type": "null"},
                            ],
                        },
                        "options": {"type": "string"},
                    },
                },
            },
            "table_rows": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["label", "key"],
                    "properties": {
                        "label": {"type": "string"},
                        "key": {"type": "string"},
                    },
                },
            },
        },
    }

    section_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["item_type", "section_label", "section_key", "columns"],
        "properties": {
            "item_type": {
                "type": "string",
                "enum": ["Tab Break", "Section Break"],
            },
            "section_label": {"type": "string"},
            "section_key": {"type": "string"},
            "columns": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["items"],
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": field_schema,
                        }
                    },
                },
            },
        },
    }

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["form_name", "description", "warnings", "sections"],
        "properties": {
            "form_name": {"type": "string"},
            "description": {"type": "string"},
            "warnings": {
                "type": "array",
                "items": {"type": "string"},
            },
            "sections": {
                "type": "array",
                "minItems": 1,
                "items": section_schema,
            },
        },
    }


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return text.strip()


def _normalize_ocr_line(value: Any) -> str:
    text = _normalize_text(value)
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def _normalize_options(value: Any) -> str:
    if isinstance(value, list):
        return "\n".join(_normalize_text(item) for item in value if _normalize_text(item))
    return _normalize_text(value)


def _slugify(value: Any) -> str:
    text = _normalize_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    if not text:
        return ""
    if text[0].isdigit():
        text = f"field_{text}"
    if text in SQL_KEYWORDS:
        text = f"{text}_field"
    return text


def _sign_jwt(header: dict[str, Any], claims: dict[str, Any], private_key_pem: str) -> str:
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise AiFormBuilderProcessingError(_("cryptography is required for Google service account authentication.")) from exc

    private_key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
    encoded_header = _b64url(json.dumps(header, separators=(",", ":")).encode())
    encoded_claims = _b64url(json.dumps(claims, separators=(",", ":")).encode())
    signing_input = f"{encoded_header}.{encoded_claims}".encode()
    signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return f"{encoded_header}.{encoded_claims}.{_b64url(signature)}"


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _current_background_job_id() -> str:
    job = get_current_job()
    if not job or not job.id:
        return ""

    job_id = str(job.id)
    if "::" in job_id:
        return job_id.rsplit("::", 1)[-1]
    return job_id


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
