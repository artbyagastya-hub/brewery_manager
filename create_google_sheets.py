"""
Brewery Manager - Google Sheets Data Entry Template Generator

Creates a complete Google Sheets workbook with all 21 data entry sheets
for staff to fill in brewery data.

Setup:
  1. pip install gspread google-auth
  2. Create a Google Cloud service account:
     - Go to console.cloud.google.com > APIs & Services > Credentials
     - Create Credentials > Service Account
     - Download the JSON key file
  3. Share your Google Drive with the service account email
  4. Set GOOGLE_SERVICE_ACCOUNT_JSON env var to the path of your JSON key file
     OR place it as 'service_account.json' in this directory
  5. Run: python create_google_sheets.py
"""

import os
import sys

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    print("Missing dependencies. Install them with:")
    print("   pip install gspread google-auth")
    sys.exit(1)


# ============================================================
# SHEET DEFINITIONS
# ============================================================

SHEETS = {
    # =========================================================
    # PHASE 1 - Master Data (No Dependencies)
    # =========================================================
    "1. Products": {
        "phase": 1,
        "description": "All beer products offered by the brewery",
        "headers": [
            "name", "style", "abv", "ibu", "description",
            "price_per_unit (VND)", "is_active (1=active, 0=inactive)"
        ],
        "required": ["name", "price_per_unit"],
        "dropdowns": {
            "is_active (1=active, 0=inactive)": ["1", "0"]
        },
        "examples": [
            ["Sai Gon Pale Ale", "American Pale Ale", "5.2", "35",
             "Refreshing pale ale with citrus notes", "45000", "1"],
            ["Hanoi IPA", "India Pale Ale", "6.5", "65",
             "Bold hoppy IPA with tropical fruit aromas", "55000", "1"],
        ]
    },

    "2. Raw Materials": {
        "phase": 1,
        "description": "All raw materials inventory (malts, hops, adjuncts, chemicals, packaging)",
        "headers": [
            "name", "category", "unit", "quantity", "min_quantity",
            "cost_per_unit (VND)", "supplier", "origin",
            "expiry_date (YYYY-MM-DD)", "storage_location", "notes"
        ],
        "required": ["name", "category", "unit", "quantity", "cost_per_unit"],
        "dropdowns": {
            "category": ["malt", "hops", "adjunct", "fruit", "water_treatment",
                         "cleaning", "packaging"],
            "unit": ["kg", "g", "L", "pcs", "oz", "lb"]
        },
        "examples": [
            ["Pale Malt 2-Row", "malt", "kg", "500", "100", "35000",
             "Weyermann", "Germany", "2026-12-31", "Grain Room A", ""],
            ["Cascade", "hops", "kg", "20", "5", "850000",
             "YCH Hops", "USA", "2027-06-30", "Cold Storage", ""],
            ["Coffee Beans (Vietnamese)", "adjunct", "kg", "30", "5", "450000",
             "Local Coffee Farm", "Vietnam", "2026-06-30", "Dry Storage", ""],
            ["PBW (Powdered Brewery Wash)", "cleaning", "kg", "20", "5", "280000",
             "Five Star", "USA", "2027-12-31", "Chemical Storage", ""],
            ["330ml Cans", "packaging", "pcs", "5000", "1000", "1500",
             "Can Supplier", "Vietnam", "", "Packaging Room", ""],
        ]
    },

    "3. Staff": {
        "phase": 1,
        "description": "All brewery employees",
        "headers": [
            "name", "position", "department", "phone", "email",
            "hire_date (YYYY-MM-DD)", "salary (VND/month)",
            "emergency_contact", "notes"
        ],
        "required": ["name", "position"],
        "dropdowns": {
            "department": ["Production", "Sales", "Quality", "Finance",
                           "Warehouse", "Front of House", "Management", "Maintenance"]
        },
        "examples": [
            ["Nguyen Van Minh", "Head Brewer", "Production", "0901234567",
             "minh@brewery.vn", "2023-01-15", "25000000", "", ""],
            ["Hoang Van Duc", "Sales Manager", "Sales", "0901234571",
             "duc@brewery.vn", "2023-04-15", "22000000", "", ""],
        ]
    },

    "4. Customers": {
        "phase": 1,
        "description": "All customer accounts (bars, restaurants, distributors, hotels, etc.)",
        "headers": [
            "name", "type", "contact_person", "phone", "email",
            "address", "city", "province", "tax_id",
            "credit_limit (VND)", "payment_terms", "notes"
        ],
        "required": ["name"],
        "dropdowns": {
            "type": ["retail", "bar", "restaurant", "distributor", "hotel", "online", "other"],
            "payment_terms": ["COD", "NET 15", "NET 30", "NET 45", "NET 60", "Prepaid"]
        },
        "examples": [
            ["Craft Beer Saigon", "bar", "Le Van Tam", "0909876501",
             "orders@craftbeersaigon.vn", "45 Nguyen Hue, Quan 1",
             "Ho Chi Minh", "Ho Chi Minh", "0123456789", "50000000", "NET 30", ""],
        ]
    },

    "5. Equipment": {
        "phase": 1,
        "description": "All brewery equipment and tanks",
        "headers": [
            "name", "equipment_type", "capacity", "capacity_unit",
            "status", "last_cleaned (YYYY-MM-DD)", "notes"
        ],
        "required": ["name", "equipment_type"],
        "dropdowns": {
            "equipment_type": ["fermenter", "brewhouse", "processing",
                               "packaging", "cooling", "cleaning", "filtration"],
            "status": ["available", "in_use", "maintenance", "cleaning", "out_of_service"],
            "capacity_unit": ["L", "kg", "gal"]
        },
        "examples": [
            ["Fermenter 2000L #1", "fermenter", "2000", "L", "available", "", ""],
            ["Brewhouse", "brewhouse", "1000", "L", "available", "", ""],
            ["Glycol Chiller", "cooling", "", "", "available", "", ""],
        ]
    },

    "6. Yeast Strains": {
        "phase": 1,
        "description": "Yeast strain catalog and specifications",
        "headers": [
            "name", "lab", "product_id", "yeast_type", "form",
            "attenuation_min", "attenuation_max", "flocculation",
            "min_temp (C)", "max_temp (C)", "alcohol_tolerance (%)",
            "description"
        ],
        "required": ["name"],
        "dropdowns": {
            "yeast_type": ["ale", "lager", "wheat", "belgian", "wild", "other"],
            "form": ["dry", "liquid"],
            "flocculation": ["low", "medium", "high"]
        },
        "examples": [
            ["US-05", "Fermentis", "US-05", "ale", "dry", "73", "77",
             "medium", "15", "24", "11",
             "Clean, neutral American ale yeast. Great for IPAs and Pale Ales."],
        ]
    },

    "7. Packaging Materials": {
        "phase": 1,
        "description": "Packaging stock inventory (cans, bottles, kegs, carriers)",
        "headers": [
            "name", "type", "quantity", "unit",
            "cost_per_unit (VND)", "supplier", "reorder_level", "notes"
        ],
        "required": ["name", "type", "quantity", "unit"],
        "dropdowns": {
            "type": ["can", "bottle", "keg", "carrier", "box", "label", "other"],
            "unit": ["pcs", "rolls", "kg"]
        },
        "examples": [
            ["330ml Can", "can", "5000", "pcs", "1500", "Can Supplier", "1000", ""],
            ["500ml Bottle", "bottle", "2000", "pcs", "2500", "Glass Supplier", "500", ""],
            ["Keg 50L", "keg", "20", "pcs", "3500000", "Keg Supplier", "5", ""],
        ]
    },

    # =========================================================
    # PHASE 2 - Recipes (References: Products, Raw Materials, Yeast)
    # =========================================================
    "8. Recipes": {
        "phase": 2,
        "description": "Main recipe info - one row per recipe. References Products.",
        "headers": [
            "product_name", "name", "style", "batch_size (L)", "batch_size_unit",
            "boil_time (min)", "efficiency (%)", "og", "fg", "abv", "ibu", "srm",
            "description", "notes"
        ],
        "required": ["product_name", "name", "batch_size (L)"],
        "dropdowns": {
            "batch_size_unit": ["L", "gal"]
        },
        "examples": [
            ["Sai Gon Pale Ale", "Sai Gon Pale Ale Recipe", "American Pale Ale",
             "1000", "L", "60", "75", "1.052", "1.012", "5.2", "35", "8",
             "Classic American Pale Ale", ""],
        ]
    },

    "9. Recipe Fermentables": {
        "phase": 2,
        "description": "Grain bill per recipe. References Raw Materials (malt/adjunct category).",
        "headers": [
            "recipe_name", "material_name", "amount", "unit",
            "percentage", "potential", "color (Lovibond)", "notes"
        ],
        "required": ["recipe_name", "material_name", "amount"],
        "dropdowns": {},
        "examples": [
            ["Sai Gon Pale Ale Recipe", "Pale Malt 2-Row", "180", "kg", "85", "1.037", "3", ""],
            ["Sai Gon Pale Ale Recipe", "Crystal 60L", "20", "kg", "10", "1.034", "60", ""],
        ]
    },

    "10. Recipe Hops": {
        "phase": 2,
        "description": "Hop additions per recipe. References Raw Materials (hops category).",
        "headers": [
            "recipe_name", "hop_name", "amount", "unit", "alpha_acid (%)",
            "boil_time (min)", "use_type", "ibu_contribution", "notes"
        ],
        "required": ["recipe_name", "hop_name", "amount"],
        "dropdowns": {
            "use_type": ["boil", "dry_hop", "whirlpool", "first_wort", "mash"]
        },
        "examples": [
            ["Sai Gon Pale Ale Recipe", "Cascade", "30", "g", "5.5", "60", "boil", "15", ""],
            ["Sai Gon Pale Ale Recipe", "Cascade", "30", "g", "5.5", "15", "boil", "5", ""],
            ["Sai Gon Pale Ale Recipe", "Centennial", "20", "g", "10", "0", "dry_hop", "0", ""],
        ]
    },

    "11. Recipe Yeast": {
        "phase": 2,
        "description": "Yeast per recipe. References Yeast Strains.",
        "headers": [
            "recipe_name", "yeast_name", "lab", "product_id", "form",
            "attenuation (%)", "min_temp (C)", "max_temp (C)", "notes"
        ],
        "required": ["recipe_name", "yeast_name"],
        "dropdowns": {
            "form": ["dry", "liquid"]
        },
        "examples": [
            ["Sai Gon Pale Ale Recipe", "US-05", "Fermentis", "US-05", "dry",
             "75", "18", "22", ""],
        ]
    },

    "12. Recipe Mash Steps": {
        "phase": 2,
        "description": "Mash schedule per recipe.",
        "headers": [
            "recipe_name", "step_number", "name", "step_type",
            "temperature (C)", "duration (min)", "notes"
        ],
        "required": ["recipe_name", "step_number", "name", "temperature (C)", "duration (min)"],
        "dropdowns": {
            "step_type": ["temperature", "decoction", "infusion", "batch_sparge", "fly_sparge"]
        },
        "examples": [
            ["Sai Gon Pale Ale Recipe", "1", "Mash In", "temperature", "66", "60", ""],
            ["Sai Gon Pale Ale Recipe", "2", "Mash Out", "temperature", "76", "10", ""],
        ]
    },

    "13. Recipe Other Ingredients": {
        "phase": 2,
        "description": "Special additions per recipe (coffee, fruit, spices, etc.).",
        "headers": [
            "recipe_name", "name", "ingredient_type", "amount", "unit",
            "add_time", "notes"
        ],
        "required": ["recipe_name", "name", "amount"],
        "dropdowns": {
            "ingredient_type": ["coffee", "chocolate", "spice", "fruit", "herb", "other"],
            "add_time": ["boil", "primary", "secondary", "packaging", "mash"]
        },
        "examples": [
            ["Mekong Stout Recipe", "Coffee Beans (Vietnamese)", "coffee",
             "5", "kg", "secondary", "Add after primary fermentation"],
        ]
    },

    # =========================================================
    # PHASE 3 - Operations (References: Products, Customers, Staff, Equipment)
    # =========================================================
    "14. Production Batches": {
        "phase": 3,
        "description": "Production batch records. References Products, Equipment, Staff.",
        "headers": [
            "batch_number", "product_name", "tank_name",
            "planned_quantity (L)", "actual_quantity (L)", "status",
            "start_date (YYYY-MM-DD)", "end_date (YYYY-MM-DD)",
            "brewer_name", "notes"
        ],
        "required": ["batch_number", "product_name", "planned_quantity (L)"],
        "dropdowns": {
            "status": ["planned", "brewing", "fermenting", "conditioning",
                       "completed", "cancelled"]
        },
        "examples": [
            ["B0001", "Sai Gon Pale Ale", "Fermenter 2000L #1",
             "1000", "", "fermenting", "2026-04-10", "",
             "Nguyen Van Minh", "First batch of the month"],
        ]
    },

    "15. Sales Orders": {
        "phase": 3,
        "description": "Customer sales orders. References Customers.",
        "headers": [
            "order_number", "customer_name", "order_date (YYYY-MM-DD)",
            "delivery_date (YYYY-MM-DD)", "status", "payment_status", "notes"
        ],
        "required": ["order_number", "customer_name", "order_date"],
        "dropdowns": {
            "status": ["pending", "processing", "shipped", "delivered", "cancelled"],
            "payment_status": ["unpaid", "paid", "partial", "refunded"]
        },
        "examples": [
            ["ORD-1001", "Craft Beer Saigon", "2026-04-15", "2026-04-18",
             "delivered", "paid", ""],
        ]
    },

    "16. Order Items": {
        "phase": 3,
        "description": "Line items per sales order. References Sales Orders + Products.",
        "headers": [
            "order_number", "product_name", "quantity",
            "unit_price (VND)", "discount (%)", "notes"
        ],
        "required": ["order_number", "product_name", "quantity", "unit_price"],
        "dropdowns": {},
        "examples": [
            ["ORD-1001", "Sai Gon Pale Ale", "48", "45000", "0", ""],
            ["ORD-1001", "Hanoi IPA", "24", "55000", "5", ""],
        ]
    },

    "17. Financial Transactions": {
        "phase": 3,
        "description": "All income and expense transactions.",
        "headers": [
            "transaction_date (YYYY-MM-DD)", "type", "category",
            "amount (VND)", "description", "payment_method",
            "reference_id", "reference_type"
        ],
        "required": ["transaction_date", "type", "amount"],
        "dropdowns": {
            "type": ["income", "expense"],
            "category": ["Sales", "Raw Materials", "Utilities", "Rent", "Salaries",
                         "Packaging", "Equipment Maintenance", "Marketing",
                         "Transportation", "Insurance", "Taxes", "Other"],
            "payment_method": ["cash", "bank_transfer", "credit_card",
                               "momo", "zalopay", "vnpay", "check"]
        },
        "examples": [
            ["2026-04-15", "income", "Sales", "4500000",
             "Payment for order ORD-1001", "bank_transfer", "", ""],
            ["2026-04-01", "expense", "Rent", "25000000",
             "Monthly facility rent", "bank_transfer", "", ""],
        ]
    },

    # =========================================================
    # PHASE 4 - Supporting Data (References: Production Batches, Staff)
    # =========================================================
    "18. Quality Records": {
        "phase": 4,
        "description": "Quality control checks for production batches.",
        "headers": [
            "batch_number", "check_type", "value", "unit",
            "passed (1=pass, 0=fail)", "inspector", "notes"
        ],
        "required": ["batch_number", "check_type"],
        "dropdowns": {
            "check_type": ["gravity", "ph", "temperature", "color",
                           "turbidity", "taste", "aroma", "clarity",
                           "carbonation", "microbiological"],
            "unit": ["SG", "pH", "C", "SRM", "NTU", "vols", "CFU/mL"]
        },
        "examples": [
            ["B0001", "gravity", "1.052", "SG", "1", "Pham Thi Mai", ""],
            ["B0001", "ph", "4.3", "pH", "1", "Pham Thi Mai", ""],
            ["B0001", "temperature", "19.5", "C", "1", "", ""],
        ]
    },

    "19. Yeast Inventory": {
        "phase": 4,
        "description": "Current yeast stock. References Yeast Strains.",
        "headers": [
            "yeast_name", "lot_number", "quantity", "unit",
            "viability (%)", "manufacture_date (YYYY-MM-DD)",
            "expiry_date (YYYY-MM-DD)", "storage_location"
        ],
        "required": ["yeast_name", "quantity"],
        "dropdowns": {
            "unit": ["packs", "vials", "mL", "L"]
        },
        "examples": [
            ["US-05", "LOT001", "15", "packs", "95",
             "2026-03-15", "2026-06-15", "Cold Storage"],
        ]
    },

    "20. Staff Schedule": {
        "phase": 4,
        "description": "Work schedules. References Staff.",
        "headers": [
            "staff_name", "schedule_date (YYYY-MM-DD)", "shift",
            "start_time (HH:MM)", "end_time (HH:MM)", "notes"
        ],
        "required": ["staff_name", "schedule_date", "shift"],
        "dropdowns": {
            "shift": ["morning", "afternoon", "evening", "night", "full_day"]
        },
        "examples": [
            ["Nguyen Van Minh", "2026-04-25", "morning", "06:00", "14:00", ""],
        ]
    },

    "21. Training Records": {
        "phase": 4,
        "description": "Staff training history. References Staff.",
        "headers": [
            "staff_name", "training_date (YYYY-MM-DD)", "topic",
            "trainer", "duration_hours", "result", "notes"
        ],
        "required": ["staff_name", "training_date", "topic"],
        "dropdowns": {
            "result": ["passed", "excellent", "failed", "in_progress"]
        },
        "examples": [
            ["Nguyen Van Minh", "2026-03-01", "Food Safety Certification",
             "Vietfood", "8", "passed", ""],
        ]
    },
}


