<template>
	<div class="pb-shell">
		<header class="pb-header">
			<div class="pb-header-main">
				<div class="pb-header-block">
					<div class="pb-kicker">{{ t("Print Builder") }}</div>
					<div class="pb-row">
						<div class="pb-field">
							<span class="pb-label">{{ t("Template") }}</span>
							<LinkControl
								:df="templateDf"
								:model-value="templateName"
								:no_label="true"
								@update:modelValue="setTemplateName"
							/>
						</div>
						<div class="pb-field">
							<span class="pb-label">{{ t("Format Name") }}</span>
							<input
								v-model="formatName"
								class="form-control"
								type="text"
								:placeholder="t('Untitled Format')"
								:disabled="isBusy"
							/>
						</div>
					</div>
				</div>

				<div class="pb-header-block pb-page-grid">
					<div class="pb-field">
						<span class="pb-label">{{ t("Page Width") }}</span>
						<input v-model="pageWidth" class="form-control" type="text" :disabled="isBusy" />
					</div>
					<div class="pb-field">
						<span class="pb-label">{{ t("Page Height") }}</span>
						<input v-model="pageHeight" class="form-control" type="text" :disabled="isBusy" />
					</div>
					<div class="pb-field">
						<span class="pb-label">{{ t("Margin Top") }}</span>
						<input v-model="marginTop" class="form-control" type="text" :disabled="isBusy" />
					</div>
					<div class="pb-field">
						<span class="pb-label">{{ t("Margin Right") }}</span>
						<input v-model="marginRight" class="form-control" type="text" :disabled="isBusy" />
					</div>
					<div class="pb-field">
						<span class="pb-label">{{ t("Margin Bottom") }}</span>
						<input v-model="marginBottom" class="form-control" type="text" :disabled="isBusy" />
					</div>
					<div class="pb-field">
						<span class="pb-label">{{ t("Margin Left") }}</span>
						<input v-model="marginLeft" class="form-control" type="text" :disabled="isBusy" />
					</div>
				</div>
			</div>

			<div class="pb-header-actions">
				<button type="button" class="btn btn-default btn-sm" :disabled="isBusy" @click="toggleSavedFormatsSidebar">
					{{ showSavedFormatsSidebar ? t("Hide Saved") : t("Show Saved") }}
				</button>
				<button type="button" class="btn btn-default btn-sm" :disabled="isBusy" @click="addMatrix('header')">
					{{ t("Add Header") }}
				</button>
				<button type="button" class="btn btn-default btn-sm" :disabled="isBusy" @click="addMatrix">
					{{ t("Add Matrix") }}
				</button>
				<button type="button" class="btn btn-default btn-sm" :disabled="isBusy" @click="addMatrix('footer')">
					{{ t("Add Footer") }}
				</button>
				<button type="button" class="btn btn-default btn-sm" :disabled="isBusy" @click="newFormat">
					{{ t("New") }}
				</button>
				<button type="button" class="btn btn-primary btn-sm" :disabled="isBusy" @click="saveFormat">
					{{ isBusy ? t("Saving...") : t("Save") }}
				</button>
			</div>
		</header>

		<div class="pb-workspace" :class="{ 'sidebar-hidden': !showSavedFormatsSidebar }">
			<aside v-if="showSavedFormatsSidebar" class="pb-sidebar pb-sidebar-left">
				<div class="pb-sidebar-section">
					<div class="pb-section-title">{{ t("Saved Formats") }}</div>
					<div v-if="formatsLoading" class="pb-empty-state">{{ t("Loading...") }}</div>
					<div v-else-if="formatList.length" class="pb-format-list">
						<button
							v-for="item in formatList"
							:key="item.name"
							type="button"
							class="pb-format-item"
							:class="{ active: item.name === activeFormatName }"
							@click="selectSavedFormat(item.name)"
						>
							<span>{{ item.format_name }}</span>
							<small v-if="item.is_default">{{ t("Default") }}</small>
						</button>
					</div>
					<div v-else class="pb-empty-state">{{ t("No print formats yet") }}</div>
				</div>
			</aside>

			<main class="pb-canvas-panel">
				<div class="pb-canvas-shell">
					<div class="pb-canvas-page" :style="pageStyle">
						<div class="pb-canvas-content" ref="contentRef" :style="contentStyle" @dragover.prevent @drop="handleCanvasDrop">
							<template v-for="item in layoutItems" :key="item.id">
									<div
										v-if="item.kind === 'matrix'"
										class="pb-matrix-item"
										:class="matrixItemClass(item)"
										:style="itemStyle(item)"
										draggable="true"
										@dragstart="handleItemDragStart(item, $event)"
										@click.stop="selectItem(item.id)"
									>
										<div v-if="item.show_heading !== false" class="pb-matrix-heading-row">
											<input
												v-model="item.heading"
												class="form-control input-sm pb-matrix-heading-input"
												type="text"
												:disabled="isBusy"
												:placeholder="t('Matrix Heading')"
											/>
											<div class="pb-matrix-meta">
												<span v-if="item.region !== 'body'" class="pb-region-pill">{{ regionLabel(item.region) }}</span>
												<span>{{ item.rows }} x {{ item.cols }}</span>
											</div>
										</div>
										<div
											class="pb-matrix-grid"
											:class="{ 'show-borders': item.show_matrix }"
											:style="matrixGridStyle(item)"
										>
											<div
												v-for="cell in visibleMatrixCells(item.cells)"
												:key="cell.key"
												class="pb-matrix-cell"
												:class="{
													filled: Boolean(cell.fieldname || cell.static_text),
													active: selectedCellKey === cell.key && selectedItemId === item.id,
													'cell-covered': Boolean(cell.covered_by),
												}"
												:style="matrixCellStyle(cell)"
												@dragover.stop.prevent
												@drop.stop="handleMatrixCellDrop(item, cell, $event)"
												@click.stop="selectCell(item.id, cell.key)"
												@dblclick.stop="handleMatrixCellDoubleClick(item, cell)"
											>
												<template v-if="cell.fieldname">
													<div v-if="cell.show_label" class="pb-matrix-cell-label">{{ cell.label }}</div>
													<div class="pb-matrix-cell-value">{{ cell.fieldname }}</div>
												</template>
												<template v-else-if="cell.static_text">
													<div class="pb-matrix-cell-value" :style="{ textAlign: cell.align }">{{ cell.static_text }}</div>
												</template>
												<span v-else class="pb-matrix-cell-placeholder">{{ t("Drop field here") }}</span>
											</div>
										</div>
									</div>
									<div
										v-else-if="isTableFieldItem(item)"
										class="pb-canvas-item pb-canvas-item-table"
										:class="{ active: item.id === selectedItemId }"
										:style="itemStyle(item)"
										draggable="true"
										@click.stop="selectItem(item.id)"
										@dragstart="handleItemDragStart(item, $event)"
									>
										<div class="pb-item-type-badge">{{ t("Table") }}</div>
										<div class="pb-item-label">{{ item.label }}</div>
										<div class="pb-item-table-preview">
											<TablePreview
												:field-type="getItemFieldType(item)"
												:columns="getItemTableConfig(item).columns"
												:row-definitions="getItemTableConfig(item).rows"
												:row-title="getItemTableConfig(item).table_row_title"
											/>
										</div>
									</div>
									<div
										v-else-if="isImageFieldItem(item)"
										class="pb-canvas-item pb-canvas-item-image"
										:class="{ active: item.id === selectedItemId }"
										:style="itemStyle(item)"
										draggable="true"
										@click.stop="selectItem(item.id)"
										@dragstart="handleItemDragStart(item, $event)"
									>
										<div class="pb-item-type-badge">{{ t("Image") }}</div>
										<div class="pb-item-image-preview">
											<div class="pb-item-image-visual">
												<svg viewBox="0 0 24 24" aria-hidden="true">
													<path d="M4 5h16a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Zm0 2v10h16V7H4Zm3 1.5A1.5 1.5 0 1 1 7 10a1.5 1.5 0 0 1 0-1.5Zm-1 6.5 3.25-4 2.5 3 1.75-2.25L19 18H6Z"></path>
												</svg>
											</div>
											<div class="pb-item-image-text">
												<div class="pb-item-label">{{ item.label }}</div>
												<div class="pb-item-value">{{ item.fieldname }}</div>
											</div>
										</div>
									</div>
								<div
									v-else
									class="pb-canvas-item"
									:class="{ active: item.id === selectedItemId }"
									:style="itemStyle(item)"
									draggable="true"
									@dragstart="handleItemDragStart(item, $event)"
									@click.stop="selectItem(item.id)"
								>
									<div v-if="item.show_label" class="pb-item-label">{{ item.label }}</div>
									<div class="pb-item-value">{{ item.fieldname }}</div>
								</div>
							</template>
						</div>
					</div>
				</div>
			</main>

			<aside class="pb-sidebar pb-sidebar-right">
				<div class="pb-sidebar-section">
					<div class="pb-section-title">{{ t("Fields") }}</div>
					<input
						v-model="fieldSearch"
						class="form-control pb-search"
						type="text"
						:placeholder="t('Search fields')"
						:disabled="isBusy"
					/>
					<div v-if="templateFields.length" class="pb-field-list" @dragover.prevent @drop="handleCanvasDrop">
						<button
							v-for="field in filteredFields"
							:key="field.fieldname"
							type="button"
							class="pb-field-item"
							draggable="true"
							@click="addField(field)"
							@dragstart="handleFieldDragStart(field, $event)"
						>
							<span class="pb-field-item-label">{{ field.label }}</span>
							<small>{{ field.fieldtype }}</small>
						</button>
					</div>
					<div v-else class="pb-empty-state">{{ templateName ? t("Loading fields...") : t("Choose a template first") }}</div>
				</div>

				<div class="pb-sidebar-section">
					<div class="pb-section-title">{{ t("Properties") }}</div>
					<div v-if="selectedItem" class="pb-properties">
						<template v-if="selectedItem.kind === 'matrix'">
							<div class="pb-field">
								<span class="pb-label">{{ t("Heading") }}</span>
								<input v-model="selectedItem.heading" class="form-control" type="text" :disabled="isBusy" />
							</div>
							<div class="pb-field">
								<span class="pb-label">{{ t("Region") }}</span>
								<select v-model="selectedItem.region" class="form-control" :disabled="isBusy">
									<option value="body">{{ t("Body") }}</option>
									<option value="header">{{ t("Header") }}</option>
									<option value="footer">{{ t("Footer") }}</option>
								</select>
							</div>
							<label class="pb-check">
								<input v-model="selectedItem.show_matrix" type="checkbox" />
								<span>{{ t("Show Matrix Borders") }}</span>
							</label>
							<label class="pb-check">
								<input v-model="selectedItem.show_heading" type="checkbox" />
								<span>{{ t("Show Heading") }}</span>
							</label>
							<div class="pb-grid-2">
								<div class="pb-field">
									<span class="pb-label">{{ t("Rows") }}</span>
									<input v-model.number="selectedItem.rows" class="form-control" type="number" min="1" :disabled="isBusy" />
								</div>
								<div class="pb-field">
									<span class="pb-label">{{ t("Columns") }}</span>
									<input v-model.number="selectedItem.cols" class="form-control" type="number" min="1" :disabled="isBusy" />
								</div>
								<div class="pb-field">
									<span class="pb-label">{{ t("Row Height") }}</span>
									<input v-model.number="selectedItem.row_height" class="form-control" type="number" min="20" :disabled="isBusy" />
								</div>
								<div class="pb-field">
									<span class="pb-label">{{ t("Heading Height") }}</span>
									<input v-model.number="selectedItem.heading_height" class="form-control" type="number" min="16" :disabled="isBusy" />
								</div>
							</div>
							<div class="pb-actions-inline">
								<button type="button" class="btn btn-default btn-sm" :disabled="isBusy" @click="adjustMatrixRows(1)">
									{{ t("Add Row") }}
								</button>
								<button type="button" class="btn btn-default btn-sm" :disabled="isBusy || selectedItem.rows <= 1" @click="adjustMatrixRows(-1)">
									{{ t("Remove Row") }}
								</button>
								<button type="button" class="btn btn-default btn-sm" :disabled="isBusy" @click="adjustMatrixCols(1)">
									{{ t("Add Column") }}
								</button>
								<button type="button" class="btn btn-default btn-sm" :disabled="isBusy || selectedItem.cols <= 1" @click="adjustMatrixCols(-1)">
									{{ t("Remove Column") }}
								</button>
							</div>
							<div v-if="selectedCell" class="pb-matrix-cell-editor">
								<div class="pb-section-subtitle">
									{{ t("Selected Cell") }}: {{ selectedCell.row + 1 }}, {{ selectedCell.col + 1 }}
								</div>
								<div v-if="!selectedCell.fieldname" class="pb-field">
									<span class="pb-label">{{ t("Static Text") }}</span>
									<input
										v-model="selectedCell.static_text"
										class="form-control"
										type="text"
										:disabled="isBusy"
										:placeholder="t('Double-click a cell to add text')"
									/>
								</div>
								<div class="pb-field">
									<span class="pb-label">{{ t("Label") }}</span>
									<input v-model="selectedCell.label" class="form-control" type="text" :disabled="isBusy" />
								</div>
								<label class="pb-check">
									<input v-model="selectedCell.show_label" type="checkbox" />
									<span>{{ t("Show Label") }}</span>
								</label>
								<div class="pb-grid-2">
									<div class="pb-field">
										<span class="pb-label">{{ t("Align") }}</span>
										<select v-model="selectedCell.align" class="form-control" :disabled="isBusy">
											<option value="left">{{ t("Left") }}</option>
											<option value="center">{{ t("Center") }}</option>
											<option value="right">{{ t("Right") }}</option>
										</select>
									</div>
									<div class="pb-field">
										<span class="pb-label">{{ t("Field") }}</span>
										<input :value="selectedCell.fieldname || t('Empty')" class="form-control" type="text" readonly />
									</div>
									<div class="pb-field">
										<span class="pb-label">{{ t("Row Span") }}</span>
										<input
											v-model.number="selectedCell.row_span"
											class="form-control"
											type="number"
											min="1"
											:disabled="isBusy"
											@input="syncSelectedMatrixCellLayout"
										/>
									</div>
									<div class="pb-field">
										<span class="pb-label">{{ t("Column Span") }}</span>
										<input
											v-model.number="selectedCell.col_span"
											class="form-control"
											type="number"
											min="1"
											:disabled="isBusy"
											@input="syncSelectedMatrixCellLayout"
										/>
									</div>
								</div>
							<div class="pb-actions-inline">
								<button type="button" class="btn btn-default btn-sm" :disabled="isBusy" @click="clearSelectedCell">
									{{ t("Clear Cell") }}
								</button>
								<button type="button" class="btn btn-danger btn-sm" :disabled="isBusy" @click="deleteSelectedMatrix">
									{{ t("Delete Matrix") }}
								</button>
							</div>
						</div>
						</template>
						<template v-else>
							<div class="pb-item-type-row">
								<span class="pb-item-type-badge">{{ getItemFieldType(selectedItem) || t("Field") }}</span>
								<span v-if="isTableFieldItem(selectedItem)" class="pb-item-type-note">{{ t("Table fields render as nested tables in the builder.") }}</span>
								<span v-else-if="isImageFieldItem(selectedItem)" class="pb-item-type-note">{{ t("Image fields render as visual placeholders in the builder.") }}</span>
							</div>
							<div v-if="isTableFieldItem(selectedItem)" class="pb-table-print-columns">
								<div class="pb-section-subtitle">{{ t("Print Columns") }}</div>
								<div class="pb-table-print-actions">
									<button type="button" class="btn btn-default btn-xs" :disabled="isBusy" @click="resetTablePrintColumns(selectedItem)">
										{{ t("Use All") }}
									</button>
									<span class="pb-table-print-help">{{ t("Leave all columns enabled to print everything.") }}</span>
								</div>
								<div v-if="getItemTableConfig(selectedItem).columns.length" class="pb-table-print-list">
									<label
										v-for="column in getItemTableConfig(selectedItem).columns"
										:key="column.id || column.fieldname"
										class="pb-table-print-item"
									>
										<input
											type="checkbox"
											:checked="isTablePrintColumnSelected(selectedItem, column.fieldname)"
											:disabled="isBusy"
											@change="toggleTablePrintColumn(selectedItem, column.fieldname, $event.target.checked)"
										>
										<div class="pb-table-print-item-body">
											<span class="pb-table-print-item-label">{{ column.label || column.fieldname }}</span>
											<span class="pb-table-print-item-meta">{{ column.fieldtype }}</span>
										</div>
									</label>
								</div>
								<div v-else class="pb-empty-state">{{ t("No table columns available") }}</div>
							</div>
							<div class="pb-field">
								<span class="pb-label">{{ t("Label") }}</span>
								<input v-model="selectedItem.label" class="form-control" type="text" :disabled="isBusy" />
							</div>
						<label class="pb-check">
							<input v-model="selectedItem.show_label" type="checkbox" />
							<span>{{ t("Show Label") }}</span>
						</label>
						<div class="pb-grid-2">
							<div class="pb-field">
								<span class="pb-label">{{ t("X") }}</span>
								<input v-model.number="selectedItem.x" class="form-control" type="number" min="0" :disabled="isBusy" />
							</div>
							<div class="pb-field">
								<span class="pb-label">{{ t("Y") }}</span>
								<input v-model.number="selectedItem.y" class="form-control" type="number" min="0" :disabled="isBusy" />
							</div>
							<div class="pb-field">
								<span class="pb-label">{{ t("Width") }}</span>
								<input v-model.number="selectedItem.width" class="form-control" type="number" min="20" :disabled="isBusy" />
							</div>
							<div class="pb-field">
								<span class="pb-label">{{ t("Height") }}</span>
								<input v-model.number="selectedItem.height" class="form-control" type="number" min="16" :disabled="isBusy" />
							</div>
							<div class="pb-field">
								<span class="pb-label">{{ t("Font Size") }}</span>
								<input v-model.number="selectedItem.font_size" class="form-control" type="number" min="8" :disabled="isBusy" />
							</div>
							<div class="pb-field">
								<span class="pb-label">{{ t("Align") }}</span>
								<select v-model="selectedItem.align" class="form-control" :disabled="isBusy">
									<option value="left">{{ t("Left") }}</option>
									<option value="center">{{ t("Center") }}</option>
									<option value="right">{{ t("Right") }}</option>
								</select>
							</div>
						</div>
							<div class="pb-actions-inline">
								<button type="button" class="btn btn-default btn-sm" :disabled="isBusy" @click="duplicateSelected">
									{{ t("Duplicate") }}
								</button>
								<button type="button" class="btn btn-danger btn-sm" :disabled="isBusy" @click="deleteSelected">
									{{ t("Delete") }}
								</button>
							</div>
						</template>
					</div>
					<div v-else class="pb-empty-state">{{ t("Select a field on the canvas") }}</div>
				</div>
			</aside>
		</div>
	</div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { getCachedTemplateSchema } from "../templateCache.js";
