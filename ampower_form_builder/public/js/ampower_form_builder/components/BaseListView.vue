<template>
	<div class="fv-list-view" :style="listStyle">
		<div class="fv-list-toolbar">
			<div class="fv-list-toolbar-left">
				<div class="fv-list-toolbar-search">
					<input
						class="form-control fv-list-search"
						type="text"
						:placeholder="searchPlaceholder"
						:aria-label="searchAriaLabel"
						:value="searchValue"
						@input="emitSearch"
					>
				</div>
				<div v-if="$slots['toolbar-filters']" class="fv-list-toolbar-filters">
					<slot name="toolbar-filters" />
				</div>
			</div>

			<div class="fv-list-toolbar-actions">
				<slot name="toolbar-before" />

				<button v-if="showFilter" type="button" class="fv-list-pill" @click="$emit('filter')">
					<span class="fv-list-pill-icon" aria-hidden="true">&#9776;</span>
					<span>{{ filterLabel }}</span>
				</button>

				<button v-if="showClear" type="button" class="fv-list-pill" @click="$emit('clear')">
					<span class="fv-list-pill-icon" aria-hidden="true">&#10005;</span>
				</button>

				<BuilderDropdown
					v-if="showGroupBy && groupByItems.length"
					:label="groupByLabel"
					:title="groupByLabel"
					:items="groupByItems"
					button-class="fv-list-pill fv-list-dropdown"
					@select="$emit('group-by-select', $event)"
				/>

				<BuilderDropdown
					v-if="showAddMenu && addMenuItems.length"
					:label="addLabel"
					:title="addLabel"
					:items="addMenuItems"
					button-class="fv-list-pill fv-list-dropdown"
					@select="$emit('add-select', $event)"
				/>

				<BuilderDropdown
					v-if="showActionMenu && actionMenuItems.length"
					:icon-only="true"
					:title="actionsLabel"
					:items="actionMenuItems"
					button-class="fv-list-pill fv-list-pill-icon-only fv-list-dropdown"
					@select="$emit('action-select', $event)"
				/>

				<button v-if="showRefresh" type="button" class="fv-list-pill fv-list-pill-icon-only" :title="refreshLabel" @click="$emit('refresh')">
					<span class="fv-list-pill-icon" aria-hidden="true">&#8635;</span>
				</button>

				<slot name="toolbar-after" />
			</div>
		</div>

		<div class="fv-list-panel">
			<div class="fv-list-head">
				<slot name="head" />
			</div>

			<div v-if="loading" class="fv-list-state fv-state-loading">
				<div class="fv-state-title">{{ loadingTitle }}</div>
				<div class="fv-state-copy">{{ loadingCopy }}</div>
			</div>

			<template v-else-if="hasItems">
				<slot />
			</template>

			<div v-else class="fv-list-state fv-state-empty">
				<div class="fv-state-title">{{ emptyTitle }}</div>
				<div class="fv-state-copy">{{ emptyCopy }}</div>
			</div>
		</div>

		<div v-if="showPagination && totalPages > 1" class="fv-list-pagination">
			<div class="fv-list-pagination-meta">{{ paginationLabel }}</div>
			<div class="fv-list-pagination-actions">
				<button
					type="button"
					class="fv-list-page-btn"
					:disabled="currentPage <= 1"
					:title="previousPageLabel"
					@click="$emit('previous-page')"
				>
					<span class="fv-list-page-icon" aria-hidden="true">&#8249;</span>
				</button>
				<button
					v-for="pageNumber in visiblePages"
					:key="pageNumber"
					type="button"
					class="fv-list-page-btn"
					:class="{ 'is-active': pageNumber === currentPage }"
					@click="$emit('go-to-page', pageNumber)"
				>
					{{ pageNumber }}
				</button>
				<button
					type="button"
					class="fv-list-page-btn"
					:disabled="currentPage >= totalPages"
					:title="nextPageLabel"
					@click="$emit('next-page')"
				>
					<span class="fv-list-page-icon" aria-hidden="true">&#8250;</span>
				</button>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";
import BuilderDropdown from "./BuilderDropdown.vue";

