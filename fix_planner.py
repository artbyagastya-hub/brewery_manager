import re

with open('utils/ai_planner.py', 'r') as f:
    text = f.read()

# Replace inventory -> raw_materials and remove active = 1
text = re.sub(r'FROM inventory\b', 'FROM raw_materials', text)
text = re.sub(r'AND active = 1', '', text)

# Replace batches -> production_batches
text = re.sub(r'FROM batches\b', 'FROM production_batches', text)

# Replace orders -> sales_orders
text = re.sub(r'FROM orders\b', 'FROM sales_orders', text)

# Replace equipment type
text = re.sub(r'type = \'tank\'', "equipment_type = 'tank'", text)
text = re.sub(r"type LIKE '%tank%'", "equipment_type LIKE '%tank%'", text)

# Replace 'except:\n    pass' with logging
text = re.sub(
    r'except:\s+pass',
    r'except Exception as e:\n            import logging\n            logging.error(f"AI Planner Error: {str(e)}")',
    text
)

# Replace empty except blocks in create_production_plan and others which might be except Exception as e: pass
text = re.sub(
    r'except Exception as e:\n\s+pass',
    r'except Exception as e:\n            import logging\n            logging.error(f"AI Planner Error: {str(e)}")',
    text
)

with open('utils/ai_planner.py', 'w') as f:
    f.write(text)