import { flattenFields, schemaToSections, getTableConfig } from "../viewerUtils.js";
import TablePreview from "../components/TablePreview.vue";
import { clone, uid } from "../utils.js";
import {
	DEFAULT_PRINT_PAGE,
	LAYOUT_FIELD_TYPES,
	clamp,
	clearFieldFromLayout,
	createMatrixPlacement,
	createPlacement,
	getLayoutBottom,
	getPageMetrics,
	normalizeLayout,
	createPreviewContentStyle,
	createPreviewPageStyle,
	normalizePlacement,
	resizeMatrixCells,
	assignMatrixCell,
	getVisibleMatrixCells,
	TABLE_FIELD_TYPES,
	IMAGE_FIELD_TYPES,
	toNumber,
} from "./utils.js";

const props = defineProps({
	page: { type: Object, default: null },
	templateName: { type: String, default: "" },
	formatName: { type: String, default: "" },
});

const t = window.__ || ((text) => text);
const isBusy = ref(false);
const formatsLoading = ref(false);
const templateDocName = ref("");
const templateLabel = ref("");
const templateDescription = ref("");
const templateSchema = ref({});
const formatList = ref([]);
const activeFormatName = ref("");
const existingFormatName = ref("");
const fieldSearch = ref("");
const layoutItems = ref([]);
const selectedItemId = ref("");
const selectedCellKey = ref("");
const showSavedFormatsSidebar = ref(true);
const contentRef = ref(null);

