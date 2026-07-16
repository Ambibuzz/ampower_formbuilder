<template>
	<div class="pb-report-shell">
		<div class="pb-report-page is-last-page" :style="pageStyle">
			<div class="pb-report-content" :style="contentStyle">
				<template v-for="(item, index) in flowItems" :key="item.id">
					<div
						v-if="item.kind === 'matrix'"
						class="pb-report-block pb-report-matrix"
						:id="item.region === 'header' ? 'header-html' : item.region === 'footer' ? 'footer-html' : null"
						:class="[
							{ 'is-plain': !item.show_matrix },
							item.region === 'header' ? 'header-html letter-head' : '',
							item.region === 'footer' ? 'footer-html' : '',
						]"
						:style="itemStyle(item)"
					>
						<table v-if="item.show_heading" class="pb-report-matrix-heading-table">
							<tbody>
								<tr>
									<th class="pb-report-matrix-heading" :colspan="Math.max(Number(item.cols || 1), 1)">
										{{ item.heading || __("Matrix") }}
									</th>
								</tr>
							</tbody>
						</table>
						<table class="pb-report-matrix-table">
							<tbody v-if="item.matrixRows?.length">
								<tr v-for="row in item.matrixRows" :key="row.index">
									<td
										v-for="cell in row.cells"
										:key="cell.key"
										class="pb-report-matrix-cell"
										:class="{ filled: Boolean(cell.fieldname || cell.static_text), 'show-borders': item.show_matrix }"
										:rowspan="Math.max(Number(cell.row_span || 1), 1)"
										:colspan="Math.max(Number(cell.col_span || 1), 1)"
									>
										<div class="pb-report-matrix-cell-body" :class="{ filled: Boolean(cell.fieldname || cell.static_text) }">
											<template v-if="cell.fieldname">
												<div v-if="cell.show_label" class="pb-report-label">
													{{ cell.label }}
												</div>
												<div v-if="cell.isImageField" class="pb-report-image-wrap">
													<img
														v-if="cell.value"
														class="pb-report-image"
														:src="cell.value"
														:alt="cell.label || cell.fieldname || __('Image')"
													>
													<span v-else class="pb-report-value pb-report-image-empty">{{ __("No image") }}</span>
												</div>
												<div v-else class="pb-report-value" :style="{ textAlign: cell.align }">
													{{ cell.value }}
												</div>
											</template>
											<template v-else-if="cell.static_text">
												<div class="pb-report-value" :style="{ textAlign: cell.align }">
													{{ cell.static_text }}
												</div>
											</template>
										</div>
									</td>
								</tr>
							</tbody>
						</table>
					</div>
					<div v-else-if="item.isTableField" class="pb-report-block pb-report-table-item" :id="item.region === 'header' ? 'header-html' : item.region === 'footer' ? 'footer-html' : null" :class="[
						item.region === 'header' ? 'header-html letter-head' : '',
						item.region === 'footer' ? 'footer-html' : '',
					]" :style="itemStyle(item)">
						<div v-if="item.show_label" class="pb-report-label">
							{{ item.label }}
						</div>
						<div class="pb-report-table-wrap">
							<table class="pb-report-table">
								<thead v-if="item.tableConfig.columns.length">
									<tr>
										<th v-for="column in item.tableConfig.columns" :key="column.id || column.fieldname">
											{{ column.label || column.fieldname }}
										</th>
									</tr>
								</thead>
								<tbody>
									<tr v-for="(row, rowIndex) in item.tableRows" :key="row.id || rowIndex">
										<td v-for="column in item.tableConfig.columns" :key="column.id || column.fieldname">
											<template v-if="isImageField(column.fieldtype)">
												<img
													v-if="getImageValue(row[column.fieldname])"
													class="pb-report-table-image"
													:src="getImageValue(row[column.fieldname])"
													:alt="column.label || column.fieldname || __('Image')"
												>
												<span v-else class="pb-report-table-empty">-</span>
											</template>
											<template v-else>
												{{ formatSubmissionValue(row[column.fieldname], "-", column.fieldtype) }}
											</template>
										</td>
									</tr>
								</tbody>
							</table>
							<div v-if="!item.tableRows.length" class="pb-report-table-empty-state">
								{{ __("No rows") }}
							</div>
						</div>
					</div>
					<div
						v-else
						class="pb-report-block pb-report-item"
						:id="item.region === 'header' ? 'header-html' : item.region === 'footer' ? 'footer-html' : null"
						:class="[
							item.region === 'header' ? 'header-html letter-head' : '',
							item.region === 'footer' ? 'footer-html' : '',
						]"
						:style="itemStyle(item)"
					>
						<div v-if="item.show_label && item.label" class="pb-report-label">
							{{ item.label }}
						</div>
						<div v-if="item.isImageField" class="pb-report-image-wrap">
							<img
								v-if="item.value"
								class="pb-report-image"
								:src="item.value"
								:alt="item.label || item.fieldname || __('Image')"
							>
							<span v-else class="pb-report-value pb-report-image-empty">{{ __("No image") }}</span>
						</div>
						<div v-else-if="item.value !== null && item.value !== undefined && item.value !== ''" class="pb-report-value" :style="{ textAlign: item.align }">
							{{ item.value }}
						</div>
						<div v-else class="pb-report-value"></div>
					</div>
					<div v-if="index < flowItems.length - 1" class="pb-report-spacer" aria-hidden="true"></div>
				</template>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { formatSubmissionValue, schemaToSections, flattenFields, getTableConfig, normalizeTableValue } from "../viewerUtils.js";
