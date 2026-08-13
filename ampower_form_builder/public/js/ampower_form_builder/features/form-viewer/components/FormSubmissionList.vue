<template>
	<BaseListView
		:loading="loading"
		:has-items="hasItems"
		:search-value="searchValue"
		:search-placeholder="searchPlaceholder"
		:group-by-label="groupByLabel"
		:group-by-items="groupByItems"
		:loading-title="loadingTitle"
		:loading-copy="loadingCopy"
		:empty-title="emptyTitle"
		:empty-copy="emptyCopy"
		:show-add-menu="false"
		:show-action-menu="false"
		:show-refresh="false"
		:show-pagination="showPagination"
		:current-page="currentPage"
		:total-pages="totalPages"
		:pagination-label="paginationLabel"
		:previous-page-label="previousPageLabel"
		:next-page-label="nextPageLabel"
		:max-visible-pages="maxVisiblePages"
		:grid-template-columns="listGridTemplateColumns"
		@update:search-value="emit('update:searchValue', $event)"
		@previous-page="emit('previous-page')"
		@next-page="emit('next-page')"
		@go-to-page="emit('go-to-page', $event)"
		@group-by-select="emit('group-by-select', $event)"
	>
		<template #head>
			<span class="fv-list-id list-subject">{{ idLabel }}</span>
			<span class="fv-list-status">{{ statusLabel }}</span>
			<span v-for="column in columns" :key="column.fieldname || column.label" class="fv-list-column-value">
				{{ column.label }}
			</span>
			<span class="fv-list-head-meta fv-list-meta list-row-activity">
				{{ countLabel }}
			</span>
		</template>

		<button
			v-for="submission in submissions"
			:key="submission._name"
			type="button"
			class="fv-list-row"
			:aria-label="__('Open submission {0}', [submission._name])"
			@click="emit('open-submission', submission._name)"
		>
			<span class="fv-list-id list-subject">{{ submission._name }}</span>
			<span class="fv-list-status">
				<span class="fv-status-pill" :class="`is-${getSubmissionStatusTone(submission)}`">
					{{ getSubmissionStatusLabel(submission) }}
				</span>
			</span>
			<span v-for="column in columns" :key="column.fieldname || column.label" class="fv-list-column-value">
				<span class="fv-list-column-text" :title="String(getSubmissionColumnValue(submission, column) ?? '')">
					{{ getSubmissionColumnValue(submission, column) }}
				</span>
			</span>
			<span class="fv-list-head-meta fv-list-meta list-row-activity">
			</span>
		</button>
	</BaseListView>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import BaseListView from "../../../components/BaseListView.vue";

const props = defineProps({
	loading: { type: Boolean, default: false },
	hasItems: { type: Boolean, default: false },
	searchValue: { type: String, default: "" },
	searchPlaceholder: { type: String, default: "ID" },
	groupByLabel: { type: String, default: "Group By" },
	groupByItems: { type: Array, default: () => [] },
	loadingTitle: { type: String, default: "Loading reports..." },
	loadingCopy: { type: String, default: "Fetching saved entries for this form." },
	emptyTitle: { type: String, default: "No reports found" },
	emptyCopy: { type: String, default: "Create the first entry for this form to start collecting reports." },
	idLabel: { type: String, default: "ID" },
	statusLabel: { type: String, default: "Status" },
	countLabel: { type: String, default: "" },
	columns: { type: Array, default: () => [] },
	submissions: { type: Array, default: () => [] },
	getSubmissionStatusTone: { type: Function, default: () => "neutral" },
	getSubmissionStatusLabel: { type: Function, default: () => "" },
	getSubmissionColumnValue: { type: Function, default: () => "-" },
	showPagination: { type: Boolean, default: false },
	currentPage: { type: Number, default: 1 },
	totalPages: { type: Number, default: 1 },
	paginationLabel: { type: String, default: "" },
	previousPageLabel: { type: String, default: "Previous page" },
	nextPageLabel: { type: String, default: "Next page" },
	maxVisiblePages: { type: Number, default: 5 },
});

const emit = defineEmits([
	"update:searchValue",
	"group-by-select",
	"open-submission",
	"previous-page",
	"next-page",
	"go-to-page",
]);

const viewportWidth = ref(typeof window !== "undefined" ? window.innerWidth : 1024);