const formatName = ref("");
const pageWidth = ref(DEFAULT_PRINT_PAGE.page_width);
const pageHeight = ref(DEFAULT_PRINT_PAGE.page_height);
const marginTop = ref(DEFAULT_PRINT_PAGE.margin_top);
const marginRight = ref(DEFAULT_PRINT_PAGE.margin_right);
const marginBottom = ref(DEFAULT_PRINT_PAGE.margin_bottom);
const marginLeft = ref(DEFAULT_PRINT_PAGE.margin_left);

const templateDf = computed(() => ({
	fieldtype: "Link",
	label: "",
	options: "Dynamic Form Template",
}));

const templateFields = computed(() => {
	const fields = flattenFields(schemaToSections(templateSchema.value || {})).filter((field) => !LAYOUT_FIELD_TYPES.has(field.fieldtype));
	return fields.map((field) => ({
		...field,
		label: field.label || field.fieldname,
	}));
});
const templateFieldMap = computed(() => Object.fromEntries(templateFields.value.map((field) => [field.fieldname, field])));

const filteredFields = computed(() => {
	const query = fieldSearch.value.trim().toLowerCase();
	if (!query) return templateFields.value;
	return templateFields.value.filter((field) => {
		return [field.label, field.fieldname, field.fieldtype]
			.filter(Boolean)
			.some((value) => String(value).toLowerCase().includes(query));
	});
});

const selectedItem = computed(() => layoutItems.value.find((item) => item.id === selectedItemId.value) || null);
const selectedCell = computed(() => {
	if (!selectedItem.value || selectedItem.value.kind !== "matrix" || !selectedCellKey.value) return null;
	return selectedItem.value.cells?.find((cell) => cell.key === selectedCellKey.value) || null;
});
const pageMetrics = computed(() => getPageMetrics({
	page_width: pageWidth.value,
	page_height: pageHeight.value,
	margin_top: marginTop.value,
	margin_right: marginRight.value,
	margin_bottom: marginBottom.value,
	margin_left: marginLeft.value,
}));
const BUILDER_CANVAS_EXTRA_SPACE = 72;
const BUILDER_HEADER_GAP = 72;
const BUILDER_FOOTER_GAP = 96;
const MATRIX_STACK_GAP = 5;
const appliedBodyTopReserve = ref(0);
const footerBandHeight = computed(() => {
	return layoutItems.value.reduce((maxHeight, item) => {
		if (item.kind !== "matrix" || item.region !== "footer") return maxHeight;
		return Math.max(maxHeight, toNumber(item.height, 0));
	}, 0);
});
const headerBandHeight = computed(() => {
	return layoutItems.value.reduce((maxHeight, item) => {
		if (item.kind !== "matrix" || item.region !== "header") return maxHeight;
		const top = Math.max(toNumber(item.y, 0), 0);
		return Math.max(maxHeight, top + toNumber(item.height, 0));
	}, 0);
});
const bodyTopReserve = computed(() => (headerBandHeight.value > 0 ? headerBandHeight.value + BUILDER_HEADER_GAP : 0));
const builderContentHeight = computed(() => {
	const footerReserve = footerBandHeight.value > 0
		? footerBandHeight.value + BUILDER_FOOTER_GAP
		: 0;
	return Math.max(
		pageMetrics.value.contentHeight,
		getLayoutBottom(layoutItems.value, { excludeRegions: ["footer"] }) + footerReserve + BUILDER_CANVAS_EXTRA_SPACE,
	);
});
const pageStyle = computed(() => ({
	...createPreviewPageStyle({
		page_width: pageWidth.value,
		page_height: pageHeight.value,
	}),
	height: `${pageMetrics.value.marginTop + builderContentHeight.value + pageMetrics.value.marginBottom}px`,
}));
const contentStyle = computed(() => ({
	...createPreviewContentStyle({
		page_width: pageWidth.value,
		page_height: pageHeight.value,
		margin_top: marginTop.value,
		margin_right: marginRight.value,
		margin_bottom: marginBottom.value,
		margin_left: marginLeft.value,
	}),
	height: `${builderContentHeight.value}px`,
}));

function extractLayoutItems(layout) {
	if (Array.isArray(layout)) return layout;
	if (layout && Array.isArray(layout.items)) return layout.items;
	return [];
}

function getTemplateField(item) {
	return templateFieldMap.value[item.fieldname] || null;
}

function getItemFieldType(item) {
	return String(item.fieldtype || getTemplateField(item)?.fieldtype || "").trim();
}

function isImageFieldItem(item) {
	return IMAGE_FIELD_TYPES.has(getItemFieldType(item));
}

function isTableFieldItem(item) {
	return TABLE_FIELD_TYPES.has(getItemFieldType(item));
}

function getItemTableConfig(item) {
	const field = getTemplateField(item) || { fieldtype: getItemFieldType(item), fieldname: item.fieldname };
	return getTableConfig(field, Array.isArray(item.print_columns) ? item.print_columns : null);
}

function getAnchoredMatrixY(item) {
	if (item.region === "header") return 0;
	if (item.region === "footer") {
		return Math.max(builderContentHeight.value - toNumber(item.height, 0), 0);
	}
	return Math.max(toNumber(item.y, 0), 0);
}

function syncAnchoredMatrixPositions() {
	layoutItems.value.forEach((item) => {
		if (item.kind !== "matrix" || !["header", "footer"].includes(item.region)) return;
		const nextX = item.span_full_width === false ? clamp(toNumber(item.x), 0, pageMetrics.value.contentWidth) : 0;
		const nextY = getAnchoredMatrixY(item);
		const nextWidth = item.span_full_width === false
			? clamp(toNumber(item.width, pageMetrics.value.contentWidth || 420), 160, pageMetrics.value.contentWidth || 9999)
			: pageMetrics.value.contentWidth;

		if (item.x !== nextX) item.x = nextX;
		if (item.y !== nextY) item.y = nextY;
		if (item.width !== nextWidth) item.width = nextWidth;
	});
}

function rangesOverlap(startA, endA, startB, endB) {
	return startA < endB && endA > startB;
}

function getBodyPlacementItems(excludeId = "") {
	return layoutItems.value.filter((item) => {
		if (!item || item.id === excludeId) return false;
		if (item.kind === "matrix" && ["header", "footer"].includes(item.region)) return false;
		return true;
	});
}

function getBodyMatrixBounds(matrix = {}) {
	const matrixHeight = toNumber(matrix.height, computeMatrixHeight(matrix));
	const lowerBound = bodyTopReserve.value;
	const footerTop = footerBandHeight.value > 0
		? Math.max(builderContentHeight.value - footerBandHeight.value - BUILDER_FOOTER_GAP, lowerBound)
		: builderContentHeight.value;
	const upperBound = Math.max(footerTop - matrixHeight, lowerBound);
	return {
		height: matrixHeight,
		lowerBound,
		upperBound,
	};
}

