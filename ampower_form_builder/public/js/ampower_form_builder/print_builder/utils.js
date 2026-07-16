import { uid, clone } from "../utils.js";

export const PX_PER_MM = 3.7795275591;
export const A4_PAGE_WIDTH = "210mm";
export const A4_PAGE_HEIGHT = "297mm";

export const DEFAULT_PRINT_PAGE = {
	page_width: A4_PAGE_WIDTH,
	page_height: A4_PAGE_HEIGHT,
	margin_top: "10mm",
	margin_right: "10mm",
	margin_bottom: "10mm",
	margin_left: "10mm",
};

export const LAYOUT_FIELD_TYPES = new Set(["Section Break", "Tab Break", "Column Break", "HTML", "Heading"]);
export const MATRIX_MIN_ROWS = 1;
export const MATRIX_MIN_COLS = 1;
export const MATRIX_DEFAULT_ROWS = 2;
export const MATRIX_DEFAULT_COLS = 2;
export const MATRIX_DEFAULT_ROW_HEIGHT = 34;
export const MATRIX_DEFAULT_HEADING_HEIGHT = 28;
export const MATRIX_PADDING = 10;
export const MATRIX_DEFAULT_SPAN = 1;
export const IMAGE_FIELD_TYPES = new Set(["Attach Image", "Image", "Signature"]);
export const TABLE_FIELD_TYPES = new Set(["Table", "Mixed Table"]);

export function toNumber(value, fallback = 0) {
	const number = Number.parseFloat(String(value ?? "").replace(/[^\d.-]/g, ""));
	return Number.isFinite(number) ? number : fallback;
}

export function toPx(value) {
	return Math.max(toNumber(value) * PX_PER_MM, 0);
}

export function toMm(value) {
	return `${Math.max(Number(value) / PX_PER_MM, 0).toFixed(2)}mm`;
}

export function clamp(value, min, max) {
	return Math.min(Math.max(value, min), max);
}

function toInteger(value, fallback = 0) {
	const number = Number.parseInt(String(value ?? ""), 10);
	return Number.isFinite(number) ? number : fallback;
}

function clampSpan(value, maxSpan) {
	return clamp(toInteger(value, MATRIX_DEFAULT_SPAN), MATRIX_DEFAULT_SPAN, Math.max(toInteger(maxSpan, MATRIX_DEFAULT_SPAN), MATRIX_DEFAULT_SPAN));
}

export function getPageMetrics(page = {}) {
	const pageWidth = toPx(page.page_width || DEFAULT_PRINT_PAGE.page_width);
	const pageHeight = toPx(page.page_height || DEFAULT_PRINT_PAGE.page_height);
	const marginTop = toPx(page.margin_top || DEFAULT_PRINT_PAGE.margin_top);
	const marginRight = toPx(page.margin_right || DEFAULT_PRINT_PAGE.margin_right);
	const marginBottom = toPx(page.margin_bottom || DEFAULT_PRINT_PAGE.margin_bottom);
	const marginLeft = toPx(page.margin_left || DEFAULT_PRINT_PAGE.margin_left);

	return {
		pageWidth,
		pageHeight,
		marginTop,
		marginRight,
		marginBottom,
		marginLeft,
		contentWidth: Math.max(pageWidth - marginLeft - marginRight, 0),
		contentHeight: Math.max(pageHeight - marginTop - marginBottom, 0),
	};
}

export function normalizePlacement(item = {}, page = {}) {
	const metrics = getPageMetrics(page);
	const fieldtype = String(item.fieldtype || "").trim();
	return {
		id: item.id || uid(),
		kind: "field",
		fieldname: String(item.fieldname || "").trim(),
		fieldtype,
		label: String(item.label || item.fieldname || "").trim(),
		print_columns: Array.isArray(item.print_columns) ? item.print_columns.map((value) => String(value || "").trim()).filter(Boolean) : undefined,
		show_label: item.show_label !== false,
		x: clamp(toNumber(item.x), 0, metrics.contentWidth),
		y: Math.max(toNumber(item.y), 0),
		width: clamp(toNumber(item.width, fieldtype ? getPlacementDefaults(fieldtype).width : 180), 40, metrics.contentWidth || 9999),
		height: clamp(toNumber(item.height, fieldtype ? getPlacementDefaults(fieldtype).height : 36), 18, metrics.contentHeight || 9999),
		font_size: clamp(toNumber(item.font_size, 11), 8, 32),
		align: ["left", "center", "right"].includes(item.align) ? item.align : "left",
		style: clone(item.style || {}),
	};
}

