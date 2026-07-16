import AttachControl from "./components/controls/AttachControl.vue";
import CheckControl from "./components/controls/CheckControl.vue";
import DataControl from "./components/controls/DataControl.vue";
import LinkControl from "./components/controls/LinkControl.vue";
import RadioControl from "./components/controls/RadioControl.vue";
import SelectControl from "./components/controls/SelectControl.vue";
import TextControl from "./components/controls/TextControl.vue";
import TextEditorControl from "./components/controls/TextEditorControl.vue";

export function registerGlobalComponents(app) {
	app.component("AttachControl", AttachControl)
		.component("AttachImageControl", AttachControl)
		.component("CheckControl", CheckControl)
		.component("ColorControl", DataControl)
		.component("DataControl", DataControl)
		.component("DateControl", DataControl)
		.component("DatetimeControl", DataControl)
		.component("DynamicLinkControl", DataControl)
		.component("IntControl", DataControl)
		.component("NumberControl", DataControl)
		.component("LinkControl", LinkControl)
		.component("LongTextControl", TextControl)
		.component("RadioControl", RadioControl)
		.component("SelectControl", SelectControl)
		.component("SmallTextControl", TextControl)
		.component("TextEditorControl", TextEditorControl)
		.component("TimeControl", DataControl);
}