function isValidBodyMatrixY(matrix, candidateY, others = getBodyPlacementItems(matrix.id)) {
	const { height, lowerBound, upperBound } = getBodyMatrixBounds(matrix);
	const y = clamp(toNumber(candidateY, lowerBound), lowerBound, upperBound);
	const bottom = y + height;
	return !others.some((item) => {
		const itemTop = Math.max(toNumber(item.y, 0), lowerBound);
		const itemBottom = itemTop + Math.max(toNumber(item.height, 0), 0);
		return rangesOverlap(y, bottom, itemTop - MATRIX_STACK_GAP, itemBottom + MATRIX_STACK_GAP);
	});
}

function getBodyStackBottom(excludeId = "") {
	return getBodyPlacementItems(excludeId).reduce((maxBottom, item) => {
		return Math.max(maxBottom, toNumber(item.y, 0) + Math.max(toNumber(item.height, 0), 0));
	}, bodyTopReserve.value);
}

function getBodyAppendY(matrix) {
	const bodyItems = getBodyPlacementItems();
	if (bodyItems.length) {
		return getBodyStackBottom() + MATRIX_STACK_GAP;
	}
	if (footerBandHeight.value > 0) {
		return Math.max(
			builderContentHeight.value - footerBandHeight.value - BUILDER_FOOTER_GAP - toNumber(matrix.height, computeMatrixHeight(matrix)),
			bodyTopReserve.value,
		);
	}
	return bodyTopReserve.value;
}

function getMatrixInsertionY(matrix, desiredY = null, { prefer = "nearest" } = {}) {
	const { height, lowerBound, upperBound } = getBodyMatrixBounds(matrix);
	const others = getBodyPlacementItems(matrix.id);
	const candidates = new Set([lowerBound, upperBound]);

	others.forEach((item) => {
		const itemTop = Math.max(toNumber(item.y, 0), lowerBound);
		const itemBottom = itemTop + Math.max(toNumber(item.height, 0), 0);
		candidates.add(clamp(itemBottom + MATRIX_STACK_GAP, lowerBound, upperBound));
		candidates.add(clamp(itemTop - height - MATRIX_STACK_GAP, lowerBound, upperBound));
	});

	const validCandidates = Array.from(candidates)
		.filter((value) => Number.isFinite(value))
		.filter((value, index, array) => array.indexOf(value) === index)
		.filter((candidate) => isValidBodyMatrixY(matrix, candidate, others));

	if (!validCandidates.length) return lowerBound;
	if (prefer === "bottom") return Math.max(...validCandidates);

	const targetY = desiredY === null || desiredY === undefined ? lowerBound : clamp(toNumber(desiredY, lowerBound), lowerBound, upperBound);
	return validCandidates.reduce((best, current) => {
		const bestDistance = Math.abs(best - targetY);
		const currentDistance = Math.abs(current - targetY);
		if (currentDistance < bestDistance) return current;
		if (currentDistance > bestDistance) return best;
		return current > best ? current : best;
	}, validCandidates[0]);
}

function shiftBodyContent(delta) {
	if (!delta) return;
	layoutItems.value = layoutItems.value.map((item) => {
		if (item.kind === "matrix" && ["header", "footer"].includes(item.region)) {
			return item;
		}
		return {
			...item,
			y: Math.max(toNumber(item.y, 0) + delta, 0),
		};
	});
}

function getTableColumnFieldnames(item) {
	return getItemTableConfig(item).columns.map((column) => column.fieldname);
}

function isTablePrintColumnSelected(item, fieldname) {
	if (!item || !isTableFieldItem(item)) return false;
	if (!Array.isArray(item.print_columns)) return true;
	const availableFieldnames = new Set(getTableColumnFieldnames(item));
	const normalizedSelection = item.print_columns.filter((name) => availableFieldnames.has(name));
	if (!normalizedSelection.length) return true;
	return normalizedSelection.includes(fieldname);
}

function resetTablePrintColumns(item) {
	if (!item || !isTableFieldItem(item)) return;
	item.print_columns = undefined;
}

function toggleTablePrintColumn(item, fieldname, checked) {
	if (!item || !isTableFieldItem(item)) return;

	const allColumns = getTableColumnFieldnames(item);
	const currentSelection = Array.isArray(item.print_columns)
		? item.print_columns.filter((name) => allColumns.includes(name))
		: [...allColumns];
	let nextSelection = checked
		? Array.from(new Set([...currentSelection, fieldname]))
		: currentSelection.filter((name) => name !== fieldname);

	if (!nextSelection.length) {
		frappe.msgprint({
			title: t("Print Columns"),
			message: t("At least one column must stay visible in the print."),
			indicator: "orange",
		});
		return;
	}

	if (nextSelection.length === allColumns.length) {
		item.print_columns = undefined;
		return;
	}

	item.print_columns = nextSelection;
}

watch(
	() => [
		pageWidth.value,
		pageHeight.value,
		marginTop.value,
		marginRight.value,
		marginBottom.value,
		marginLeft.value,
	],
	() => {
		layoutItems.value = layoutItems.value.map((item) => {
			if (item.kind === "matrix") {
				const normalized = resizeMatrixCells(item, item.rows, item.cols);
				const nextX = normalized.span_full_width === false ? clamp(toNumber(item.x), 0, pageMetrics.value.contentWidth) : 0;
				return {
					...normalized,
					x: nextX,
					y: item.region === "footer"
						? Math.max(builderContentHeight.value - normalized.height, 0)
						: item.region === "header"
							? 0
							: Math.max(toNumber(item.y), 0),
					width: normalized.span_full_width === false
						? clamp(toNumber(item.width, pageMetrics.value.contentWidth || 420), 160, pageMetrics.value.contentWidth || 9999)
						: pageMetrics.value.contentWidth,
				};
			}
			return normalizePlacement(item, {
				page_width: pageWidth.value,
				page_height: pageHeight.value,
				margin_top: marginTop.value,
				margin_right: marginRight.value,
				margin_bottom: marginBottom.value,
				margin_left: marginLeft.value,
			});
		});
	},
	{ immediate: false }
);

watch(
	() =>
		selectedItem.value && selectedItem.value.kind === "matrix"
			? [
				selectedItem.value.rows,
				selectedItem.value.cols,
				selectedItem.value.row_height,
				selectedItem.value.heading_height,
				selectedItem.value.show_heading,
				selectedItem.value.region,
				(selectedItem.value.cells || []).map((cell) => `${cell.key}:${cell.row_span || 1}:${cell.col_span || 1}:${cell.label || ""}:${cell.fieldname || ""}:${cell.static_text || ""}:${cell.show_label !== false}`).join("|"),
			]
			: null,
	() => {
		if (!selectedItem.value || selectedItem.value.kind !== "matrix") return;
		selectedItem.value.height = computeMatrixHeight(selectedItem.value);
		selectedItem.value.cells = resizeMatrixCells(selectedItem.value, selectedItem.value.rows, selectedItem.value.cols).cells;
		selectedItem.value.y = selectedItem.value.region === "footer"
			? getAnchoredMatrixY(selectedItem.value)
			: selectedItem.value.region === "header"
				? 0
				: selectedItem.value.y;
	},
	{ deep: false }
);

function computeMatrixHeight(item) {
	const rowHeight = getMatrixAutoRowHeight(item);
	const headingHeight = item.show_heading === false ? 0 : clamp(toNumber(item.heading_height, 28), 16, 80);
	return 20 + headingHeight + (toNumber(item.rows, 2) * rowHeight);
}

function estimateTextLines(text = "", widthPx = 0) {
	const normalized = String(text || "").replace(/\s+/g, " ").trim();
	if (!normalized) return 1;
	const charsPerLine = Math.max(Math.floor(Math.max(widthPx, 40) / 7), 8);
	return normalized.split(/\r?\n/).reduce((lineCount, line) => {
		return lineCount + Math.max(Math.ceil(line.length / charsPerLine), 1);
	}, 0);
}

function estimateTextBlockHeight(text = "", widthPx = 0, { lineHeight = 13, paddingY = 10, minHeight = 0 } = {}) {
	return Math.max(minHeight, paddingY + (estimateTextLines(text, widthPx) * lineHeight));
}

function estimateMatrixCellHeight(item = {}, cell = {}) {
	const rowHeight = clamp(toNumber(item.row_height, 34), 20, 120);
	const cols = Math.max(toNumber(item.cols, 1), 1);
	const span = Math.max(toNumber(cell.col_span, 1), 1);
	const cellWidth = Math.max(((toNumber(item.width, 0) - 20) / cols) * span, 40);
	const content = cell.fieldname
		? [cell.show_label !== false ? cell.label : "", cell.fieldname].filter(Boolean).join("\n")
		: (cell.static_text || "");
	const minHeight = cell.fieldname && cell.show_label !== false ? 36 : 28;
	return Math.max(rowHeight, Math.ceil(estimateTextBlockHeight(content, cellWidth, {
		lineHeight: 13,
		paddingY: 10,
		minHeight,
	}) / Math.max(toNumber(cell.row_span, 1), 1)));
}

function getMatrixAutoRowHeight(item = {}) {
	const rowHeight = clamp(toNumber(item.row_height, 34), 20, 120);
	const cells = visibleMatrixCells(item.cells || []);
	if (!cells.length) return rowHeight;
	return Math.max(rowHeight, ...cells.map((cell) => estimateMatrixCellHeight(item, cell)));
}

