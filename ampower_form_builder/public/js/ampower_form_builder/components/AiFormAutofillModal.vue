<template>
	<Teleport to="body">
		<div v-if="open" class="afb-ai-modal">
			<div class="afb-ai-backdrop" @click="handleClose" />
			<div class="afb-ai-shell" role="dialog" aria-modal="true">
				<header class="afb-ai-header">
					<div>
						<div class="afb-ai-kicker">{{ t("AI Autofill") }}</div>
						<h2>{{ t("Autofill with AI") }}</h2>
						<p>
							{{ t("Upload a PDF or image. We will OCR the file, map the text to the current form template, and apply the values to the viewer.") }}
						</p>
					</div>
					<button class="btn btn-default btn-sm" type="button" @click="handleClose">
						{{ t("Close") }}
					</button>
				</header>

				<div class="afb-ai-body">
					<section class="afb-ai-steps">
						<div class="afb-ai-step">
							<span class="afb-ai-step-index">1</span>
							<div>
								<h4>{{ t("Upload") }}</h4>
								<p>{{ t("Choose a PDF or image to extract text from the document.") }}</p>
							</div>
						</div>
						<div class="afb-ai-step">
							<span class="afb-ai-step-index">2</span>
							<div>
								<h4>{{ t("OCR + Map") }}</h4>
								<p>{{ t("Google Vision reads the document and OpenAI maps the values to the current form fields.") }}</p>
							</div>
						</div>
						<div class="afb-ai-step">
							<span class="afb-ai-step-index">3</span>
							<div>
								<h4>{{ t("Apply") }}</h4>
								<p>{{ t("The matched values are applied to the live form so you can review and submit.") }}</p>
							</div>
						</div>
					</section>

					<section class="afb-ai-panel">
						<div v-if="stage === 'idle'" class="afb-ai-dropzone" :class="{ 'is-dragging': isDragging }" @dragover.prevent="isDragging = true" @dragleave.prevent="isDragging = false" @drop.prevent="handleDrop">
							<input
								ref="fileInput"
								class="d-none"
								type="file"
								accept=".pdf,image/*,.png,.jpg,.jpeg,.webp,.gif,.bmp,.tif,.tiff"
								@change="handleFileSelect"
							>
							<div class="afb-ai-dropzone-copy">
								<div class="afb-ai-dropzone-title">{{ t("Drop a file here") }}</div>
								<div class="afb-ai-dropzone-subtitle">{{ t("or pick one from your device") }}</div>
								<div class="afb-ai-dropzone-hint">{{ t("Supported: PDF, PNG, JPG, JPEG, WEBP, GIF, BMP, TIF, TIFF") }}</div>
							</div>
							<div class="afb-ai-dropzone-actions">
								<button class="btn btn-primary" type="button" :disabled="busy" @click="browseFiles">
									{{ t("Choose File") }}
								</button>
							</div>
						</div>

						<div v-else class="afb-ai-progress-card">
							<div class="afb-ai-file-meta">
								<div class="afb-ai-file-name">{{ selectedFileName }}</div>
								<div class="afb-ai-file-subtitle">{{ statusMessage }}</div>
							</div>
							<div class="afb-ai-progress-track" :aria-valuenow="activeProgress" aria-valuemin="0" aria-valuemax="100">
								<div class="afb-ai-progress-fill" :style="{ width: `${activeProgress}%` }"></div>
							</div>
							<div class="afb-ai-progress-caption">
								<span>{{ activeProgress }}%</span>
								<span>{{ activeStageLabel }}</span>
							</div>

							<div v-if="stage === 'error'" class="afb-ai-error">
								<div class="afb-ai-error-title">{{ t("We could not finish the autofill") }}</div>
								<p>{{ errorMessage }}</p>
								<button class="btn btn-default btn-sm" type="button" @click="resetToIdle">
									{{ t("Try Another File") }}
								</button>
							</div>

							<div v-if="stage === 'uploading'" class="afb-ai-uploading-note">
								{{ t("Uploading to the server before background processing starts.") }}
							</div>
						</div>
					</section>
				</div>
			</div>
		</div>
	</Teleport>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";

const props = defineProps({
	open: { type: Boolean, default: false },
	templateName: { type: String, default: "" },
});

const emit = defineEmits(["close", "applied"]);

const t = window.__ || ((text) => text);

const fileInput = ref(null);
const isDragging = ref(false);
const stage = ref("idle");
const uploadProgress = ref(0);
const processingProgress = ref(0);
const statusMessage = ref("");
const errorMessage = ref("");
const jobId = ref("");
const selectedFile = ref(null);
const pollTimer = ref(null);
const uploadedFileDoc = ref(null);
const workflowToken = ref(0);
const uploadRequest = ref(null);