const props = defineProps({
	loading: { type: Boolean, default: false },
	hasItems: { type: Boolean, default: false },
	loadingTitle: { type: String, default: "Loading..." },
	loadingCopy: { type: String, default: "Please wait while the list is loaded." },
	emptyTitle: { type: String, default: "No items found" },
	emptyCopy: { type: String, default: "There is nothing to show right now." },
	searchValue: { type: String, default: "" },
	searchPlaceholder: { type: String, default: "Search" },
	searchAriaLabel: { type: String, default: "Search list" },
	filterLabel: { type: String, default: "Filter" },
	groupByLabel: { type: String, default: "Group By" },
	addLabel: { type: String, default: "Add New" },
	actionsLabel: { type: String, default: "More actions" },
	refreshLabel: { type: String, default: "Refresh list" },
	groupByItems: { type: Array, default: () => [] },
	addMenuItems: { type: Array, default: () => [] },
	actionMenuItems: { type: Array, default: () => [] },
	showFilter: { type: Boolean, default: false },
	showClear: { type: Boolean, default: false },
	showGroupBy: { type: Boolean, default: true },
	showAddMenu: { type: Boolean, default: true },
	showActionMenu: { type: Boolean, default: true },
	showRefresh: { type: Boolean, default: true },
	showPagination: { type: Boolean, default: false },
	currentPage: { type: Number, default: 1 },
	totalPages: { type: Number, default: 1 },
	paginationLabel: { type: String, default: "" },
	previousPageLabel: { type: String, default: "Previous page" },
	nextPageLabel: { type: String, default: "Next page" },
	maxVisiblePages: { type: Number, default: 5 },
	gridTemplateColumns: { type: String, default: "" },
});

const emit = defineEmits([
	"update:searchValue",
	"filter",
	"clear",
	"group-by-select",
	"add-select",
	"action-select",
	"refresh",
	"previous-page",
	"next-page",
	"go-to-page",
]);

function emitSearch(event) {
	emit("update:searchValue", event.target.value);
}

const listStyle = computed(() => {
	if (!props.gridTemplateColumns) return null;

	return {
		"--fv-list-grid-template": props.gridTemplateColumns,
	};
});

const visiblePages = computed(() => {
	const total = Math.max(1, props.totalPages);
	const current = Math.min(Math.max(1, props.currentPage), total);
	const maxVisible = Math.max(3, props.maxVisiblePages);

	if (total <= maxVisible) {
		return Array.from({ length: total }, (_, index) => index + 1);
	}

	const half = Math.floor(maxVisible / 2);
	let start = Math.max(1, current - half);
	let end = start + maxVisible - 1;

	if (end > total) {
		end = total;
		start = Math.max(1, end - maxVisible + 1);
	}

	return Array.from({ length: end - start + 1 }, (_, index) => start + index);
});
</script>

<style scoped>
.fv-list-view {
	display: flex;
	flex-direction: column;
	gap: 10px;
}

.fv-list-toolbar {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 10px;
	flex-wrap: nowrap;
	padding: 12px 14px;
	border: 1px solid var(--fv-border);
	border-bottom: 0;
	border-radius: var(--border-radius-tiny, 4px) var(--border-radius-tiny, 4px) 0 0;
	background: var(--fv-surface);
}

.fv-list-toolbar-left {
	display: flex;
	align-items: center;
	gap: 10px;
	flex: 1 1 auto;
	min-width: 0;
}

.fv-list-toolbar-search {
	flex: 1 1 220px;
	min-width: 0;
}

.fv-list-search {
	width: 100%;
	max-width: 280px;
	height: 38px;
	border: 1px solid var(--fv-border);
	border-radius: var(--border-radius-tiny, 4px);
	background: var(--fv-surface);
	box-shadow: none;
}

.fv-list-toolbar-filters {
	display: flex;
	align-items: center;
	gap: 10px;
	flex-wrap: nowrap;
}

.fv-list-toolbar-actions {
	display: flex;
	align-items: center;
	gap: 10px;
	flex-wrap: nowrap;
	margin-left: auto;
}

.fv-list-pill {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	gap: 10px;
	min-height: 38px;
	padding: 0.45rem 0.8rem;
	border: 1px solid var(--fv-border);
	border-radius: var(--border-radius-tiny, 4px);
	background: var(--fv-surface);
	color: var(--fv-text-main);
	font-size: 0.95rem;
	font-weight: 500;
	box-shadow: none;
}

.fv-list-pill:hover {
	background: var(--subtle-fg);
}

.fv-list-pill-icon {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	min-width: 1rem;
	font-size: 1rem;
	line-height: 1;
	color: var(--fv-text-muted);
}

.fv-list-pill-icon-only {
	min-width: 40px;
	padding-inline: 0.65rem;
}

.fv-list-dropdown {
	padding-right: 0.75rem;
}

.fv-list-panel {
	border: 1px solid var(--fv-border);
	border-radius: 0 0 var(--border-radius-tiny, 4px) var(--border-radius-tiny, 4px);
	background: var(--fv-surface);
	max-height: calc(100vh - 228px);
	overflow: auto;
	scrollbar-gutter: stable;
}

.fv-list-head,
.fv-list-row {
	display: grid;
	grid-template-columns: var(--fv-list-grid-template, 34px minmax(180px, 1.8fr) minmax(120px, 0.75fr) repeat(2, minmax(160px, 1fr)) minmax(64px, auto));
	gap: 10px;
	align-items: center;
}