function itemStyle(item) {
	return {
		left: `${toNumber(item.x)}px`,
		top: `${toNumber(item.y)}px`,
		width: `${toNumber(item.width, 180)}px`,
		height: `${toNumber(item.height, 36)}px`,
		fontSize: `${toNumber(item.font_size, 11)}px`,
		textAlign: item.align || "left",
		cursor: item.kind === "matrix" ? "default" : "move",
		...item.style,
	};
}

function matrixGridStyle(item) {
	const rowHeight = getMatrixAutoRowHeight(item);
	return {
		gridTemplateColumns: `repeat(${Math.max(toNumber(item.cols, 1), 1)}, minmax(0, 1fr))`,
		gridTemplateRows: `repeat(${Math.max(toNumber(item.rows, 1), 1)}, ${rowHeight}px)`,
	};
}

function matrixCellStyle(cell) {
	return {
		gridColumn: `${toNumber(cell.col, 0) + 1} / span ${Math.max(toNumber(cell.col_span, 1), 1)}`,
		gridRow: `${toNumber(cell.row, 0) + 1} / span ${Math.max(toNumber(cell.row_span, 1), 1)}`,
	};
}

function matrixItemClass(item) {
	return {
		active: item.id === selectedItemId.value,
		[`is-${item.region}`]: Boolean(item.region && item.region !== "body"),
	};
}

function regionLabel(region) {
	if (region === "header") return t("Header");
	if (region === "footer") return t("Footer");
	return t("Body");
}

function visibleMatrixCells(cells) {
	return getVisibleMatrixCells(cells);
}

function setTemplateName(value) {
	templateDocName.value = value || "";
	if (templateDocName.value === props.templateName) {
		return;
	}
	if (!templateDocName.value) {
		resetDraft();
		return;
	}
	loadTemplate(templateDocName.value, { clearFormat: true });
}

function resetDraft() {
	templateDocName.value = "";
	templateLabel.value = "";
	templateDescription.value = "";
	templateSchema.value = {};
	formatList.value = [];
	activeFormatName.value = "";
	existingFormatName.value = "";
	formatName.value = "";
	layoutItems.value = [];
	selectedItemId.value = "";
	selectedCellKey.value = "";
	fieldSearch.value = "";
	pageWidth.value = DEFAULT_PRINT_PAGE.page_width;
	pageHeight.value = DEFAULT_PRINT_PAGE.page_height;
	marginTop.value = DEFAULT_PRINT_PAGE.margin_top;
	marginRight.value = DEFAULT_PRINT_PAGE.margin_right;
	marginBottom.value = DEFAULT_PRINT_PAGE.margin_bottom;
	marginLeft.value = DEFAULT_PRINT_PAGE.margin_left;
}

async function loadTemplate(templateName, { clearFormat = false } = {}) {
	if (!templateName) return;
	isBusy.value = true;
	selectedCellKey.value = "";
	try {
		const doc = await getCachedTemplateSchema(templateName);
		if (!doc) {
			frappe.msgprint({
				title: t("Template not found"),
				message: t("The selected dynamic form template could not be loaded."),
				indicator: "red",
			});
			resetDraft();
			return;
		}

		templateDocName.value = doc.name || templateName;
		templateLabel.value = doc.form_name || doc.name || templateName;
		templateDescription.value = doc.description || "";
		templateSchema.value = doc.schema || {};

		if (clearFormat) {
			activeFormatName.value = "";
			existingFormatName.value = "";
			formatName.value = `${templateLabel.value} Print`;
			layoutItems.value = [];
			selectedItemId.value = "";
			selectedCellKey.value = "";
			fieldSearch.value = "";
		}

		await reloadFormatList();
		if (!activeFormatName.value && formatList.value.length) {
			await loadFormat(formatList.value[0].name);
		}
	} catch (error) {
		frappe.msgprint({
			title: t("Load Error"),
			message: error?.message || t("Unable to load template."),
			indicator: "red",
		});
		resetDraft();
	} finally {
		isBusy.value = false;
	}
}

async function reloadFormatList() {
	if (!templateDocName.value) {
		formatList.value = [];
		return;
	}

	formatsLoading.value = true;
	try {
		const response = await frappe.xcall("ampower_form_builder.print_builder.api.list_print_formats", {
			dynamic_form_template: templateDocName.value,
		});
		formatList.value = Array.isArray(response) ? response : [];
		if (!activeFormatName.value) {
			const defaultFormat = formatList.value.find((item) => item.is_default) || formatList.value[0];
			activeFormatName.value = defaultFormat?.name || "";
		}
	} finally {
		formatsLoading.value = false;
	}
}

async function loadFormat(name) {
	if (!name) return;
	isBusy.value = true;
	try {
		const response = await frappe.xcall("ampower_form_builder.print_builder.api.get_print_format", {
			format_name: name,
		});
		if (!response) return;

		const previousTemplateName = templateDocName.value;
		const nextTemplateName = response.dynamic_form_template || previousTemplateName;
		const templateChanged = Boolean(nextTemplateName && nextTemplateName !== previousTemplateName);

		existingFormatName.value = response.name;
		activeFormatName.value = response.name;
		templateDocName.value = nextTemplateName;
		formatName.value = response.format_name || response.name;
		pageWidth.value = response.page_width || DEFAULT_PRINT_PAGE.page_width;
		pageHeight.value = response.page_height || DEFAULT_PRINT_PAGE.page_height;
		marginTop.value = response.margin_top || DEFAULT_PRINT_PAGE.margin_top;
			marginRight.value = response.margin_right || DEFAULT_PRINT_PAGE.margin_right;
			marginBottom.value = response.margin_bottom || DEFAULT_PRINT_PAGE.margin_bottom;
			marginLeft.value = response.margin_left || DEFAULT_PRINT_PAGE.margin_left;
			layoutItems.value = extractLayoutItems(normalizeLayout(response.layout || {}, response));
			selectedItemId.value = layoutItems.value[0]?.id || "";
		selectedCellKey.value = "";
		fieldSearch.value = "";

		if (nextTemplateName && (templateChanged || !templateSchema.value || !Object.keys(templateSchema.value).length)) {
			const templateDoc = await getCachedTemplateSchema(nextTemplateName);
			templateSchema.value = templateDoc?.schema || {};
			templateLabel.value = templateDoc?.form_name || templateLabel.value;
			templateDescription.value = templateDoc?.description || templateDescription.value;
		}
		syncAnchoredMatrixPositions();
	} catch (error) {
		frappe.msgprint({
			title: t("Load Error"),
			message: error?.message || t("Unable to load the print format."),
			indicator: "red",
		});
	} finally {
		isBusy.value = false;
	}
}

async function selectSavedFormat(name) {
	if (!name) return;
	activeFormatName.value = name;
	await loadFormat(name);

	const route = frappe.get_route?.() || [];
	if (route[0] !== "print_builder" || route[1] !== name) {
		frappe.set_route("print_builder", name);
	}
}

function newFormat() {
	existingFormatName.value = "";
	activeFormatName.value = "";
	formatName.value = templateLabel.value ? `${templateLabel.value} Print` : "";
	layoutItems.value = [];
	selectedItemId.value = "";
	selectedCellKey.value = "";
	fieldSearch.value = "";
}

function addMatrix(region = "body") {
	const matrix = createMatrixPlacement({
		page_width: pageWidth.value,
		page_height: pageHeight.value,
		margin_top: marginTop.value,
		margin_right: marginRight.value,
		margin_bottom: marginBottom.value,
		margin_left: marginLeft.value,
	}, {
		heading: region === "header"
			? (templateLabel.value ? `${templateLabel.value} Header` : "Header")
			: region === "footer"
				? (templateLabel.value ? `${templateLabel.value} Footer` : "Footer")
				: (templateLabel.value ? `${templateLabel.value} Matrix` : "Matrix"),
		region,
		x: 0,
		y: region === "footer" ? Math.max(pageMetrics.value.contentHeight - 180, 0) : 0,
		width: pageMetrics.value.contentWidth,
		rows: 2,
		cols: 2,
		span_full_width: true,
		show_matrix: true,
		show_heading: true,
	});
	if (region === "header") {
		matrix.y = 0;
	} else if (region === "footer") {
		matrix.y = getAnchoredMatrixY(matrix);
	} else {
		matrix.y = getBodyAppendY(matrix);
	}
	layoutItems.value.push(matrix);
	selectedItemId.value = matrix.id;
	selectedCellKey.value = "";
}

function toggleSavedFormatsSidebar() {
	showSavedFormatsSidebar.value = !showSavedFormatsSidebar.value;
}

function selectItem(itemId) {
	selectedItemId.value = itemId;
	selectedCellKey.value = "";
}

function selectCell(itemId, cellKey) {
	selectedItemId.value = itemId;
	selectedCellKey.value = cellKey;
}