# ============================================================
# INSTRUCTIONS TEXT
# ============================================================

INSTRUCTIONS = [
    ["BREWERY MANAGER - DATA ENTRY INSTRUCTIONS"],
    [""],
    ["IMPORT ORDER (MUST follow this sequence):"],
    [""],
    ["PHASE 1 - Master Data (can fill simultaneously):"],
    ["  Sheet 1: Products - All beer products"],
    ["  Sheet 2: Raw Materials - Malts, hops, adjuncts, chemicals, packaging"],
    ["  Sheet 3: Staff - All employees"],
    ["  Sheet 4: Customers - Bars, restaurants, distributors, hotels"],
    ["  Sheet 5: Equipment - Fermenters, tanks, brewhouse equipment"],
    ["  Sheet 6: Yeast Strains - Yeast catalog"],
    ["  Sheet 7: Packaging Materials - Cans, bottles, kegs, carriers"],
    [""],
    ["PHASE 2 - Recipes (requires Phase 1):"],
    ["  Sheet 8: Recipes - Main recipe info (must reference Products)"],
    ["  Sheet 9: Recipe Fermentables - Grain bill per recipe"],
    ["  Sheet 10: Recipe Hops - Hop additions per recipe"],
    ["  Sheet 11: Recipe Yeast - Yeast per recipe"],
    ["  Sheet 12: Recipe Mash Steps - Mash schedule"],
    ["  Sheet 13: Recipe Other Ingredients - Coffee, fruit, spices"],
    [""],
    ["PHASE 3 - Operations (requires Phase 1 + 2):"],
    ["  Sheet 14: Production Batches - Brew batches"],
    ["  Sheet 15: Sales Orders - Customer orders"],
    ["  Sheet 16: Order Items - Line items per order"],
    ["  Sheet 17: Financial Transactions - Income and expenses"],
    [""],
    ["PHASE 4 - Supporting (requires Phase 1 + 3):"],
    ["  Sheet 18: Quality Records - QC checks per batch"],
    ["  Sheet 19: Yeast Inventory - Current yeast stock"],
    ["  Sheet 20: Staff Schedule - Work schedules"],
    ["  Sheet 21: Training Records - Training history"],
    [""],
    ["IMPORTANT RULES:"],
    ["  - Delete EXAMPLE rows (rows 5-7) before importing"],
    ["  - Keep the DESCRIPTION (row 1), HEADERS (row 2), and TYPE HINTS (row 4) intact"],
    ["  - NAME FIELDS MUST MATCH EXACTLY between sheets (e.g. product_name must match a Products name)"],
    ["  - Dates must be in YYYY-MM-DD format"],
    ["  - Amounts in VND without commas or dots (e.g. 45000 not 45,000)"],
    ["  - All data starts from row 7 onwards (after examples)"],
    ["  - Required fields are marked with REQUIRED in row 3"],
    [""],
    ["DATA ENTRY TIPS:"],
    ["  - Use dropdown menus where available (click the cell, then the arrow)"],
    ["  - For reference fields (e.g. product_name), copy-paste the exact name"],
    ["  - Save frequently - changes auto-save in Google Sheets"],
    ["  - Use the NOTES column for any extra information"],
    [""],
    ["AFTER FILLING ALL SHEETS:"],
    ["  Contact your system administrator to import the data into Brewery Manager"],
    ["  The import script will read these sheets and populate the database."],
]