import { getPageMetrics, getVisibleMatrixCells, normalizeLayout, toNumber } from "./utils.js";

const IMAGE_FIELD_TYPES = new Set(["Attach Image", "Image", "Signature"]);
const TABLE_FIELD_TYPES = new Set(["Table", "Mixed Table"]);
const REPORT_ELEMENT_GAP = 5;
const REPORT_PAGE_EDGE_GAP = 10;
const REPORT_PAGE_HEIGHT_SAFETY = 10;

const props = defineProps({
	format: {
		type: Object,
		default: null,
	},
	template: {
		type: Object,
		default: null,
	},
	submission: {
		type: Object,
		default: null,
	},
});

const fieldMap = computed(() => {
	const templateSchema = props.template?.schema || {};
	const fields = flattenFields(schemaToSections(templateSchema)).filter((field) => {
		return !["Section Break", "Tab Break", "Column Break", "HTML", "Heading"].includes(field.fieldtype);
	});
	return Object.fromEntries(fields.map((field) => [field.fieldname, field]));
});

const pageMetrics = computed(() => getPageMetrics(props.format || {}));
const layout = computed(() => normalizeLayout(props.format?.layout || {}, props.format || {}));

const renderedItems = computed(() =>
	layout.value.items.map((item) => {
		if (item.kind === "matrix") {
			const cells = item.cells.map((cell) => {
				const field = fieldMap.value[cell.fieldname] || {};
				const value = props.submission?.data?.[cell.fieldname];
				return {
					...cell,
					isImageField: IMAGE_FIELD_TYPES.has(field.fieldtype),
					value: cell.fieldname ? normalizeValueForReport(value, field.fieldtype || "") : cell.static_text || "",
				};
			});
			return {
				...item,
				cells,
				matrixRows: buildMatrixRows(cells, item.rows),
			};
		}

		const field = fieldMap.value[item.fieldname] || {};
		const value = props.submission?.data?.[item.fieldname];
		if (TABLE_FIELD_TYPES.has(field.fieldtype)) {
			const tableConfig = getTableConfig(field, item.print_columns);
			const tableRows = normalizeTableValue(field, Array.isArray(value) ? value : []);
			return {
				...item,
				isTableField: true,
				isImageField: false,
				tableConfig,
				tableRows,
				value: tableRows,
			};
		}

		return {
			...item,
			isTableField: false,
			isImageField: IMAGE_FIELD_TYPES.has(field.fieldtype),
			value: normalizeValueForReport(value, field.fieldtype || ""),
		};
	})
);

const flowItems = computed(() => {
	const headerItems = [];
	const bodyItems = [];
	const footerItems = [];

	renderedItems.value.forEach((item) => {
		if (item.kind === "matrix" && item.region === "header") {
			headerItems.push(item);
			return;
		}
		if (item.kind === "matrix" && item.region === "footer") {
			footerItems.push(item);
			return;
		}
		bodyItems.push(item);
	});

	return [...headerItems, ...bodyItems, ...footerItems];
});

const pageStyle = computed(() => ({
	width: "100%",
	height: "auto",
}));
const contentStyle = computed(() => ({
	display: "flex",
	flexDirection: "column",
	gap: "0px",
	width: "100%",
	height: "auto",
}));