function handleResize() {
	if (typeof window === "undefined") return;
	viewportWidth.value = window.innerWidth;
}

onMounted(() => {
	if (typeof window === "undefined") return;
	window.addEventListener("resize", handleResize, { passive: true });
});

onBeforeUnmount(() => {
	if (typeof window === "undefined") return;
	window.removeEventListener("resize", handleResize);
});

const listGridTemplateColumns = computed(() => {
	const columnCount = Math.max(1, props.columns.length);
	const isCompact = viewportWidth.value < 768;
	const idMin = isCompact ? 112 : 140;
	const statusMin = isCompact ? 92 : 120;
	const columnMin = isCompact ? 120 : 150;
	const metaMin = isCompact ? 88 : 130;
	const dynamicColumns = Array.from({ length: columnCount }, () => `minmax(${columnMin}px, 1fr)`).join(" ");
	return `minmax(${idMin}px, 1.1fr) minmax(${statusMin}px, 0.85fr) ${dynamicColumns} ${metaMin}px`;
});
</script>

<style scoped>
.fv-list-head,
.fv-list-row {
	display: grid;
	grid-template-columns: var(--fv-list-grid-template, minmax(140px, 1.1fr) minmax(120px, 0.85fr) repeat(2, minmax(150px, 1fr)) 130px);
	gap: 8px;
	align-items: center;
}

.fv-list-head {
	padding: 0.8rem 1rem;
	border-bottom: 1px solid var(--border-color);
	background: var(--subtle-fg);
	font-size: 0.74rem;
	font-weight: 700;
	letter-spacing: 0.04em;
	text-transform: uppercase;
	color: var(--text-muted);
}

.fv-list-head > * {
	min-width: 0;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.fv-list-row {
	width: 100%;
	padding: 0.85rem 1rem;
	border: 0;
	border-bottom: 1px solid #e5e7eb;
	background: transparent;
	text-align: left;
	transition: background-color 0.16s ease;
	cursor: pointer;
}

.fv-list-row:hover,
.fv-list-row:focus-visible {
	background: var(--subtle-fg);
}

.fv-list-row:focus-visible {
	outline: 2px solid rgba(249, 115, 22, 0.35);
	outline-offset: -2px;
}

@media (max-width: 992px) {
	.fv-list-head,
	.fv-list-row {
		gap: 6px;
	}
}

@media (max-width: 768px) {
	.fv-list-head,
	.fv-list-row {
		gap: 6px;
		padding-inline: 0.75rem;
	}

	.fv-list-row {
		padding-block: 0.8rem;
	}
}

.fv-list-id,
.fv-list-column-value,
.fv-list-status,
.fv-list-head-meta {
	min-width: 0;
	overflow: hidden;
}

.fv-list-id {
	font-size: 0.93rem;
	font-weight: 700;
	color: var(--text-color);
	text-overflow: ellipsis;
	white-space: nowrap;
}

.fv-list-status {
	display: flex;
	align-items: center;
}

.fv-list-column-value {
	display: flex;
	align-items: center;
	font-size: 0.9rem;
	color: var(--text-muted);
}

.fv-list-head-meta {
	display: flex;
	align-items: center;
	justify-content: flex-end;
	gap: 10px;
	color: var(--text-muted);
}


.fv-status-pill {
	display: inline-flex;
	align-items: center;
	padding: 0.28rem 0.65rem;
	border: 1px solid var(--border-color);
	border-radius: var(--border-radius-tiny, 4px);
	background: var(--subtle-fg);
	color: #334155;
	font-size: 0.75rem;
	font-weight: 700;
	white-space: nowrap;
}

.fv-status-pill.is-submitted {
	background: rgba(22, 163, 74, 0.12);
	color: #15803d;
}

.fv-status-pill.is-draft,
.fv-status-pill.is-neutral {
	background: rgba(36, 144, 239, 0.12);
	color: #0f6cbd;
}

.fv-status-pill.is-cancelled {
	background: rgba(220, 38, 38, 0.08);
	color: #b91c1c;
}

.fv-list-column-text {
	display: inline-flex;
	align-items: center;
	gap: 8px;
	max-width: 100%;
	padding: 0.3rem 0;
	border: 0;
	background: transparent;
	font-size: 0.9rem;
	color: var(--text-muted);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

</style>