function getPlacementDefaults(fieldtype = "") {
	if (IMAGE_FIELD_TYPES.has(fieldtype)) {
		return { width: 220, height: 160 };
	}
	if (TABLE_FIELD_TYPES.has(fieldtype)) {
		return { width: 420, height: 220 };
	}
	return { width: 180, height: 36 };
}

function normalizeMatrixCell(cell = {}, row = 0, col = 0) {
	return {
		id: cell.id || uid(),
		key: cell.key || `${row}:${col}`,
		row,
		col,
		fieldname: String(cell.fieldname || "").trim(),
		label: String(cell.label || cell.fieldname || "").trim(),
		static_text: String(cell.static_text || "").trim(),
		show_label: cell.show_label !== false,
		align: ["left", "center", "right"].includes(cell.align) ? cell.align : "left",
		row_span: clampSpan(cell.row_span, 24 - row),
		col_span: clampSpan(cell.col_span, 12 - col),
		style: clone(cell.style || {}),
	};
}

function buildMatrixCells(rows, cols, existingCells = []) {
	const byKey = new Map(
		existingCells
			.filter((cell) => cell && typeof cell === "object")
			.map((cell) => {
				const row = clamp(toInteger(cell.row), 0, rows - 1);
				const col = clamp(toInteger(cell.col), 0, cols - 1);
				return [`${row}:${col}`, normalizeMatrixCell(cell, row, col)];
			})
	);

	const cells = [];
	const occupied = new Map();
	for (let row = 0; row < rows; row += 1) {
		for (let col = 0; col < cols; col += 1) {
			const key = `${row}:${col}`;
			const coveredBy = occupied.get(key) || "";
			const cell = byKey.get(key) || normalizeMatrixCell({}, row, col);

			if (coveredBy) {
				cells.push({
					...normalizeMatrixCell({}, row, col),
					covered_by: coveredBy,
				});
				continue;
			}

			const normalized = normalizeMatrixCell(cell, row, col);
			cells.push(normalized);

			if (!normalized.fieldname && normalized.row_span === 1 && normalized.col_span === 1) {
				continue;
			}

			for (let rowOffset = 0; rowOffset < normalized.row_span; rowOffset += 1) {
				for (let colOffset = 0; colOffset < normalized.col_span; colOffset += 1) {
					const targetRow = row + rowOffset;
					const targetCol = col + colOffset;
					if (targetRow >= rows || targetCol >= cols) continue;
					if (targetRow === row && targetCol === col) continue;
					occupied.set(`${targetRow}:${targetCol}`, normalized.key);
				}
			}
		}
	}
	return cells;
}

export function getVisibleMatrixCells(cells = []) {
	return Array.isArray(cells) ? cells.filter((cell) => !cell?.covered_by) : [];
}

function getMatrixHeight(matrix) {
	const rowHeight = clamp(toNumber(matrix.row_height, MATRIX_DEFAULT_ROW_HEIGHT), 20, 120);
	const headingHeight = matrix.show_heading === false ? 0 : clamp(toNumber(matrix.heading_height, MATRIX_DEFAULT_HEADING_HEIGHT), 16, 80);
	return MATRIX_PADDING * 2 + headingHeight + (toInteger(matrix.rows, MATRIX_DEFAULT_ROWS) * rowHeight);
}