function itemStyle(item) {
	const safeStyle = { ...(item.style || {}) };
	delete safeStyle.position;
	delete safeStyle.left;
	delete safeStyle.top;
	delete safeStyle.right;
	delete safeStyle.bottom;
	delete safeStyle.width;
	delete safeStyle.height;
	return {
		width: "100%",
		fontSize: `${toNumber(item.font_size, 11)}px`,
		height: "auto",
		margin: 0,
		...safeStyle,
	};
}

function normalizeValueForReport(value, fieldtype = "") {
	if (IMAGE_FIELD_TYPES.has(fieldtype)) {
		return getImageValue(value);
	}
	return formatSubmissionValue(value, "", fieldtype);
}

function isImageField(fieldtype = "") {
	return IMAGE_FIELD_TYPES.has(fieldtype);
}

function getImageValue(value) {
	if (value === null || value === undefined || value === "") return "";
	if (Array.isArray(value)) return getImageValue(value[0]);
	if (typeof value === "string") return value;
	if (typeof value === "object") {
		return value.file_url || value.url || value.src || value.name || "";
	}
	return String(value);
}

function visibleMatrixCells(cells) {
	return getVisibleMatrixCells(cells);
}

function estimateTextLines(text = "", widthPx = 0) {
	const normalized = String(text || "").replace(/\s+/g, " ").trim();
	if (!normalized) return 1;
	const charsPerLine = Math.max(Math.floor(Math.max(widthPx, 40) / 7), 8);
	return normalized.split(/\r?\n/).reduce((lineCount, line) => {
		return lineCount + Math.max(Math.ceil(line.length / charsPerLine), 1);
	}, 0);
}

function estimateTextBlockHeight(text = "", widthPx = 0, { lineHeight = 14, paddingY = 12, minHeight = 0 } = {}) {
	return Math.max(minHeight, paddingY + (estimateTextLines(text, widthPx) * lineHeight));
}

function estimateMatrixCellHeight(item = {}, cell = {}) {
	const rowHeight = Math.max(toNumber(item.row_height, 34), 20);
	const cols = Math.max(toNumber(item.cols, 1), 1);
	const cellWidth = Math.max((toNumber(item.width, 0) / cols) * Math.max(toNumber(cell.col_span, 1), 1), 40);
	const content = cell.fieldname ? (cell.value ?? cell.label ?? "") : (cell.static_text ?? "");
	const baseHeight = cell.isImageField
		? 88
		: estimateTextBlockHeight(content, cellWidth, {
			lineHeight: 14,
			paddingY: cell.show_label && (cell.fieldname || cell.static_text) ? 16 : 8,
			minHeight: 18,
		});
	return Math.max(rowHeight, Math.ceil(baseHeight / Math.max(toNumber(cell.row_span, 1), 1)));
}

function estimateMatrixRowHeight(item = {}, row = {}) {
	const rowHeight = Math.max(toNumber(item.row_height, 34), 20);
	const cells = Array.isArray(row.cells) ? row.cells : [];
	if (!cells.length) return rowHeight;
	return cells.reduce((maxHeight, cell) => Math.max(maxHeight, estimateMatrixCellHeight(item, cell)), rowHeight);
}

function getMatrixBandMetrics(items = [], region = "") {
	const regionItems = (Array.isArray(items) ? items : []).filter((item) => item.kind === "matrix" && item.region === region);
	if (!regionItems.length) {
		return {
			items: [],
			top: 0,
			bottom: 0,
			height: 0,
		};
	}

	const top = Math.min(...regionItems.map((item) => Math.max(toNumber(item.y, 0), 0)));
	const bottom = Math.max(...regionItems.map((item) => Math.max(toNumber(item.y, 0), 0) + Math.max(toNumber(item.height, 0), 0)));
	return {
		items: regionItems,
		top,
		bottom,
		height: Math.max(bottom - top, 0),
	};
}

function cloneBandItems(items = [], band = {}, targetTop = 0, pageId = "") {
	return (Array.isArray(items) ? items : []).map((item, index) => ({
		...item,
		id: pageId ? `${pageId}__${item.id || index}` : `${item.id || index}`,
		x: Math.max(toNumber(item.x, 0) + REPORT_PAGE_EDGE_GAP, REPORT_PAGE_EDGE_GAP),
		y: targetTop + Math.max(toNumber(item.y, 0) - toNumber(band.top, 0), 0),
		width: Math.max(toNumber(item.width, 0) - (REPORT_PAGE_EDGE_GAP * 2), 0),
	}));
}