const busy = computed(() => stage.value === "uploading" || stage.value === "processing");
const selectedFileName = computed(() => selectedFile.value?.name || uploadedFileDoc.value?.file_name || t("No file selected"));
const activeProgress = computed(() => {
	if (stage.value === "uploading") return uploadProgress.value;
	if (stage.value === "processing") return processingProgress.value;
	if (stage.value === "error") return processingProgress.value || uploadProgress.value || 100;
	return 0;
});
const activeStageLabel = computed(() => {
	if (stage.value === "uploading") return t("Uploading");
	if (stage.value === "processing") return t("Processing");
	if (stage.value === "error") return t("Failed");
	return t("Ready");
});

const supportedExtensions = new Set(["pdf", "png", "jpg", "jpeg", "webp", "gif", "bmp", "tif", "tiff"]);

watch(() => props.open, (isOpen) => {
	if (isOpen) {
		resetToIdle();
		return;
	}
	stopPolling();
});

onBeforeUnmount(() => {
	stopPolling();
	stopUploadRequest();
});

function handleClose() {
	emit("close");
}

function browseFiles() {
	if (busy.value) return;
	fileInput.value?.click();
}

function handleFileSelect(event) {
	const file = event.target.files?.[0];
	event.target.value = "";
	if (!file) return;
	if (!isSupportedFile(file)) {
		errorMessage.value = t("Only PDF and image files are supported.");
		stage.value = "error";
		statusMessage.value = errorMessage.value;
		return;
	}
	selectedFile.value = file;
	startUpload(file);
}

function handleDrop(event) {
	isDragging.value = false;
	if (busy.value) return;
	const file = event.dataTransfer?.files?.[0];
	if (!file) return;
	if (!isSupportedFile(file)) {
		errorMessage.value = t("Only PDF and image files are supported.");
		stage.value = "error";
		statusMessage.value = errorMessage.value;
		return;
	}
	selectedFile.value = file;
	startUpload(file);
}

function isSupportedFile(file) {
	const lowerName = String(file?.name || "").toLowerCase();
	const mimeType = String(file?.type || "").toLowerCase();
	const ext = lowerName.includes(".") ? lowerName.split(".").pop() : "";
	return mimeType === "application/pdf" || mimeType.startsWith("image/") || supportedExtensions.has(ext);
}

function startUpload(file) {
	const token = nextWorkflowToken();
	stopUploadRequest();
	stage.value = "uploading";
	uploadProgress.value = 0;
	processingProgress.value = 0;
	statusMessage.value = t("Uploading the selected file...");
	errorMessage.value = "";
	uploadedFileDoc.value = null;
	jobId.value = "";
	stopPolling();

	const xhr = new XMLHttpRequest();
	uploadRequest.value = xhr;
	xhr.upload.addEventListener("progress", (event) => {
		if (!event.lengthComputable) return;
		uploadProgress.value = Math.max(1, Math.round((event.loaded / event.total) * 100));
	});
	xhr.addEventListener("error", () => {
		if (!isCurrentWorkflow(token)) return;
		stage.value = "error";
		errorMessage.value = t("The file upload failed. Please try again.");
		statusMessage.value = errorMessage.value;
	});
	xhr.onreadystatechange = async () => {
		if (!isCurrentWorkflow(token)) return;
		if (xhr.readyState !== XMLHttpRequest.DONE) return;
		uploadRequest.value = null;
		if (xhr.status !== 200) {
			stage.value = "error";
			errorMessage.value = parseUploadError(xhr.responseText) || t("The file upload failed.");
			statusMessage.value = errorMessage.value;
			return;
		}

		let response = null;
		try {
			response = JSON.parse(xhr.responseText);
		} catch (error) {
			stage.value = "error";
			errorMessage.value = t("The file upload returned an invalid response.");
			statusMessage.value = errorMessage.value;
			return;
		}

		const fileDoc = response?.message;
		if (!fileDoc?.name) {
			stage.value = "error";
			errorMessage.value = t("The file was uploaded but the server did not return a File record.");
			statusMessage.value = errorMessage.value;
			return;
		}

		uploadedFileDoc.value = fileDoc;
		statusMessage.value = t("File uploaded. Queueing background autofill...");
		await queueAutofill(fileDoc.name, token);
	};

	const formData = new FormData();
	formData.append("file", file, file.name);
	formData.append("is_private", "1");
	formData.append("folder", "Home");

	xhr.open("POST", "/api/method/upload_file", true);
	xhr.setRequestHeader("Accept", "application/json");
	xhr.setRequestHeader("X-Frappe-CSRF-Token", frappe.csrf_token);
	xhr.send(formData);
}

