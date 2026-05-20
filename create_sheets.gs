/**
 * BREWERY MANAGER - Google Sheets Data Entry Template Generator
 *
 * HOW TO USE:
 * 1. Open a new Google Sheet (sheets.new)
 * 2. Go to Extensions > Apps Script
 * 3. Delete any code in the editor
 * 4. Paste this entire script
 * 5. Click "Run" > select "setupBrewerySheets" from the dropdown
 * 6. Authorize when prompted (it only modifies this spreadsheet)
 * 7. Wait ~30 seconds for all 22 tabs to be created
 * 8. Close the Apps Script tab and return to your spreadsheet
 *
 * The script will create 24 sheets with headers, formatting,
 * dropdown validations, and example rows for all brewery data.
 */

function setupBrewerySheets() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();

  // ========== CLEANUP - Remove existing brewery sheets for re-run ==========
  var allSheetNames = [
    "0. Instructions", "1. Products", "2. Raw Materials", "3. Staff",
    "4. Customers", "5. Equipment", "6. Yeast Strains", "7. Packaging Materials",
    "8. Recipes", "9. Recipe Fermentables", "10. Recipe Hops", "11. Recipe Yeast",
    "12. Recipe Mash Steps", "13. Recipe Other Ingredients",
    "14. Production Batches", "15. Sales Orders", "16. Order Items",
    "17. Financial Transactions", "18. Quality Records", "19. Yeast Inventory",
    "20. Staff Schedule", "21. Training Records",
    "22. Maintenance Checklist", "23. Asset List"
  ];
  var existingSheets = ss.getSheets();
  for (var i = existingSheets.length - 1; i >= 0; i--) {
    if (allSheetNames.indexOf(existingSheets[i].getName()) !== -1) {
      if (ss.getSheets().length > 1) {
        ss.deleteSheet(existingSheets[i]);
      }
    }
  }

  // ========== 0. INSTRUCTIONS ==========
  // Reuse if it already exists (it may be the only sheet and can't be deleted)
  var instSheet = ss.getSheetByName("0. Instructions");
  if (instSheet) {
    instSheet.clear();
  } else {
    instSheet = ss.insertSheet("0. Instructions");
  }
  var instData = [
    ["BREWERY MANAGER - DATA ENTRY INSTRUCTIONS"],
    [""],
    ["IMPORT ORDER (MUST follow this sequence):"],
    [""],
    ["PHASE 1 - Master Data (fill first, can fill simultaneously):"],
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
    ["  Sheet 13: Recipe Other Ingredients - Coffee, fruit, spices, etc."],
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
    ["PHASE 5 - Maintenance & Assets (requires Phase 1):"],
    ["  Sheet 22: Maintenance Checklist - Preventive & corrective maintenance tasks"],
    ["  Sheet 23: Asset List - All brewery assets with value, condition, warranty"],
    [""],
    ["IMPORTANT RULES:"],
    ["  - Delete EXAMPLE rows (highlighted in yellow) before importing"],
    ["  - NAME FIELDS MUST MATCH EXACTLY between sheets"],
    ["  - Dates must be in YYYY-MM-DD format"],
    ["  - Amounts in VND without commas or dots (e.g. 45000 not 45,000)"],
    ["  - Required fields are marked with REQUIRED in red text"],
    [""],
    ["AFTER FILLING ALL SHEETS:"],
    ["  Contact your system administrator to import the data into Brewery Manager"],
  ];
  for (var r = 0; r < instData.length; r++) {
    instSheet.getRange(r + 1, 1).setValue(instData[r][0]);
  }
  instSheet.getRange("A1").setFontWeight("bold").setFontSize(14);
  instSheet.getRange("A1:A50").setWrap(true);
  instSheet.setColumnWidth(1, 800);

  // ========== PHASE 1 - MASTER DATA ==========

  // 1. Products
  createSheet(ss, "1. Products",
    ["name", "style", "abv", "ibu", "description", "price_per_unit (VND)", "is_active (1/0)"],
    ["name", "price_per_unit"],
    ["All beer products offered by the brewery"],
    {
      "is_active (1/0)": ["1", "0"]
    },
    [
      ["Sai Gon Pale Ale", "American Pale Ale", "5.2", "35", "Refreshing pale ale with citrus notes", "45000", "1"],
      ["Hanoi IPA", "India Pale Ale", "6.5", "65", "Bold hoppy IPA with tropical fruit", "55000", "1"],
    ]
  );

  // 2. Raw Materials
  createSheet(ss, "2. Raw Materials",
    ["name", "category", "unit", "quantity", "min_quantity", "cost_per_unit (VND)", "supplier", "origin", "expiry_date (YYYY-MM-DD)", "storage_location", "notes"],
    ["name", "category", "unit", "quantity", "cost_per_unit"],
    ["All raw materials inventory (malts, hops, adjuncts, chemicals, packaging)"],
    {
      "category": ["malt", "hops", "adjunct", "fruit", "water_treatment", "cleaning", "packaging"],
      "unit": ["kg", "g", "L", "pcs", "oz", "lb"]
    },
    [
      ["Pale Malt 2-Row", "malt", "kg", "500", "100", "35000", "Weyermann", "Germany", "2026-12-31", "Grain Room A", ""],
      ["Cascade Hops", "hops", "kg", "20", "5", "850000", "YCH Hops", "USA", "2027-06-30", "Cold Storage", ""],
      ["Coffee Beans (Vietnamese)", "adjunct", "kg", "30", "5", "450000", "Local Farm", "Vietnam", "2026-06-30", "Dry Storage", ""],
      ["PBW Cleaner", "cleaning", "kg", "20", "5", "280000", "Five Star", "USA", "2027-12-31", "Chemical Storage", ""],
      ["330ml Cans", "packaging", "pcs", "5000", "1000", "1500", "Can Supplier", "Vietnam", "", "Packaging Room", ""],
    ]
  );

  // 3. Staff
  createSheet(ss, "3. Staff",
    ["name", "position", "department", "phone", "email", "hire_date (YYYY-MM-DD)", "salary (VND/month)", "emergency_contact", "notes"],
    ["name", "position"],
    ["All brewery employees"],
    {
      "department": ["Production", "Sales", "Quality", "Finance", "Warehouse", "Front of House", "Management", "Maintenance"]
    },
    [
      ["Nguyen Van Minh", "Head Brewer", "Production", "0901234567", "minh@brewery.vn", "2023-01-15", "25000000", "", ""],
      ["Hoang Van Duc", "Sales Manager", "Sales", "0901234571", "duc@brewery.vn", "2023-04-15", "22000000", "", ""],
    ]
  );

  // 4. Customers
  createSheet(ss, "4. Customers",
    ["name", "type", "contact_person", "phone", "email", "address", "city", "province", "tax_id", "credit_limit (VND)", "payment_terms", "notes"],
    ["name"],
    ["All customer accounts (bars, restaurants, distributors, hotels, etc.)"],
    {
      "type": ["retail", "bar", "restaurant", "distributor", "hotel", "online", "other"],
      "payment_terms": ["COD", "NET 15", "NET 30", "NET 45", "NET 60", "Prepaid"]
    },
    [
      ["Craft Beer Saigon", "bar", "Le Van Tam", "0909876501", "orders@craftbeersaigon.vn", "45 Nguyen Hue, Quan 1", "Ho Chi Minh", "Ho Chi Minh", "0123456789", "50000000", "NET 30", ""],
    ]
  );

  // 5. Equipment
  createSheet(ss, "5. Equipment",
    ["name", "equipment_type", "capacity", "capacity_unit", "status", "last_cleaned (YYYY-MM-DD)", "notes"],
    ["name", "equipment_type"],
    ["All brewery equipment and tanks"],
    {
      "equipment_type": ["fermenter", "brewhouse", "processing", "packaging", "cooling", "cleaning", "filtration"],
      "status": ["available", "in_use", "maintenance", "cleaning", "out_of_service"],
      "capacity_unit": ["L", "kg", "gal"]
    },
    [
      ["Fermenter 2000L #1", "fermenter", "2000", "L", "available", "", ""],
      ["Brewhouse", "brewhouse", "1000", "L", "available", "", ""],
      ["Glycol Chiller", "cooling", "", "", "available", "", ""],
    ]
  );

  // 6. Yeast Strains
  createSheet(ss, "6. Yeast Strains",
    ["name", "lab", "product_id", "yeast_type", "form", "attenuation_min", "attenuation_max", "flocculation", "min_temp (C)", "max_temp (C)", "alcohol_tolerance (%)", "description"],
    ["name"],
    ["Yeast strain catalog and specifications"],
    {
      "yeast_type": ["ale", "lager", "wheat", "belgian", "wild", "other"],
      "form": ["dry", "liquid"],
      "flocculation": ["low", "medium", "high"]
    },
    [
      ["US-05", "Fermentis", "US-05", "ale", "dry", "73", "77", "medium", "15", "24", "11", "Clean, neutral American ale yeast"],
    ]
  );

  // 7. Packaging Materials
  createSheet(ss, "7. Packaging Materials",
    ["name", "type", "quantity", "unit", "cost_per_unit (VND)", "supplier", "reorder_level", "notes"],
    ["name", "type", "quantity", "unit"],
    ["Packaging stock inventory (cans, bottles, kegs, carriers)"],
    {
      "type": ["can", "bottle", "keg", "carrier", "box", "label", "other"],
      "unit": ["pcs", "rolls", "kg"]
    },
    [
      ["330ml Can", "can", "5000", "pcs", "1500", "Can Supplier", "1000", ""],
      ["500ml Bottle", "bottle", "2000", "pcs", "2500", "Glass Supplier", "500", ""],
      ["Keg 50L", "keg", "20", "pcs", "3500000", "Keg Supplier", "5", ""],
    ]
  );

  // ========== PHASE 2 - RECIPES ==========

  // 8. Recipes
  createSheet(ss, "8. Recipes",
    ["product_name", "name", "style", "batch_size (L)", "batch_size_unit", "boil_time (min)", "efficiency (%)", "og", "fg", "abv", "ibu", "srm", "description", "notes"],
    ["product_name", "name", "batch_size (L)"],
    ["Main recipe info - one row per recipe. References Products."],
    {
      "batch_size_unit": ["L", "gal"]
    },
    [
      ["Sai Gon Pale Ale", "SGPA Recipe", "American Pale Ale", "1000", "L", "60", "75", "1.052", "1.012", "5.2", "35", "8", "Classic American Pale Ale", ""],
    ]
  );

  // 9. Recipe Fermentables
  createSheet(ss, "9. Recipe Fermentables",
    ["recipe_name", "material_name", "amount", "unit", "percentage", "potential", "color (Lovibond)", "notes"],
    ["recipe_name", "material_name", "amount"],
    ["Grain bill per recipe. References Raw Materials (malt/adjunct)."],
    {},
    [
      ["SGPA Recipe", "Pale Malt 2-Row", "180", "kg", "85", "1.037", "3", ""],
      ["SGPA Recipe", "Crystal 60L", "20", "kg", "10", "1.034", "60", ""],
    ]
  );

  // 10. Recipe Hops
  createSheet(ss, "10. Recipe Hops",
    ["recipe_name", "hop_name", "amount", "unit", "alpha_acid (%)", "boil_time (min)", "use_type", "ibu_contribution", "notes"],
    ["recipe_name", "hop_name", "amount"],
    ["Hop additions per recipe. References Raw Materials (hops)."],
    {
      "use_type": ["boil", "dry_hop", "whirlpool", "first_wort", "mash"]
    },
    [
      ["SGPA Recipe", "Cascade", "30", "g", "5.5", "60", "boil", "15", ""],
      ["SGPA Recipe", "Cascade", "30", "g", "5.5", "15", "boil", "5", ""],
      ["SGPA Recipe", "Centennial", "20", "g", "10", "0", "dry_hop", "0", ""],
    ]
  );

  // 11. Recipe Yeast
  createSheet(ss, "11. Recipe Yeast",
    ["recipe_name", "yeast_name", "lab", "product_id", "form", "attenuation (%)", "min_temp (C)", "max_temp (C)", "notes"],
    ["recipe_name", "yeast_name"],
    ["Yeast per recipe. References Yeast Strains."],
    {
      "form": ["dry", "liquid"]
    },
    [
      ["SGPA Recipe", "US-05", "Fermentis", "US-05", "dry", "75", "18", "22", ""],
    ]
  );

  // 12. Recipe Mash Steps
  createSheet(ss, "12. Recipe Mash Steps",
    ["recipe_name", "step_number", "name", "step_type", "temperature (C)", "duration (min)", "notes"],
    ["recipe_name", "step_number", "name", "temperature (C)", "duration (min)"],
    ["Mash schedule per recipe."],
    {
      "step_type": ["temperature", "decoction", "infusion", "batch_sparge", "fly_sparge"]
    },
    [
      ["SGPA Recipe", "1", "Mash In", "temperature", "66", "60", ""],
      ["SGPA Recipe", "2", "Mash Out", "temperature", "76", "10", ""],
    ]
  );

  // 13. Recipe Other Ingredients
  createSheet(ss, "13. Recipe Other Ingredients",
    ["recipe_name", "name", "ingredient_type", "amount", "unit", "add_time", "notes"],
    ["recipe_name", "name", "amount"],
    ["Special additions per recipe (coffee, fruit, spices, etc.)."],
    {
      "ingredient_type": ["coffee", "chocolate", "spice", "fruit", "herb", "other"],
      "add_time": ["boil", "primary", "secondary", "packaging", "mash"]
    },
    [
      ["Mekong Stout Recipe", "Coffee Beans", "coffee", "5", "kg", "secondary", "Add after primary fermentation"],
    ]
  );

  // ========== PHASE 3 - OPERATIONS ==========

  // 14. Production Batches
  createSheet(ss, "14. Production Batches",
    ["batch_number", "product_name", "tank_name", "planned_quantity (L)", "actual_quantity (L)", "status", "start_date (YYYY-MM-DD)", "end_date (YYYY-MM-DD)", "brewer_name", "notes"],
    ["batch_number", "product_name", "planned_quantity (L)"],
    ["Production batch records. References Products, Equipment, Staff."],
    {
      "status": ["planned", "brewing", "fermenting", "conditioning", "completed", "cancelled"]
    },
    [
      ["B0001", "Sai Gon Pale Ale", "Fermenter 2000L #1", "1000", "", "fermenting", "2026-04-10", "", "Nguyen Van Minh", "First batch of the month"],
    ]
  );

  // 15. Sales Orders
  createSheet(ss, "15. Sales Orders",
    ["order_number", "customer_name", "order_date (YYYY-MM-DD)", "delivery_date (YYYY-MM-DD)", "status", "payment_status", "notes"],
    ["order_number", "customer_name", "order_date"],
    ["Customer sales orders. References Customers."],
    {
      "status": ["pending", "processing", "shipped", "delivered", "cancelled"],
      "payment_status": ["unpaid", "paid", "partial", "refunded"]
    },
    [
      ["ORD-1001", "Craft Beer Saigon", "2026-04-15", "2026-04-18", "delivered", "paid", ""],
    ]
  );

  // 16. Order Items
  createSheet(ss, "16. Order Items",
    ["order_number", "product_name", "quantity", "unit_price (VND)", "discount (%)", "notes"],
    ["order_number", "product_name", "quantity", "unit_price"],
    ["Line items per sales order. References Sales Orders + Products."],
    {},
    [
      ["ORD-1001", "Sai Gon Pale Ale", "48", "45000", "0", ""],
      ["ORD-1001", "Hanoi IPA", "24", "55000", "5", ""],
    ]
  );

  // 17. Financial Transactions
  createSheet(ss, "17. Financial Transactions",
    ["transaction_date (YYYY-MM-DD)", "type", "category", "amount (VND)", "description", "payment_method", "reference_id", "reference_type"],
    ["transaction_date", "type", "amount"],
    ["All income and expense transactions."],
    {
      "type": ["income", "expense"],
      "category": ["Sales", "Raw Materials", "Utilities", "Rent", "Salaries", "Packaging", "Equipment Maintenance", "Marketing", "Transportation", "Insurance", "Taxes", "Other"],
      "payment_method": ["cash", "bank_transfer", "credit_card", "momo", "zalopay", "vnpay", "check"]
    },
    [
      ["2026-04-15", "income", "Sales", "4500000", "Payment for order ORD-1001", "bank_transfer", "", ""],
      ["2026-04-01", "expense", "Rent", "25000000", "Monthly facility rent", "bank_transfer", "", ""],
    ]
  );

  // ========== PHASE 4 - SUPPORTING DATA ==========

  // 18. Quality Records
  createSheet(ss, "18. Quality Records",
    ["batch_number", "check_type", "value", "unit", "passed (1=pass, 0=fail)", "inspector", "notes"],
    ["batch_number", "check_type"],
    ["Quality control checks for production batches."],
    {
      "check_type": ["gravity", "ph", "temperature", "color", "turbidity", "taste", "aroma", "clarity", "carbonation", "microbiological"],
      "unit": ["SG", "pH", "C", "SRM", "NTU", "vols", "CFU/mL"],
      "passed (1=pass, 0=fail)": ["1", "0"]
    },
    [
      ["B0001", "gravity", "1.052", "SG", "1", "Pham Thi Mai", ""],
      ["B0001", "ph", "4.3", "pH", "1", "Pham Thi Mai", ""],
      ["B0001", "temperature", "19.5", "C", "1", "", ""],
    ]
  );

  // 19. Yeast Inventory
  createSheet(ss, "19. Yeast Inventory",
    ["yeast_name", "lot_number", "quantity", "unit", "viability (%)", "manufacture_date (YYYY-MM-DD)", "expiry_date (YYYY-MM-DD)", "storage_location"],
    ["yeast_name", "quantity"],
    ["Current yeast stock. References Yeast Strains."],
    {
      "unit": ["packs", "vials", "mL", "L"]
    },
    [
      ["US-05", "LOT001", "15", "packs", "95", "2026-03-15", "2026-06-15", "Cold Storage"],
    ]
  );

  // 20. Staff Schedule
  createSheet(ss, "20. Staff Schedule",
    ["staff_name", "schedule_date (YYYY-MM-DD)", "shift", "start_time (HH:MM)", "end_time (HH:MM)", "notes"],
    ["staff_name", "schedule_date", "shift"],
    ["Work schedules. References Staff."],
    {
      "shift": ["morning", "afternoon", "evening", "night", "full_day"]
    },
    [
      ["Nguyen Van Minh", "2026-04-25", "morning", "06:00", "14:00", ""],
    ]
  );

  // 21. Training Records
  createSheet(ss, "21. Training Records",
    ["staff_name", "training_date (YYYY-MM-DD)", "topic", "trainer", "duration_hours", "result", "notes"],
    ["staff_name", "training_date", "topic"],
    ["Staff training history. References Staff."],
    {
      "result": ["passed", "excellent", "failed", "in_progress"]
    },
    [
      ["Nguyen Van Minh", "2026-03-01", "Food Safety Certification", "Vietfood", "8", "passed", ""],
    ]
  );

  // ========== PHASE 5 - MAINTENANCE & ASSETS ==========

  // 22. Maintenance Checklist
  createSheet(ss, "22. Maintenance Checklist",
    ["equipment_name", "task_name", "task_type", "frequency_days", "next_due (YYYY-MM-DD)", "assigned_to", "status", "priority", "estimated_duration_min", "last_completed (YYYY-MM-DD)", "completion_notes", "notes"],
    ["equipment_name", "task_name", "task_type", "frequency_days"],
    ["Preventive & corrective maintenance tasks. References Equipment and Staff."],
    {
      "task_type": ["cleaning", "inspection", "calibration", "lubrication", "replacement", "repair", "testing", "other"],
      "status": ["scheduled", "overdue", "completed", "skipped", "in_progress"],
      "priority": ["critical", "high", "medium", "low"]
    },
    [
      ["Fermenter 2000L #1", "CIP Clean", "cleaning", "7", "2026-04-26", "Nguyen Van Minh", "scheduled", "high", "120", "", "", "Acid + caustic cycle"],
      ["Fermenter 2000L #1", "Gasket Inspection", "inspection", "30", "2026-05-10", "Nguyen Van Minh", "scheduled", "medium", "30", "", "", "Check door & port gaskets"],
      ["Brewhouse", "Brewhouse Clean", "cleaning", "3", "2026-04-27", "Nguyen Van Minh", "scheduled", "high", "90", "", "", "Full CIP after brew day"],
      ["Glycol Chiller", "Glycol Level Check", "inspection", "7", "2026-04-26", "Nguyen Van Minh", "scheduled", "high", "15", "", "", "Check glycol concentration & level"],
      ["Canning Line", "Canning Line Flush", "cleaning", "1", "2026-04-25", "Nguyen Van Minh", "scheduled", "high", "30", "", "", "Daily rinse and flush after use"],
    ]
  );

  // 23. Asset List
  createSheet(ss, "23. Asset List",
    ["asset_name", "asset_type", "category", "serial_number", "manufacturer", "model", "purchase_date (YYYY-MM-DD)", "purchase_cost (VND)", "current_value (VND)", "condition", "location", "assigned_to", "warranty_expiry (YYYY-MM-DD)", "insurance_policy", "notes"],
    ["asset_name", "asset_type", "category", "condition"],
    ["All brewery physical assets (tanks, equipment, furniture, IT, vehicles, etc.)"],
    {
      "asset_type": ["production_equipment", "packaging_equipment", "cooling_system", "storage", "furniture", "IT_hardware", "vehicle", "safety_equipment", "lab_equipment", "other"],
      "category": ["tangible_fixed_asset", "current_asset", "tool", "fixture", "consumable"],
      "condition": ["new", "excellent", "good", "fair", "poor", "out_of_service", "disposed"]
    },
    [
      ["Fermenter 2000L #1", "production_equipment", "tangible_fixed_asset", "FER-2024-001", "Alpha Brewing", "Uni-Tank 2000", "2023-06-15", "350000000", "300000000", "excellent", "Brewing Floor A", "", "2026-06-15", "INS-001", "Stainless steel 304"],
      ["Brewhouse", "production_equipment", "tangible_fixed_asset", "BRW-2023-001", "Alpha Brewing", "1000L 3-Vessel", "2023-01-20", "800000000", "650000000", "excellent", "Brewing Floor A", "", "2026-01-20", "INS-001", "Mash/lauter, kettle, whirlpool"],
      ["Glycol Chiller", "cooling_system", "tangible_fixed_asset", "CHL-2023-001", "ProRefrigeration", "HP-50", "2023-03-10", "180000000", "150000000", "good", "Utility Room", "", "2025-03-10", "", "5HP, glycol + water"],
      ["Packaging Table", "furniture", "fixture", "", "Local", "Custom SS", "2023-06-01", "15000000", "12000000", "good", "Packaging Room", "", "", "", ""],
      ["Laptop - Brewer", "IT_hardware", "current_asset", "", "Dell", "Latitude 5540", "2024-01-15", "22000000", "18000000", "good", "Office", "Nguyen Van Minh", "2027-01-15", "", "For BeerSmith & inventory"],
    ]
  );

  // ========== FINAL CLEANUP ==========
  // Delete the default "Sheet1" if it exists
  var sheets = ss.getSheets();
  for (var i = 0; i < sheets.length; i++) {
    if (sheets[i].getName() === "Sheet1" && sheets.length > 1) {
      ss.deleteSheet(sheets[i]);
      break;
    }
  }

  // Move Instructions to first position
  var instSheet = ss.getSheetByName("0. Instructions");
  if (instSheet) {
    ss.setActiveSheet(instSheet);
    ss.moveActiveSheet(1);
  }

  SpreadsheetApp.getUi().alert(
    "Done! Created 24 sheets.\n\n" +
    "Next steps:\n" +
    "1. Fill Phase 1 sheets first (Products, Raw Materials, Staff, etc.)\n" +
    "2. Then Phase 2 (Recipes)\n" +
    "3. Then Phase 3 (Production, Sales, Finance)\n" +
    "4. Finally Phase 4 (Quality, Schedules)\n\n" +
    "Delete the yellow example rows before importing!"
  );
}


