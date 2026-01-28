# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, add_days, today, flt
import json


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	chart = get_chart(data, filters)
	summary = get_summary(data)
	
	return columns, data, None, chart, summary


def get_columns(filters):
	group_by = filters.get("group_by", "gateway")
	
	columns = []
	
	if group_by == "gateway":
		columns.append({
			"label": _("Payment Gateway"),
			"fieldname": "group_field",
			"fieldtype": "Data",
			"width": 150
		})
	elif group_by == "status":
		columns.append({
			"label": _("Status"),
			"fieldname": "group_field",
			"fieldtype": "Data",
			"width": 120
		})
	elif group_by == "date":
		columns.append({
			"label": _("Date"),
			"fieldname": "group_field",
			"fieldtype": "Date",
			"width": 120
		})
	
	columns.extend([
		{
			"label": _("Total Transactions"),
			"fieldname": "total_transactions",
			"fieldtype": "Int",
			"width": 140
		},
		{
			"label": _("Successful"),
			"fieldname": "successful",
			"fieldtype": "Int",
			"width": 100
		},
		{
			"label": _("Failed"),
			"fieldname": "failed",
			"fieldtype": "Int",
			"width": 100
		},
		{
			"label": _("Success Rate (%)"),
			"fieldname": "success_rate",
			"fieldtype": "Percent",
			"width": 120
		},
		{
			"label": _("Total Amount"),
			"fieldname": "total_amount",
			"fieldtype": "Currency",
			"width": 140
		},
		{
			"label": _("Avg Amount"),
			"fieldname": "avg_amount",
			"fieldtype": "Currency",
			"width": 120
		}
	])
	
	return columns


def get_data(filters):
	conditions = get_conditions(filters)
	group_by = filters.get("group_by", "gateway")
	
	if group_by == "gateway":
		group_field = "integration_request_service"
	elif group_by == "status":
		group_field = "status"
	elif group_by == "date":
		group_field = "DATE(creation)"
	else:
		group_field = "integration_request_service"
	
	query = """
		SELECT
			{group_field} as group_field,
			COUNT(*) as total_transactions,
			SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as successful,
			SUM(CASE WHEN status = 'Failed' THEN 1 ELSE 0 END) as failed,
			SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) / COUNT(*) * 100 as success_rate
		FROM `tabIntegration Request`
		WHERE integration_request_service IN (
			SELECT name FROM `tabPayment Gateway`
		)
		{conditions}
		GROUP BY {group_field}
		ORDER BY total_transactions DESC
	""".format(group_field=group_field, conditions=conditions)
	
	data = frappe.db.sql(query, filters, as_dict=True)
	
	# Calculate amounts from data field
	for row in data:
		amounts = get_amounts_for_group(row["group_field"], filters, group_by)
		row["total_amount"] = amounts["total"]
		row["avg_amount"] = amounts["avg"]
		row["success_rate"] = round(row.get("success_rate") or 0, 2)
	
	return data


def get_amounts_for_group(group_value, filters, group_by):
	"""Calculate payment amounts from Integration Request data field."""
	conditions = get_conditions(filters)
	
	if group_by == "gateway":
		group_condition = "AND integration_request_service = %(group_value)s"
	elif group_by == "status":
		group_condition = "AND status = %(group_value)s"
	elif group_by == "date":
		group_condition = "AND DATE(creation) = %(group_value)s"
	else:
		group_condition = ""
	
	filters["group_value"] = group_value
	
	requests = frappe.db.sql("""
		SELECT data
		FROM `tabIntegration Request`
		WHERE integration_request_service IN (
			SELECT name FROM `tabPayment Gateway`
		)
		AND status = 'Completed'
		{conditions}
		{group_condition}
	""".format(conditions=conditions, group_condition=group_condition), filters, as_dict=True)
	
	total_amount = 0
	count = 0
	
	for req in requests:
		try:
			data = json.loads(req.data or "{}")
			amount = flt(data.get("amount", 0))
			if amount > 0:
				total_amount += amount
				count += 1
		except (json.JSONDecodeError, TypeError):
			pass
	
	return {
		"total": total_amount,
		"avg": total_amount / count if count > 0 else 0
	}


def get_conditions(filters):
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("AND creation >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("AND creation <= %(to_date)s")
	
	if filters.get("gateway"):
		conditions.append("AND integration_request_service = %(gateway)s")
	
	if filters.get("status"):
		conditions.append("AND status = %(status)s")
	
	return " ".join(conditions)


def get_chart(data, filters):
	if not data:
		return None
	
	group_by = filters.get("group_by", "gateway")
	
	labels = [str(row.get("group_field") or "Unknown") for row in data[:15]]
	successful = [row.get("successful") or 0 for row in data[:15]]
	failed = [row.get("failed") or 0 for row in data[:15]]
	
	chart_type = "bar" if group_by != "date" else "line"
	
	return {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": _("Successful"),
					"values": successful
				},
				{
					"name": _("Failed"),
					"values": failed
				}
			]
		},
		"type": chart_type,
		"colors": ["#36a2eb", "#ff6384"],
		"barOptions": {
			"stacked": True
		}
	}


def get_summary(data):
	if not data:
		return []
	
	total_transactions = sum(row.get("total_transactions") or 0 for row in data)
	total_successful = sum(row.get("successful") or 0 for row in data)
	total_failed = sum(row.get("failed") or 0 for row in data)
	total_amount = sum(row.get("total_amount") or 0 for row in data)
	
	overall_success_rate = (total_successful / total_transactions * 100) if total_transactions > 0 else 0
	
	return [
		{
			"value": total_transactions,
			"label": _("Total Transactions"),
			"datatype": "Int"
		},
		{
			"value": total_successful,
			"label": _("Successful"),
			"datatype": "Int",
			"indicator": "green"
		},
		{
			"value": total_failed,
			"label": _("Failed"),
			"datatype": "Int",
			"indicator": "red"
		},
		{
			"value": round(overall_success_rate, 1),
			"label": _("Success Rate (%)"),
			"datatype": "Percent"
		},
		{
			"value": total_amount,
			"label": _("Total Amount"),
			"datatype": "Currency"
		}
	]
