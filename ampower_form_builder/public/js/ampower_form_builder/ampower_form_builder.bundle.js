import { createApp, reactive } from "vue";
import { createPinia } from "pinia";
import FormBuilderComponent from "./FormBuilder.vue";
import FormViewerComponent from "./features/form-viewer/FormViewerPage.vue";
import PrintBuilderComponent from "./print_builder/PrintBuilder.vue";
import { registerGlobalComponents } from "./globals.js";

const activeViewers = new Set();

function installGlobalSaveInterceptor() {
	const FormClass = globalThis.frappe?.ui?.form?.Form;
	if (!FormClass?.prototype || FormClass.prototype._afbAmpowerSaveInterceptorInstalled) return;

	const originalSave = FormClass.prototype.save;
	if (typeof originalSave !== "function") return;

	FormClass.prototype._afbAmpowerOriginalSave = originalSave;
	FormClass.prototype._afbAmpowerSaveInterceptorInstalled = true;
	FormClass.prototype.save = async function (save_action, callback, btn, on_error) {
		if (this._afbSkipSubmissionSync) {
			return originalSave.call(this, save_action, callback, btn, on_error);
		}

		const viewer = this._afbBoundViewer || findMatchingViewer(this);
		if (viewer?.syncSubmission && !viewer?.vm?.isReadOnly?.() && viewer?.vm?.canSyncSubmission?.()) {
			const submissionMethod = viewer?.getSubmissionMethod?.();
			const submissionName = await viewer.syncSubmission({
				method: submissionMethod,
			});
			const submissionFieldname = viewer?.props?.submissionFieldname || "";
			if (submissionName && submissionFieldname && this.doc?.[submissionFieldname] !== submissionName) {
				if (typeof this.set_value === "function") {
					await this.set_value(submissionFieldname, submissionName);
					this.refresh_field?.(submissionFieldname);
				} else {
					this.doc[submissionFieldname] = submissionName;
					this.refresh_field?.(submissionFieldname);
				}
			}
		}

		return originalSave.call(this, save_action, callback, btn, on_error);
	};
}

function registerViewer(viewer) {
	activeViewers.add(viewer);
	installGlobalSaveInterceptor();
}

function unregisterViewer(viewer) {
	activeViewers.delete(viewer);
}

function findMatchingViewer(frm) {
	const parentDoctype = frm?.doctype || "";
	const parentDocname = frm?.doc?.name || "";

	for (const viewer of activeViewers) {
		const viewerDoctype = viewer?.props?.parentDoctype || "";
		const viewerDocname = viewer?.props?.parentDocname || "";
		if (!viewerDoctype || viewerDoctype !== parentDoctype) continue;
		if (viewerDocname && parentDocname && viewerDocname !== parentDocname) continue;
		if (!viewerDocname && !parentDocname && typeof frm?.is_new === "function" && frm.is_new()) continue;
		return viewer;
	}

	return null;
}

class AmpowerVueMount {
	constructor({ wrapper, component, props = {} }) {
		this.wrapper = wrapper;
		this.component = component;
		this.props = reactive(props);
		this.app = null;
		this.vm = null;
		this.boundForm = null;
		this.mount();
	}

	mount() {
		try {
			const pinia = createPinia();
			const app = createApp(this.component, this.props);
			SetVueGlobals(app);
			app.use(pinia);
			registerGlobalComponents(app);
			this.app = app;
			this.vm = app.mount(this.wrapper);
			registerViewer(this);
			this.vm?.syncRouteContext?.(this.props);
		} catch (error) {
			console.error("Ampower Vue mount failed", error);
			frappe.msgprint({
				title: __("Form Load Error"),
				message: error?.message || __("Unable to load the Vue form."),
				indicator: "red",
			});
			throw error;
		}
	}

	update(nextProps = {}) {
		if (!this.app) return;
		Object.assign(this.props, nextProps);
		this.vm?.syncRouteContext?.(nextProps);
	}

	syncSubmission(options = {}) {
		return this.vm?.syncSubmission?.(options);
	}

	attachToForm(frm) {
		if (!frm || this.boundForm === frm) return;
		frm._afbBoundViewer = this;
		this.boundForm = frm;
		installGlobalSaveInterceptor();
	}

	destroy() {
		unregisterViewer(this);
		if (this.boundForm && this.boundForm._afbBoundViewer === this) {
			delete this.boundForm._afbBoundViewer;
			delete this.boundForm._afbSkipSubmissionSync;
		}
		this.boundForm = null;
		if (this.app) {
			this.app.unmount();
		}
		this.app = null;
		this.vm = null;
		if (this.wrapper?.innerHTML !== undefined) {
			this.wrapper.innerHTML = "";
		}
	}
}

class AmpowerFormBuilder extends AmpowerVueMount {
	constructor({ wrapper, page }) {
		super({
			wrapper,
			component: FormBuilderComponent,
			props: { page },
		});
	}
}

class AmpowerFormViewer extends AmpowerVueMount {
	constructor({
		wrapper,
		page,
		frm = null,
		templateName = "",
		builderRoute = "form_builder",
		embedded = false,
		parentDoctype = "",
		parentDocname = "",
		submissionName = "",
		submissionFieldname = "",
		autofillSubmissionStatus = "",
		beforeSubmit = null,
		onSubmissionSaved = null,
	}) {
		super({
			wrapper,
			component: FormViewerComponent,
			props: {
				page,
				frm,
				templateName,
				builderRoute,
				embedded,
				parentDoctype,
				parentDocname,
				submissionName,
				submissionFieldname,
				autofillSubmissionStatus,
				beforeSubmit,
				onSubmissionSaved,
			},
		});
		if (frm) {
			this.attachToForm(frm);
		}
	}
}

class AmpowerPrintBuilder extends AmpowerVueMount {
	constructor({ wrapper, page, templateName = "", formatName = "" }) {
		super({
			wrapper,
			component: PrintBuilderComponent,
			props: {
				page,
				templateName,
				formatName,
			},
		});
	}
}

frappe.provide("frappe.ui");
frappe.ui.AmpowerFormBuilder = AmpowerFormBuilder;
frappe.ui.AmpowerFormViewer = AmpowerFormViewer;
frappe.ui.AmpowerPrintBuilder = AmpowerPrintBuilder;
export default AmpowerFormBuilder;