function buildMatrixRows(cells = [], rowCount = 0) {
	const totalRows = Math.max(toNumber(rowCount, 0), 1);
	const rows = Array.from({ length: totalRows }, (_, index) => ({
		index,
		cells: [],
	}));

	visibleMatrixCells(cells).forEach((cell) => {
		const row = rows[cell.row];
		if (!row) return;
		row.cells.push({
			...cell,
			row_span: Math.max(Number(cell.row_span || 1), 1),
			col_span: Math.max(Number(cell.col_span || 1), 1),
		});
	});

	rows.forEach((row) => {
		row.cells.sort((left, right) => Number(left.col || 0) - Number(right.col || 0));
	});

	return rows;
}

function getMatrixRowBreaks(rows = []) {
	const safeBreaks = [];
	let activeSpanEnd = -1;

	rows.forEach((row, rowIndex) => {
		const rowSpanEnd = (row.cells || []).reduce((maxEnd, cell) => {
			const span = Math.max(Number(cell.row_span || 1), 1);
			return Math.max(maxEnd, rowIndex + span - 1);
		}, rowIndex);
		activeSpanEnd = Math.max(activeSpanEnd, rowSpanEnd);
		safeBreaks[rowIndex] = activeSpanEnd <= rowIndex;
	});

	return safeBreaks;
}

function sliceMatrixRows(rows = [], startIndex = 0, endIndex = 0) {
	const segmentRows = rows.slice(startIndex, endIndex + 1);
	return segmentRows.map((row, rowOffset) => {
		const rowsRemaining = segmentRows.length - rowOffset;
		return {
			index: row.index,
			cells: (row.cells || []).map((cell) => ({
				...cell,
				row_span: Math.max(1, Math.min(Math.max(Number(cell.row_span || 1), 1), rowsRemaining)),
			})),
		};
	});
}

function estimateMatrixHeight(item = {}) {
	const headingHeight = item.show_heading === false ? 0 : Math.max(toNumber(item.heading_height, 28), 16);
	const rows = Array.isArray(item.matrixRows) ? item.matrixRows : buildMatrixRows(item.cells, item.rows);
	const bodyHeight = rows.reduce((sum, row) => sum + estimateMatrixRowHeight(item, row), 0);
	return 20 + headingHeight + bodyHeight + (item.show_heading === false ? 0 : REPORT_ELEMENT_GAP);
}

function getMatrixMinimumHeight(item = {}) {
	const headingHeight = item.show_heading === false ? 0 : Math.max(toNumber(item.heading_height, 28), 16);
	const rows = Array.isArray(item.matrixRows) ? item.matrixRows : buildMatrixRows(item.cells, item.rows);
	const firstRowHeight = rows.length ? estimateMatrixRowHeight(item, rows[0]) : Math.max(toNumber(item.row_height, 34), 20);
	return 20 + headingHeight + firstRowHeight + (item.show_heading === false ? 0 : REPORT_ELEMENT_GAP);
}

function paginateMatrixItem(item = {}, firstPageAvailableHeight = 0, pageHeight = 0, firstPageOffset = 0, repeatPageOffset = REPORT_ELEMENT_GAP) {
	const rows = Array.isArray(item.matrixRows) ? item.matrixRows : buildMatrixRows(item.cells, item.rows);
	if (!rows.length) {
		return [item];
	}

	const segments = [];
	let index = 0;

	while (index < rows.length) {
		const availableHeight = segments.length === 0 ? firstPageAvailableHeight : pageHeight;
		const headingHeight = item.show_heading === false ? 0 : Math.max(toNumber(item.heading_height, 28), 16);
		let usedHeight = 20 + headingHeight + (item.show_heading === false ? 0 : REPORT_ELEMENT_GAP);
		let endIndex = index - 1;

		while (endIndex + 1 < rows.length) {
			const nextRowHeight = estimateMatrixRowHeight(item, rows[endIndex + 1]);
			if (endIndex >= index && usedHeight + nextRowHeight > availableHeight) {
				break;
			}
			if (endIndex < index && usedHeight + nextRowHeight > availableHeight) {
				endIndex = index;
				break;
			}
			endIndex += 1;
			usedHeight += nextRowHeight;
		}

		segments.push({
			...item,
			id: `${item.id}__segment_${segments.length + 1}`,
			matrixRows: sliceMatrixRows(rows, index, endIndex),
			matrixSegmentIndex: segments.length,
			matrixSegmentCount: 0,
			y: segments.length === 0 ? firstPageOffset : repeatPageOffset,
		});

		index = endIndex + 1;
	}

	const segmentCount = segments.length;
	segments.forEach((segment) => {
		segment.matrixSegmentCount = segmentCount;
	});

	return segments;
}

