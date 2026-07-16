from frappe import _


def get_data():
    return [
        {
            "module_name": "Ampower Form Builder",
            "category": "Modules",
            "label": _("Ampower Form Builder"),
            "icon": "octicon octicon-file-directory",
            "type": "module",
            "description": "Dynamic form builder with drag-and-drop interface.",
        },
        {
            "module_name": "Print Builder",
            "category": "Modules",
            "label": _("Print Builder"),
            "icon": "octicon octicon-printer",
            "type": "module",
            "description": "Dynamic print format builder for form templates.",
        }
    ]