async function queueAutofill(fileDocname, token) {
	if (!isCurrentWorkflow(token)) return;
	if (!props.templateName) {
		stage.value = "error";
		errorMessage.value = t("Form template is missing.");
		statusMessage.value = errorMessage.value;
		return;
	}

	try {
		const { message } = await frappe.call({
			method: "ampower_form_builder.api.enqueue_ai_form_autofill",
			args: {
				file_docname: fileDocname,
				template_name: props.templateName,
			},
		});

		if (!isCurrentWorkflow(token)) return;
		jobId.value = message?.job_id || "";
		if (!jobId.value) {
			throw new Error(t("The server did not return an autofill job id."));
		}
		stage.value = "processing";
		statusMessage.value = t("OCR and field mapping are running in the background...");
		startPolling(jobId.value, token);
	} catch (error) {
		if (!isCurrentWorkflow(token)) return;
		stage.value = "error";
		errorMessage.value = error?.message || error?.exc || t("Unable to start AI autofill.");
		statusMessage.value = errorMessage.value;
	}
}

function startPolling(nextJobId, token) {
	stopPolling();
	pollTimer.value = window.setInterval(() => {
		pollStatus(nextJobId, token);
	}, 2000);
	pollStatus(nextJobId, token);
}

async function pollStatus(nextJobId, token) {
	if (!isCurrentWorkflow(token) || !nextJobId) return;

	try {
		const { message } = await frappe.call({
			method: "ampower_form_builder.api.get_ai_form_autofill_status",
			args: { job_id: nextJobId },
		});

		if (!isCurrentWorkflow(token)) return;
		if (!message) return;

		processingProgress.value = Number(message.progress || 0);
		statusMessage.value = message.message || t("Processing...");

		if (message.status === "failed") {
			stage.value = "error";
			errorMessage.value = message.error || message.message || t("Autofill failed.");
			stopPolling();
			return;
		}

		if (message.status === "completed" && message.result?.values) {
			stopPolling();
			stage.value = "idle";
			emit("applied", message.result);
			handleClose();
		}
	} catch (error) {
		if (!isCurrentWorkflow(token)) return;
		stage.value = "error";
		errorMessage.value = error?.message || error?.exc || t("Unable to check autofill status.");
		statusMessage.value = errorMessage.value;
		stopPolling();
	}
}

function resetToIdle() {
	stage.value = "idle";
	uploadProgress.value = 0;
	processingProgress.value = 0;
	statusMessage.value = t("Ready to upload.");
	errorMessage.value = "";
	jobId.value = "";
	selectedFile.value = null;
	uploadedFileDoc.value = null;
	stopPolling();
	stopUploadRequest();
	if (fileInput.value) {
		fileInput.value.value = "";
	}
}

function stopPolling() {
	if (pollTimer.value) {
		window.clearInterval(pollTimer.value);
		pollTimer.value = null;
	}
}

function stopUploadRequest() {
	if (!uploadRequest.value) return;
	try {
		uploadRequest.value.abort();
	} catch (error) {
		// Ignore aborted upload errors.
	}
	uploadRequest.value = null;
}

function nextWorkflowToken() {
	workflowToken.value += 1;
	return workflowToken.value;
}

function isCurrentWorkflow(token) {
	return workflowToken.value === token;
}

function parseUploadError(responseText) {
	if (!responseText) return "";
	try {
		const response = JSON.parse(responseText);
		return response?.exception || response?.message || "";
	} catch (error) {
		return responseText;
	}
}
</script>

<style scoped>
.afb-ai-modal {
	position: fixed;
	inset: 0;
	z-index: 1080;
	display: grid;
	place-items: center;
	padding: 24px;
}

.afb-ai-backdrop {
	position: absolute;
	inset: 0;
	background: rgba(12, 17, 29, 0.58);
	backdrop-filter: blur(10px);
}