function paginateRenderedItems(items = [], metrics = {}) {
	const pageHeight = Math.max(toNumber(metrics.contentHeight) - REPORT_PAGE_HEIGHT_SAFETY, 0);
	if (!pageHeight) {
		return [{ id: "page-1", items: Array.isArray(items) ? items : [] }];
	}

	const headerBand = getMatrixBandMetrics(items, "header");
	const footerBand = getMatrixBandMetrics(items, "footer");
	const bodyItems = [...(items || [])]
		.filter((item) => !(item.kind === "matrix" && ["header", "footer"].includes(item.region)))
		.sort((left, right) => {
			const topDiff = toNumber(left.y) - toNumber(right.y);
			if (topDiff) return topDiff;
			return toNumber(left.x) - toNumber(right.x);
		});

	const headerTop = headerBand.items.length ? REPORT_PAGE_EDGE_GAP : 0;
	const footerTop = footerBand.items.length ? Math.max(pageHeight - footerBand.height - REPORT_PAGE_EDGE_GAP, 0) : pageHeight;
	const bodyTop = headerBand.items.length ? headerTop + headerBand.height + REPORT_ELEMENT_GAP : REPORT_PAGE_EDGE_GAP;
	const bodyBottom = footerBand.items.length ? Math.max(footerTop - REPORT_ELEMENT_GAP, bodyTop) : pageHeight;
	const bodyPageHeight = Math.max(bodyBottom - bodyTop, 0);

	const sortedItems = bodyItems;
	const pages = [];
	let pageCounter = 0;
	let currentPage = createPage(`page-${++pageCounter}`);
	let cursorY = bodyTop;

	const flushPage = () => {
		if (currentPage.items.length) {
			pages.push(currentPage);
		}
		currentPage = createPage(`page-${++pageCounter}`);
		cursorY = bodyTop;
	};

	sortedItems.forEach((item) => {
		const itemHeight = estimateItemHeight(item);
		const availableHeight = Math.max(bodyBottom - cursorY, 0);

		if ((item.isTableField || item.kind === "matrix") && itemHeight > bodyPageHeight) {
			const minHeight = item.kind === "matrix" ? getMatrixMinimumHeight(item) : getTableMinimumHeight(item);
			if (currentPage.items.length && availableHeight < minHeight) {
				flushPage();
			}

			const firstPageAvailableHeight = currentPage.items.length ? Math.max(bodyBottom - cursorY, 0) : bodyPageHeight;
			const paginateItem = item.kind === "matrix" ? paginateMatrixItem : paginateTableItem;
			const segments = paginateItem(item, firstPageAvailableHeight, bodyPageHeight, cursorY, bodyTop);

			segments.forEach((segment) => {
				currentPage.items.push(segment);
				flushPage();
			});

			return;
		}

		if (currentPage.items.length && cursorY > bodyTop && cursorY + itemHeight > bodyBottom) {
			flushPage();
		}

		currentPage.items.push({
			...item,
			y: cursorY,
		});
		cursorY += itemHeight + REPORT_ELEMENT_GAP;
	});

	if (currentPage.items.length) {
		pages.push(currentPage);
	}

	if (!pages.length) {
		pages.push(createPage("page-1"));
	}

	return pages.map((page, index) => {
		const pageId = page.id || `page-${index + 1}`;
		return {
			...page,
			id: pageId,
			items: [
				...cloneBandItems(headerBand.items, headerBand, headerTop, `${pageId}__header`),
				...page.items,
				...cloneBandItems(footerBand.items, footerBand, footerTop, `${pageId}__footer`),
			],
		};
	});
}

function createPage(id) {
	return {
		id,
		items: [],
	};
}

function estimateItemHeight(item = {}) {
	if (item.isTableField) {
		return estimateTableHeight(item);
	}
	if (item.kind === "matrix") {
		return estimateMatrixHeight(item);
	}
	return Math.max(toNumber(item.height, 0), 0);
}

