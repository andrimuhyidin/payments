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
	
	# content is a Long Text field that stores JSON string (default: "[]")
	# Ensure content is a JSON string, not a list
	if "content" in workspace_data:
		if isinstance(workspace_data["content"], list):
			workspace_data["content"] = json.dumps(workspace_data["content"])
		elif not isinstance(workspace_data["content"], str):
			workspace_data["content"] = "[]"
	else:
		workspace_data["content"] = "[]"
	
	# Extract child table data (these are Table fieldtypes)
	charts = workspace_data.pop("charts", [])
	links = workspace_data.pop("links", [])
	shortcuts = workspace_data.pop("shortcuts", [])
	quick_lists = workspace_data.pop("quick_lists", [])
	number_cards = workspace_data.pop("number_cards", [])
	custom_blocks = workspace_data.pop("custom_blocks", [])
	
	# Create workspace document (without child tables first)
	workspace = frappe.get_doc(workspace_data)
	
	# Add child table items using append() method
	for item in charts:
		workspace.append("charts", item)
	
	for item in links:
		workspace.append("links", item)
	
	for item in shortcuts:
		workspace.append("shortcuts", item)
	
	for item in quick_lists:
		workspace.append("quick_lists", item)
	
	for item in number_cards:
		workspace.append("number_cards", item)
	
	for item in custom_blocks:
		workspace.append("custom_blocks", item)
	
	workspace.insert(ignore_permissions=True)
	
	frappe.db.commit()
	frappe.logger().info(f"Successfully imported workspace: {workspace_name}")