function setMatrixCellStaticText(matrix, cell, text) {
	const matrixIndex = layoutItems.value.findIndex((item) => item.id === matrix.id);
	if (matrixIndex < 0) return;

	const nextText = String(text ?? "").trim();
	const nextMatrix = clone(layoutItems.value[matrixIndex]);
	nextMatrix.cells = nextMatrix.cells.map((entry) => {
		if (entry.key !== cell.key) return entry;
		return {
			...entry,
			static_text: nextText,
			fieldname: "",
			label: "",
			show_label: true,
		};
	});
	const normalized = resizeMatrixCells(nextMatrix, nextMatrix.rows, nextMatrix.cols);
	nextMatrix.cells = normalized.cells;
	nextMatrix.height = computeMatrixHeight(normalized);
	layoutItems.value.splice(matrixIndex, 1, nextMatrix);
	selectedItemId.value = nextMatrix.id;
	selectedCellKey.value = cell.key;
}

function handleMatrixCellDoubleClick(matrix, cell) {
	if (cell.fieldname) return;
	selectCell(matrix.id, cell.key);
	const currentValue = String(cell.static_text || "");
	const nextValue = window.prompt(t("Enter static text for this cell"), currentValue);
	if (nextValue === null) return;
	setMatrixCellStaticText(matrix, cell, nextValue);
}

function addField(field) {
	layoutItems.value = clearFieldFromLayout(layoutItems.value, field.fieldname);
	const placement = createPlacement(field, {
		page_width: pageWidth.value,
		page_height: pageHeight.value,
		margin_top: marginTop.value,
		margin_right: marginRight.value,
		margin_bottom: marginBottom.value,
		margin_left: marginLeft.value,
	}, {
		x: 24 + (layoutItems.value.length % 4) * 24,
		y: bodyTopReserve.value + 24 + (layoutItems.value.length % 5) * 18,
	});
	layoutItems.value.push(placement);
	selectedItemId.value = placement.id;
	selectedCellKey.value = "";
}

function handleFieldDragStart(field, event) {
	const dataTransfer = event.dataTransfer;
	if (!dataTransfer) return;

	dataTransfer.effectAllowed = "copy";
	dataTransfer.dropEffect = "copy";
	dataTransfer.setData("text/plain", field.fieldname || field.label || "");
	dataTransfer.setData(
		"application/json",
		JSON.stringify({
			kind: "field",
			field,
		})
	);
	setTransparentDragImage(dataTransfer);
}

function handleItemDragStart(item, event) {
	const dataTransfer = event.dataTransfer;
	if (!dataTransfer) return;

	dataTransfer.effectAllowed = "move";
	dataTransfer.dropEffect = "move";
	dataTransfer.setData("text/plain", item.fieldname || item.label || item.id || "");
	dataTransfer.setData(
		"application/json",
		JSON.stringify({
			kind: "item",
			id: item.id,
		})
	);
	setTransparentDragImage(dataTransfer);
}

let dragGhostCanvas = null;

function setTransparentDragImage(dataTransfer) {
	if (!dataTransfer || typeof dataTransfer.setDragImage !== "function") return;
	if (!dragGhostCanvas) {
		dragGhostCanvas = document.createElement("canvas");
		dragGhostCanvas.width = 1;
		dragGhostCanvas.height = 1;
	}
	const context = dragGhostCanvas.getContext("2d");
	context?.clearRect(0, 0, 1, 1);
	dataTransfer.setDragImage(dragGhostCanvas, 0, 0);
}

function dropPoint(event, width, height) {
	const rect = contentRef.value?.getBoundingClientRect();
	if (!rect) return { x: 0, y: 0 };

	const x = clamp(event.clientX - rect.left - width / 2, 0, Math.max(rect.width - width, 0));
	const y = Math.max(event.clientY - rect.top - height / 2, 0);
	return { x, y };
}

function handleCanvasDrop(event) {
	const raw = event.dataTransfer?.getData("application/json");
	if (!raw) return;

	let payload = null;
	try {
		payload = JSON.parse(raw);
	} catch {
		return;
	}

	const metrics = pageMetrics.value;
	if (payload.kind === "field" && payload.field?.fieldname) {
		layoutItems.value = clearFieldFromLayout(layoutItems.value, payload.field.fieldname);
		const placement = createPlacement(payload.field, {
			page_width: pageWidth.value,
			page_height: pageHeight.value,
			margin_top: marginTop.value,
			margin_right: marginRight.value,
			margin_bottom: marginBottom.value,
			margin_left: marginLeft.value,
		}, dropPoint(event, 180, 36));
		layoutItems.value.push(placement);
		selectedItemId.value = placement.id;
		selectedCellKey.value = "";
		return;
	}

	if (payload.kind === "item" && payload.id) {
		const item = layoutItems.value.find((entry) => entry.id === payload.id);
		if (!item) return;
		const position = dropPoint(event, toNumber(item.width, 180), toNumber(item.height, 36));
		item.x = clamp(position.x, 0, Math.max(metrics.contentWidth - toNumber(item.width, 180), 0));
		item.y = item.kind === "matrix" && item.region === "header"
			? 0
			: item.kind === "matrix" && item.region === "footer"
				? getAnchoredMatrixY(item)
				: item.kind === "matrix"
					? getMatrixInsertionY(item, position.y, { prefer: "nearest" })
					: Math.max(position.y, 0);
		selectedItemId.value = item.id;
		selectedCellKey.value = "";
	}
}

function handleMatrixCellDrop(matrix, cell, event) {
	event.preventDefault();
	event.stopPropagation();
	const raw = event.dataTransfer?.getData("application/json");
	if (!raw) return;

	let payload = null;
	try {
		payload = JSON.parse(raw);
	} catch {
		return;
	}

	if (payload.kind !== "field" || !payload.field?.fieldname) return;
	layoutItems.value = clearFieldFromLayout(layoutItems.value, payload.field.fieldname);
	const matrixIndex = layoutItems.value.findIndex((item) => item.id === matrix.id);
	if (matrixIndex < 0) return;
	const updated = assignMatrixCell(layoutItems.value[matrixIndex], cell.row, cell.col, payload.field);
	layoutItems.value.splice(matrixIndex, 1, {
		...updated,
		height: computeMatrixHeight(updated),
	});
	selectedItemId.value = matrix.id;
	selectedCellKey.value = cell.key;
}

function deleteSelected() {
	if (!selectedItem.value) return;
	if (selectedItem.value.kind === "matrix" && selectedCell.value) {
		clearSelectedCell();
		return;
	}
	layoutItems.value = layoutItems.value.filter((item) => item.id !== selectedItem.value.id);
	selectedItemId.value = layoutItems.value[0]?.id || "";
	selectedCellKey.value = "";
}

function deleteSelectedMatrix() {
	if (!selectedItem.value || selectedItem.value.kind !== "matrix") return;
	layoutItems.value = layoutItems.value.filter((item) => item.id !== selectedItem.value.id);
	selectedItemId.value = layoutItems.value[0]?.id || "";
	selectedCellKey.value = "";
}

function duplicateSelected() {
	if (!selectedItem.value) return;
	if (selectedItem.value.kind === "matrix") {
		const copy = {
			...clone(selectedItem.value),
			id: uid(),
			x: clamp(toNumber(selectedItem.value.x, 0) + 12, 0, pageMetrics.value.contentWidth),
			y: selectedItem.value.region === "footer"
				? getAnchoredMatrixY(selectedItem.value)
				: selectedItem.value.region === "header"
					? 0
					: getMatrixInsertionY(selectedItem.value, toNumber(selectedItem.value.y, 0) + 12, { prefer: "nearest" }),
			cells: (selectedItem.value.cells || []).map((cell) => ({
				...clone(cell),
				id: uid(),
			})),
		};
		layoutItems.value.push(copy);
		selectedItemId.value = copy.id;
		selectedCellKey.value = "";
		return;
	}
	const copy = {
		...selectedItem.value,
		id: uid(),
		x: clamp(toNumber(selectedItem.value.x, 0) + 12, 0, pageMetrics.value.contentWidth),
		y: Math.max(toNumber(selectedItem.value.y, 0) + 12, 0),
	};
	layoutItems.value.push(copy);
	selectedItemId.value = copy.id;
	selectedCellKey.value = "";
}

function adjustMatrixRows(delta) {
	if (!selectedItem.value || selectedItem.value.kind !== "matrix") return;
	const nextRows = Math.max(1, toNumber(selectedItem.value.rows, 2) + delta);
	const updated = resizeMatrixCells(selectedItem.value, nextRows, selectedItem.value.cols);
	selectedItem.value.rows = updated.rows;
	selectedItem.value.cells = updated.cells;
	selectedItem.value.height = computeMatrixHeight(updated);
	selectedItem.value.y = selectedItem.value.region === "footer"
		? getAnchoredMatrixY(selectedItem.value)
		: selectedItem.value.region === "header"
			? 0
			: getMatrixInsertionY(selectedItem.value, selectedItem.value.y, { prefer: "nearest" });
}

function adjustMatrixCols(delta) {
	if (!selectedItem.value || selectedItem.value.kind !== "matrix") return;
	const nextCols = Math.max(1, toNumber(selectedItem.value.cols, 2) + delta);
	const updated = resizeMatrixCells(selectedItem.value, selectedItem.value.rows, nextCols);
	selectedItem.value.cols = updated.cols;
	selectedItem.value.cells = updated.cells;
	selectedItem.value.height = computeMatrixHeight(updated);
	selectedItem.value.y = selectedItem.value.region === "footer"
		? getAnchoredMatrixY(selectedItem.value)
		: selectedItem.value.region === "header"
			? 0
			: getMatrixInsertionY(selectedItem.value, selectedItem.value.y, { prefer: "nearest" });
}

