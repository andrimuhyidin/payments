"""
Manual script to import Payments workspace.
Run this via: bench --site [site-name] console
Then: exec(open('apps/payments/payments/utils/import_workspace_manual.py').read())
"""
import json
import os

import frappe


def import_workspace():
	"""Import Payments workspace from JSON file."""
	workspace_name = "Payments"
	
	# Check if workspace already exists
	if frappe.db.exists("Workspace", workspace_name):
		print(f"Workspace {workspace_name} already exists")
		workspace = frappe.get_doc("Workspace", workspace_name)
		print(f"Workspace details: {workspace.name}, Label: {workspace.label}")
		return workspace
	
	# Get workspace JSON file path
	app_path = frappe.get_app_path("payments")
	workspace_path = os.path.join(app_path, "config", "workspace.json")
	
	if not os.path.exists(workspace_path):
		print(f"ERROR: Workspace file not found at {workspace_path}")
		return None
	
	# Read and import workspace
	with open(workspace_path, "r") as f:
		workspace_data = json.load(f)
	
	# Create workspace document
	workspace = frappe.get_doc(workspace_data)
	workspace.insert(ignore_permissions=True)
	
	frappe.db.commit()
	print(f"✓ Successfully imported workspace: {workspace_name}")
	print(f"  Label: {workspace.label}")
	print(f"  Module: {workspace.module}")
	print(f"  Content items: {len(workspace.content)}")
	
	return workspace


if __name__ == "__main__" or "exec" in str(__file__):
	import_workspace()