function estimateTableHeight(item = {}) {
	const labelHeight = item.show_label ? 22 : 0;
	const headerHeight = Array.isArray(item.tableConfig?.columns) && item.tableConfig.columns.length ? 34 : 0;
	const verticalPadding = 18;
	const rows = Array.isArray(item.tableRows) ? item.tableRows : [];
	const bodyHeight = rows.length
		? rows.reduce((sum, row) => sum + estimateTableRowHeight(item, row), 0)
		: 40;
	return labelHeight + headerHeight + bodyHeight + verticalPadding;
}

function getTableMinimumHeight(item = {}) {
	const labelHeight = item.show_label ? 22 : 0;
	const headerHeight = Array.isArray(item.tableConfig?.columns) && item.tableConfig.columns.length ? 34 : 0;
	const verticalPadding = 18;
	const hasImageColumn = Array.isArray(item.tableConfig?.columns)
		? item.tableConfig.columns.some((column) => IMAGE_FIELD_TYPES.has(column.fieldtype))
		: false;
	const firstRowHeight = Array.isArray(item.tableRows) && item.tableRows.length
		? estimateTableRowHeight(item, item.tableRows[0], hasImageColumn)
		: (hasImageColumn ? 100 : 38);
	return labelHeight + headerHeight + firstRowHeight + verticalPadding;
}

function estimateTableRowHeight(item = {}, row = {}, hasImageColumn = false) {
	const columns = Array.isArray(item.tableConfig?.columns) ? item.tableConfig.columns : [];
	const rowWidth = Math.max(toNumber(item.width, 0), 160);
	const columnWidth = columns.length ? rowWidth / columns.length : rowWidth;

	return columns.reduce((maxHeight, column) => {
		if (IMAGE_FIELD_TYPES.has(column.fieldtype)) {
			return Math.max(maxHeight, 100);
		}

		const rawValue = row?.[column.fieldname];
		const content = rawValue === null || rawValue === undefined || rawValue === "" ? "-" : String(rawValue);
		return Math.max(maxHeight, estimateTextBlockHeight(content, columnWidth, {
			lineHeight: 14,
			paddingY: 12,
			minHeight: 20,
		}));
	}, hasImageColumn ? 100 : 38);
}

function paginateTableItem(item = {}, firstPageAvailableHeight = 0, pageHeight = 0, firstPageOffset = 0, repeatPageOffset = REPORT_ELEMENT_GAP) {
	const rows = Array.isArray(item.tableRows) ? item.tableRows : [];
	if (!rows.length) {
		return [item];
	}

	const segments = [];
	let index = 0;

	while (index < rows.length) {
		const availableHeight = segments.length === 0 ? firstPageAvailableHeight : pageHeight;
		const labelHeight = item.show_label ? 22 : 0;
		const headerHeight = Array.isArray(item.tableConfig?.columns) && item.tableConfig.columns.length ? 34 : 0;
		const verticalPadding = 18;
		const hasImageColumn = Array.isArray(item.tableConfig?.columns)
			? item.tableConfig.columns.some((column) => IMAGE_FIELD_TYPES.has(column.fieldtype))
			: false;
		let usedHeight = labelHeight + headerHeight + verticalPadding;
		const segmentRows = [];

		while (index + segmentRows.length < rows.length) {
			const nextRow = rows[index + segmentRows.length];
			const nextRowHeight = estimateTableRowHeight(item, nextRow, hasImageColumn);
			if (segmentRows.length > 0 && usedHeight + nextRowHeight > availableHeight) {
				break;
			}
			if (segmentRows.length === 0 && usedHeight + nextRowHeight > availableHeight) {
				segmentRows.push(nextRow);
				break;
			}
			segmentRows.push(nextRow);
			usedHeight += nextRowHeight;
		}

		segments.push({
			...item,
			id: `${item.id}__segment_${segments.length + 1}`,
			tableRows: segmentRows,
			tableSegmentIndex: segments.length,
			tableSegmentCount: 0,
			y: segments.length === 0 ? firstPageOffset : repeatPageOffset,
		});
		index += segmentRows.length;
	}

	const segmentCount = segments.length;
	segments.forEach((segment) => {
		segment.tableSegmentCount = segmentCount;
	});

	return segments;
}
</script>