watch(
	() => [builderContentHeight.value, pageMetrics.value.contentWidth, pageMetrics.value.contentHeight],
	() => {
		syncAnchoredMatrixPositions();
	},
	{ immediate: true }
);

watch(
	() => bodyTopReserve.value,
	(nextReserve) => {
		const delta = nextReserve - appliedBodyTopReserve.value;
		if (delta) {
			shiftBodyContent(delta);
		}
		appliedBodyTopReserve.value = nextReserve;
		syncAnchoredMatrixPositions();
	},
	{ immediate: true }
);

function clearSelectedCell() {
	if (!selectedItem.value || selectedItem.value.kind !== "matrix" || !selectedCell.value) return;
	const matrixIndex = layoutItems.value.findIndex((item) => item.id === selectedItem.value.id);
	if (matrixIndex < 0) return;
	const nextMatrix = clone(layoutItems.value[matrixIndex]);
	nextMatrix.cells = nextMatrix.cells.map((cell) => {
		if (cell.key !== selectedCell.value.key) return cell;
		return {
			...cell,
			fieldname: "",
			label: "",
			static_text: "",
			show_label: true,
			row_span: 1,
			col_span: 1,
		};
	});
	const normalized = resizeMatrixCells(nextMatrix, nextMatrix.rows, nextMatrix.cols);
	nextMatrix.cells = normalized.cells;
	nextMatrix.height = computeMatrixHeight(normalized);
	layoutItems.value.splice(matrixIndex, 1, nextMatrix);
	selectedCellKey.value = "";
}

function syncSelectedMatrixCellLayout() {
	if (!selectedItem.value || selectedItem.value.kind !== "matrix" || !selectedCell.value) return;
	const matrixIndex = layoutItems.value.findIndex((item) => item.id === selectedItem.value.id);
	if (matrixIndex < 0) return;

	const nextMatrix = clone(layoutItems.value[matrixIndex]);
	nextMatrix.cells = nextMatrix.cells.map((cell) => {
		if (cell.key !== selectedCell.value.key) return cell;
		return {
			...cell,
			row_span: Math.max(1, toNumber(selectedCell.value.row_span, 1)),
			col_span: Math.max(1, toNumber(selectedCell.value.col_span, 1)),
		};
	});

	const normalized = resizeMatrixCells(nextMatrix, nextMatrix.rows, nextMatrix.cols);
	nextMatrix.cells = normalized.cells;
	nextMatrix.height = computeMatrixHeight(normalized);
	layoutItems.value.splice(matrixIndex, 1, nextMatrix);
	selectedItemId.value = nextMatrix.id;
	selectedCellKey.value = selectedCell.value.key;
}

async function saveFormat() {
	if (!templateDocName.value) {
		frappe.msgprint({
			title: t("Missing Template"),
			message: t("Choose a dynamic form template before saving."),
			indicator: "orange",
		});
		return;
	}

	if (!formatName.value.trim()) {
		frappe.msgprint({
			title: t("Missing Format Name"),
			message: t("Enter a print format name before saving."),
			indicator: "orange",
		});
		return;
	}

	isBusy.value = true;
	frappe.dom?.freeze?.(t("Saving print format..."));
	try {
		const payload = await frappe.xcall("ampower_form_builder.print_builder.api.save_print_format", {
			name: existingFormatName.value || "",
			format_name: formatName.value.trim(),
			dynamic_form_template: templateDocName.value,
			is_default: activeFormatName.value === existingFormatName.value ? 1 : 0,
			is_active: 1,
			page_width: pageWidth.value,
			page_height: pageHeight.value,
			margin_top: marginTop.value,
			margin_right: marginRight.value,
			margin_bottom: marginBottom.value,
			margin_left: marginLeft.value,
			layout_json: {
				items: layoutItems.value,
			},
		});
		existingFormatName.value = payload.name;
		activeFormatName.value = payload.name;
		formatName.value = payload.format_name || formatName.value;
		layoutItems.value = extractLayoutItems(normalizeLayout(payload.layout || {}, payload));
		await reloadFormatList();
		frappe.show_alert({
			message: t("Print format saved successfully."),
			indicator: "green",
		});
	} catch (error) {
		frappe.msgprint({
			title: t("Save Error"),
			message: error?.message || t("Unable to save the print format."),
			indicator: "red",
		});
	} finally {
		isBusy.value = false;
		frappe.dom?.unfreeze?.();
	}
}

function handleKeydown(event) {
	if (event.defaultPrevented) return;
	if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName)) return;

	if ((event.ctrlKey || event.metaKey) && String(event.key).toLowerCase() === "s") {
		event.preventDefault();
		saveFormat();
		return;
	}

	if (event.key === "Delete" || event.key === "Backspace") {
		deleteSelected();
	}
}

watch(
	() => props.templateName,
	(value) => {
		if (!value) return;
		if (value === templateDocName.value) return;
		resetDraft();
		formatName.value = "";
		loadTemplate(value, { clearFormat: true });
	},
	{ immediate: true }
);

watch(
	() => props.formatName,
	(value) => {
		if (!value || value === existingFormatName.value) return;
		loadFormat(value);
	},
	{ immediate: true }
);

onMounted(() => {
	window.addEventListener("keydown", handleKeydown);
});

onBeforeUnmount(() => {
	window.removeEventListener("keydown", handleKeydown);
});
</script>

<style scoped>
.pb-shell {
	display: flex;
	flex-direction: column;
	height: calc(100vh - var(--navbar-height));
	background: linear-gradient(180deg, #f6f7fb 0%, #eef2f7 100%);
	overflow: hidden;
}

.pb-header {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 20px;
	padding: 16px 20px;
	border-bottom: 1px solid rgba(15, 23, 42, 0.08);
	background: rgba(255, 255, 255, 0.88);
	backdrop-filter: blur(10px);
}

.pb-header-main {
	flex: 1 1 auto;
	min-width: 0;
	display: grid;
	grid-template-columns: minmax(320px, 1.2fr) minmax(340px, 1fr);
	gap: 16px;
}

.pb-header-block {
	background: #fff;
	border: 1px solid rgba(15, 23, 42, 0.08);
	border-radius: 16px;
	padding: 14px;
	box-shadow: 0 12px 32px rgba(15, 23, 42, 0.06);
}

.pb-kicker {
	font-size: 12px;
	font-weight: 700;
	color: #475569;
	text-transform: uppercase;
	letter-spacing: 0.08em;
	margin-bottom: 10px;
}

.pb-row,
.pb-page-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 12px;
}

.pb-page-grid {
	grid-template-columns: repeat(3, minmax(0, 1fr));
}

.pb-field {
	display: flex;
	flex-direction: column;
	gap: 6px;
}

.pb-label {
	font-size: 12px;
	font-weight: 600;
	color: #64748b;
}

.pb-header-actions {
	flex: 0 0 auto;
	display: flex;
	gap: 8px;
	align-items: center;
	padding-top: 12px;
}

.pb-workspace {
	flex: 1;
	display: grid;
	grid-template-columns: 280px minmax(0, 1fr) 320px;
	gap: 16px;
	padding: 16px;
	min-height: 0;
	overflow: hidden;
}

.pb-workspace.sidebar-hidden {
	grid-template-columns: minmax(0, 1fr) 320px;
}

.pb-sidebar {
	min-height: 0;
	display: flex;
	flex-direction: column;
	gap: 16px;
}

.pb-sidebar-right {
	min-height: 0;
	overflow-y: auto;
	padding-right: 4px;
	scrollbar-gutter: stable;
	overscroll-behavior: contain;
}

.pb-sidebar-right .pb-sidebar-section {
	flex: 0 0 auto;
}

.pb-sidebar-section {
	flex: 1;
	background: rgba(255, 255, 255, 0.92);
	border: 1px solid rgba(15, 23, 42, 0.08);
	border-radius: 18px;
	padding: 16px;
	box-shadow: 0 12px 32px rgba(15, 23, 42, 0.06);
	display: flex;
	flex-direction: column;
	gap: 12px;
	min-height: 0;
}

.pb-section-title {
	font-size: 14px;
	font-weight: 700;
	color: #0f172a;
}

.pb-format-list,
.pb-field-list {
	display: flex;
	flex-direction: column;
	gap: 8px;
	overflow: auto;
	min-height: 0;
}

.pb-format-item,
.pb-field-item {
	display: flex;
	align-items: center;
	justify-content: space-between;
	width: 100%;
	padding: 10px 12px;
	border: 1px solid rgba(15, 23, 42, 0.08);
	border-radius: 12px;
	background: #fff;
	text-align: left;
}

.pb-format-item.active {
	border-color: #0f766e;
	box-shadow: inset 0 0 0 1px rgba(15, 118, 110, 0.15);
}

.pb-field-item {
	cursor: grab;
}

.pb-field-item:hover,
.pb-format-item:hover {
	border-color: rgba(15, 118, 110, 0.35);
	background: #f8fffe;
}

.pb-field-item-label {
	font-weight: 600;
	color: #0f172a;
}

.pb-table-print-columns {
	display: grid;
	gap: 10px;
	padding: 12px;
	border: 1px solid rgba(15, 23, 42, 0.08);
	border-radius: 14px;
	background: rgba(248, 250, 252, 0.92);
}

