"""
AI Tools - Function definitions for MiMo function calling
Provides database query and action capabilities
"""

import os
import sys
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.database import Database
from utils.agent import get_proactive_agent, AUTONOMY_OFF, AUTONOMY_OBSERVER, AUTONOMY_SUGGESTER, AUTONOMY_ACTOR, AUTONOMY_AUTONOMOUS

db = Database()

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects"""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

def make_json_serializable(data):
    """Convert datetime/date objects to strings in a dict or list"""
    if isinstance(data, dict):
        return {k: make_json_serializable(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [make_json_serializable(item) for item in data]
    elif isinstance(data, (datetime, date)):
        return data.isoformat()
    return data

def get_tools() -> List[Dict]:
    """Return all available tools for the AI"""
    return [
        {
            "type": "function",
            "function": {
                "name": "execute_full_management_cycle",
                "description": "Execute a full background management sweep of the brewery. This analyzes the entire brewery situation, creates production/inventory/sales plans, and processes all proactive agent rules. Use this whenever the user asks you to manage or run the brewery.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_inventory",
                "description": "Query raw materials inventory. Can filter by category, low stock, or expiring items.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filter": {
                            "type": "string",
                            "enum": ["all", "low_stock", "expiring_soon", "by_category"],
                            "description": "Filter type"
                        },
                        "category": {
                            "type": "string",
                            "description": "Material category (required if filter is 'by_category')"
                        },
                        "days_ahead": {
                            "type": "integer",
                            "description": "Days to check for expiry (default 7)",
                            "default": 7
                        }
                    },
                    "required": ["filter"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_batches",
                "description": "Query production batches. Can filter by status.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["all", "planned", "in_progress", "fermenting", "completed", "cancelled"],
                            "description": "Batch status filter"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of batches to return",
                            "default": 10
                        }
                    },
                    "required": ["status"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_staff",
                "description": "Query staff members and their schedules.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query_type": {
                            "type": "string",
                            "enum": ["all_active", "available_today", "on_leave", "by_department"],
                            "description": "Query type"
                        },
                        "department": {
                            "type": "string",
                            "description": "Department name (required if query_type is 'by_department')"
                        }
                    },
                    "required": ["query_type"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_sales",
                "description": "Query sales orders and revenue data.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query_type": {
                            "type": "string",
                            "enum": ["recent_orders", "pending_orders", "today_revenue", "monthly_revenue", "top_products"],
                            "description": "Query type"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 10
                        }
                    },
                    "required": ["query_type"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_equipment",
                "description": "Query equipment status and maintenance schedules.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query_type": {
                            "type": "string",
                            "enum": ["all", "available", "in_use", "maintenance_due", "fermenters", "tanks"],
                            "description": "Query type"
                        }
                    },
                    "required": ["query_type"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_task",
                "description": "Create a new daily task and assign to a staff member.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Task title"
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed task description"
                        },
                        "assigned_to_id": {
                            "type": "integer",
                            "description": "Staff member ID to assign to"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "normal", "high", "urgent"],
                            "description": "Task priority"
                        },
                        "task_type": {
                            "type": "string",
                            "enum": ["production", "inventory", "maintenance", "quality", "delivery", "other"],
                            "description": "Task type"
                        }
                    },
                    "required": ["title", "priority", "task_type"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "update_task_status",
                "description": "Update the status of a daily task.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "integer",
                            "description": "Task ID"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed", "cancelled"],
                            "description": "New status"
                        },
                        "notes": {
                            "type": "string",
                            "description": "Optional notes about the status change"
                        }
                    },
                    "required": ["task_id", "status"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_daily_tasks",
                "description": "Get tasks for a specific date.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_date": {
                            "type": "string",
                            "description": "Date in YYYY-MM-DD format (default: today)"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["all", "pending", "in_progress", "completed"],
                            "description": "Filter by status"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "schedule_batch",
                "description": "Schedule a new production batch.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {
                            "type": "integer",
                            "description": "Product ID to produce"
                        },
                        "tank_id": {
                            "type": "integer",
                            "description": "Tank/equipment ID to use"
                        },
                        "planned_quantity": {
                            "type": "number",
                            "description": "Planned production quantity in liters"
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Start date in YYYY-MM-DD format"
                        },
                        "notes": {
                            "type": "string",
                            "description": "Production notes"
                        }
                    },
                    "required": ["product_id", "planned_quantity", "start_date"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_batch_status",
                "description": "Get detailed status of a production batch.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "batch_id": {
                            "type": "integer",
                            "description": "Batch ID"
                        }
                    },
                    "required": ["batch_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "check_stock_levels",
                "description": "Analyze stock levels and predict when items will run out.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Filter by category (optional)"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_products",
                "description": "Get list of brewery products.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "active_only": {
                            "type": "boolean",
                            "description": "Only return active products",
                            "default": True
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_staff_list",
                "description": "Get list of all staff members.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "active_only": {
                            "type": "boolean",
                            "description": "Only return active staff",
                            "default": True
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "analyze_costs",
                "description": "Analyze costs and profitability.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "period": {
                            "type": "string",
                            "enum": ["today", "week", "month", "quarter"],
                            "description": "Time period to analyze"
                        }
                    },
                    "required": ["period"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_dashboard_summary",
                "description": "Get a complete dashboard summary of brewery operations.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_products",
                "description": "Search products by name.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_staff",
                "description": "Search staff by name.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_tank_availability",
                "description": "Check which tanks are available for new batches.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "update_tank_status",
                "description": "Update the status of a tank (available, in_use, maintenance, cleaning).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tank_id": {
                            "type": "integer",
                            "description": "Tank/equipment ID to update"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["available", "in_use", "maintenance", "cleaning"],
                            "description": "New status for the tank"
                        }
                    },
                    "required": ["tank_id", "status"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "mark_tank_cleaned",
                "description": "Mark a tank as cleaned and set it to available status.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tank_id": {
                            "type": "integer",
                            "description": "Tank/equipment ID to mark as cleaned"
                        }
                    },
                    "required": ["tank_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "unassign_tank_batch",
                "description": "Remove batch assignment from a tank (sets tank to available).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tank_id": {
                            "type": "integer",
                            "description": "Tank/equipment ID to unassign"
                        }
                    },
                    "required": ["tank_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "log_temperature",
                "description": "Log a temperature reading for a fermentation tank.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tank_id": {
                            "type": "integer",
                            "description": "Tank/equipment ID"
                        },
                        "temperature": {
                            "type": "number",
                            "description": "Temperature value in Celsius"
                        },
                        "batch_id": {
                            "type": "integer",
                            "description": "Batch ID (optional, for tracking)"
                        },
                        "notes": {
                            "type": "string",
                            "description": "Additional notes"
                        }
                    },
                    "required": ["tank_id", "temperature"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_temperature_logs",
                "description": "Query temperature logs for a tank or batch.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tank_id": {
                            "type": "integer",
                            "description": "Tank ID (optional)"
                        },
                        "batch_id": {
                            "type": "integer",
                            "description": "Batch ID (optional)"
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Start date YYYY-MM-DD (optional)"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date YYYY-MM-DD (optional)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results (default 100)"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_temperature_alerts",
                "description": "Get temperature readings that are outside normal range.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "log_quality_for_batch",
                "description": "Log quality check data for a fermentation batch (pH, gravity, temperature, taste).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "batch_id": {
                            "type": "integer",
                            "description": "Batch ID"
                        },
                        "check_type": {
                            "type": "string",
                            "enum": ["pH", "gravity", "temperature", "taste", "appearance", "color", "aroma", "ABV", "other"],
                            "description": "Type of quality check"
                        },
                        "value": {
                            "type": "number",
                            "description": "Measured value"
                        },
                        "unit": {
                            "type": "string",
                            "description": "Unit of measurement"
                        },
                        "passed": {
                            "type": "boolean",
                            "description": "Whether the check passed"
                        },
                        "inspector": {
                            "type": "string",
                            "description": "Name of the inspector"
                        },
                        "notes": {
                            "type": "string",
                            "description": "Additional notes"
                        }
                    },
                    "required": ["batch_id", "check_type", "value", "passed"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "calculate_sugar_content",
                "description": "Calculate sugar content for wort or must based on gravity reading.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "gravity": {
                            "type": "number",
                            "description": "Specific gravity reading (e.g., 1.050)"
                        },
                        "volume_liters": {
                            "type": "number",
                            "description": "Volume in liters"
                        },
                        "sugar_type": {
                            "type": "string",
                            "enum": ["sucrose", "glucose", "fructose", "maltose"],
                            "description": "Type of sugar (default: sucrose)"
                        }
                    },
                    "required": ["gravity"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_rice_inventory",
                "description": "Query rice and grain inventory with stock levels.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": ["rice", "malt", "grain", "all"],
                            "description": "Filter by category (default: all)"
                        },
                        "low_stock_only": {
                            "type": "boolean",
                            "description": "Only return items below minimum stock level"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "add_rice_inventory",
                "description": "Add rice or grain to inventory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the rice/grain"
                        },
                        "category": {
                            "type": "string",
                            "enum": ["rice", "malt", "grain"],
                            "description": "Category"
                        },
                        "quantity": {
                            "type": "number",
                            "description": "Quantity to add"
                        },
                        "unit": {
                            "type": "string",
                            "enum": ["kg", "g", "ton"],
                            "description": "Unit of measurement"
                        },
                        "supplier": {
                            "type": "string",
                            "description": "Supplier name"
                        },
                        "origin": {
                            "type": "string",
                            "description": "Origin/region"
                        },
                        "cost_per_unit": {
                            "type": "number",
                            "description": "Cost per unit"
                        },
                        "min_quantity": {
                            "type": "number",
                            "description": "Minimum stock level for alerts"
                        }
                    },
                    "required": ["name", "category", "quantity", "unit"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "calculate_batch_ingredients",
                "description": "Calculate required ingredients for a batch based on recipe.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "recipe_id": {
                            "type": "integer",
                            "description": "Recipe ID"
                        },
                        "batch_size_liters": {
                            "type": "number",
                            "description": "Target batch size in liters"
                        }
                    },
                    "required": ["recipe_id", "batch_size_liters"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_fermentation_status",
                "description": "Get detailed fermentation status for all active batches.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_order",
                "description": "Create a new sales order for a customer.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "integer",
                            "description": "Customer ID"
                        },
                        "items": {
                            "type": "array",
                            "description": "Order items with product_id, quantity, and unit_price",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "product_id": {"type": "integer"},
                                    "quantity": {"type": "number"},
                                    "unit_price": {"type": "number"}
                                }
                            }
                        },
                        "delivery_date": {
                            "type": "string",
                            "description": "Delivery date in YYYY-MM-DD format"
                        },
                        "notes": {
                            "type": "string",
                            "description": "Order notes"
                        }
                    },
                    "required": ["customer_id", "items"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_customers",
                "description": "Search or list customers.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "search": {
                            "type": "string",
                            "description": "Search by name or phone"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 20
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "log_quality_check",
                "description": "Log a quality control check for a batch.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "batch_id": {
                            "type": "integer",
                            "description": "Batch ID"
                        },
                        "check_type": {
                            "type": "string",
                            "enum": ["pH", "gravity", "temperature", "taste", "appearance", "other"],
                            "description": "Type of check"
                        },
                        "value": {
                            "type": "string",
                            "description": "Measured value"
                        },
                        "passed": {
                            "type": "boolean",
                            "description": "Whether check passed"
                        },
                        "notes": {
                            "type": "string",
                            "description": "Additional notes"
                        }
                    },
                    "required": ["batch_id", "check_type", "value", "passed"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_quality_checks",
                "description": "Query quality control checks for a batch.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "batch_id": {
                            "type": "integer",
                            "description": "Batch ID"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 20
                        }
                    },
                    "required": ["batch_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_transactions",
                "description": "Query financial transactions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["income", "expense", "all"],
                            "description": "Transaction type"
                        },
                        "date_from": {
                            "type": "string",
                            "description": "Start date YYYY-MM-DD"
                        },
                        "date_to": {
                            "type": "string",
                            "description": "End date YYYY-MM-DD"
                        },
                        "category": {
                            "type": "string",
                            "description": "Category filter"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results",
                            "default": 50
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_recipes",
                "description": "List available beer recipes.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "style": {
                            "type": "string",
                            "description": "Beer style filter"
                        },
                        "search": {
                            "type": "string",
                            "description": "Search by name"
                        },
                        "active_only": {
                            "type": "boolean",
                            "description": "Only active recipes",
                            "default": True
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "update_order_status",
                "description": "Update the status of a sales order.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {
                            "type": "integer",
                            "description": "Order ID"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "confirmed", "processing", "shipped", "delivered", "cancelled"],
                            "description": "New status"
                        },
                        "notes": {
                            "type": "string",
                            "description": "Status change notes"
                        }
                    },
                    "required": ["order_id", "status"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "add_inventory_item",
                "description": "Add a new raw material to inventory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Material name"
                        },
                        "category": {
                            "type": "string",
                            "description": "Category (malt, hops, yeast, other)"
                        },
                        "quantity": {
                            "type": "number",
                            "description": "Initial quantity"
                        },
                        "unit": {
                            "type": "string",
                            "description": "Unit (kg, g, L, pcs)"
                        },
                        "min_quantity": {
                            "type": "number",
                            "description": "Minimum stock level"
                        },
                        "supplier": {
                            "type": "string",
                            "description": "Supplier name"
                        }
                    },
                    "required": ["name", "category", "quantity", "unit"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "update_inventory_quantity",
                "description": "Update inventory quantity (add or remove stock).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "material_id": {
                            "type": "integer",
                            "description": "Material ID"
                        },
                        "quantity_change": {
                            "type": "number",
                            "description": "Quantity to add (positive) or remove (negative)"
                        },
                        "reason": {
                            "type": "string",
                            "description": "Reason for change"
                        }
                    },
                    "required": ["material_id", "quantity_change"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_customer",
                "description": "Create a new customer record.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Customer name (business or individual)"
                        },
                        "type": {
                            "type": "string",
                            "enum": ["retail", "wholesale", "distributor", "restaurant", "bar"],
                            "description": "Customer type"
                        },
                        "contact_person": {
                            "type": "string",
                            "description": "Contact person name"
                        },
                        "phone": {
                            "type": "string",
                            "description": "Phone number"
                        },
                        "email": {
                            "type": "string",
                            "description": "Email address"
                        },
                        "address": {
                            "type": "string",
                            "description": "Street address"
                        },
                        "city": {
                            "type": "string",
                            "description": "City"
                        },
                        "province": {
                            "type": "string",
                            "description": "Province"
                        },
                        "credit_limit": {
                            "type": "number",
                            "description": "Credit limit amount (default: 0)"
                        },
                        "payment_terms": {
                            "type": "string",
                            "enum": ["COD", "NET7", "NET15", "NET30", "NET60"],
                            "description": "Payment terms (default: COD)"
                        },
                        "notes": {
                            "type": "string",
                            "description": "Additional notes"
                        }
                    },
                    "required": ["name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_transaction",
                "description": "Record a financial transaction (income or expense).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["income", "expense"],
                            "description": "Transaction type"
                        },
                        "category": {
                            "type": "string",
                            "description": "Category (e.g., 'sales', 'ingredients', 'utilities', 'salary', 'maintenance')"
                        },
                        "amount": {
                            "type": "number",
                            "description": "Transaction amount"
                        },
                        "description": {
                            "type": "string",
                            "description": "Transaction description"
                        },
                        "payment_method": {
                            "type": "string",
                            "enum": ["cash", "bank_transfer", "card", "credit"],
                            "description": "Payment method"
                        },
                        "transaction_date": {
                            "type": "string",
                            "description": "Transaction date YYYY-MM-DD (default: today)"
                        }
                    },
                    "required": ["type", "amount", "description"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "log_quality_record",
                "description": "Log a quality control record for a batch.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "batch_id": {
                            "type": "integer",
                            "description": "Batch ID"
                        },
                        "check_type": {
                            "type": "string",
                            "enum": ["pH", "gravity", "temperature", "taste", "appearance", "color", "aroma", "ABV", "other"],
                            "description": "Type of quality check"
                        },
                        "value": {
                            "type": "number",
                            "description": "Measured value"
                        },
                        "unit": {
                            "type": "string",
                            "description": "Unit of measurement"
                        },
                        "passed": {
                            "type": "boolean",
                            "description": "Whether the check passed"
                        },
                        "inspector": {
                            "type": "string",
                            "description": "Name of the inspector"
                        },
                        "notes": {
                            "type": "string",
                            "description": "Additional notes"
                        }
                    },
                    "required": ["batch_id", "check_type", "value", "passed"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_recipe_details",
                "description": "Get detailed recipe information including ingredients and mash steps.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "recipe_id": {
                            "type": "integer",
                            "description": "Recipe ID"
                        }
                    },
                    "required": ["recipe_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "update_batch_status",
                "description": "Update the status of a production batch.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "batch_id": {
                            "type": "integer",
                            "description": "Batch ID"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["planned", "brewing", "fermenting", "conditioning", "packaging", "completed", "cancelled"],
                            "description": "New status"
                        },
                        "actual_quantity": {
                            "type": "number",
                            "description": "Actual produced quantity (for completed batches)"
                        },
                        "notes": {
                            "type": "string",
                            "description": "Status change notes"
                        }
                    },
                    "required": ["batch_id", "status"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "assign_brewer",
                "description": "Assign a brewer (staff member) to a production batch.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "batch_id": {
                            "type": "integer",
                            "description": "Batch ID"
                        },
                        "brewer_id": {
                            "type": "integer",
                            "description": "Staff ID of the brewer"
                        }
                    },
                    "required": ["batch_id", "brewer_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_financial_summary",
                "description": "Get financial summary for a period.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "period": {
                            "type": "string",
                            "enum": ["today", "week", "month", "quarter", "year"],
                            "description": "Time period"
                        }
                    },
                    "required": ["period"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_customer_orders",
                "description": "Get order history for a customer.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "integer",
                            "description": "Customer ID"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of orders to return",
                            "default": 20
                        }
                    },
                    "required": ["customer_id"]
                }
            }
        },
        # ====================================================================
        # SELF-IMPROVEMENT & PROACTIVE PLANNING TOOLS
        # ====================================================================
        {
            "type": "function",
            "function": {
                "name": "analyze_system_performance",
                "description": "Analyze system performance, database health, and operational metrics. Use this proactively to identify bottlenecks.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "identify_improvement_opportunities",
                "description": "Identify specific improvement opportunities across inventory, production, quality, sales, and capacity. Proactively find issues before they become problems.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "generate_optimization_report",
                "description": "Generate a comprehensive optimization report with ROI calculations, efficiency scores, and actionable recommendations for the entire brewery.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_automation_workflow",
                "description": "Create an automation workflow for repetitive tasks. Use this to set up proactive automations for alerts, reminders, and scheduled actions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "workflow_type": {
                            "type": "string",
                            "enum": ["low_stock_alert", "quality_check_reminder", "tank_cleaning_schedule", "customer_reorder_reminder", "daily_briefing"],
                            "description": "Type of automation workflow to create"
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Optional parameters for the workflow"
                        }
                    },
                    "required": ["workflow_type"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "propose_feature_enhancement",
                "description": "Propose new feature enhancements based on usage patterns and data analysis. Use this to suggest improvements to the brewery manager system.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "usage_pattern": {
                            "type": "string",
                            "description": "Optional specific usage pattern to analyze"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "log_improvement",
                "description": "Log an improvement or change made to track impact and learn from outcomes. Use this after implementing any optimization.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "improvement_type": {
                            "type": "string",
                            "enum": ["process", "system", "workflow", "feature", "optimization"],
                            "description": "Type of improvement"
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of the improvement"
                        },
                        "impact": {
                            "type": "string",
                            "description": "Expected or actual impact"
                        },
                        "metrics_before": {
                            "type": "object",
                            "description": "Metrics before the improvement"
                        },
                        "metrics_after": {
                            "type": "object",
                            "description": "Metrics after the improvement"
                        }
                    },
                    "required": ["improvement_type", "description"]
                }
            }
        },
        # ====================================================================
        # PROACTIVE AGENT TOOLS (Phase 4 - Autonomous Operation)
        # ====================================================================
        {
            "type": "function",
            "function": {
                "name": "scan_for_opportunities",
                "description": "Proactively scan for opportunities and issues across all brewery operations. Use this regularly to stay ahead of problems.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "detect_anomalies",
                "description": "Detect anomalies in brewery operations including low stock, overdue batches, maintenance issues, and sales declines. Use this for proactive monitoring.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_autonomy_level",
                "description": "Get the current AI autonomy level and configuration settings.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "set_autonomy_level",
                "description": "Set the AI autonomy level. Controls how independently the AI can act.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "level": {
                            "type": "string",
                            "enum": ["off", "observer", "suggester", "actor", "autonomous"],
                            "description": "Autonomy level: off=disabled, observer=read-only, suggester=recommend only, actor=execute safe actions, autonomous=full planning"
                        }
                    },
                    "required": ["level"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_pending_suggestions",
                "description": "Get pending AI suggestions awaiting user review. Use this to show the user what improvements are waiting for approval.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "approve_suggestion",
                "description": "Approve and execute a pending AI suggestion by its index.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "index": {
                            "type": "integer",
                            "description": "Index of the suggestion to approve (from get_pending_suggestions)"
                        }
                    },
                    "required": ["index"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "dismiss_suggestion",
                "description": "Dismiss a pending AI suggestion by its index.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "index": {
                            "type": "integer",
                            "description": "Index of the suggestion to dismiss"
                        }
                    },
                    "required": ["index"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_goal_progress",
                "description": "Get progress for all brewery goals. Use this to track and report on strategic objectives.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "add_brewery_goal",
                "description": "Add a new brewery goal for the AI to track and work toward.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Goal name"
                        },
                        "description": {
                            "type": "string",
                            "description": "Goal description"
                        },
                        "target_value": {
                            "type": "number",
                            "description": "Target value to achieve"
                        },
                        "current_value": {
                            "type": "number",
                            "description": "Current value (default: 0)"
                        },
                        "unit": {
                            "type": "string",
                            "description": "Unit of measurement (e.g., 'VND', 'liters', '%')"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "normal", "high", "critical"],
                            "description": "Goal priority (default: normal)"
                        },
                        "category": {
                            "type": "string",
                            "enum": ["general", "production", "quality", "sales", "inventory", "finance"],
                            "description": "Goal category (default: general)"
                        }
                    },
                    "required": ["name", "description", "target_value"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "update_goal",
                "description": "Update progress toward a brewery goal.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "goal_id": {
                            "type": "integer",
                            "description": "Goal ID to update"
                        },
                        "current_value": {
                            "type": "number",
                            "description": "New current value"
                        }
                    },
                    "required": ["goal_id", "current_value"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_proactive_activity_log",
                "description": "Get recent proactive AI activity log showing what the AI has been doing autonomously.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of activities to return (default: 50)"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "read_system_file",
                "description": "Developer tool: Read the content of a file in the brewery manager system.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Relative or absolute path to the file"
                        }
                    },
                    "required": ["file_path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "write_system_file",
                "description": "Developer tool: Write content to a file in the system. Requires developer_mode to be enabled. Use this to patch or improve the system code.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file to modify"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write or append"
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["write", "append"],
                            "description": "Write mode (write replaces file content, append adds to the end)"
                        }
                    },
                    "required": ["file_path", "content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "execute_system_command",
                "description": "Developer tool: Execute a bash command on the host. Requires developer_mode to be enabled.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The bash command string to execute"
                        }
                    },
                    "required": ["command"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "toggle_developer_mode",
                "description": "Enable or disable Developer Mode (allow AI to alter system code and run shell commands). Enable this if user asks you to improve the system.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "enabled": {
                            "type": "boolean",
                            "description": "True to enable developer powers, False to disable."
                        }
                    },
                    "required": ["enabled"]
                }
            }
        }
    ]

def execute_tool(name: str, args: Dict) -> Any:
    """Execute a tool function and return the result"""
    try:
        if name == "query_inventory":
            return _query_inventory(args)
        elif name == "query_batches":
            return _query_batches(args)
        elif name == "query_staff":
            return _query_staff(args)
        elif name == "query_sales":
            return _query_sales(args)
        elif name == "query_equipment":
            return _query_equipment(args)
        elif name == "create_task":
            return _create_task(args)
        elif name == "update_task_status":
            return _update_task_status(args)
        elif name == "get_daily_tasks":
            return _get_daily_tasks(args)
        elif name == "schedule_batch":
            return _schedule_batch(args)
        elif name == "get_batch_status":
            return _get_batch_status(args)
        elif name == "check_stock_levels":
            return _check_stock_levels(args)
        elif name == "get_products":
            return _get_products(args)
        elif name == "get_staff_list":
            return _get_staff_list(args)
        elif name == "analyze_costs":
            return _analyze_costs(args)
        elif name == "get_dashboard_summary":
            return _get_dashboard_summary()
        elif name == "search_products":
            return _search_products(args)
        elif name == "search_staff":
            return _search_staff(args)
        elif name == "get_tank_availability":
            return _get_tank_availability()
        elif name == "update_tank_status":
            return _update_tank_status(args)
        elif name == "mark_tank_cleaned":
            return _mark_tank_cleaned(args)
        elif name == "unassign_tank_batch":
            return _unassign_tank_batch(args)
        elif name == "create_order":
            return _create_order(args)
        elif name == "query_customers":
            return _query_customers(args)
        elif name == "log_quality_check":
            return _log_quality_check(args)
        elif name == "query_quality_checks":
            return _query_quality_checks(args)
        elif name == "query_transactions":
            return _query_transactions(args)
        elif name == "query_recipes":
            return _query_recipes(args)
        elif name == "update_order_status":
            return _update_order_status(args)
        elif name == "add_inventory_item":
            return _add_inventory_item(args)
        elif name == "update_inventory_quantity":
            return _update_inventory_quantity(args)
        elif name == "create_customer":
            return _create_customer(args)
        elif name == "create_transaction":
            return _create_transaction(args)
        elif name == "log_quality_record":
            return _log_quality_record(args)
        elif name == "get_recipe_details":
            return _get_recipe_details(args)
        elif name == "update_batch_status":
            return _update_batch_status(args)
        elif name == "assign_brewer":
            return _assign_brewer(args)
        elif name == "get_financial_summary":
            return _get_financial_summary(args)
        elif name == "get_customer_orders":
            return _get_customer_orders(args)
        elif name == "log_temperature":
            return _log_temperature(args)
        elif name == "query_temperature_logs":
            return _query_temperature_logs(args)
        elif name == "get_temperature_alerts":
            return _get_temperature_alerts()
        elif name == "log_quality_for_batch":
            return _log_quality_for_batch(args)
        elif name == "calculate_sugar_content":
            return _calculate_sugar_content(args)
        elif name == "query_rice_inventory":
            return _query_rice_inventory(args)
        elif name == "add_rice_inventory":
            return _add_rice_inventory(args)
        elif name == "calculate_batch_ingredients":
            return _calculate_batch_ingredients(args)
        elif name == "get_fermentation_status":
            return _get_fermentation_status()
        # Self-improvement tools
        elif name == "analyze_system_performance":
            return _analyze_system_performance()
        elif name == "identify_improvement_opportunities":
            return _identify_improvement_opportunities()
        elif name == "generate_optimization_report":
            return _generate_optimization_report()
        elif name == "create_automation_workflow":
            return _create_automation_workflow(args.get('workflow_type'), args.get('parameters'))
        elif name == "propose_feature_enhancement":
            return _propose_feature_enhancement(args.get('usage_pattern'))
        elif name == "log_improvement":
            return _log_improvement(args.get('improvement_type'), args.get('description'), 
                                   args.get('impact'), args.get('metrics_before'), args.get('metrics_after'))
        # Proactive agent tools
        elif name == "scan_for_opportunities":
            return scan_for_opportunities()
        elif name == "detect_anomalies":
            return detect_anomalies()
        elif name == "get_autonomy_level":
            return get_autonomy_level()
        elif name == "set_autonomy_level":
            return set_autonomy_level(args.get('level'))
        elif name == "get_pending_suggestions":
            return get_pending_suggestions()
        elif name == "approve_suggestion":
            return approve_suggestion(args.get('index'))
        elif name == "dismiss_suggestion":
            return dismiss_suggestion(args.get('index'))
        elif name == "get_goal_progress":
            return get_goal_progress()
        elif name == "add_brewery_goal":
            return add_brewery_goal(args.get('name'), args.get('description'), args.get('target_value'),
                                    args.get('current_value', 0), args.get('unit', ''),
                                    args.get('priority', 'normal'), args.get('category', 'general'))
        elif name == "update_goal":
            return update_goal(args.get('goal_id'), args.get('current_value'))
        elif name == "get_proactive_activity_log":
            return get_proactive_activity_log(args.get('limit', 50))
        elif name == "execute_full_management_cycle":
            return _execute_full_management_cycle()
        else:
            return {"error": f"Unknown tool: {name}"}
    except Exception as e:
        return {"error": str(e)}

def _query_inventory(args: Dict) -> Dict:
    conn = db.get_connection()
    cursor = conn.cursor()
    filter_type = args.get('filter', 'all')
    
    if filter_type == 'all':
        cursor.execute("SELECT * FROM raw_materials ORDER BY name LIMIT 50")
    elif filter_type == 'low_stock':
        cursor.execute("SELECT * FROM raw_materials WHERE quantity <= min_quantity ORDER BY name")
    elif filter_type == 'expiring_soon':
        days = args.get('days_ahead', 7)
        future_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
        cursor.execute("SELECT * FROM raw_materials WHERE expiry_date <= ? AND expiry_date IS NOT NULL ORDER BY expiry_date", (future_date,))
    elif filter_type == 'by_category':
        category = args.get('category', '')
        cursor.execute("SELECT * FROM raw_materials WHERE category = ? ORDER BY name", (category,))
    
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return make_json_serializable({"items": items, "count": len(items)})

def _query_batches(args: Dict) -> Dict:
    conn = db.get_connection()
    cursor = conn.cursor()
    status = args.get('status', 'all')
    limit = args.get('limit', 10)

    query = """
        SELECT pb.*, p.name as product_name, e.name as tank_name
        FROM production_batches pb
        LEFT JOIN products p ON pb.product_id = p.id
        LEFT JOIN equipment e ON pb.tank_id = e.id
    """

    if status == 'all':
        query += " ORDER BY pb.created_at DESC LIMIT ?"
        cursor.execute(query, (limit,))
    else:
        query += " WHERE pb.status = ? ORDER BY pb.created_at DESC LIMIT ?"
        cursor.execute(query, (status, limit))

    batches = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return make_json_serializable({"batches": batches, "count": len(batches)})

def _query_staff(args: Dict) -> Dict:
    conn = db.get_connection()
    cursor = conn.cursor()
    query_type = args.get('query_type', 'all_active')
    
    if query_type == 'all_active':
        cursor.execute("SELECT * FROM staff WHERE is_active = 1 ORDER BY name")
    elif query_type == 'available_today':
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT s.* FROM staff s
            WHERE s.is_active = 1 AND s.id NOT IN (
                SELECT staff_id FROM staff_schedule WHERE schedule_date = ? AND shift = 'leave'
            )
            ORDER BY s.name
        """, (today,))
    elif query_type == 'on_leave':
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT s.* FROM staff s
            JOIN staff_schedule ss ON s.id = ss.staff_id
            WHERE ss.schedule_date = ? AND ss.shift = 'leave'
        """, (today,))
    elif query_type == 'by_department':
        dept = args.get('department', '')
        cursor.execute("SELECT * FROM staff WHERE department = ? AND is_active = 1 ORDER BY name", (dept,))
    
    staff = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return make_json_serializable({"staff": staff, "count": len(staff)})

def _query_sales(args: Dict) -> Dict:
    conn = db.get_connection()
    cursor = conn.cursor()
    query_type = args.get('query_type', 'recent_orders')
    limit = args.get('limit', 10)
    
    if query_type == 'recent_orders':
        cursor.execute("""
            SELECT so.*, c.name as customer_name
            FROM sales_orders so
            JOIN customers c ON so.customer_id = c.id
            ORDER BY so.created_at DESC LIMIT ?
        """, (limit,))
    elif query_type == 'pending_orders':
        cursor.execute("""
            SELECT so.*, c.name as customer_name
            FROM sales_orders so
            JOIN customers c ON so.customer_id = c.id
            WHERE so.status IN ('pending', 'confirmed')
            ORDER BY so.delivery_date
        """)
    elif query_type == 'today_revenue':
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("SELECT COALESCE(SUM(total_amount), 0) as revenue FROM sales_orders WHERE order_date = ?", (today,))
        result = cursor.fetchone()
        conn.close()
        return {"date": today, "revenue": result[0] if result else 0}
    elif query_type == 'monthly_revenue':
        month_start = datetime.now().replace(day=1).strftime('%Y-%m-%d')
        cursor.execute("SELECT COALESCE(SUM(total_amount), 0) as revenue FROM sales_orders WHERE order_date >= ?", (month_start,))
        result = cursor.fetchone()
        conn.close()
        return {"revenue": result[0] if result else 0}
    elif query_type == 'top_products':
        cursor.execute("""
            SELECT p.name, SUM(oi.quantity) as total_sold, SUM(oi.subtotal) as total_revenue
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            GROUP BY oi.product_id
            ORDER BY total_sold DESC LIMIT ?
        """, (limit,))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return make_json_serializable({"results": results, "count": len(results)})

def _query_equipment(args: Dict) -> Dict:
    conn = db.get_connection()
    cursor = conn.cursor()
    query_type = args.get('query_type', 'all')
    
    if query_type == 'all':
        cursor.execute("SELECT * FROM equipment ORDER BY equipment_type, name")
    elif query_type == 'available':
        cursor.execute("SELECT * FROM equipment WHERE status = 'available' ORDER BY equipment_type, name")
    elif query_type == 'in_use':
        cursor.execute("SELECT * FROM equipment WHERE status = 'in_use' ORDER BY equipment_type, name")
    elif query_type == 'maintenance_due':
        cursor.execute("""
            SELECT e.*, ms.task_name, ms.next_due
            FROM equipment e
            JOIN maintenance_schedule ms ON e.id = ms.equipment_id
            WHERE ms.next_due <= datetime('now', '+7 days')
            ORDER BY ms.next_due
        """)
    elif query_type == 'fermenters':
        cursor.execute("SELECT * FROM equipment WHERE equipment_type = 'fermenter' ORDER BY name")
    elif query_type == 'tanks':
        cursor.execute("SELECT * FROM equipment WHERE equipment_type IN ('fermenter', 'tank') ORDER BY name")
    
    equipment = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return make_json_serializable({"equipment": equipment, "count": len(equipment)})

def _create_task(args: Dict) -> Dict:
    conn = db.get_connection()
    cursor = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    
    cursor.execute("""
        INSERT INTO daily_tasks (task_date, task_type, title, description, assigned_to, priority, status)
        VALUES (?, ?, ?, ?, ?, ?, 'pending')
    """, (today, args.get('task_type', 'other'), args['title'],
          args.get('description'), args.get('assigned_to_id'), args.get('priority', 'normal')))
    
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"success": True, "task_id": task_id, "message": f"Task created: {args['title']}"}

def _update_task_status(args: Dict) -> Dict:
    conn = db.get_connection()
    cursor = conn.cursor()
    
    if args['status'] == 'completed':
        cursor.execute("""
            UPDATE daily_tasks SET status = ?, completed_at = CURRENT_TIMESTAMP, notes = ?
            WHERE id = ?
        """, (args['status'], args.get('notes'), args['task_id']))
    else:
        cursor.execute("""
            UPDATE daily_tasks SET status = ?, notes = ?
            WHERE id = ?
        """, (args['status'], args.get('notes'), args['task_id']))
    
    conn.commit()
    conn.close()
    return {"success": True, "message": f"Task {args['task_id']} updated to {args['status']}"}

def _get_daily_tasks(args: Dict) -> Dict:
    conn = db.get_connection()
    cursor = conn.cursor()
    task_date = args.get('task_date', datetime.now().strftime('%Y-%m-%d'))
    status = args.get('status', 'all')
    
    query = """
        SELECT dt.*, s.name as assignee_name
        FROM daily_tasks dt
        LEFT JOIN staff s ON dt.assigned_to = s.id
        WHERE dt.task_date = ?
    """
    
    if status != 'all':
        query += " AND dt.status = ?"
        cursor.execute(query + " ORDER BY dt.priority DESC, dt.created_at", (task_date, status))
    else:
        cursor.execute(query + " ORDER BY dt.priority DESC, dt.created_at", (task_date,))
    
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return make_json_serializable({"date": task_date, "tasks": tasks, "count": len(tasks)})

def _schedule_batch(args: Dict) -> Dict:
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT MAX(id) as max_id FROM production_batches")
    result = cursor.fetchone()
    next_num = (result[0] or 0) + 1
    batch_number = f"BATCH-{next_num:04d}"
    
    cursor.execute("""
        INSERT INTO production_batches (batch_number, product_id, tank_id, planned_quantity, 
                                        status, start_date, notes)
        VALUES (?, ?, ?, ?, 'planned', ?, ?)
    """, (batch_number, args['product_id'], args.get('tank_id'),
          args['planned_quantity'], args['start_date'], args.get('notes')))
    
    if args.get('tank_id'):
        cursor.execute("UPDATE equipment SET status = 'in_use', current_batch_id = ? WHERE id = ?",
                       (cursor.lastrowid, args['tank_id']))
    
    conn.commit()
    batch_id = cursor.lastrowid
    conn.close()
    return {"success": True, "batch_id": batch_id, "batch_number": batch_number}

def _get_batch_status(args: Dict) -> Dict:
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT pb.*, p.name as product_name, e.name as tank_name, s.name as brewer_name
        FROM production_batches pb
        LEFT JOIN products p ON pb.product_id = p.id
        LEFT JOIN equipment e ON pb.tank_id = e.id
        LEFT JOIN staff s ON pb.brewer_id = s.id
        WHERE pb.id = ?
    """, (args['batch_id'],))
    
    batch = cursor.fetchone()
    conn.close()
    
    if batch:
        return make_json_serializable({"batch": dict(batch)})
    return {"error": "Batch not found"}