export function normalizeMatrixItem(item = {}, page = {}) {
	const metrics = getPageMetrics(page);
	const rows = clamp(toInteger(item.rows, MATRIX_DEFAULT_ROWS), MATRIX_MIN_ROWS, 24);
	const cols = clamp(toInteger(item.cols, MATRIX_DEFAULT_COLS), MATRIX_MIN_COLS, 12);
	const rowHeight = clamp(toNumber(item.row_height, MATRIX_DEFAULT_ROW_HEIGHT), 20, 120);
	const headingHeight = clamp(toNumber(item.heading_height, MATRIX_DEFAULT_HEADING_HEIGHT), 16, 80);
	const cells = buildMatrixCells(rows, cols, item.cells || []);
	const width = clamp(toNumber(item.width, metrics.contentWidth || 420), 160, metrics.contentWidth || 9999);
	const height = getMatrixHeight({
		rows,
		row_height: rowHeight,
		heading_height: headingHeight,
		show_heading: item.show_heading,
	});

	return {
		id: item.id || uid(),
		kind: "matrix",
		region: ["header", "footer"].includes(item.region) ? item.region : "body",
		heading: String(item.heading || "").trim(),
		show_heading: item.show_heading !== false,
		show_matrix: item.show_matrix !== false,
		span_full_width: item.span_full_width !== false,
		x: clamp(toNumber(item.x), 0, metrics.contentWidth),
		y: Math.max(toNumber(item.y), 0),
		width: item.span_full_width === false ? width : metrics.contentWidth,
		height,
		rows,
		cols,
		row_height: rowHeight,
		heading_height: headingHeight,
		style: clone(item.style || {}),
		cells,
	};
}

export function createMatrixPlacement(page = {}, position = {}) {
	const metrics = getPageMetrics(page);
	const rows = clamp(toInteger(position.rows, MATRIX_DEFAULT_ROWS), MATRIX_MIN_ROWS, 24);
	const cols = clamp(toInteger(position.cols, MATRIX_DEFAULT_COLS), MATRIX_MIN_COLS, 12);
	const rowHeight = clamp(toNumber(position.row_height, MATRIX_DEFAULT_ROW_HEIGHT), 20, 120);
	const headingHeight = clamp(toNumber(position.heading_height, MATRIX_DEFAULT_HEADING_HEIGHT), 16, 80);
	const width = clamp(toNumber(position.width, metrics.contentWidth || 420), 160, metrics.contentWidth || 9999);
	const height = getMatrixHeight({
		rows,
		row_height: rowHeight,
		heading_height: headingHeight,
		show_heading: position.show_heading,
	});

	return normalizeMatrixItem(
		{
			id: uid(),
			heading: String(position.heading || "").trim(),
			region: ["header", "footer"].includes(position.region) ? position.region : "body",
			show_heading: position.show_heading !== false,
			show_matrix: position.show_matrix !== false,
			span_full_width: position.span_full_width !== false,
			x: clamp(toNumber(position.x, 0), 0, Math.max(metrics.contentWidth - width, 0)),
			y: Math.max(toNumber(position.y, 0), 0),
			width: position.span_full_width === false ? width : metrics.contentWidth,
			height,
			rows,
			cols,
			row_height: rowHeight,
			heading_height: headingHeight,
			style: {},
			cells: [],
		},
		page
	);
}

export function resizeMatrixCells(matrix = {}, nextRows, nextCols) {
	const rows = clamp(toInteger(nextRows, MATRIX_DEFAULT_ROWS), MATRIX_MIN_ROWS, 24);
	const cols = clamp(toInteger(nextCols, MATRIX_DEFAULT_COLS), MATRIX_MIN_COLS, 12);
	const cells = buildMatrixCells(rows, cols, Array.isArray(matrix.cells) ? matrix.cells : []);
	const updated = {
		...matrix,
		rows,
		cols,
		cells,
	};
	updated.height = getMatrixHeight(updated);
	return updated;
}

