import json
import os

import frappe


def execute():
	"""
	Import Payments workspace from JSON file.
	"""
	workspace_name = "Payments"
	
	# Check if workspace already exists
	if frappe.db.exists("Workspace", workspace_name):
		frappe.logger().info(f"Workspace {workspace_name} already exists, skipping import")
		return
	
	# Get workspace JSON file path
	app_path = frappe.get_app_path("payments")
	workspace_path = os.path.join(app_path, "config", "workspace.json")
	
	if not os.path.exists(workspace_path):
		frappe.logger().error(f"Workspace file not found at {workspace_path}")
		return
	
	# Read and import workspace
	with open(workspace_path, "r") as f:
		workspace_data = json.load(f)
	
	# Convert list fields to JSON strings (Frappe expects JSON strings, not lists)
	# Fields that need to be converted: content, charts, links, shortcuts, quick_lists, number_cards, custom_blocks
	list_fields = ["content", "charts", "links", "shortcuts", "quick_lists", "number_cards", "custom_blocks"]
	
	for field in list_fields:
		if field in workspace_data and isinstance(workspace_data[field], list):
			workspace_data[field] = json.dumps(workspace_data[field])
	
	# Create workspace document
	workspace = frappe.get_doc(workspace_data)
	workspace.insert(ignore_permissions=True)
	
	frappe.db.commit()
	frappe.logger().info(f"Successfully imported workspace: {workspace_name}")