def _check_stock_levels(args: Dict) -> Dict:
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT name, quantity, min_quantity, unit,
               CASE WHEN quantity <= min_quantity THEN 'low' ELSE 'ok' END as status
        FROM raw_materials
        WHERE quantity <= min_quantity * 1.5
        ORDER BY quantity / NULLIF(min_quantity, 0)
    """)
    
    low_items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return make_json_serializable({"low_stock_items": low_items, "count": len(low_items)})

def _get_products(args: Dict) -> Dict:
    conn = db.get_connection()
    cursor = conn.cursor()
    
    if args.get('active_only', True):
        cursor.execute("SELECT * FROM products WHERE is_active = 1 ORDER BY name")
    else:
        cursor.execute("SELECT * FROM products ORDER BY name")
    
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return make_json_serializable({"products": products, "count": len(products)})

def _get_staff_list(args: Dict) -> Dict:
    conn = db.get_connection()
    cursor = conn.cursor()
    
    if args.get('active_only', True):
        cursor.execute("SELECT * FROM staff WHERE is_active = 1 ORDER BY name")
    else:
        cursor.execute("SELECT * FROM staff ORDER BY name")
    
    staff = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return make_json_serializable({"staff": staff, "count": len(staff)})

def _analyze_costs(args: Dict) -> Dict:
    conn = db.get_connection()
    cursor = conn.cursor()
    period = args.get('period', 'month')
    
    if period == 'today':
        date_filter = datetime.now().strftime('%Y-%m-%d')
    elif period == 'week':
        date_filter = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    elif period == 'month':
        date_filter = datetime.now().replace(day=1).strftime('%Y-%m-%d')
    elif period == 'quarter':
        month = datetime.now().month
        quarter_start = datetime.now().replace(month=((month - 1) // 3) * 3 + 1, day=1).strftime('%Y-%m-%d')
        date_filter = quarter_start
    
    cursor.execute("""
        SELECT type, category, SUM(amount) as total
        FROM financial_transactions
        WHERE transaction_date >= ?
        GROUP BY type, category
        ORDER BY total DESC
    """, (date_filter,))
    
    transactions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"period": period, "transactions": transactions}

def _get_dashboard_summary() -> Dict:
    conn = db.get_connection()
    cursor = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    
    cursor.execute("SELECT COUNT(*) FROM production_batches WHERE status IN ('in_progress', 'fermenting')")
    active_batches = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM sales_orders WHERE order_date = ? AND status = 'pending'", (today,))
    pending_orders = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM raw_materials WHERE quantity <= min_quantity")
    low_stock = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM daily_tasks WHERE task_date = ? AND status != 'completed'", (today,))
    pending_tasks = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM staff WHERE is_active = 1")
    active_staff = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM equipment WHERE status = 'available'")
    available_equipment = cursor.fetchone()[0]
    
    conn.close()
    return {
        "active_batches": active_batches,
        "pending_orders": pending_orders,
        "low_stock_items": low_stock,
        "pending_tasks": pending_tasks,
        "active_staff": active_staff,
        "available_equipment": available_equipment
    }

def _search_products(args: Dict) -> Dict:
    conn = db.get_connection()
    cursor = conn.cursor()
    query = f"%{args['query']}%"
    cursor.execute("SELECT * FROM products WHERE name LIKE ? AND is_active = 1 ORDER BY name", (query,))
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return make_json_serializable({"products": products, "count": len(products)})

def _search_staff(args: Dict) -> Dict:
    conn = db.get_connection()
    cursor = conn.cursor()
    query = f"%{args['query']}%"
    cursor.execute("SELECT * FROM staff WHERE name LIKE ? AND is_active = 1 ORDER BY name", (query,))
    staff = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return make_json_serializable({"staff": staff, "count": len(staff)})

def _get_tank_availability() -> Dict:
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM equipment 
        WHERE equipment_type IN ('fermenter', 'tank') AND status = 'available'
        ORDER BY capacity DESC
    """)
    tanks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return make_json_serializable({"available_tanks": tanks, "count": len(tanks)})