<style scoped>
.pb-report-shell {
	display: flex;
	justify-content: center;
	flex-direction: column;
	width: 100%;
	padding: 12px;
	gap: 16px;
}

.pb-report-page {
	position: relative;
	background: white;
	box-shadow: 0 20px 60px rgba(14, 23, 38, 0.12);
	border: 1px solid rgba(15, 23, 42, 0.12);
	overflow: hidden;
}

.pb-report-page.is-last-page {
	margin-bottom: 0;
}

.pb-report-content {
	position: absolute;
	box-sizing: border-box;
}

.pb-report-item {
	position: absolute;
	box-sizing: border-box;
	display: flex;
	flex-direction: column;
	justify-content: flex-start;
	gap: 5px;
	overflow: hidden;
	color: #0f172a;
}

.pb-report-label {
	font-size: 0.85em;
	font-weight: 600;
	color: #64748b;
	line-height: 1.2;
}

.pb-report-value {
	font-weight: 500;
	line-height: 1.25;
	word-break: break-word;
	white-space: pre-wrap;
}

.pb-report-image-wrap {
	display: flex;
	align-items: flex-start;
	justify-content: flex-start;
}

.pb-report-image {
	display: block;
	max-width: 100%;
	max-height: 140px;
	object-fit: contain;
	border-radius: 8px;
	border: 1px solid rgba(15, 23, 42, 0.12);
	background: #fff;
}

.pb-report-image-empty {
	color: #94a3b8;
	font-style: italic;
}

.pb-report-table-item {
	display: flex;
	flex-direction: column;
	gap: 8px;
}

.pb-report-table-wrap {
	overflow: auto;
	max-width: 100%;
	border: 1px solid #000;
	border-radius: 0;
	background: #fff;
}

.pb-report-table {
	width: 100%;
	border-collapse: collapse;
	font-size: 12px;
	color: #0f172a;
	page-break-inside: auto;
	break-inside: auto;
}

.pb-report-table thead {
	display: table-header-group;
}

.pb-report-table tbody {
	display: table-row-group;
}

.pb-report-table th,
.pb-report-table td {
	padding: 8px 10px;
	border-right: 1px solid #000;
	border-bottom: 1px solid #000;
	vertical-align: top;
}

.pb-report-table th {
	font-size: 11px;
	font-weight: 700;
	color: #111;
	background: #f2f2f2;
	text-align: center;
}

.pb-report-table tr:last-child td {
	border-bottom: 0;
}

.pb-report-table th:last-child,
.pb-report-table td:last-child {
	border-right: 0;
}

.pb-report-table tr {
	break-inside: avoid;
	page-break-inside: avoid;
}

.pb-report-table-image {
	display: block;
	max-width: 88px;
	max-height: 88px;
	object-fit: contain;
	border-radius: 6px;
}

.pb-report-table-empty,
.pb-report-table-empty-state {
	color: #94a3b8;
	font-style: italic;
}

.pb-report-matrix {
	position: absolute;
	box-sizing: border-box;
	display: flex;
	flex-direction: column;
	gap: 5px;
	padding: 0;
	color: #0f172a;
	background: #fff;
	border: 0;
	border-radius: 0;
	overflow: hidden;
}

.pb-report-matrix-heading-table {
	width: 100%;
	border-collapse: collapse;
	table-layout: fixed;
	font-size: 12px;
	color: #0f172a;
	background: transparent;
	page-break-inside: avoid;
	break-inside: avoid;
}

.pb-report-matrix-heading-table tbody {
	display: table-row-group;
}

.pb-report-matrix-heading-table th {
	padding: 6px 8px;
	border: 1px solid #000;
	font-size: 13px;
	font-weight: 700;
	color: #111;
	background: #f2f2f2;
	text-align: center;
}

.pb-report-matrix-table {
	width: 100%;
	border-collapse: collapse;
	table-layout: fixed;
	font-size: 12px;
	color: #0f172a;
	background: transparent;
	page-break-inside: auto;
	break-inside: auto;
}

.pb-report-matrix-table tbody {
	display: table-row-group;
}

.pb-report-matrix-table th,
.pb-report-matrix-table td {
	padding: 6px 8px;
	border-right: 1px solid #000;
	border-bottom: 1px solid #000;
	vertical-align: top;
}

.pb-report-matrix-table th {
	font-size: 13px;
	font-weight: 700;
	color: #111;
	background: #f2f2f2;
	text-align: center;
}

