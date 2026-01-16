import json
import os

import frappe


def execute():
	"""
	Import or update Payments workspace from JSON file.
	"""
	workspace_name = "Payments"
	
	# Get workspace JSON file path
	app_path = frappe.get_app_path("payments")
	workspace_path = os.path.join(app_path, "config", "workspace.json")
	
	if not os.path.exists(workspace_path):
		frappe.logger().error(f"Workspace file not found at {workspace_path}")
		return
	
	# Read workspace data from JSON file
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
	
	# Auto-calculate link_count for Card Breaks
	# Count links between Card Breaks
	current_card_break_index = None
	for idx, link in enumerate(links):
		if link.get("type") == "Card Break":
			# Calculate link_count for previous card break
			if current_card_break_index is not None:
				link_count = idx - current_card_break_index - 1
				links[current_card_break_index]["link_count"] = link_count
			current_card_break_index = idx
		elif idx == len(links) - 1 and current_card_break_index is not None:
			# Last item, calculate for last card break
			link_count = idx - current_card_break_index
			links[current_card_break_index]["link_count"] = link_count
	
	# Validate workspace structure
	if not workspace_data.get("label"):
		frappe.logger().error("Workspace label is required")
		return
	
	if not workspace_data.get("module"):
		frappe.logger().error("Workspace module is required")
		return
	
	# Check if workspace already exists
	if frappe.db.exists("Workspace", workspace_name):
		# Update existing workspace
		workspace = frappe.get_doc("Workspace", workspace_name)
		
		# Update main fields (excluding child tables)
		for key, value in workspace_data.items():
			if key not in ["doctype", "name"]:
				setattr(workspace, key, value)
		
		# Clear existing child tables
		workspace.set("charts", [])
		workspace.set("links", [])
		workspace.set("shortcuts", [])
		workspace.set("quick_lists", [])
		workspace.set("number_cards", [])
		workspace.set("custom_blocks", [])
		
		# Add new child table items
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
		
		workspace.save(ignore_permissions=True)
		frappe.logger().info(
			f"Successfully updated workspace: {workspace_name} "
			f"(Links: {len(links)}, Shortcuts: {len(shortcuts)}, Number Cards: {len(number_cards)})"
		)
	else:
		# Create new workspace
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
		frappe.logger().info(
			f"Successfully imported workspace: {workspace_name} "
			f"(Links: {len(links)}, Shortcuts: {len(shortcuts)}, Number Cards: {len(number_cards)})"
		)
	
	frappe.db.commit()