# ============================================================
# SHEET CREATION LOGIC
# ============================================================

def get_credentials():
    """Load Google service account credentials."""
    json_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")

    if not json_path:
        for candidate in ["service_account.json", "credentials.json"]:
            if os.path.exists(candidate):
                json_path = candidate
                break

    if not json_path or not os.path.exists(json_path):
        print("Could not find service account credentials.")
        print()
        print("Please do ONE of the following:")
        print("  1. Set GOOGLE_SERVICE_ACCOUNT_JSON env var to your JSON key path")
        print("  2. Place 'service_account.json' in this directory")
        print()
        print("To create a service account:")
        print("  1. Go to https://console.cloud.google.com")
        print("  2. APIs & Services > Library > Enable 'Google Sheets API' and 'Google Drive API'")
        print("  3. APIs & Services > Credentials > Create Credentials > Service Account")
        print("  4. Create a key for the service account (JSON format)")
        print("  5. Share your Google Sheet with the service account email")
        sys.exit(1)

    return Credentials.from_service_account_file(json_path, scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ])


def col_letter(idx):
    """Convert 0-based column index to spreadsheet letter (A, B, ..., Z, AA, ...)."""
    result = ""
    while True:
        result = chr(65 + idx % 26) + result
        idx = idx // 26 - 1
        if idx < 0:
            break
    return result