def _create_order(args: Dict) -> Dict:
    conn = db.get_connection()
    cursor = conn.cursor()
    
    total_amount = sum(item['quantity'] * item['unit_price'] for item in args['items'])
    
    cursor.execute("""
        INSERT INTO sales_orders (customer_id, status, total_amount, delivery_date, notes)
        VALUES (?, 'pending', ?, ?, ?)
    """, (args['customer_id'], total_amount, args.get('delivery_date'), args.get('notes')))
    
    order_id = cursor.lastrowid
    
    for item in args['items']:
        subtotal = item['quantity'] * item['unit_price']
        cursor.execute("""
            INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal)
            VALUES (?, ?, ?, ?, ?)
        """, (order_id, item['product_id'], item['quantity'], item['unit_price'], subtotal))
    
    conn.commit()
    conn.close()
    return {"success": True, "order_id": order_id, "total_amount": total_amount}

def _query_customers(args: Dict) -> Dict:
    conn = db.get_connection()
    cursor = conn.cursor()
    search = args.get('search', '')
    limit = args.get('limit', 20)
    
    if search:
        query = f"%{search}%"
        cursor.execute("SELECT * FROM customers WHERE name LIKE ? OR phone LIKE ? ORDER BY name LIMIT ?", (query, query, limit))
    else:
        cursor.execute("SELECT * FROM customers ORDER BY name LIMIT ?", (limit,))
    
    customers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return make_json_serializable({"customers": customers, "count": len(customers)})