.pb-report-matrix-table tr:last-child td {
	border-bottom: 0;
}

.pb-report-matrix-table th:last-child,
.pb-report-matrix-table td:last-child {
	border-right: 0;
}

.pb-report-matrix-table tr {
	break-inside: avoid;
	page-break-inside: avoid;
}

.pb-report-matrix.is-plain {
	background: transparent;
	border: 0;
	padding: 0;
	overflow: visible;
}

.pb-report-matrix.is-plain .pb-report-matrix-heading-table,
.pb-report-matrix.is-plain .pb-report-matrix-table {
	background: transparent;
	border-color: transparent;
}

.pb-report-matrix.is-plain .pb-report-matrix-heading-table th,
.pb-report-matrix.is-plain .pb-report-matrix-table th,
.pb-report-matrix.is-plain .pb-report-matrix-table td {
	background: transparent;
	border-color: transparent;
	padding-left: 0;
	padding-right: 0;
}

.pb-report-matrix-heading {
	font-size: 13px;
	font-weight: 700;
	color: #0f172a;
	line-height: 1.2;
}

.pb-report-matrix-cell {
	box-sizing: border-box;
	min-width: 0;
	min-height: 0;
	overflow: hidden;
}

.pb-report-matrix-cell.show-borders {
	border-right: 1px solid rgba(148, 163, 184, 0.35);
	border-bottom: 1px solid rgba(148, 163, 184, 0.35);
}

.pb-report-matrix-cell-body {
	min-width: 0;
	min-height: 0;
}

.pb-report-matrix-cell-body.filled {
	display: flex;
	flex-direction: column;
	gap: 5px;
}

@media print {
	.pb-report-shell {
		padding: 0;
		gap: 0;
		display: block;
	}

	.pb-report-page {
		page-break-after: always;
		break-after: page;
		box-shadow: none;
		border: 0;
		overflow: visible;
		margin: 0;
	}

	.pb-report-page.is-last-page {
		page-break-after: auto;
		break-after: auto;
	}

	.pb-report-content {
		position: absolute;
		overflow: visible;
	}

	.pb-report-item,
	.pb-report-matrix,
	.pb-report-table-item {
		break-inside: avoid;
		page-break-inside: avoid;
	}

	.pb-report-table-wrap {
		overflow: visible;
	}
}

/* Flow preview overrides */
.pb-report-shell {
	padding: 0;
	gap: 0;
}

.pb-report-page {
	width: 100%;
	background: #fff;
	box-shadow: none;
	border: 0;
	overflow: visible;
	padding: 10px;
	box-sizing: border-box;
}

.pb-report-content {
	position: static;
	display: flex;
	flex-direction: column;
	gap: 0;
	width: 100%;
	height: auto;
	box-sizing: border-box;
}

.pb-report-block,
.pb-report-item,
.pb-report-table-item,
.pb-report-matrix {
	position: static;
	width: 100%;
	box-sizing: border-box;
}

.pb-report-block,
.pb-report-item,
.pb-report-table-item,
.pb-report-matrix,
.pb-report-table-wrap,
.pb-report-image-wrap {
	margin: 0;
}

.pb-report-item {
	display: flex;
	flex-direction: column;
	gap: 5px;
}

.pb-report-table-item {
	display: flex;
	flex-direction: column;
	gap: 5px;
}

.pb-report-spacer {
	flex: 0 0 5px;
	width: 100%;
	height: 5px;
}

.pb-report-matrix {
	display: flex;
	flex-direction: column;
	gap: 5px;
	padding: 0;
	border: 0;
	border-radius: 0;
	background: #fff;
	overflow: visible;
}

.letter-head {
	width: 100%;
}

.footer-html {
	width: 100%;
}

.pb-report-table-wrap {
	max-width: 100%;
	border: 1px solid #000;
	background: #fff;
	overflow: visible;
}

.pb-report-table {
	width: 100%;
	border-collapse: collapse;
	page-break-inside: auto;
	break-inside: auto;
}

.pb-report-table tr,
.pb-report-matrix-table tr {
	break-inside: avoid;
	page-break-inside: avoid;
}

.pb-report-matrix-heading-table,
.pb-report-matrix-table {
	width: 100%;
	border-collapse: collapse;
	table-layout: fixed;
	background: transparent;
	page-break-inside: auto;
	break-inside: auto;
}

.pb-report-table-empty-state {
	padding: 6px 0;
}
</style>