/**
 * Helper: Create a formatted sheet with headers, required row, type hints,
 * dropdown validations, and example data.
 *
 * @param {Spreadsheet} ss - The spreadsheet
 * @param {string} sheetName - Name of the sheet to create
 * @param {string[]} headers - Column headers
 * @param {string[]} [required] - List of required field names
 * @param {string} [description] - Sheet description
 * @param {Object} [dropdowns] - Map of header -> options array
 * @param {Array[]} [examples] - Example data rows
 */
function createSheet(ss, sheetName, headers, required, description, dropdowns, examples) {
  // Defaults
  required = required || [];
  description = description || "";
  dropdowns = dropdowns || {};
  examples = examples || [];

  // Create or get the sheet
  var sheet = ss.getSheetByName(sheetName);
  if (!sheet) {
    sheet = ss.insertSheet(sheetName);
  }

  // Clear existing content
  sheet.clear();

  var numCols = headers.length;

  // --- Row 1: Description ---
  sheet.getRange("A1").setValue("  " + description).setFontWeight("bold").setFontSize(12);
  if (numCols > 1) {
    sheet.getRange(1, 1, 1, numCols).merge().setBackground("#d9e8f7");
  } else {
    sheet.getRange("A1").setBackground("#d9e8f7");
  }

  // --- Row 2: Headers ---
  var headerRange = sheet.getRange(2, 1, 1, numCols);
  headerRange.setValues([headers]);
  headerRange.setFontWeight("bold").setFontSize(11)
    .setFontColor("#ffffff")
    .setBackground("#336699")
    .setHorizontalAlignment("center");

  // --- Row 3: Required indicator ---
  var requiredRow = [];
  for (var i = 0; i < headers.length; i++) {
    var baseName = headers[i].split(" (")[0];
    requiredRow.push(required.indexOf(baseName) !== -1 ? "REQUIRED" : "");
  }
  var reqRange = sheet.getRange(3, 1, 1, numCols);
  reqRange.setValues([requiredRow]);
  reqRange.setFontColor("#cc0000").setFontStyle("italic").setFontSize(9);

  // --- Row 4: Type hints ---
  var typeHints = [];
  for (var i = 0; i < headers.length; i++) {
    var h = headers[i].toLowerCase();
    var baseName = headers[i].split(" (")[0];
    if (h.indexOf("date") !== -1) {
      typeHints.push("YYYY-MM-DD");
    } else if (h.indexOf("time") !== -1 && h.indexOf("date") === -1) {
      typeHints.push("HH:MM");
    } else if (h.match(/price|cost|amount|salary|credit|budget/)) {
      typeHints.push("VND (no commas)");
    } else if (h.indexOf("quantity") !== -1) {
      typeHints.push("Number");
    } else if (dropdowns[baseName]) {
      var opts = dropdowns[baseName];
      typeHints.push("Options: " + opts.slice(0, 5).join(", "));
    } else {
      typeHints.push("Text");
    }
  }
  var typeRange = sheet.getRange(4, 1, 1, numCols);
  typeRange.setValues([typeHints]);
  typeRange.setFontColor("#666666").setFontSize(9).setBackground("#f5f5f5");

  // --- Row 5: Examples header ---
  var dataStartRow = 6;
  if (examples.length > 0) {
    var exHeaderRange = sheet.getRange(5, 1, 1, numCols);
    exHeaderRange.merge();
    exHeaderRange.setValue("-- EXAMPLES (delete these rows before importing) --");
    exHeaderRange.setFontStyle("italic").setFontSize(9).setFontColor("#888888");
    exHeaderRange.setBackground("#fff8e1");

    // --- Example rows ---
    for (var r = 0; r < examples.length; r++) {
      var row = examples[r];
      // Pad row to match header length
      while (row.length < numCols) row.push("");
      var rowRange = sheet.getRange(6 + r, 1, 1, numCols);
      rowRange.setValues([row.slice(0, numCols)]);
      rowRange.setBackground("#fffde7"); // Light yellow for examples
    }
    dataStartRow = 6 + examples.length + 1;
  }

  // --- Add dropdown validations ---
  for (var colName in dropdowns) {
    if (!dropdowns.hasOwnProperty(colName)) continue;
    var options = dropdowns[colName];
    var colIdx = -1;
    for (var i = 0; i < headers.length; i++) {
      var baseName = headers[i].split(" (")[0];
      if (headers[i] === colName || baseName === colName) {
        colIdx = i;
        break;
      }
    }
    if (colIdx !== -1) {
      var validation = SpreadsheetApp.newDataValidation()
        .requireValueInList(options, true)
        .setAllowInvalid(true)
        .build();
      sheet.getRange(dataStartRow, colIdx + 1, 1000, 1).setDataValidation(validation);
    }
  }

  // --- Freeze header rows ---
  sheet.setFrozenRows(4);

  // --- Auto-resize columns ---
  for (var i = 0; i < numCols; i++) {
    sheet.autoResizeColumn(i + 1);
  }

  return sheet;
}