def _log_quality_check(args: Dict) -> Dict:
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO quality_records (batch_id, check_type, check_date, value, passed, notes)
        VALUES (?, ?, datetime('now'), ?, ?, ?)
    """, (args['batch_id'], args['check_type'], args['value'], args['passed'], args.get('notes')))
    
    check_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"success": True, "check_id": check_id, "message": f"Quality check logged: {args['check_type']} = {args['value']} ({'PASS' if args['passed'] else 'FAIL'})"}

def _query_quality_checks(args: Dict) -> Dict:
    conn = db.get_connection()
    cursor = conn.cursor()
    limit = args.get('limit', 20)
    cursor.execute("""
        SELECT qr.*, pb.batch_number 
        FROM quality_records qr
        JOIN production_batches pb ON qr.batch_id = pb.id
        WHERE qr.batch_id = ?
        ORDER BY qr.check_date DESC LIMIT ?
    """, (args['batch_id'], limit))
    
    checks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return make_json_serializable({"checks": checks, "count": len(checks)})

def _query_transactions(args: Dict) -> Dict:
    conn = db.get_connection()
    cursor = conn.cursor()
    tx_type = args.get('type', 'all')
    limit = args.get('limit', 50)
    
    query = "SELECT * FROM financial_transactions WHERE 1=1"
    params = []
    
    if tx_type != 'all':
        query += " AND type = ?"
        params.append(tx_type)
    
    if args.get('date_from'):
        query += " AND transaction_date >= ?"
        params.append(args['date_from'])
    
    if args.get('date_to'):
        query += " AND transaction_date <= ?"
        params.append(args['date_to'])
    
    if args.get('category'):
        query += " AND category = ?"
        params.append(args['category'])
    
    query += " ORDER BY transaction_date DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    transactions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return make_json_serializable({"transactions": transactions, "count": len(transactions)})

def _query_recipes(args: Dict) -> Dict:
    conn = db.get_connection()
    cursor = conn.cursor()
    active_only = args.get('active_only', True)
    
    query = "SELECT * FROM recipes"
    conditions = []
    params = []
    
    if active_only:
        conditions.append("is_active = 1")
    
    if args.get('style'):
        conditions.append("style = ?")
        params.append(args['style'])
    
    if args.get('search'):
        conditions.append("name LIKE ?")
        params.append(f"%{args['search']}%")
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY name"
    cursor.execute(query, params)
    recipes = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return make_json_serializable({"recipes": recipes, "count": len(recipes)})

def _update_order_status(args: Dict) -> Dict:
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE sales_orders SET status = ?, notes = ? WHERE id = ?",
                   (args['status'], args.get('notes'), args['order_id']))
    
    conn.commit()
    conn.close()
    return {"success": True, "message": f"Order {args['order_id']} updated to {args['status']}"}

def _add_inventory_item(args: Dict) -> Dict:
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO raw_materials (name, category, quantity, unit, min_quantity, supplier)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (args['name'], args['category'], args['quantity'], args['unit'],
          args.get('min_quantity', 0), args.get('supplier')))
    
    material_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"success": True, "material_id": material_id, "message": f"Added {args['name']} to inventory ({args['quantity']} {args['unit']})"}

def _update_inventory_quantity(args: Dict) -> Dict:
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name, quantity, unit FROM raw_materials WHERE id = ?", (args['material_id'],))
    material = cursor.fetchone()
    
    if not material:
        conn.close()
        return {"error": "Material not found"}
    
    new_quantity = material['quantity'] + args['quantity_change']
    
    if new_quantity < 0:
        conn.close()
        return {"error": f"Insufficient stock. Current: {material['quantity']} {material['unit']}"}
    
    cursor.execute("UPDATE raw_materials SET quantity = ? WHERE id = ?", (new_quantity, args['material_id']))
    conn.commit()
    conn.close()
    
    return {"success": True, "message": f"Updated {material['name']}: {material['quantity']} -> {new_quantity} {material['unit']}"}

def _create_customer(args: Dict) -> Dict:
    """Create a new customer"""
    try:
        customer_id = db.add_customer({
            'name': args['name'],
            'type': args.get('type', 'retail'),
            'contact_person': args.get('contact_person'),
            'phone': args.get('phone'),
            'email': args.get('email'),
            'address': args.get('address'),
            'city': args.get('city'),
            'province': args.get('province'),
            'credit_limit': args.get('credit_limit', 0),
            'payment_terms': args.get('payment_terms', 'COD'),
            'notes': args.get('notes')
        })
        return {"success": True, "customer_id": customer_id, "message": f"Customer '{args['name']}' created successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _create_transaction(args: Dict) -> Dict:
    """Create a financial transaction"""
    try:
        transaction_date = args.get('transaction_date', datetime.now().strftime('%Y-%m-%d'))
        transaction_id = db.add_transaction({
            'type': args['type'],
            'category': args.get('category'),
            'amount': args['amount'],
            'description': args['description'],
            'payment_method': args.get('payment_method'),
            'transaction_date': transaction_date
        })
        return {"success": True, "transaction_id": transaction_id, "message": f"Transaction recorded: {args['type']} of {args['amount']:,} VND for {args['description']}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _log_quality_record(args: Dict) -> Dict:
    """Log a quality control record"""
    try:
        record_id = db.add_quality_record({
            'batch_id': args['batch_id'],
            'check_type': args['check_type'],
            'value': args['value'],
            'unit': args.get('unit'),
            'passed': 1 if args['passed'] else 0,
            'inspector': args.get('inspector'),
            'notes': args.get('notes')
        })
        status = "PASSED" if args['passed'] else "FAILED"
        return {"success": True, "record_id": record_id, "message": f"Quality check recorded: {args['check_type']} = {args['value']} {args.get('unit', '')} ({status})"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _get_recipe_details(args: Dict) -> Dict:
    """Get detailed recipe information"""
    try:
        recipe = db.get_recipe_details(args['recipe_id'])
        if recipe:
            return make_json_serializable({"success": True, "recipe": recipe})
        return {"success": False, "error": "Recipe not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _update_batch_status(args: Dict) -> Dict:
    """Update batch status"""
    try:
        success = db.update_batch_status(
            args['batch_id'],
            args['status'],
            args.get('actual_quantity')
        )
        if success:
            return {"success": True, "message": f"Batch {args['batch_id']} status updated to {args['status']}"}
        return {"success": False, "error": "Batch not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _assign_brewer(args: Dict) -> Dict:
    """Assign a brewer to a batch"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Update batch with brewer
        cursor.execute("""
            UPDATE production_batches 
            SET brewer_id = ?
            WHERE id = ?
        """, (args['brewer_id'], args['batch_id']))
        
        # Get brewer name
        cursor.execute("SELECT name FROM staff WHERE id = ?", (args['brewer_id'],))
        brewer = cursor.fetchone()
        
        conn.commit()
        conn.close()
        
        if brewer:
            return {"success": True, "message": f"Brewer '{brewer['name']}' assigned to batch {args['batch_id']}"}
        return {"success": False, "error": "Brewer not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _get_financial_summary(args: Dict) -> Dict:
    """Get financial summary for a period"""
    try:
        period = args['period']
        today = datetime.now()
        
        if period == 'today':
            start_date = today.strftime('%Y-%m-%d')
            end_date = start_date
        elif period == 'week':
            start_date = (today - timedelta(days=7)).strftime('%Y-%m-%d')
            end_date = today.strftime('%Y-%m-%d')
        elif period == 'month':
            start_date = today.replace(day=1).strftime('%Y-%m-%d')
            end_date = today.strftime('%Y-%m-%d')
        elif period == 'quarter':
            quarter_month = ((today.month - 1) // 3) * 3 + 1
            start_date = today.replace(month=quarter_month, day=1).strftime('%Y-%m-%d')
            end_date = today.strftime('%Y-%m-%d')
        elif period == 'year':
            start_date = today.replace(month=1, day=1).strftime('%Y-%m-%d')
            end_date = today.strftime('%Y-%m-%d')
        else:
            start_date = None
            end_date = None
        
        summary = db.get_financial_summary(start_date, end_date)
        
        return make_json_serializable({
            "success": True,
            "period": period,
            "start_date": start_date,
            "end_date": end_date,
            "summary": summary
        })
    except Exception as e:
        return {"success": False, "error": str(e)}

def _get_customer_orders(args: Dict) -> Dict:
    """Get order history for a customer"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        limit = args.get('limit', 20)
        
        cursor.execute("""
            SELECT so.*, c.name as customer_name
            FROM sales_orders so
            JOIN customers c ON so.customer_id = c.id
            WHERE so.customer_id = ?
            ORDER BY so.order_date DESC
            LIMIT ?
        """, (args['customer_id'], limit))
        
        orders = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return make_json_serializable({
            "success": True,
            "customer_id": args['customer_id'],
            "orders": orders,
            "count": len(orders)
        })
    except Exception as e:
        return {"success": False, "error": str(e)}

def _update_tank_status(args: Dict) -> Dict:
    """Update tank status"""
    try:
        tank_id = args['tank_id']
        status = args['status']
        success = db.update_equipment_status(tank_id, status)
        if success:
            return {"success": True, "message": f"Tank {tank_id} status updated to '{status}'"}
        return {"success": False, "error": "Tank not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _mark_tank_cleaned(args: Dict) -> Dict:
    """Mark a tank as cleaned"""
    try:
        tank_id = args['tank_id']
        success = db.mark_tank_cleaned(tank_id)
        if success:
            return {"success": True, "message": f"Tank {tank_id} marked as cleaned and set to available. Next cleaning due in 7 days."}
        return {"success": False, "error": "Tank not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _unassign_tank_batch(args: Dict) -> Dict:
    """Remove batch assignment from a tank"""
    try:
        tank_id = args['tank_id']
        success = db.update_equipment_status(tank_id, 'available', None)
        if success:
            return {"success": True, "message": f"Tank {tank_id} unassigned and set to available"}
        return {"success": False, "error": "Tank not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _log_temperature(args: Dict) -> Dict:
    """Log temperature reading for a tank"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO temperature_logs (tank_id, batch_id, temperature, logged_by, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (args['tank_id'], args.get('batch_id'), args['temperature'],
              args.get('logged_by', 'AI'), args.get('notes')))
        
        log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {"success": True, "log_id": log_id, 
                "message": f"Temperature {args['temperature']}°C logged for tank {args['tank_id']}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _query_temperature_logs(args: Dict) -> Dict:
    """Query temperature logs"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT tl.*, e.name as tank_name, pb.batch_number
            FROM temperature_logs tl
            LEFT JOIN equipment e ON tl.tank_id = e.id
            LEFT JOIN production_batches pb ON tl.batch_id = pb.id
            WHERE 1=1
        """
        params = []
        
        if args.get('tank_id'):
            query += " AND tl.tank_id = ?"
            params.append(args['tank_id'])
        if args.get('batch_id'):
            query += " AND tl.batch_id = ?"
            params.append(args['batch_id'])
        if args.get('start_date'):
            query += " AND tl.logged_at >= ?"
            params.append(args['start_date'])
        if args.get('end_date'):
            query += " AND tl.logged_at <= ?"
            params.append(args['end_date'])
        
        limit = args.get('limit', 100)
        query += f" ORDER BY tl.logged_at DESC LIMIT {limit}"
        
        cursor.execute(query, params)
        logs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return make_json_serializable({"success": True, "logs": logs, "count": len(logs)})
    except Exception as e:
        return {"success": False, "error": str(e)}

def _get_temperature_alerts() -> Dict:
    """Get temperature alerts (outside normal range)"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT tl.*, e.name as tank_name,
                   CASE 
                       WHEN tl.temperature < 10 THEN 'too_low'
                       WHEN tl.temperature > 30 THEN 'too_high'
                       ELSE 'normal'
                   END as alert_type
            FROM temperature_logs tl
            JOIN equipment e ON tl.tank_id = e.id
            WHERE tl.temperature < 10 OR tl.temperature > 30
            ORDER BY tl.logged_at DESC
            LIMIT 50
        """)
        
        alerts = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return make_json_serializable({"success": True, "alerts": alerts, "count": len(alerts)})
    except Exception as e:
        return {"success": False, "error": str(e)}