def setup_sheet(spreadsheet, sheet_name, sheet_def):
    """Set up a single sheet with headers, formatting, validation, and examples."""
    all_sheets = spreadsheet.worksheets()

    # Find or create the sheet
    target_sheet = None
    for s in all_sheets:
        if s.title == sheet_name:
            target_sheet = s
            break

    if target_sheet is None:
        target_sheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)

    headers = sheet_def["headers"]
    description = sheet_def.get("description", "")
    examples = sheet_def.get("examples", [])
    dropdowns = sheet_def.get("dropdowns", {})
    required = sheet_def.get("required", [])
    last_col = col_letter(len(headers) - 1)

    # --- Row 1: Description ---
    target_sheet.update(range_name="A1", values=[["  " + description]])
    target_sheet.format("A1", {
        "textFormat": {"bold": True, "fontSize": 12},
        "backgroundColor": {"red": 0.85, "green": 0.92, "blue": 1.0}
    })
    end_col = col_letter(len(headers) - 1)
    target_sheet.merge_cells(
        start_row=1, start_column=1, end_row=1, end_column=len(headers)
    )

    # --- Row 2: Headers ---
    header_row = 2
    target_sheet.update(range_name="A" + str(header_row), values=[headers])
    target_sheet.format(
        "A" + str(header_row) + ":" + last_col + str(header_row),
        {
            "textFormat": {"bold": True, "fontSize": 11,
                           "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
            "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.7},
            "horizontalAlignment": "CENTER",
        }
    )

    # --- Row 3: Required indicator ---
    required_row = []
    for h in headers:
        base = h.split(" (")[0]
        if base in required:
            required_row.append("REQUIRED")
        else:
            required_row.append("")
    target_sheet.update(range_name="A3", values=[required_row])
    target_sheet.format("A3:" + last_col + "3", {
        "textFormat": {
            "foregroundColor": {"red": 0.8, "green": 0, "blue": 0},
            "italic": True, "fontSize": 9
        }
    })

    # --- Row 4: Data type hints ---
    type_hints = []
    for h in headers:
        h_lower = h.lower()
        base = h.split(" (")[0]
        if "date" in h_lower:
            type_hints.append("YYYY-MM-DD")
        elif "time" in h_lower and "date" not in h_lower:
            type_hints.append("HH:MM")
        elif any(kw in h_lower for kw in ["price", "cost", "amount", "salary", "credit"]):
            type_hints.append("VND (no commas)")
        elif "quantity" in h_lower:
            type_hints.append("Number")
        elif base in dropdowns:
            opts = dropdowns[base]
            type_hints.append("Options: " + ", ".join(opts[:5]))
        else:
            type_hints.append("Text")

    target_sheet.update(range_name="A4", values=[type_hints])
    target_sheet.format("A4:" + last_col + "4", {
        "textFormat": {"fontSize": 9,
                       "foregroundColor": {"red": 0.4, "green": 0.4, "blue": 0.4}},
        "backgroundColor": {"red": 0.96, "green": 0.96, "blue": 0.96}
    })

    # --- Row 5: Examples header ---
    data_start_row = 6
    if examples:
        target_sheet.update(
            range_name="A5",
            values=[["-- EXAMPLES (delete these rows before importing) --"]]
        )
        target_sheet.format("A5:" + last_col + "5", {
            "textFormat": {
                "italic": True, "fontSize": 9,
                "foregroundColor": {"red": 0.5, "green": 0.5, "blue": 0.5}
            },
            "backgroundColor": {"red": 1.0, "green": 0.98, "blue": 0.9}
        })
        target_sheet.merge_cells(
            start_row=5, start_column=1, end_row=5, end_column=len(headers)
        )

        # --- Example rows ---
        for i, example in enumerate(examples):
            row_num = 6 + i
            padded = example + [""] * (len(headers) - len(example))
            target_sheet.update(
                range_name="A" + str(row_num), values=[padded[:len(headers)]]
            )
            data_start_row = 6 + len(examples) + 1

    # --- Add dropdown validations ---
    for col_name, options in dropdowns.items():
        col_idx = None
        for i, h in enumerate(headers):
            base = h.split(" (")[0]
            if h == col_name or base == col_name:
                col_idx = i
                break

        if col_idx is not None:
            cl = col_letter(col_idx)
            val_range = cl + str(data_start_row) + ":" + cl + "1000"
            try:
                target_sheet.add_validation(
                    gspread.DataValidation(
                        range=val_range,
                        condition=gspread.conditions.ListCondition(options),
                        showCustomUi=True
                    )
                )
            except Exception as e:
                print("   [WARN] Could not add dropdown for " + col_name + ": " + str(e))

    # --- Freeze header rows ---
    target_sheet.freeze(rows=4)

    # --- Auto-resize columns ---
    for i in range(len(headers)):
        try:
            target_sheet.columns_auto_resize(i, i)
        except Exception:
            pass

    return target_sheet


def create_workbook(gc, title="Brewery Manager - Data Entry"):
    """Create the main Google Sheets workbook."""
    print("Creating workbook: " + title)
    spreadsheet = gc.create(title)
    url = "https://docs.google.com/spreadsheets/d/" + spreadsheet.id
    print("   URL: " + url)
    return spreadsheet


def main():
    print("=" * 60)
    print("BREWERY MANAGER - Google Sheets Data Entry Generator")
    print("=" * 60)
    print()

    creds = get_credentials()
    gc = gspread.authorize(creds)

    # Create the workbook
    spreadsheet = create_workbook(gc)

    # Get the default sheet (we'll rename it for the first data sheet)
    default_sheet = spreadsheet.sheet1

    # Process each sheet definition
    sheet_items = list(SHEETS.items())
    for idx, (sheet_name, sheet_def) in enumerate(sheet_items):
        phase = sheet_def.get("phase", 0)
        print()
        print("Creating: " + sheet_name + " (Phase " + str(phase) + ")")

        if idx == 0:
            # Rename the default sheet for the first entry
            default_sheet.update_title(sheet_name)
        else:
            spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)

        setup_sheet(spreadsheet, sheet_name, sheet_def)
        print("   Done")

    # Create Instructions sheet
    print()
    print("Creating: Instructions")
    try:
        inst_sheet = spreadsheet.add_worksheet(title="0. Instructions", rows=50, cols=10)
        spreadsheet.move_worksheet(inst_sheet, 0)
    except Exception:
        inst_sheet = spreadsheet.worksheet("0. Instructions")

    inst_sheet.update(range_name="A1", values=INSTRUCTIONS)
    inst_sheet.format("A1", {
        "textFormat": {"bold": True, "fontSize": 14}
    })
    inst_sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=10)

    # Delete any leftover default "Sheet1"
    try:
        leftover = spreadsheet.worksheet("Sheet1")
        if leftover.title == "Sheet1" and len(spreadsheet.worksheets()) > 1:
            leftover.delete()
    except Exception:
        pass

    # Share with user if email provided
    share_email = os.environ.get("SHARE_WITH_EMAIL", "")
    if share_email:
        print()
        print("Sharing with: " + share_email)
        spreadsheet.share(share_email, perm_type="user", role="writer")

    print()
    print("=" * 60)
    print("ALL DONE!")
    print("=" * 60)
    url = "https://docs.google.com/spreadsheets/d/" + spreadsheet.id
    print("Open your workbook: " + url)
    print()
    print("Next steps:")
    print("  1. Open the URL above")
    print("  2. Follow the Instructions sheet")
    print("  3. Fill in Phase 1 sheets first (Products, Raw Materials, Staff, etc.)")
    print("  4. Then Phase 2 (Recipes)")
    print("  5. Then Phase 3 (Production, Sales, Finance)")
    print("  6. Finally Phase 4 (Quality, Schedules)")
    print()
    print("Set SHARE_WITH_EMAIL env var to auto-share with your team.")


if __name__ == "__main__":
    main()