export function assignMatrixCell(matrix = {}, row = 0, col = 0, field = {}) {
	const targetRow = clamp(toInteger(row), 0, Math.max(toInteger(matrix.rows, MATRIX_DEFAULT_ROWS) - 1, 0));
	const targetCol = clamp(toInteger(col), 0, Math.max(toInteger(matrix.cols, MATRIX_DEFAULT_COLS) - 1, 0));
	const cellKey = `${targetRow}:${targetCol}`;
	const cells = buildMatrixCells(
		toInteger(matrix.rows, MATRIX_DEFAULT_ROWS),
		toInteger(matrix.cols, MATRIX_DEFAULT_COLS),
		Array.isArray(matrix.cells) ? matrix.cells : []
	).map((cell) => {
		if (cell.key !== cellKey) return cell;
		return normalizeMatrixCell(
			{
				...cell,
				fieldname: field.fieldname,
				label: field.label || field.fieldname,
				static_text: "",
				show_label: true,
				row_span: cell.row_span || 1,
				col_span: cell.col_span || 1,
			},
			cell.row,
			cell.col
		);
	});

	return {
		...matrix,
		cells,
		height: getMatrixHeight(matrix),
	};
}

export function clearFieldFromLayout(layoutItems = [], fieldname = "") {
	const targetFieldname = String(fieldname || "").trim();
	if (!targetFieldname) return layoutItems;

	return layoutItems.flatMap((item) => {
		if (item.kind === "matrix" && Array.isArray(item.cells)) {
			return [{
				...item,
				cells: item.cells.map((cell) => {
					if (cell.fieldname !== targetFieldname) return cell;
					return normalizeMatrixCell(
						{
							...cell,
							fieldname: "",
							label: "",
							static_text: "",
							show_label: true,
						},
						cell.row,
						cell.col
					);
				}),
			}];
		}
		if (item.fieldname !== targetFieldname) return [item];
		return [];
	});
}

export function createPlacement(field = {}, page = {}, position = {}) {
	const metrics = getPageMetrics(page);
	const fieldtype = String(field.fieldtype || "").trim();
	const defaults = getPlacementDefaults(fieldtype);
	const width = clamp(toNumber(position.width, defaults.width), 40, metrics.contentWidth || 9999);
	const height = clamp(toNumber(position.height, defaults.height), 18, metrics.contentHeight || 9999);
	const x = clamp(toNumber(position.x, 24), 0, Math.max(metrics.contentWidth - width, 0));
	const y = Math.max(toNumber(position.y, 24), 0);

	return normalizePlacement(
		{
			id: uid(),
			kind: "field",
			fieldname: field.fieldname,
			fieldtype,
			label: field.label || field.fieldname,
			show_label: true,
			x,
			y,
			width,
			height,
			font_size: 11,
			align: "left",
			style: {},
		},
		page
	);
}

export function normalizeLayout(layout = {}, page = {}) {
	const items = Array.isArray(layout.items) ? layout.items : [];
	return {
		items: items
			.map((item) => {
				if (item?.kind === "matrix" || Array.isArray(item?.cells)) {
					return normalizeMatrixItem(item, page);
				}
				return normalizePlacement(item, page);
			})
			.filter((item) => item.kind === "matrix" || item.fieldname),
	};
}

export function createPreviewPageStyle(page = {}) {
	const metrics = getPageMetrics(page);
	return {
		width: `${metrics.pageWidth}px`,
		height: `${metrics.pageHeight}px`,
	};
}

export function createPreviewContentStyle(page = {}) {
	const metrics = getPageMetrics(page);
	return {
		left: `${metrics.marginLeft}px`,
		top: `${metrics.marginTop}px`,
		width: `${metrics.contentWidth}px`,
		height: `${metrics.contentHeight}px`,
	};
}

export function getLayoutBottom(items = [], { excludeKinds = [], excludeRegions = [] } = {}) {
	return (Array.isArray(items) ? items : []).reduce((maxBottom, item) => {
		if (!item) return maxBottom;
		if (excludeKinds.includes(item.kind)) return maxBottom;
		if (excludeRegions.includes(item.region)) return maxBottom;
		const top = Math.max(toNumber(item.y), 0);
		const height = Math.max(toNumber(item.height, 0), 0);
		return Math.max(maxBottom, top + height);
	}, 0);
}