.pb-table-print-actions {
	display: flex;
	align-items: center;
	gap: 10px;
	flex-wrap: wrap;
}

.pb-table-print-help {
	font-size: 12px;
	color: #64748b;
}

.pb-table-print-list {
	display: grid;
	gap: 8px;
	max-height: 240px;
	overflow: auto;
	padding-right: 2px;
}

.pb-table-print-item {
	display: flex;
	align-items: flex-start;
	gap: 10px;
	padding: 10px 12px;
	border: 1px solid rgba(15, 23, 42, 0.08);
	border-radius: 12px;
	background: #fff;
	cursor: pointer;
}

.pb-table-print-item-body {
	display: grid;
	gap: 2px;
	min-width: 0;
}

.pb-table-print-item-label {
	font-weight: 600;
	color: #0f172a;
	line-height: 1.2;
}

.pb-table-print-item-meta {
	font-size: 12px;
	color: #64748b;
}

.pb-empty-state {
	padding: 12px;
	border-radius: 12px;
	background: #f8fafc;
	border: 1px dashed rgba(15, 23, 42, 0.14);
	color: #64748b;
	font-size: 13px;
}

.pb-canvas-panel {
	min-width: 0;
	min-height: 0;
	display: flex;
	justify-content: center;
	overflow: auto;
}

.pb-canvas-shell {
	padding: 16px;
}

.pb-canvas-page {
	position: relative;
	background: white;
	border: 1px solid rgba(15, 23, 42, 0.15);
	border-radius: 20px;
	box-shadow: 0 24px 72px rgba(15, 23, 42, 0.12);
	overflow: hidden;
}

.pb-canvas-content {
	position: absolute;
	box-sizing: border-box;
	background:
		linear-gradient(to right, rgba(148, 163, 184, 0.12) 1px, transparent 1px),
		linear-gradient(to bottom, rgba(148, 163, 184, 0.12) 1px, transparent 1px);
	background-size: 24px 24px;
}

.pb-canvas-item {
	position: absolute;
	box-sizing: border-box;
	border: 1px solid rgba(15, 23, 42, 0.14);
	border-radius: 10px;
	background: rgba(255, 255, 255, 0.94);
	padding: 8px 10px;
	display: flex;
	flex-direction: column;
	gap: 3px;
	cursor: move;
	overflow: hidden;
}

.pb-canvas-item.active {
	border-color: #0f766e;
	box-shadow: 0 0 0 2px rgba(15, 118, 110, 0.14);
}

.pb-canvas-item-table {
	gap: 6px;
	background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.98));
}

.pb-canvas-item-image {
	gap: 8px;
	background: linear-gradient(180deg, rgba(240, 253, 250, 0.98), rgba(255, 255, 255, 0.98));
}

.pb-item-type-row {
	display: flex;
	align-items: center;
	gap: 8px;
	flex-wrap: wrap;
}

.pb-item-type-badge {
	display: inline-flex;
	align-items: center;
	padding: 2px 8px;
	border-radius: 999px;
	background: rgba(15, 118, 110, 0.1);
	color: #0f766e;
	font-size: 10px;
	font-weight: 800;
	text-transform: uppercase;
	letter-spacing: 0.06em;
}

.pb-item-type-note {
	font-size: 11px;
	color: #64748b;
	line-height: 1.3;
}

.pb-item-table-preview {
	width: 100%;
	min-height: 0;
	overflow: hidden;
}

.pb-item-table-preview :deep(.table-preview-header) {
	display: none;
}

.pb-item-table-preview :deep(.table-preview) {
	gap: 0;
}

.pb-item-table-preview :deep(.form-grid-container) {
	transform: scale(0.72);
	transform-origin: top left;
	width: 138.9%;
}

.pb-item-table-preview :deep(.fv-table-row),
.pb-item-table-preview :deep(.grid-static-col) {
	font-size: 10px;
}

.pb-item-image-preview {
	display: flex;
	align-items: center;
	gap: 12px;
	min-width: 0;
}

.pb-item-image-visual {
	flex: 0 0 auto;
	width: 72px;
	height: 72px;
	border-radius: 14px;
	border: 1px dashed rgba(15, 23, 42, 0.16);
	background:
		linear-gradient(135deg, rgba(15, 118, 110, 0.12), rgba(148, 163, 184, 0.08)),
		repeating-linear-gradient(45deg, rgba(255, 255, 255, 0.6) 0, rgba(255, 255, 255, 0.6) 8px, transparent 8px, transparent 16px);
	display: flex;
	align-items: center;
	justify-content: center;
	color: #0f766e;
}

.pb-item-image-visual svg {
	width: 28px;
	height: 28px;
	fill: currentColor;
}

.pb-item-image-text {
	min-width: 0;
	display: flex;
	flex-direction: column;
	gap: 4px;
}

.pb-item-label {
	font-size: 11px;
	font-weight: 700;
	color: #475569;
	line-height: 1.15;
}

.pb-item-value {
	font-size: 12px;
	font-weight: 600;
	color: #0f172a;
	line-height: 1.2;
	word-break: break-word;
}

.pb-search {
	margin-bottom: 4px;
}

.pb-properties {
	display: flex;
	flex-direction: column;
	gap: 12px;
}

.pb-grid-2 {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 12px;
}

.pb-check {
	display: flex;
	align-items: center;
	gap: 8px;
	font-size: 13px;
	font-weight: 600;
	color: #0f172a;
	margin: 0;
}

.pb-actions-inline {
	display: flex;
	gap: 8px;
}

.pb-section-subtitle {
	font-size: 12px;
	font-weight: 700;
	color: #0f172a;
}

.pb-matrix-item {
	position: absolute;
	box-sizing: border-box;
	display: flex;
	flex-direction: column;
	gap: 8px;
	padding: 10px;
	background: rgba(255, 255, 255, 0.96);
	border: 1px solid rgba(15, 23, 42, 0.16);
	border-radius: 12px;
	overflow: hidden;
	box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}

.pb-matrix-item.active {
	border-color: #0f766e;
	box-shadow: 0 0 0 2px rgba(15, 118, 110, 0.14), 0 10px 24px rgba(15, 23, 42, 0.08);
}

.pb-matrix-item.is-header {
	background: rgba(240, 253, 250, 0.98);
}

.pb-matrix-item.is-footer {
	background: rgba(248, 250, 252, 0.98);
}

.pb-matrix-heading-row {
	display: flex;
	align-items: center;
	gap: 10px;
}

.pb-matrix-heading-input {
	flex: 1 1 auto;
	min-width: 0;
}

.pb-matrix-meta {
	flex: 0 0 auto;
	display: flex;
	align-items: center;
	gap: 6px;
	font-size: 11px;
	font-weight: 700;
	color: #64748b;
	white-space: nowrap;
}

.pb-region-pill {
	display: inline-flex;
	align-items: center;
	padding: 2px 8px;
	border-radius: 999px;
	background: rgba(15, 118, 110, 0.1);
	color: #0f766e;
	font-size: 10px;
	font-weight: 800;
	text-transform: uppercase;
	letter-spacing: 0.06em;
}

.pb-matrix-grid {
	display: grid;
	gap: 0;
	min-width: 0;
}

.pb-matrix-cell {
	box-sizing: border-box;
	padding: 6px 8px;
	min-width: 0;
	min-height: 0;
	overflow: hidden;
	border: 1px dashed transparent;
	border-radius: 8px;
	background: rgba(248, 250, 252, 0.9);
	display: flex;
	flex-direction: column;
	justify-content: center;
	gap: 2px;
}

.pb-matrix-grid.show-borders .pb-matrix-cell {
	border-color: rgba(148, 163, 184, 0.45);
	background: #fff;
	border-radius: 0;
}

.pb-matrix-cell.active {
	border-color: #0f766e !important;
	box-shadow: inset 0 0 0 1px rgba(15, 118, 110, 0.18);
}

.pb-matrix-cell.cell-covered {
	opacity: 0.65;
}

.pb-matrix-cell-placeholder {
	font-size: 11px;
	color: #94a3b8;
	font-style: italic;
}

.pb-matrix-cell-label {
	font-size: 11px;
	font-weight: 700;
	color: #475569;
	line-height: 1.15;
}

.pb-matrix-cell-value {
	font-size: 12px;
	font-weight: 600;
	color: #0f172a;
	line-height: 1.2;
	word-break: break-word;
}

.pb-matrix-cell-editor {
	display: flex;
	flex-direction: column;
	gap: 12px;
	padding-top: 4px;
	border-top: 1px solid rgba(15, 23, 42, 0.08);
}

@media (max-width: 1400px) {
	.pb-workspace {
		grid-template-columns: 260px minmax(0, 1fr);
	}

	.pb-sidebar-right {
		grid-column: 1 / -1;
		display: grid;
		grid-template-columns: 1fr 1fr;
	}

	.pb-workspace.sidebar-hidden {
		grid-template-columns: minmax(0, 1fr);
	}
}

@media (max-width: 1100px) {
	.pb-header-main {
		grid-template-columns: 1fr;
	}

	.pb-page-grid {
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}

	.pb-workspace {
		grid-template-columns: 1fr;
	}
}
</style>
