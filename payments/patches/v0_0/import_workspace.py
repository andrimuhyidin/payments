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
	
	# Create workspace document
	workspace = frappe.get_doc(workspace_data)
	workspace.insert(ignore_permissions=True)
	
	frappe.db.commit()
	frappe.logger().info(f"Successfully imported workspace: {workspace_name}")