.afb-ai-shell {
	position: relative;
	z-index: 1;
	width: min(1120px, 100%);
	max-height: min(90vh, 980px);
	overflow: auto;
	border-radius: 24px;
	background: linear-gradient(180deg, #fffdf9 0%, #ffffff 100%);
	box-shadow: 0 28px 80px rgba(17, 24, 39, 0.28);
	border: 1px solid rgba(148, 163, 184, 0.18);
	padding: 24px;
}

.afb-ai-header {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 20px;
	margin-bottom: 24px;
}

.afb-ai-kicker {
	font-size: 11px;
	font-weight: 700;
	letter-spacing: 0.16em;
	text-transform: uppercase;
	color: #7c2d12;
	margin-bottom: 8px;
}

.afb-ai-header h2 {
	margin: 0;
	font-size: 30px;
	line-height: 1.1;
	color: #111827;
}

.afb-ai-header p {
	margin: 10px 0 0;
	max-width: 720px;
	color: #4b5563;
}

.afb-ai-body {
	display: grid;
	grid-template-columns: 320px minmax(0, 1fr);
	gap: 20px;
}

.afb-ai-steps {
	display: flex;
	flex-direction: column;
	gap: 14px;
}

.afb-ai-step {
	display: flex;
	gap: 14px;
	padding: 16px;
	border-radius: 18px;
	background: linear-gradient(180deg, rgba(255, 247, 237, 0.92) 0%, rgba(255, 251, 245, 0.86) 100%);
	border: 1px solid rgba(249, 115, 22, 0.12);
}

.afb-ai-step-index {
	width: 30px;
	height: 30px;
	border-radius: 999px;
	display: grid;
	place-items: center;
	font-size: 12px;
	font-weight: 700;
	color: #9a3412;
	background: rgba(251, 146, 60, 0.16);
	flex: 0 0 auto;
}

.afb-ai-step h4 {
	margin: 0 0 4px;
	font-size: 15px;
	color: #111827;
}

.afb-ai-step p {
	margin: 0;
	font-size: 13px;
	line-height: 1.5;
	color: #4b5563;
}

.afb-ai-panel {
	min-height: 360px;
}

.afb-ai-dropzone,
.afb-ai-progress-card {
	min-height: 100%;
	border-radius: 22px;
	border: 1px dashed rgba(148, 163, 184, 0.45);
	background: linear-gradient(180deg, rgba(248, 250, 252, 0.92) 0%, rgba(255, 255, 255, 1) 100%);
	padding: 24px;
	display: flex;
	flex-direction: column;
	justify-content: center;
	gap: 18px;
}

.afb-ai-dropzone {
	align-items: center;
	text-align: center;
	cursor: pointer;
	transition: 0.18s ease;
}

.afb-ai-dropzone.is-dragging {
	border-color: #f97316;
	background: linear-gradient(180deg, rgba(255, 247, 237, 0.96) 0%, rgba(255, 255, 255, 1) 100%);
	transform: scale(1.01);
}

.afb-ai-dropzone-copy {
	display: flex;
	flex-direction: column;
	gap: 8px;
}

.afb-ai-dropzone-title {
	font-size: 22px;
	font-weight: 700;
	color: #111827;
}

.afb-ai-dropzone-subtitle {
	font-size: 15px;
	color: #4b5563;
}

.afb-ai-dropzone-hint {
	font-size: 12px;
	color: #6b7280;
}

.afb-ai-progress-card {
	justify-content: flex-start;
}

.afb-ai-file-meta {
	display: flex;
	flex-direction: column;
	gap: 6px;
}

.afb-ai-file-name {
	font-size: 18px;
	font-weight: 700;
	color: #111827;
	word-break: break-word;
}

.afb-ai-file-subtitle {
	font-size: 13px;
	color: #6b7280;
}

.afb-ai-progress-track {
	width: 100%;
	height: 14px;
	border-radius: 999px;
	background: rgba(226, 232, 240, 1);
	overflow: hidden;
}

.afb-ai-progress-fill {
	height: 100%;
	border-radius: inherit;
	background: linear-gradient(90deg, #f97316 0%, #fb7185 100%);
	transition: width 0.18s ease;
}

.afb-ai-progress-caption {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 16px;
	font-size: 12px;
	font-weight: 600;
	color: #6b7280;
}

.afb-ai-error {
	margin-top: 4px;
	padding: 16px;
	border-radius: 16px;
	background: rgba(254, 242, 242, 1);
	border: 1px solid rgba(248, 113, 113, 0.24);
	color: #991b1b;
}

.afb-ai-error-title {
	font-size: 15px;
	font-weight: 700;
	margin-bottom: 8px;
}

.afb-ai-error p {
	margin: 0 0 14px;
	white-space: pre-line;
	color: #b91c1c;
}

.afb-ai-uploading-note {
	font-size: 12px;
	color: #6b7280;
}

@media (max-width: 992px) {
	.afb-ai-body {
		grid-template-columns: 1fr;
	}
}

@media (max-width: 640px) {
	.afb-ai-modal {
		padding: 12px;
	}

	.afb-ai-shell {
		padding: 18px;
		border-radius: 18px;
	}

	.afb-ai-header {
		flex-direction: column;
	}

	.afb-ai-header h2 {
		font-size: 24px;
	}
}
</style>