def _log_quality_for_batch(args: Dict) -> Dict:
    """Log quality check for a batch"""
    try:
        record_id = db.add_quality_record({
            'batch_id': args['batch_id'],
            'check_type': args['check_type'],
            'value': args['value'],
            'unit': args.get('unit'),
            'passed': 1 if args['passed'] else 0,
            'inspector': args.get('inspector', 'AI'),
            'notes': args.get('notes')
        })
        
        status = "PASSED" if args['passed'] else "FAILED"
        return {"success": True, "record_id": record_id,
                "message": f"Quality check: {args['check_type']} = {args['value']} {args.get('unit', '')} ({status})"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _calculate_sugar_content(args: Dict) -> Dict:
    """Calculate sugar content from gravity"""
    try:
        gravity = args['gravity']
        volume = args.get('volume_liters', 20)
        sugar_type = args.get('sugar_type', 'sucrose')
        
        # Plato formula: extract = ((Brix * gravity) / 100)
        # Approximate: Brix = ((gravity - 1) * 1000) / 4
        brix = ((gravity - 1) * 1000) / 4
        
        # Sugar concentration in g/L
        sugar_concentration = (brix * gravity) * 10  # Approximation
        
        # Total sugar in volume
        total_sugar = sugar_concentration * volume
        
        return {
            "success": True,
            "gravity": gravity,
            "plato": round(brix, 2),
            "sugar_concentration_g_per_L": round(sugar_concentration, 2),
            "total_sugar_g": round(total_sugar, 2),
            "volume_liters": volume
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def _query_rice_inventory(args: Dict) -> Dict:
    """Query rice and grain inventory"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        category = args.get('category', 'all')
        low_stock = args.get('low_stock_only', False)
        
        query = "SELECT * FROM raw_materials WHERE 1=1"
        params = []
        
        if category == 'rice':
            query += " AND (name LIKE '%gạo%' OR name LIKE '%rice%' OR category = 'rice')"
        elif category == 'malt':
            query += " AND (name LIKE '%malt%' OR category = 'malt')"
        elif category == 'grain':
            query += " AND (name LIKE '%lúa%' OR name LIKE '%grain%' OR category IN ('rice', 'malt'))"
        
        if low_stock:
            query += " AND quantity <= min_quantity"
        
        query += " ORDER BY category, name"
        
        cursor.execute(query, params)
        items = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return make_json_serializable({"success": True, "items": items, "count": len(items)})
    except Exception as e:
        return {"success": False, "error": str(e)}

def _add_rice_inventory(args: Dict) -> Dict:
    """Add rice/grain to inventory"""
    try:
        material_id = db.add_raw_material({
            'name': args['name'],
            'category': args['category'],
            'quantity': args['quantity'],
            'unit': args['unit'],
            'supplier': args.get('supplier'),
            'origin': args.get('origin'),
            'cost_per_unit': args.get('cost_per_unit', 0),
            'min_quantity': args.get('min_quantity', 0)
        })
        
        return {"success": True, "material_id": material_id,
                "message": f"Added {args['quantity']} {args['unit']} of {args['name']} to inventory"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _calculate_batch_ingredients(args: Dict) -> Dict:
    """Calculate required ingredients for a batch"""
    try:
        recipe_id = args['recipe_id']
        target_volume = args['batch_size_liters']
        
        recipe = db.get_recipe_details(recipe_id)
        if not recipe:
            return {"success": False, "error": "Recipe not found"}
        
        base_volume = recipe.get('batch_size', 20)
        scale_factor = target_volume / base_volume
        
        ingredients = []
        
        for fermentable in recipe.get('fermentables', []):
            ingredients.append({
                "name": fermentable['name'],
                "type": "fermentable",
                "amount": round(fermentable['amount'] * scale_factor, 2),
                "unit": fermentable.get('unit', 'kg')
            })
        
        for hop in recipe.get('hops', []):
            ingredients.append({
                "name": hop['name'],
                "type": "hop",
                "amount": round(hop['amount'] * scale_factor, 1),
                "unit": hop.get('unit', 'g')
            })
        
        if recipe.get('yeast'):
            ingredients.append({
                "name": recipe['yeast']['name'],
                "type": "yeast",
                "amount": round(target_volume / 20, 1),  # Scale yeast proportionally
                "unit": "packs"
            })
        
        return make_json_serializable({
            "success": True,
            "recipe_name": recipe['name'],
            "base_volume": base_volume,
            "target_volume": target_volume,
            "scale_factor": round(scale_factor, 2),
            "ingredients": ingredients
        })
    except Exception as e:
        return {"success": False, "error": str(e)}

def _get_fermentation_status() -> Dict:
    """Get detailed fermentation status"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                pb.id as batch_id,
                pb.batch_number,
                pb.status,
                pb.start_date,
                pb.planned_quantity,
                pb.actual_quantity,
                p.name as product_name,
                p.style as product_style,
                e.name as tank_name,
                e.capacity as tank_capacity,
                s.name as brewer_name,
                julianday('now') - julianday(pb.start_date) as days_in_fermentation
            FROM production_batches pb
            LEFT JOIN products p ON pb.product_id = p.id
            LEFT JOIN equipment e ON pb.tank_id = e.id
            LEFT JOIN staff s ON pb.brewer_id = s.id
            WHERE pb.status IN ('brewing', 'fermenting', 'conditioning')
            ORDER BY pb.start_date DESC
        """)
        
        batches = [dict(row) for row in cursor.fetchall()]
        
        # Get latest quality checks for each batch
        for batch in batches:
            cursor.execute("""
                SELECT check_type, value, unit, passed, check_date
                FROM quality_records
                WHERE batch_id = ?
                ORDER BY check_date DESC
                LIMIT 10
            """, (batch['batch_id'],))
            batch['recent_checks'] = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return make_json_serializable({"success": True, "batches": batches, "count": len(batches)})
    except Exception as e:
        return {"success": False, "error": str(e)}

# ============================================================================
# SELF-IMPROVEMENT & PROACTIVE PLANNING TOOLS
# ============================================================================

def _analyze_system_performance() -> Dict:
    """Analyze system performance and identify bottlenecks"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        metrics = {}
        
        # 1. Database size and table counts
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row['name'] for row in cursor.fetchall()]
        
        table_stats = {}
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = cursor.fetchone()['count']
            table_stats[table] = count
        
        metrics['table_counts'] = table_stats
        
        # 2. Recent activity (last 24 hours)
        cursor.execute("""
            SELECT COUNT(*) as count FROM production_batches 
            WHERE created_at >= datetime('now', '-1 day')
        """)
        recent_batches = cursor.fetchone()['count']
        
        cursor.execute("""
            SELECT COUNT(*) as count FROM sales_orders 
            WHERE created_at >= datetime('now', '-1 day')
        """)
        recent_orders = cursor.fetchone()['count']
        
        cursor.execute("""
            SELECT COUNT(*) as count FROM daily_tasks 
            WHERE created_at >= datetime('now', '-1 day')
        """)
        recent_tasks = cursor.fetchone()['count']
        
        metrics['recent_activity'] = {
            'new_batches_24h': recent_batches,
            'new_orders_24h': recent_orders,
            'new_tasks_24h': recent_tasks
        }
        
        # 3. Operational efficiency indicators
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled
            FROM production_batches
            WHERE created_at >= datetime('now', '-30 day')
        """)
        batch_efficiency = dict(cursor.fetchone())
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) as delivered,
                SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled
            FROM sales_orders
            WHERE created_at >= datetime('now', '-30 day')
        """)
        order_efficiency = dict(cursor.fetchone())
        
        metrics['efficiency_30d'] = {
            'batches': batch_efficiency,
            'orders': order_efficiency
        }
        
        # 4. Data quality issues
        cursor.execute("SELECT COUNT(*) as count FROM raw_materials WHERE quantity < 0")
        negative_inventory = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM production_batches WHERE status = 'planned' AND start_date < date('now')")
        overdue_batches = cursor.fetchone()['count']
        
        metrics['data_quality'] = {
            'negative_inventory_items': negative_inventory,
            'overdue_planned_batches': overdue_batches
        }
        
        # 5. Staff workload
        cursor.execute("""
            SELECT s.name, COUNT(dt.id) as task_count
            FROM staff s
            LEFT JOIN daily_tasks dt ON s.id = dt.assigned_to 
                AND dt.status IN ('pending', 'in_progress')
                AND dt.task_date = date('now')
            WHERE s.is_active = 1
            GROUP BY s.id
            ORDER BY task_count DESC
        """)
        staff_workload = [dict(row) for row in cursor.fetchall()]
        
        metrics['staff_workload'] = staff_workload
        
        conn.close()
        
        return make_json_serializable({
            "success": True,
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return {"success": False, "error": str(e)}

def _identify_improvement_opportunities() -> Dict:
    """Identify specific improvement opportunities based on data patterns"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        opportunities = []
        
        # 1. Inventory optimization
        cursor.execute("""
            SELECT name, quantity, min_quantity, 
                   CASE WHEN quantity < min_quantity THEN 'low' 
                        WHEN quantity > min_quantity * 3 THEN 'excess' 
                        ELSE 'normal' END as status
            FROM raw_materials
            WHERE quantity < min_quantity OR quantity > min_quantity * 3
        """)
        inventory_issues = [dict(row) for row in cursor.fetchall()]
        
        if inventory_issues:
            low_stock = [i for i in inventory_issues if i['status'] == 'low']
            excess_stock = [i for i in inventory_issues if i['status'] == 'excess']
            
            if low_stock:
                opportunities.append({
                    "category": "inventory",
                    "priority": "high",
                    "title": "Low stock items detected",
                    "description": f"{len(low_stock)} items below minimum stock level",
                    "items": [i['name'] for i in low_stock[:5]],
                    "recommendation": "Set up automatic reorder alerts or increase min_quantity"
                })
            
            if excess_stock:
                opportunities.append({
                    "category": "inventory",
                    "priority": "low",
                    "title": "Excess stock detected",
                    "description": f"{len(excess_stock)} items with excess inventory",
                    "items": [i['name'] for i in excess_stock[:5]],
                    "recommendation": "Consider reducing order quantities or promotions"
                })
        
        # 2. Production scheduling efficiency
        cursor.execute("""
            SELECT COUNT(*) as planned_count
            FROM production_batches
            WHERE status = 'planned' AND start_date > date('now', '+7 days')
        """)
        far_future_planned = cursor.fetchone()['planned_count']
        
        if far_future_planned > 5:
            opportunities.append({
                "category": "production",
                "priority": "medium",
                "title": "Long-term planning detected",
                "description": f"{far_future_planned} batches planned more than 7 days ahead",
                "recommendation": "Consider just-in-time scheduling to reduce uncertainty"
            })
        
        # 3. Tank utilization
        cursor.execute("""
            SELECT 
                COUNT(*) as total_tanks,
                SUM(CASE WHEN status = 'available' THEN 1 ELSE 0 END) as available,
                SUM(CASE WHEN status = 'in_use' THEN 1 ELSE 0 END) as in_use
            FROM equipment
            WHERE equipment_type IN ('fermenter', 'tank', 'bright_tank')
        """)
        tank_stats = dict(cursor.fetchone())
        
        if tank_stats['total_tanks'] > 0:
            utilization = tank_stats['in_use'] / tank_stats['total_tanks'] * 100
            if utilization < 50:
                opportunities.append({
                    "category": "capacity",
                    "priority": "medium",
                    "title": "Low tank utilization",
                    "description": f"Only {utilization:.0f}% of tanks in use",
                    "recommendation": "Increase production or consider leasing tank space"
                })
            elif utilization > 85:
                opportunities.append({
                    "category": "capacity",
                    "priority": "high",
                    "title": "High tank utilization",
                    "description": f"{utilization:.0f}% of tanks in use - approaching capacity",
                    "recommendation": "Plan for additional tank capacity or optimize scheduling"
                })
        
        # 4. Quality control gaps
        cursor.execute("""
            SELECT pb.id, pb.batch_number, pb.start_date, pb.status
            FROM production_batches pb
            LEFT JOIN quality_records qr ON pb.id = qr.batch_id
            WHERE pb.status IN ('fermenting', 'conditioning')
            AND qr.id IS NULL
            AND julianday('now') - julianday(pb.start_date) > 3
        """)
        batches_missing_qc = [dict(row) for row in cursor.fetchall()]
        
        if batches_missing_qc:
            opportunities.append({
                "category": "quality",
                "priority": "high",
                "title": "Missing quality checks",
                "description": f"{len(batches_missing_qc)} active batches without quality records",
                "batches": [b['batch_number'] for b in batches_missing_qc[:5]],
                "recommendation": "Schedule quality checks for active fermentation batches"
            })
        
        # 5. Customer follow-up opportunities
        cursor.execute("""
            SELECT c.name, c.id, MAX(so.order_date) as last_order
            FROM customers c
            LEFT JOIN sales_orders so ON c.id = so.customer_id
            WHERE c.is_active = 1
            GROUP BY c.id
            HAVING last_order < date('now', '-30 day') OR last_order IS NULL
        """)
        inactive_customers = [dict(row) for row in cursor.fetchall()]
        
        if inactive_customers:
            opportunities.append({
                "category": "sales",
                "priority": "medium",
                "title": "Customer re-engagement opportunity",
                "description": f"{len(inactive_customers)} customers inactive for 30+ days",
                "customers": [c['name'] for c in inactive_customers[:5]],
                "recommendation": "Launch re-engagement campaign or special offers"
            })
        
        # 6. Financial optimization
        cursor.execute("""
            SELECT p.name, p.style, 
                   AVG(soi.unit_price) as avg_price,
                   COUNT(soi.id) as order_count
            FROM products p
            LEFT JOIN sales_order_items soi ON p.id = soi.product_id
            LEFT JOIN sales_orders so ON soi.order_id = so.id
            WHERE so.order_date >= date('now', '-90 day')
            GROUP BY p.id
            HAVING order_count > 0
            ORDER BY order_count DESC
        """)
        product_performance = [dict(row) for row in cursor.fetchall()]
        
        if product_performance:
            top_products = product_performance[:3]
            opportunities.append({
                "category": "sales",
                "priority": "medium",
                "title": "Top performing products",
                "description": "Focus marketing on these products",
                "products": [f"{p['name']} ({p['order_count']} orders)" for p in top_products],
                "recommendation": "Increase production capacity for top sellers"
            })
        
        conn.close()
        
        return make_json_serializable({
            "success": True,
            "opportunities": opportunities,
            "count": len(opportunities),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return {"success": False, "error": str(e)}

def _generate_optimization_report() -> Dict:
    """Generate a comprehensive optimization report with ROI calculations"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "sections": []
        }
        
        # 1. Production Efficiency Report
        cursor.execute("""
            SELECT 
                COUNT(*) as total_batches,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled,
                AVG(julianday(CASE WHEN status = 'completed' THEN actual_end_date ELSE 'now' END) - julianday(start_date)) as avg_duration_days
            FROM production_batches
            WHERE created_at >= date('now', '-90 day')
        """)
        prod_stats = dict(cursor.fetchone())
        
        completion_rate = (prod_stats['completed'] / prod_stats['total_batches'] * 100) if prod_stats['total_batches'] > 0 else 0
        
        report['sections'].append({
            "title": "Production Efficiency",
            "metrics": {
                "total_batches_90d": prod_stats['total_batches'],
                "completion_rate": f"{completion_rate:.1f}%",
                "cancellation_rate": f"{(prod_stats['cancelled'] / prod_stats['total_batches'] * 100):.1f}%" if prod_stats['total_batches'] > 0 else "0%",
                "avg_production_days": f"{prod_stats['avg_duration_days']:.1f}" if prod_stats['avg_duration_days'] else "N/A"
            },
            "recommendations": [
                "Target 95%+ completion rate" if completion_rate < 95 else "Maintain excellent completion rate",
                "Reduce cancellations through better planning" if prod_stats['cancelled'] > 2 else "Low cancellation rate - good planning"
            ]
        })
        
        # 2. Revenue Analysis
        cursor.execute("""
            SELECT 
                SUM(total_amount) as total_revenue,
                COUNT(*) as order_count,
                AVG(total_amount) as avg_order_value
            FROM sales_orders
            WHERE order_date >= date('now', '-90 day')
            AND status != 'cancelled'
        """)
        revenue_stats = dict(cursor.fetchone())
        
        cursor.execute("""
            SELECT 
                SUM(total_amount) as total_revenue_prev
            FROM sales_orders
            WHERE order_date >= date('now', '-180 day')
            AND order_date < date('now', '-90 day')
            AND status != 'cancelled'
        """)
        prev_revenue = cursor.fetchone()['total_revenue_prev'] or 0
        
        current_revenue = revenue_stats['total_revenue'] or 0
        growth_rate = ((current_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
        
        report['sections'].append({
            "title": "Revenue Performance",
            "metrics": {
                "revenue_90d": f"{current_revenue:,.0f} VND",
                "order_count": revenue_stats['order_count'],
                "avg_order_value": f"{(revenue_stats['avg_order_value'] or 0):,.0f} VND",
                "growth_vs_prev_90d": f"{growth_rate:+.1f}%"
            },
            "recommendations": [
                "Focus on increasing order frequency" if (revenue_stats['order_count'] or 0) < 50 else "Maintain order volume",
                "Upsell to increase average order value" if (revenue_stats['avg_order_value'] or 0) < 500000 else "Strong average order value"
            ]
        })
        
        # 3. Inventory Health
        cursor.execute("""
            SELECT 
                COUNT(*) as total_items,
                SUM(CASE WHEN quantity < min_quantity THEN 1 ELSE 0 END) as low_stock,
                SUM(CASE WHEN quantity = 0 THEN 1 ELSE 0 END) as out_of_stock,
                SUM(quantity * cost_per_unit) as inventory_value
            FROM raw_materials
        """)
        inv_stats = dict(cursor.fetchone())
        
        stock_health = ((inv_stats['total_items'] - inv_stats['low_stock']) / inv_stats['total_items'] * 100) if inv_stats['total_items'] > 0 else 100
        
        report['sections'].append({
            "title": "Inventory Health",
            "metrics": {
                "total_items": inv_stats['total_items'],
                "stock_health_score": f"{stock_health:.0f}%",
                "low_stock_items": inv_stats['low_stock'],
                "out_of_stock_items": inv_stats['out_of_stock'],
                "inventory_value": f"{(inv_stats['inventory_value'] or 0):,.0f} VND"
            },
            "recommendations": [
                "Address low stock items immediately" if inv_stats['low_stock'] > 5 else "Stock levels healthy",
                "Set up automatic reorder alerts" if inv_stats['out_of_stock'] > 0 else "No stockouts - good inventory management"
            ]
        })
        
        # 4. Staff Productivity
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT s.id) as active_staff,
                COUNT(dt.id) as total_tasks,
                SUM(CASE WHEN dt.status = 'completed' THEN 1 ELSE 0 END) as completed_tasks
            FROM staff s
            LEFT JOIN daily_tasks dt ON s.id = dt.assigned_to
                AND dt.task_date >= date('now', '-30 day')
            WHERE s.is_active = 1
        """)
        staff_stats = dict(cursor.fetchone())
        
        task_completion = (staff_stats['completed_tasks'] / staff_stats['total_tasks'] * 100) if staff_stats['total_tasks'] > 0 else 0
        tasks_per_staff = (staff_stats['total_tasks'] / staff_stats['active_staff']) if staff_stats['active_staff'] > 0 else 0
        
        report['sections'].append({
            "title": "Staff Productivity",
            "metrics": {
                "active_staff": staff_stats['active_staff'],
                "tasks_30d": staff_stats['total_tasks'],
                "task_completion_rate": f"{task_completion:.0f}%",
                "avg_tasks_per_staff": f"{tasks_per_staff:.1f}"
            },
            "recommendations": [
                "Improve task tracking and completion" if task_completion < 80 else "Good task completion rate",
                "Consider workload rebalancing" if tasks_per_staff > 20 else "Workload distribution looks healthy"
            ]
        })
        
        # 5. Overall Optimization Score
        scores = [completion_rate, stock_health, task_completion]
        overall_score = sum(scores) / len(scores)
        
        report['overall_optimization_score'] = f"{overall_score:.0f}%"
        report['summary'] = {
            "strengths": [],
            "improvement_areas": []
        }
        
        if completion_rate >= 90:
            report['summary']['strengths'].append("Excellent production completion rate")
        else:
            report['summary']['improvement_areas'].append("Production completion rate needs improvement")
        
        if stock_health >= 90:
            report['summary']['strengths'].append("Healthy inventory levels")
        else:
            report['summary']['improvement_areas'].append("Multiple low-stock items need attention")
        
        if task_completion >= 85:
            report['summary']['strengths'].append("Strong task completion culture")
        else:
            report['summary']['improvement_areas'].append("Task completion rate could be higher")
        
        conn.close()
        
        return make_json_serializable({"success": True, "report": report})
    except Exception as e:
        return {"success": False, "error": str(e)}

def _create_automation_workflow(workflow_type: str, parameters: Dict = None) -> Dict:
    """Create an automation workflow for repetitive tasks"""
    try:
        workflows = {
            "low_stock_alert": {
                "name": "Low Stock Alert Automation",
                "description": "Automatically create tasks when inventory falls below minimum",
                "trigger": "inventory_check",
                "actions": ["create_reorder_task", "notify_manager"],
                "schedule": "daily"
            },
            "quality_check_reminder": {
                "name": "Quality Check Reminder",
                "description": "Remind brewers to perform quality checks on active batches",
                "trigger": "batch_fermentation_day",
                "conditions": ["batch.status IN ('fermenting', 'conditioning')", "days_since_start >= 3"],
                "actions": ["create_quality_task"],
                "schedule": "daily"
            },
            "tank_cleaning_schedule": {
                "name": "Tank Cleaning Automation",
                "description": "Schedule tank cleaning after batch completion",
                "trigger": "batch_completed",
                "actions": ["update_tank_status_cleaning", "create_cleaning_task"],
                "schedule": "event_based"
            },
            "customer_reorder_reminder": {
                "name": "Customer Reorder Reminder",
                "description": "Identify customers who haven't ordered recently",
                "trigger": "schedule",
                "conditions": ["last_order_date < date('now', '-30 days')"],
                "actions": ["create_follow_up_task", "generate_reminder_list"],
                "schedule": "weekly"
            },
            "daily_briefing": {
                "name": "Automated Daily Briefing",
                "description": "Generate morning briefing with key metrics and tasks",
                "trigger": "schedule",
                "actions": ["generate_briefing", "notify_managers"],
                "schedule": "daily_at_7am"
            }
        }
        
        if workflow_type not in workflows:
            return {
                "success": False,
                "error": f"Unknown workflow type: {workflow_type}",
                "available_types": list(workflows.keys())
            }
        
        workflow = workflows[workflow_type]
        workflow['id'] = f"wf_{workflow_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        workflow['created_at'] = datetime.now().isoformat()
        workflow['status'] = 'active'
        workflow['parameters'] = parameters or {}
        
        return make_json_serializable({
            "success": True,
            "workflow": workflow,
            "message": f"Workflow '{workflow['name']}' created successfully"
        })
    except Exception as e:
        return {"success": False, "error": str(e)}

def _propose_feature_enhancement(usage_pattern: str = None) -> Dict:
    """Propose feature enhancements based on usage patterns"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        proposals = []
        
        # Analyze most used tables/features
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row['name'] for row in cursor.fetchall()]
        
        feature_usage = {}
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            feature_usage[table] = cursor.fetchone()['count']
        
        # Sort by usage
        sorted_features = sorted(feature_usage.items(), key=lambda x: x[1], reverse=True)
        
        # Generate proposals based on usage patterns
        high_usage = [f for f, c in sorted_features[:5]]
        
        if 'sales_orders' in high_usage:
            proposals.append({
                "feature": "Advanced Sales Analytics Dashboard",
                "reasoning": "High sales order volume indicates need for better analytics",
                "benefits": [
                    "Real-time sales trends visualization",
                    "Customer segmentation analysis",
                    "Product performance comparison",
                    "Revenue forecasting"
                ],
                "estimated_impact": "High - improves decision making",
                "complexity": "Medium"
            })
        
        if 'production_batches' in high_usage:
            proposals.append({
                "feature": "Production Optimization Engine",
                "reasoning": "Active production management suggests demand for scheduling optimization",
                "benefits": [
                    "Automated schedule optimization",
                    "Tank utilization maximization",
                    "Resource conflict detection",
                    "Predictive maintenance scheduling"
                ],
                "estimated_impact": "High - increases production efficiency",
                "complexity": "High"
            })
        
        if 'quality_records' in high_usage and feature_usage.get('quality_records', 0) > 50:
            proposals.append({
                "feature": "Predictive Quality Control",
                "reasoning": "Extensive quality data enables predictive analytics",
                "benefits": [
                    "Early detection of quality issues",
                    "Recipe optimization suggestions",
                    "Consistency improvement tracking",
                    "Automated quality alerts"
                ],
                "estimated_impact": "Medium - improves product quality",
                "complexity": "High"
            })
        
        # Check for missing integrations
        cursor.execute("SELECT COUNT(*) as count FROM customers WHERE email IS NOT NULL AND email != ''")
        customers_with_email = cursor.fetchone()['count']
        
        if customers_with_email > 10:
            proposals.append({
                "feature": "Email Marketing Integration",
                "reasoning": f"{customers_with_email} customers have email addresses",
                "benefits": [
                    "Automated order confirmations",
                    "Promotional campaign management",
                    "Customer newsletter",
                    "Re-engagement emails"
                ],
                "estimated_impact": "Medium - increases customer retention",
                "complexity": "Low"
            })
        
        # Check for mobile/field work needs
        cursor.execute("SELECT COUNT(*) as count FROM staff WHERE department IN ('production', 'delivery')")
        field_staff = cursor.fetchone()['count']
        
        if field_staff > 3:
            proposals.append({
                "feature": "Mobile Staff App",
                "reasoning": f"{field_staff} staff members work in production/delivery",
                "benefits": [
                    "Real-time task updates on mobile",
                    "Barcode scanning for inventory",
                    "Delivery confirmation with photos",
                    "Offline capability for brewery floor"
                ],
                "estimated_impact": "High - improves field efficiency",
                "complexity": "High"
            })
        
        conn.close()
        
        return make_json_serializable({
            "success": True,
            "proposals": proposals,
            "count": len(proposals),
            "generated_at": datetime.now().isoformat()
        })
    except Exception as e:
        return {"success": False, "error": str(e)}

def _log_improvement(improvement_type: str, description: str, impact: str = None, metrics_before: Dict = None, metrics_after: Dict = None) -> Dict:
    """Log an improvement for tracking and learning"""
    try:
        improvement = {
            "id": f"imp_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "type": improvement_type,
            "description": description,
            "impact": impact,
            "metrics_before": metrics_before,
            "metrics_after": metrics_after,
            "created_at": datetime.now().isoformat(),
            "status": "logged"
        }
        
        # In a full implementation, this would be stored in a database table
        # For now, return the improvement record
        
        return make_json_serializable({
            "success": True,
            "improvement": improvement,
            "message": "Improvement logged successfully"
        })
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================
# PROACTIVE AUTOMATION TOOLS (Phase 4)
# ============================================================

def scan_for_opportunities() -> Dict:
    """Proactively scan for opportunities and issues in brewery operations"""
    try:
        agent = get_proactive_agent()
        suggestions = agent.run_proactive_scan()
        return make_json_serializable({
            "success": True,
            "suggestions": suggestions,
            "count": len(suggestions),
            "scanned_at": datetime.now().isoformat()
        })
    except Exception as e:
        return {"success": False, "error": str(e)}

def detect_anomalies() -> Dict:
    """Detect anomalies in brewery operations using statistical analysis"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        anomalies = []
        
        # Check for unusual inventory levels
        cursor.execute("""
            SELECT name, quantity, min_quantity, unit,
                   CASE WHEN min_quantity > 0 THEN ROUND(quantity * 100.0 / min_quantity, 1) ELSE 0 END as stock_pct
            FROM raw_materials
            ORDER BY stock_pct ASC
            LIMIT 5
        """)
        low_stock = cursor.fetchall()
        for item in low_stock:
            if item['stock_pct'] < 50:
                anomalies.append({
                    "type": "inventory_low",
                    "severity": "high" if item['stock_pct'] < 20 else "medium",
                    "item": item['name'],
                    "message": f"{item['name']} at {item['stock_pct']}% of minimum stock",
                    "value": item['quantity'],
                    "threshold": item['min_quantity']
                })
        
        # Check for overdue batches
        cursor.execute("""
            SELECT b.id, p.name as product_name, b.status, b.start_date,
                   JULIANDAY('now') - JULIANDAY(b.start_date) as days_running
            FROM production_batches b
            JOIN products p ON b.product_id = p.id
            WHERE b.status IN ('fermenting', 'conditioning')
            AND JULIANDAY('now') - JULIANDAY(b.start_date) > 21
        """)
        long_batches = cursor.fetchall()
        for batch in long_batches:
            anomalies.append({
                "type": "batch_overdue",
                "severity": "medium",
                "item": f"Batch #{batch['id']} ({batch['product_name']})",
                "message": f"Running for {int(batch['days_running'])} days",
                "value": batch['days_running'],
                "threshold": 21
            })
        
        # Check for overdue maintenance
        try:
            cursor.execute("""
                SELECT ms.task_name, e.name as equipment_name, ms.next_due
                FROM maintenance_schedule ms
                JOIN equipment e ON ms.equipment_id = e.id
                WHERE ms.next_due < DATE('now')
                AND ms.status != 'completed'
            """)
            overdue_maintenance = cursor.fetchall()
            for eq in overdue_maintenance:
                anomalies.append({
                    "type": "maintenance_overdue",
                    "severity": "high",
                    "item": eq['equipment_name'],
                    "message": f"Maintenance overdue: {eq['task_name']} (was due: {eq['next_due']})",
                    "value": eq['next_due'],
                    "threshold": datetime.now().strftime('%Y-%m-%d')
                })
        except Exception:
            pass
        
        # Check for declining sales trend
        try:
            cursor.execute("""
                SELECT DATE(order_date) as sale_date, SUM(total_amount) as daily_total
                FROM sales_orders
                WHERE order_date >= DATE('now', '-14 days')
                GROUP BY DATE(order_date)
                ORDER BY sale_date
            """)
            sales_data = cursor.fetchall()
        except Exception:
            sales_data = []
        if len(sales_data) >= 7:
            recent_avg = sum(s['daily_total'] for s in sales_data[-3:]) / 3
            older_avg = sum(s['daily_total'] for s in sales_data[:3]) / 3
            if older_avg > 0 and recent_avg < older_avg * 0.7:
                anomalies.append({
                    "type": "sales_decline",
                    "severity": "high",
                    "item": "Revenue",
                    "message": f"Sales declined {round((1 - recent_avg/older_avg) * 100, 1)}% compared to earlier this week",
                    "value": recent_avg,
                    "threshold": older_avg
                })
        
        conn.close()
        
        return make_json_serializable({
            "success": True,
            "anomalies": anomalies,
            "count": len(anomalies),
            "detected_at": datetime.now().isoformat()
        })
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_autonomy_level() -> Dict:
    """Get current AI autonomy level and configuration"""
    try:
        agent = get_proactive_agent()
        config = agent.get_autonomy_config()
        return make_json_serializable({
            "success": True,
            "config": config
        })
    except Exception as e:
        return {"success": False, "error": str(e)}

def set_autonomy_level(level: str) -> Dict:
    """Set AI autonomy level (off, observer, suggester, actor, autonomous)"""
    try:
        agent = get_proactive_agent()
        agent.set_autonomy_level(level)
        return make_json_serializable({
            "success": True,
            "level": level,
            "message": f"Autonomy level set to {level}"
        })
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_pending_suggestions() -> Dict:
    """Get pending AI suggestions awaiting user review"""
    try:
        agent = get_proactive_agent()
        suggestions = agent.get_pending_suggestions()
        return make_json_serializable({
            "success": True,
            "suggestions": suggestions,
            "count": len(suggestions)
        })
    except Exception as e:
        return {"success": False, "error": str(e)}

def approve_suggestion(index: int) -> Dict:
    """Approve and execute a pending AI suggestion"""
    try:
        agent = get_proactive_agent()
        success = agent.approve_suggestion(index)
        return make_json_serializable({
            "success": success,
            "message": "Suggestion approved and executed" if success else "Invalid suggestion index"
        })
    except Exception as e:
        return {"success": False, "error": str(e)}

def dismiss_suggestion(index: int) -> Dict:
    """Dismiss a pending AI suggestion"""
    try:
        agent = get_proactive_agent()
        success = agent.dismiss_suggestion(index)
        return make_json_serializable({
            "success": success,
            "message": "Suggestion dismissed" if success else "Invalid suggestion index"
        })
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_goal_progress() -> Dict:
    """Get progress for all brewery goals"""
    try:
        agent = get_proactive_agent()
        goals = agent.get_goal_progress()
        return make_json_serializable({
            "success": True,
            "goals": goals,
            "count": len(goals)
        })
    except Exception as e:
        return {"success": False, "error": str(e)}

def add_brewery_goal(name: str, description: str, target_value: float,
                     current_value: float = 0, unit: str = '',
                     priority: str = 'normal', category: str = 'general') -> Dict:
    """Add a new brewery goal for the AI to track"""
    try:
        agent = get_proactive_agent()
        goal_id = agent.add_goal(name, description, target_value, current_value, unit, priority, category)
        return make_json_serializable({
            "success": goal_id > 0,
            "goal_id": goal_id,
            "message": f"Goal '{name}' added successfully"
        })
    except Exception as e:
        return {"success": False, "error": str(e)}

def update_goal(goal_id: int, current_value: float) -> Dict:
    """Update progress toward a brewery goal"""
    try:
        agent = get_proactive_agent()
        agent.update_goal_progress(goal_id, current_value)
        return make_json_serializable({
            "success": True,
            "message": f"Goal #{goal_id} updated to {current_value}"
        })
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_proactive_activity_log(limit: int = 50) -> Dict:
    """Get recent proactive AI activity log"""
    try:
        agent = get_proactive_agent()
        activities = agent.get_activity_log(limit)
        return make_json_serializable({
            "success": True,
            "activities": activities,
            "count": len(activities)
        })
    except Exception as e:
        return {"success": False, "error": str(e)}

# ==========================================
# Developer / Clawdbot System Tools
# ==========================================

def _is_developer_mode_enabled() -> bool:
    """Check if the AI is authorized to modify system code"""
    try:
        from models.database import Database
        _db = Database()
        row = _db.execute_query("SELECT value FROM settings WHERE key = 'ai_developer_mode'")
        if row and str(row[0]['value']).lower() in ('true', '1', 'yes', 'enabled'):
            return True
        return False
    except Exception:
        return False

def _read_system_file(file_path: str) -> Dict:
    """Read the contents of a system file"""
    try:
        if not os.path.exists(file_path):
            return {"success": False, "error": f"File not found: {file_path}"}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        return make_json_serializable({
            "success": True,
            "file_path": file_path,
            "content": content,
            "size_bytes": len(content)
        })
    except Exception as e:
        return {"success": False, "error": str(e)}

def _write_system_file(file_path: str, content: str, mode: str = 'write') -> Dict:
    """Write or amend a system file"""
    try:
        if not _is_developer_mode_enabled():
            return {"success": False, "error": "Action denied: Developer mode is not enabled in setting ai_developer_mode. Request user to toggle_developer_mode(true) first."}
        
        write_mode = 'a' if mode == 'append' else 'w'
        
        # Ensure directory exists if there's a dir path
        dir_name = os.path.dirname(os.path.abspath(file_path))
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        
        with open(file_path, write_mode, encoding='utf-8') as f:
            f.write(content)
            
        return make_json_serializable({
            "success": True,
            "message": f"Successfully {'appended to' if mode == 'append' else 'wrote'} {file_path}"
        })
    except Exception as e:
        return {"success": False, "error": str(e)}

def _execute_system_command(command: str) -> Dict:
    """Execute a system bash command"""
    try:
        if not _is_developer_mode_enabled():
            return {"success": False, "error": "Action denied: Developer mode is not enabled in setting ai_developer_mode. Request user to toggle_developer_mode(true) first."}
            
        import subprocess
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True,
            timeout=30
        )
        
        return make_json_serializable({
            "success": result.returncode == 0,
            "return_code": result.returncode,
            "stdout": result.stdout[:2000], # truncate to avoid blowing up context
            "stderr": result.stderr[:2000]
        })
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command execution timed out after 30 seconds."}
    except Exception as e:
        return {"success": False, "error": str(e)}

def toggle_developer_mode(enabled: bool) -> Dict:
    """Toggle the developer mode switch (useful for the agent to recommend but requires manual approval usually)"""
    try:
        from models.database import Database
        _db = Database()
        _db.execute_query(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('ai_developer_mode', ?)",
            ('true' if enabled else 'false',)
        )
        return {"success": True, "message": f"Developer mode set to {enabled}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _execute_full_management_cycle() -> Dict:
    """Executes a full management sweep of the brewery."""
    try:
        from utils.ai_planner import get_planner
        from utils.agent import get_proactive_agent
        
        planner = get_planner()
        agent = get_proactive_agent()
        
        agent_actions = agent.run_check_cycle()
        situation = planner.analyze_situation()
        production_plan = planner.create_production_plan()
        inventory_plan = planner.create_inventory_plan()
        suggestions = planner.get_proactive_suggestions()
        
        return make_json_serializable({
            "success": True,
            "automated_agent_actions_taken": agent_actions,
            "current_brewery_situation": situation,
            "production_bottleneck_plan": production_plan,
            "inventory_restock_plan": inventory_plan,
            "top_proactive_suggestions": suggestions[:3]
        })
    except Exception as e:
        return {"success": False, "error": str(e)}