.fv-list-head {
	padding: 0.85rem 1rem;
	border-bottom: 1px solid var(--fv-border);
	background: var(--subtle-fg);
	font-size: 0.9rem;
	font-weight: 700;
	color: var(--fv-text-main);
}

.fv-list-head span {
	min-width: 0;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.fv-list-head-meta {
	display: flex;
	align-items: center;
	justify-content: flex-end;
	gap: 10px;
	font-weight: 700;
	color: var(--fv-text-main);
}

.fv-list-heart {
	font-size: 1rem;
	line-height: 1;
	color: var(--fv-text-muted);
}

.fv-list-state {
	padding: 1rem;
	border-top: 1px solid var(--fv-border);
}

.fv-list-row {
	width: 100%;
	padding: 0.85rem 1rem;
	border: 0;
	border-top: 1px solid var(--fv-border);
	background: var(--fv-surface);
	text-align: left;
	cursor: pointer;
	transition: background-color 0.15s ease;
}

.fv-list-row:hover {
	background: var(--subtle-fg);
}



.fv-list-id {
	font-size: 1rem;
	font-weight: 700;
	color: var(--fv-primary);
	min-width: 0;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.fv-list-status,
.fv-list-series,
.fv-list-meta {
	display: flex;
	align-items: center;
	min-width: 0;
}

.fv-list-pagination {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 12px;
	padding: 12px 14px;
	border: 1px solid var(--fv-border);
	border-top: 0;
	border-radius: 0 0 var(--border-radius-tiny, 4px) var(--border-radius-tiny, 4px);
	background: var(--fv-surface);
}

.fv-list-pagination-meta {
	font-size: 0.9rem;
	color: var(--fv-text-muted);
}

.fv-list-pagination-actions {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	flex-wrap: wrap;
}

.fv-list-page-btn {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	min-width: 34px;
	height: 34px;
	padding: 0 0.75rem;
	border: 1px solid var(--fv-border);
	border-radius: var(--border-radius-tiny, 4px);
	background: var(--fv-surface);
	color: var(--fv-text-main);
	font-size: 0.9rem;
	font-weight: 600;
	box-shadow: none;
}

.fv-list-page-btn:hover:not(:disabled),
.fv-list-page-btn.is-active {
	background: var(--primary);
	border-color: var(--primary);
	color: #ffffff;
}

.fv-list-page-btn:disabled {
	opacity: 0.45;
	cursor: not-allowed;
}

.fv-list-page-icon {
	font-size: 1rem;
	line-height: 1;
}

.fv-status-pill {
	display: inline-flex;
	align-items: center;
	padding: 0.32rem 0.68rem;
	border-radius: 3px;
	border: 1px solid var(--fv-border);
	background: var(--fv-surface);
	font-size: 0.9rem;
	font-weight: 500;
	color: var(--fv-text-muted);
}

.fv-list-series,
.fv-list-column-value,
.fv-list-status {
	justify-self: start;
}

.fv-list-meta,
.fv-list-head-meta {
	justify-self: end;
}

@media (max-width: 992px) {
	.fv-list-toolbar {
		flex-wrap: wrap;
		align-items: stretch;
	}

	.fv-list-toolbar-left,
	.fv-list-toolbar-actions {
		width: 100%;
	}

	.fv-list-toolbar-actions {
		justify-content: flex-start;
		flex-wrap: wrap;
	}

	.fv-list-toolbar-search {
		flex: 1 1 100%;
	}

	.fv-list-search {
		max-width: none;
	}

	.fv-list-panel {
		max-height: calc(100vh - 248px);
	}

	.fv-list-pagination {
		flex-wrap: wrap;
	}
}

@media (max-width: 768px) {
	.fv-list-toolbar {
		padding: 12px;
	}

	.fv-list-toolbar-left,
	.fv-list-toolbar-actions {
		width: 100%;
	}

	.fv-list-toolbar-actions {
		justify-content: flex-start;
	}

	.fv-list-search {
		max-width: none;
	}

	.fv-list-head {
		display: none;
	}

	.fv-list-row {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-start;
		gap: 0.4rem 0.75rem;
		padding: 0.8rem 0.85rem;
		min-width: 760px;
	}

	.fv-list-head {
		min-width: 760px;
	}

	.fv-list-row > * {
		flex: 1 1 100%;
		min-width: 0;
	}



	.fv-list-head-meta,
	.fv-list-meta {
		justify-content: flex-start;
		flex-wrap: wrap;
	}

	.fv-list-id,
	.fv-list-series,
	.fv-list-updated,
	.fv-list-column-value,
	.fv-list-column-text {
		white-space: normal;
	}

	.fv-list-pagination {
		flex-direction: column;
		align-items: flex-start;
	}

	.fv-list-pagination-actions {
		width: 100%;
	}
}
</style>
