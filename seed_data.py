"""
Brewery Manager - Seed Data Script
Populates the database with realistic dummy data for testing
"""

import sys
import os
import random
from datetime import datetime, date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.database import Database

def seed_database():
    """Populate database with realistic dummy data"""
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    print("🌱 Seeding database with dummy data...")
    
    # Disable foreign keys temporarily
    cursor.execute("PRAGMA foreign_keys = OFF")
    
    # Clear existing data (except users and equipment)
    tables_to_clear = [
        'batch_ingredients', 'quality_records', 'order_items', 'sales_orders',
        'financial_transactions', 'production_batches', 'recipes', 'recipe_fermentables',
        'recipe_hops', 'recipe_yeast', 'recipe_mash_steps', 'recipe_other_ingredients',
        'yeast_inventory', 'yeast_propagations', 'yeast_usage_log', 'yeast_viability_tests',
        'raw_materials', 'products', 'customers', 'staff', 'staff_schedule',
        'daily_tasks', 'production_schedule', 'briefing_log', 'invoices', 'invoice_items',
        'deliveries', 'packaging_materials', 'notifications', 'shift_handovers',
        'training_records', 'performance_metrics'
    ]
    
    for table in tables_to_clear:
        try:
            cursor.execute(f"DELETE FROM {table}")
        except:
            pass
    
    # Re-enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")
    
    print("  ✓ Cleared existing data")
    
    # ==================== RAW MATERIALS ====================
    raw_materials = [
        # Base Malts
        ('Pale Malt 2-Row', 'malt', 'kg', 500, 100, 35000, 'Weyermann', 'Germany', '2026-12-31', 'Grain Room A'),
        ('Pilsner Malt', 'malt', 'kg', 400, 80, 38000, 'Weyermann', 'Germany', '2026-11-30', 'Grain Room A'),
        ('Vienna Malt', 'malt', 'kg', 200, 50, 40000, 'Briess', 'USA', '2026-10-31', 'Grain Room A'),
        ('Munich Malt', 'malt', 'kg', 150, 40, 42000, 'Weyermann', 'Germany', '2026-09-30', 'Grain Room A'),
        
        # Specialty Malts
        ('Crystal 60L', 'malt', 'kg', 100, 25, 55000, 'Briess', 'USA', '2026-08-31', 'Grain Room B'),
        ('Chocolate Malt', 'malt', 'kg', 50, 15, 65000, 'Simpsons', 'UK', '2026-07-31', 'Grain Room B'),
        ('Roasted Barley', 'malt', 'kg', 40, 10, 60000, 'Bairds', 'UK', '2026-06-30', 'Grain Room B'),
        ('Wheat Malt', 'malt', 'kg', 80, 20, 45000, 'Weyermann', 'Germany', '2026-12-31', 'Grain Room A'),
        ('Oat Flakes', 'adjunct', 'kg', 60, 15, 25000, 'Bob\'s Red Mill', 'USA', '2026-11-30', 'Grain Room B'),
        ('Rice Flakes', 'adjunct', 'kg', 100, 25, 18000, 'Local Supplier', 'Vietnam', '2026-10-31', 'Grain Room B'),
        
        # Hops
        ('Cascade', 'hops', 'kg', 20, 5, 850000, 'YCH Hops', 'USA', '2027-06-30', 'Cold Storage'),
        ('Centennial', 'hops', 'kg', 15, 3, 950000, 'YCH Hops', 'USA', '2027-05-31', 'Cold Storage'),
        ('Citra', 'hops', 'kg', 10, 2, 1200000, 'Hop Alliance', 'USA', '2027-04-30', 'Cold Storage'),
        ('Mosaic', 'hops', 'kg', 12, 2, 1100000, 'Hop Alliance', 'USA', '2027-03-31', 'Cold Storage'),
        ('Saaz', 'hops', 'kg', 8, 2, 750000, 'Czech Hops', 'Czech Republic', '2027-02-28', 'Cold Storage'),
        ('Hallertau', 'hops', 'kg', 6, 1, 800000, 'German Hops', 'Germany', '2027-01-31', 'Cold Storage'),
        ('Simcoe', 'hops', 'kg', 10, 2, 980000, 'YCH Hops', 'USA', '2027-06-30', 'Cold Storage'),
        ('Amarillo', 'hops', 'kg', 8, 2, 920000, 'Hop Alliance', 'USA', '2027-05-31', 'Cold Storage'),
        
        # Adjuncts & Specialties
        ('Coffee Beans (Vietnamese)', 'adjunct', 'kg', 30, 5, 450000, 'Local Coffee Farm', 'Vietnam', '2026-06-30', 'Dry Storage'),
        ('Cacao Nibs', 'adjunct', 'kg', 20, 3, 680000, 'Valrhona', 'France', '2026-12-31', 'Dry Storage'),
        ('Vanilla Beans', 'adjunct', 'kg', 5, 1, 2500000, 'Local Supplier', 'Vietnam', '2026-09-30', 'Dry Storage'),
        ('Lemongrass', 'adjunct', 'kg', 10, 2, 120000, 'Local Market', 'Vietnam', '2026-04-30', 'Dry Storage'),
        ('Ginger Root', 'adjunct', 'kg', 15, 3, 85000, 'Local Market', 'Vietnam', '2026-05-31', 'Dry Storage'),
        ('Passion Fruit Puree', 'fruit', 'kg', 50, 10, 180000, 'Local Supplier', 'Vietnam', '2026-07-31', 'Cold Storage'),
        ('Mango Puree', 'fruit', 'kg', 40, 8, 160000, 'Local Supplier', 'Vietnam', '2026-06-30', 'Cold Storage'),
        ('Dragon Fruit Puree', 'fruit', 'kg', 30, 5, 200000, 'Local Supplier', 'Vietnam', '2026-08-31', 'Cold Storage'),
        
        # Water Treatment
        ('Calcium Chloride', 'water_treatment', 'kg', 10, 2, 45000, 'Chemical Supplier', 'Vietnam', '2027-12-31', 'Chemical Storage'),
        ('Gypsum', 'water_treatment', 'kg', 10, 2, 35000, 'Chemical Supplier', 'Vietnam', '2027-12-31', 'Chemical Storage'),
        ('Lactic Acid', 'water_treatment', 'L', 5, 1, 120000, 'Chemical Supplier', 'Vietnam', '2027-06-30', 'Chemical Storage'),
        ('Phosphoric Acid', 'water_treatment', 'L', 5, 1, 150000, 'Chemical Supplier', 'Vietnam', '2027-06-30', 'Chemical Storage'),
        
        # Cleaning & Sanitization
        ('PBW (Powdered Brewery Wash)', 'cleaning', 'kg', 20, 5, 280000, 'Five Star', 'USA', '2027-12-31', 'Chemical Storage'),
        ('Star San', 'cleaning', 'L', 10, 2, 350000, 'Five Star', 'USA', '2027-12-31', 'Chemical Storage'),
        ('Iodophor', 'cleaning', 'L', 5, 1, 280000, 'Chemical Supplier', 'USA', '2027-06-30', 'Chemical Storage'),
        
        # Packaging
        ('330ml Cans', 'packaging', 'pcs', 5000, 1000, 1500, 'Can Supplier', 'Vietnam', None, 'Packaging Room'),
        ('500ml Cans', 'packaging', 'pcs', 3000, 500, 1800, 'Can Supplier', 'Vietnam', None, 'Packaging Room'),
        ('330ml Bottles', 'packaging', 'pcs', 2000, 500, 2500, 'Glass Supplier', 'Vietnam', None, 'Packaging Room'),
        ('Crowlers (32oz)', 'packaging', 'pcs', 500, 100, 5000, 'Can Supplier', 'Vietnam', None, 'Packaging Room'),
        ('Kegs (50L)', 'packaging', 'pcs', 20, 5, 3500000, 'Keg Supplier', 'Vietnam', None, 'Keg Storage'),
    ]
    
    for name, category, unit, qty, min_qty, cost, supplier, origin, expiry, location in raw_materials:
        cursor.execute("""
            INSERT INTO raw_materials (name, category, unit, quantity, min_quantity, 
                                       cost_per_unit, supplier, origin, expiry_date, storage_location)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, category, unit, qty, min_qty, cost, supplier, origin, expiry, location))
    
    print(f"  ✓ Added {len(raw_materials)} raw materials")
    
    # ==================== PRODUCTS ====================
    products = [
        ('Sài Gon Pale Ale', 'American Pale Ale', 5.2, 35, 'A refreshing pale ale with citrus notes, perfect for Vietnam\'s tropical climate', 45000),
        ('Hanoi IPA', 'India Pale Ale', 6.5, 65, 'Bold and hoppy IPA with tropical fruit aromas from Citra and Mosaic hops', 55000),
        ('Da Lat Wheat', 'American Wheat Beer', 4.8, 15, 'Light and crisp wheat beer with hints of orange and coriander', 42000),
        ('Hoi An Amber', 'American Amber Ale', 5.5, 30, 'Rich amber ale with caramel malt backbone and balanced bitterness', 48000),
        ('Mekong Stout', 'Imperial Stout', 8.5, 45, 'Rich and complex stout with Vietnamese coffee and dark chocolate notes', 65000),
        ('Nha Trang Lager', 'Czech Pilsner', 4.5, 25, 'Clean and crisp lager brewed with Saaz hops in traditional Czech style', 40000),
        ('Tropical Sour', 'Berliner Weisse', 4.0, 8, 'Tart and refreshing sour beer with passion fruit and dragon fruit', 50000),
        ('Vietnamese Coffee Stout', 'Milk Stout', 6.0, 25, 'Creamy milk stout infused with locally roasted Vietnamese coffee', 58000),
        ('Ginger Lemongrass Ale', 'Spiced Ale', 5.0, 20, 'Unique ale brewed with fresh Vietnamese ginger and lemongrass', 52000),
        ('Mango Haze', 'New England IPA', 6.8, 40, 'Hazy and juicy IPA with massive mango and tropical fruit character', 58000),
    ]
    
    for name, style, abv, ibu, description, price in products:
        cursor.execute("""
            INSERT INTO products (name, style, abv, ibu, description, price_per_unit)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, style, abv, ibu, description, price))
    
    print(f"  ✓ Added {len(products)} products")
    
    # ==================== STAFF ====================
    staff_members = [
        ('Nguyễn Văn Minh', 'Head Brewer', 'Production', '0901234567', 'minh@brewery.vn', '2023-01-15', 25000000),
        ('Trần Thị Hương', 'Brewer', 'Production', '0901234568', 'huong@brewery.vn', '2023-03-20', 18000000),
        ('Lê Hoàng Nam', 'Brewer', 'Production', '0901234569', 'nam@brewery.vn', '2023-06-10', 16000000),
        ('Phạm Thị Mai', 'Quality Control Manager', 'Quality', '0901234570', 'mai@brewery.vn', '2023-02-01', 20000000),
        ('Hoàng Văn Đức', 'Sales Manager', 'Sales', '0901234571', 'duc@brewery.vn', '2023-04-15', 22000000),
        ('Võ Thị Lan', 'Sales Representative', 'Sales', '0901234572', 'lan@brewery.vn', '2023-07-01', 15000000),
        ('Đặng Văn Tùng', 'Warehouse Manager', 'Warehouse', '0901234573', 'tung@brewery.vn', '2023-05-10', 16000000),
        ('Bùi Thị Ngọc', 'Accountant', 'Finance', '0901234574', 'ngoc@brewery.vn', '2023-08-01', 18000000),
        ('Ngô Văn Hùng', 'Packaging Operator', 'Production', '0901234575', 'hung@brewery.vn', '2023-09-15', 12000000),
        ('Lý Thị Thảo', 'Taproom Manager', 'Front of House', '0901234576', 'thao@brewery.vn', '2023-10-01', 14000000),
    ]
    
    for name, position, department, phone, email, hire_date, salary in staff_members:
        cursor.execute("""
            INSERT INTO staff (name, position, department, phone, email, hire_date, salary)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, position, department, phone, email, hire_date, salary))
    
    print(f"  ✓ Added {len(staff_members)} staff members")
    
    # ==================== CUSTOMERS ====================
    customers = [
        # Bars & Restaurants
        ('Craft Beer Saigon', 'bar', 'Lê Văn Tám', '0909876501', 'orders@craftbeersaigon.vn', 
         '45 Nguyễn Huệ, Quận 1', 'Hồ Chí Minh', 'Hồ Chí Minh', '0123456789', 50000000, 'NET 30'),
        ('Hanoi Beer House', 'bar', 'Nguyễn Thị Hoa', '0909876502', 'info@hanoibeerhouse.vn',
         '23 Hàng Bài, Hoàn Kiếm', 'Hà Nội', 'Hà Nội', '0123456790', 40000000, 'NET 30'),
        ('BiaCraft Danang', 'bar', 'Trần Văn Hùng', '0909876503', 'hung@biacraft.vn',
         '78 Bạch Đằng, Hải Châu', 'Đà Nẵng', 'Đà Nẵng', '0123456791', 30000000, 'NET 15'),
        ('The Refinery', 'restaurant', 'Sophie Martin', '0909876504', 'sophie@therefinery.vn',
         '74 Hai Bà Trưng, Quận 1', 'Hồ Chí Minh', 'Hồ Chí Minh', '0123456792', 35000000, 'NET 30'),
        ('Pizza 4P\'s', 'restaurant', 'Yuki Tanaka', '0909876505', 'yuki@pizza4ps.vn',
         '8 Thủ Khoa Huân, Quận 1', 'Hồ Chí Minh', 'Hồ Chí Minh', '0123456793', 45000000, 'NET 15'),
        
        # Distributors
        ('Sapporo Vietnam', 'distributor', 'Nguyễn Văn An', '0909876506', 'an@sapporo.vn',
         '123 Nguyễn Văn Linh, Quận 7', 'Hồ Chí Minh', 'Hồ Chí Minh', '0123456794', 200000000, 'NET 45'),
        ('Bia Hơi Distribution', 'distributor', 'Phạm Văn Bình', '0909876507', 'binh@biahoi.vn',
         '456 Giải Phóng, Hai Bà Trưng', 'Hà Nội', 'Hà Nội', '0123456795', 150000000, 'NET 30'),
        
        # Retail
        ('VinMart+', 'retail', 'Lê Thị Cúc', '0909876508', 'cuc@vinmart.vn',
         '789 Nguyễn Thị Minh Khai, Quận 3', 'Hồ Chí Minh', 'Hồ Chí Minh', '0123456796', 25000000, 'COD'),
        ('Circle K Vietnam', 'retail', 'David Wilson', '0909876509', 'david@circlek.vn',
         '321 Lê Lợi, Quận 1', 'Hồ Chí Minh', 'Hồ Chí Minh', '0123456797', 20000000, 'COD'),
        
        # Hotels
        ('Hotel des Arts Saigon', 'hotel', 'Marie Dupont', '0909876510', 'marie@hoteldesarts.vn',
         '76-78 Nguyễn Thị Minh Khai, Quận 3', 'Hồ Chí Minh', 'Hồ Chí Minh', '0123456798', 60000000, 'NET 30'),
        ('Metropole Hanoi', 'hotel', 'James Smith', '0909876511', 'james@metropole.vn',
         '15 Ngô Quyền, Hoàn Kiếm', 'Hà Nội', 'Hà Nội', '0123456799', 70000000, 'NET 30'),
        
        # Online
        ('Lazada Vietnam', 'online', 'eCommerce Dept', '0909876512', 'ecommerce@lazada.vn',
         'Tầng 20, CentrePoint, Phú Nhuận', 'Hồ Chí Minh', 'Hồ Chí Minh', '0123456800', 100000000, 'NET 15'),
        ('Shopee Vietnam', 'online', 'Beer Category', '0909876513', 'beer@shopee.vn',
         'Tầng 15, Vạn Đô Tower, Quận 1', 'Hồ Chí Minh', 'Hồ Chí Minh', '0123456801', 80000000, 'NET 15'),
    ]
    
    for name, ctype, contact, phone, email, address, city, province, tax_id, credit, terms in customers:
        cursor.execute("""
            INSERT INTO customers (name, type, contact_person, phone, email, address, 
                                   city, province, tax_id, credit_limit, payment_terms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, ctype, contact, phone, email, address, city, province, tax_id, credit, terms))
    
    print(f"  ✓ Added {len(customers)} customers")
    
    # ==================== YEAST STRAINS ====================
    yeast_strains = [
        ('US-05', 'Fermentis', 'US-05', 'ale', 'dry', 73, 77, 'medium', 15, 24, 11,
         'Clean, neutral American ale yeast. Great for IPAs and Pale Ales.'),
        ('S-04', 'Fermentis', 'S-04', 'ale', 'dry', 69, 75, 'high', 15, 24, 11,
         'English ale yeast with fruity esters. Great for bitters and stouts.'),
        ('W-34/70', 'Fermentis', 'W-34/70', 'lager', 'dry', 80, 84, 'medium', 10, 22, 11,
         'Classic German lager yeast. Clean, crisp, malty character.'),
        ('WB-06', 'Fermentis', 'WB-06', 'wheat', 'dry', 65, 72, 'low', 12, 25, 11,
         'Hefeweizen yeast with banana and clove character.'),
        ('T-58', 'Fermentis', 'T-58', 'ale', 'dry', 70, 75, 'medium', 15, 30, 12,
         'Spicy Belgian-style ale yeast with fruity esters.'),
        ('BRY-97', 'White Labs', 'WLP001', 'ale', 'liquid', 73, 80, 'medium', 18, 23, 15,
         'California Ale yeast. Clean, neutral profile.'),
        ('WLP002', 'White Labs', 'WLP002', 'ale', 'liquid', 63, 70, 'high', 18, 21, 10,
         'English Ale yeast. Fruity, malty character.'),
        ('WLP830', 'White Labs', 'WLP830', 'lager', 'liquid', 76, 83, 'medium', 10, 13, 12,
         'German Lager yeast. Clean, crisp, malty.'),
    ]
    
    for name, lab, product_id, ytype, form, atten_min, atten_max, floc, min_t, max_t, tolerance, desc in yeast_strains:
        cursor.execute("""
            INSERT INTO yeast_strains (name, lab, product_id, yeast_type, form, 
                                       attenuation_min, attenuation_max, flocculation,
                                       min_temp, max_temp, alcohol_tolerance, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, lab, product_id, ytype, form, atten_min, atten_max, floc, min_t, max_t, tolerance, desc))
    
    print(f"  ✓ Added {len(yeast_strains)} yeast strains")
    
    # Add yeast inventory
    cursor.execute("SELECT id FROM yeast_strains")
    yeast_ids = [row[0] for row in cursor.fetchall()]
    
    for yeast_id in yeast_ids[:6]:
        cursor.execute("""
            INSERT INTO yeast_inventory (yeast_id, lot_number, quantity, unit, viability, 
                                         manufacture_date, expiry_date, storage_location)
            VALUES (?, ?, ?, 'packs', 95, ?, ?, 'Cold Storage')
        """, (yeast_id, f'LOT{yeast_id:03d}', random.randint(5, 20), 
              (date.today() - timedelta(days=30)).isoformat(),
              (date.today() + timedelta(days=90)).isoformat()))
    
    print(f"  ✓ Added yeast inventory")
    
    conn.commit()
    
    # ==================== RECIPES ====================
    cursor.execute("SELECT id FROM products")
    product_ids = [row[0] for row in cursor.fetchall()]
    
    recipes_data = [
        # Sai Gon Pale Ale
        (product_ids[0], 'Sai Gon Pale Ale Recipe', 'American Pale Ale', 1000, 60, 75, 1.052, 1.012, 5.2, 35, 8,
         [(1, 'Pale Malt 2-Row', 180, 'kg', 85, 1.037, 3),
          (1, 'Crystal 60L', 20, 'kg', 10, 1.034, 60),
          (1, 'Wheat Malt', 10, 'kg', 5, 1.037, 2)],
         [(1, 'Cascade', 30, 'g', 5.5, 60, 'boil', 15),
          (1, 'Cascade', 30, 'g', 5.5, 15, 'boil', 5),
          (1, 'Centennial', 20, 'g', 10, 0, 'dry_hop', 0)],
         [(1, 'US-05', 'Fermentis', 'US-05', 'dry', 75, 18, 22)],
         [(1, 1, 'Mash In', 'temperature', 66, 60),
          (1, 2, 'Mash Out', 'temperature', 76, 10)]),
        
        # Hanoi IPA
        (product_ids[1], 'Hanoi IPA Recipe', 'India Pale Ale', 1000, 75, 72, 1.065, 1.012, 6.5, 65, 6,
         [(2, 'Pale Malt 2-Row', 200, 'kg', 80, 1.037, 3),
          (2, 'Vienna Malt', 30, 'kg', 12, 1.036, 4),
          (2, 'Crystal 60L', 15, 'kg', 6, 1.034, 60),
          (2, 'Dextrose', 5, 'kg', 2, 1.046, 0)],
         [(2, 'Citra', 40, 'g', 12, 60, 'boil', 25),
          (2, 'Mosaic', 40, 'g', 12.5, 15, 'boil', 8),
          (2, 'Citra', 50, 'g', 12, 0, 'dry_hop', 0),
          (2, 'Mosaic', 50, 'g', 12.5, 0, 'dry_hop', 0)],
         [(2, 'US-05', 'Fermentis', 'US-05', 'dry', 75, 18, 22)],
         [(2, 1, 'Mash In', 'temperature', 65, 60),
          (2, 2, 'Mash Out', 'temperature', 76, 10)]),
        
        # Da Lat Wheat
        (product_ids[2], 'Da Lat Wheat Recipe', 'American Wheat Beer', 1000, 60, 75, 1.048, 1.010, 4.8, 15, 4,
         [(3, 'Wheat Malt', 100, 'kg', 50, 1.037, 2),
          (3, 'Pale Malt 2-Row', 90, 'kg', 45, 1.037, 3),
          (3, 'Oat Flakes', 10, 'kg', 5, 1.032, 1)],
         [(3, 'Hallertau', 25, 'g', 4.5, 60, 'boil', 10),
          (3, 'Cascade', 15, 'g', 5.5, 5, 'boil', 2)],
         [(3, 'WB-06', 'Fermentis', 'WB-06', 'wheat', 68, 16, 24)],
         [(3, 1, 'Mash In', 'temperature', 64, 60),
          (3, 2, 'Mash Out', 'temperature', 76, 10)]),
        
        # Hoi An Amber
        (product_ids[3], 'Hoi An Amber Recipe', 'American Amber Ale', 1000, 60, 75, 1.056, 1.014, 5.5, 30, 12,
         [(4, 'Pale Malt 2-Row', 160, 'kg', 70, 1.037, 3),
          (4, 'Munich Malt', 40, 'kg', 18, 1.035, 9),
          (4, 'Crystal 60L', 20, 'kg', 9, 1.034, 60),
          (4, 'Chocolate Malt', 5, 'kg', 3, 1.028, 350)],
         [(4, 'Centennial', 30, 'g', 10, 60, 'boil', 18),
          (4, 'Cascade', 25, 'g', 5.5, 15, 'boil', 4)],
         [(4, 'US-05', 'Fermentis', 'US-05', 'dry', 75, 18, 22)],
         [(4, 1, 'Mash In', 'temperature', 67, 60),
          (4, 2, 'Mash Out', 'temperature', 76, 10)]),
        
        # Mekong Stout
        (product_ids[4], 'Mekong Stout Recipe', 'Imperial Stout', 1000, 90, 70, 1.085, 1.018, 8.5, 45, 40,
         [(5, 'Pale Malt 2-Row', 220, 'kg', 65, 1.037, 3),
          (5, 'Munich Malt', 40, 'kg', 12, 1.035, 9),
          (5, 'Chocolate Malt', 30, 'kg', 9, 1.028, 350),
          (5, 'Roasted Barley', 25, 'kg', 7, 1.025, 500),
          (5, 'Crystal 60L', 20, 'kg', 6, 1.034, 60),
          (5, 'Oat Flakes', 15, 'kg', 4, 1.032, 1)],
         [(5, 'Simcoe', 40, 'g', 13, 60, 'boil', 30),
          (5, 'Centennial', 30, 'g', 10, 30, 'boil', 12)],
         [(5, 'S-04', 'Fermentis', 'S-04', 'ale', 72, 18, 22)],
         [(5, 1, 'Mash In', 'temperature', 68, 75),
          (5, 2, 'Mash Out', 'temperature', 76, 10)],
         [(5, 'Coffee Beans (Vietnamese)', 'coffee', 5, 'kg', 'secondary', 'Add after primary fermentation'),
          (5, 'Cacao Nibs', 'chocolate', 2, 'kg', 'secondary', 'Add after primary fermentation'),
          (5, 'Vanilla Beans', 'spice', 0.05, 'kg', 'secondary', 'Scrape and add to secondary')]),
    ]
    
    for recipe_data in recipes_data[:5]:
        # Unpack base fields (first 11 are always present)
        product_id, name, style, batch_size, boil_time, efficiency, og, fg, abv, ibu, srm = recipe_data[:11]
        fermentables = recipe_data[11]
        hops = recipe_data[12]
        yeast = recipe_data[13]
        mash_steps = recipe_data[14]
        other_ingredients = recipe_data[15] if len(recipe_data) > 15 else []
        
        # Insert recipe
        cursor.execute("""
            INSERT INTO recipes (product_id, name, style, batch_size, boil_time, efficiency, 
                                 og, fg, abv, ibu, srm, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (product_id, name, style, batch_size, boil_time, efficiency, og, fg, abv, ibu, srm))
        recipe_id = cursor.lastrowid
        
        # Insert fermentables
        for fermentable in fermentables:
            _, fname, amount, unit, percentage, potential, color = fermentable
            cursor.execute("""
                INSERT INTO recipe_fermentables (recipe_id, name, amount, unit, percentage, potential, color)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (recipe_id, fname, amount, unit, percentage, potential, color))
        
        # Insert hops
        for hop in hops:
            _, hname, amount, unit, alpha, boil_t, use_t, ibu_cont = hop
            cursor.execute("""
                INSERT INTO recipe_hops (recipe_id, name, amount, unit, alpha_acid, boil_time, use_type, ibu_contribution)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (recipe_id, hname, amount, unit, alpha, boil_t, use_t, ibu_cont))
        
        # Insert yeast
        for y in yeast:
            _, yname, lab, prod_id, form, atten, min_temp, max_temp = y
            cursor.execute("""
                INSERT INTO recipe_yeast (recipe_id, name, lab, product_id, form, attenuation, min_temp, max_temp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (recipe_id, yname, lab, prod_id, form, atten, min_temp, max_temp))
        
        # Insert mash steps
        for step in mash_steps:
            _, step_num, step_name, step_type, temp, duration = step
            cursor.execute("""
                INSERT INTO recipe_mash_steps (recipe_id, step_number, name, step_type, temperature, duration)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (recipe_id, step_num, step_name, step_type, temp, duration))
        
        # Insert other ingredients if present
        for ingredient in other_ingredients:
            _, iname, itype, amount, unit, add_time, notes = ingredient
            cursor.execute("""
                INSERT INTO recipe_other_ingredients (recipe_id, name, ingredient_type, amount, unit, add_time, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (recipe_id, iname, itype, amount, unit, add_time, notes))
    
    print(f"  ✓ Added {len(recipes_data[:5])} recipes with ingredients")
    
    conn.commit()
    
    # ==================== PRODUCTION BATCHES ====================
    cursor.execute("SELECT id FROM products")
    product_ids = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT id FROM equipment WHERE equipment_type = 'fermenter'")
    fermenter_ids = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT id FROM staff WHERE department = 'Production'")
    brewer_ids = [row[0] for row in cursor.fetchall()]
    
    # Create batches for last 3 months
    batch_number = 1
    for months_ago in range(3, 0, -1):
        for week in range(4):
            for _ in range(random.randint(2, 4)):
                product_id = random.choice(product_ids)
                tank_id = random.choice(fermenter_ids) if random.random() > 0.2 else None
                brewer_id = random.choice(brewer_ids)
                
                start_date = date.today() - timedelta(days=months_ago * 30 + week * 7 + random.randint(0, 6))
                duration = random.randint(14, 21)
                end_date = start_date + timedelta(days=duration)
                
                status_weights = {
                    'completed': 70,
                    'fermenting': 15,
                    'conditioning': 10,
                    'planned': 5
                }
                status = random.choices(list(status_weights.keys()), weights=list(status_weights.values()))[0]
                
                planned_qty = random.choice([500, 800, 1000, 1500, 2000])
                actual_qty = planned_qty * random.uniform(0.85, 0.98) if status == 'completed' else None
                
                cursor.execute("""
                    INSERT INTO production_batches (batch_number, product_id, tank_id, planned_quantity,
                                                    actual_quantity, status, start_date, end_date, brewer_id, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (f'B{batch_number:04d}', product_id, tank_id, planned_qty, actual_qty,
                      status, start_date.isoformat(), end_date.isoformat() if status == 'completed' else None,
                      brewer_id, f'Batch #{batch_number}'))
                
                batch_id = cursor.lastrowid
                batch_number += 1
                
                # Add quality records
                if status in ['completed', 'fermenting', 'conditioning']:
                    quality_checks = [
                        ('gravity', random.uniform(1.010, 1.020), 'SG', 1, 'Phạm Thị Mai'),
                        ('ph', random.uniform(4.0, 4.6), 'pH', 1, 'Phạm Thị Mai'),
                        ('temperature', random.uniform(18, 22), '°C', 1, None),
                        ('color', random.uniform(4, 30), 'SRM', 1, 'Phạm Thị Mai'),
                        ('turbidity', random.uniform(0, 50), 'NTU', 1, 'Phạm Thị Mai'),
                    ]
                    
                    for check_type, value, unit, passed, inspector in quality_checks:
                        if random.random() > 0.1:  # 90% pass rate
                            cursor.execute("""
                                INSERT INTO quality_records (batch_id, check_type, value, unit, passed, inspector)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (batch_id, check_type, round(value, 2), unit, passed, inspector))
    
    print(f"  ✓ Added {batch_number - 1} production batches with quality records")
    
    conn.commit()
    
    # ==================== SALES ORDERS ====================
    cursor.execute("SELECT id FROM customers")
    customer_ids = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT id FROM products")
    product_ids = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT id, price_per_unit FROM products")
    products_with_prices = {row[0]: row[1] for row in cursor.fetchall()}
    
    order_number = 1000
    for months_ago in range(3, 0, -1):
        for _ in range(random.randint(15, 25)):
            customer_id = random.choice(customer_ids)
            order_date = date.today() - timedelta(days=months_ago * 30 + random.randint(0, 29))
            delivery_date = order_date + timedelta(days=random.randint(1, 7))
            
            status_weights = {
                'delivered': 60,
                'processing': 20,
                'pending': 15,
                'cancelled': 5
            }
            status = random.choices(list(status_weights.keys()), weights=list(status_weights.values()))[0]
            
            cursor.execute("""
                INSERT INTO sales_orders (order_number, customer_id, order_date, delivery_date, status, payment_status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (f'ORD-{order_number}', customer_id, order_date.isoformat(), 
                  delivery_date.isoformat() if status != 'cancelled' else None,
                  status, 'paid' if status == 'delivered' else 'unpaid'))
            
            order_id = cursor.lastrowid
            order_number += 1
            
            # Add order items
            num_items = random.randint(1, 4)
            total_amount = 0
            for _ in range(num_items):
                product_id = random.choice(product_ids)
                quantity = random.choice([24, 48, 72, 96, 120])  # Cases
                unit_price = products_with_prices[product_id]
                discount = random.choice([0, 0, 0, 5, 10])  # Occasional discount
                subtotal = quantity * unit_price * (1 - discount / 100)
                total_amount += subtotal
                
                cursor.execute("""
                    INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount, subtotal)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (order_id, product_id, quantity, unit_price, discount, subtotal))
            
            # Update order total
            cursor.execute("UPDATE sales_orders SET total_amount = ? WHERE id = ?", (total_amount, order_id))
            
            # Create delivery for delivered orders
            if status == 'delivered':
                cursor.execute("""
                    INSERT INTO deliveries (order_id, delivery_date, status, delivered_at)
                    VALUES (?, ?, 'delivered', ?)
                """, (order_id, delivery_date.isoformat(), 
                      datetime.combine(delivery_date, datetime.min.time()).isoformat()))
    
    print(f"  ✓ Added {order_number - 1000} sales orders with items and deliveries")
    
    conn.commit()
    
    # ==================== FINANCIAL TRANSACTIONS ====================
    cursor.execute("SELECT id, total_amount, order_date FROM sales_orders WHERE status = 'delivered'")
    delivered_orders = cursor.fetchall()
    
    for order_id, amount, order_date in delivered_orders:
        # Revenue transaction
        cursor.execute("""
            INSERT INTO financial_transactions (transaction_date, type, category, amount, description, 
                                                payment_method, reference_id, reference_type)
            VALUES (?, 'income', 'Sales', ?, ?, 'bank_transfer', ?, 'order')
        """, (order_date, amount, f'Payment for order #{order_id}', order_id))
    
    # Add expense transactions
    expense_categories = [
        ('Raw Materials', 'Purchase of malt and hops', random.uniform(20000000, 50000000)),
        ('Utilities', 'Electricity and water', random.uniform(3000000, 8000000)),
        ('Rent', 'Facility rent', 25000000),
        ('Salaries', 'Staff salaries', 150000000),
        ('Packaging', 'Cans and bottles', random.uniform(5000000, 15000000)),
        ('Equipment Maintenance', 'Equipment service', random.uniform(2000000, 10000000)),
        ('Marketing', 'Promotion and advertising', random.uniform(3000000, 12000000)),
    ]
    
    for months_ago in range(3, 0, -1):
        for category, description, amount in expense_categories:
            # Monthly expenses
            transaction_date = date.today() - timedelta(days=months_ago * 30 + random.randint(0, 29))
            cursor.execute("""
                INSERT INTO financial_transactions (transaction_date, type, category, amount, description, payment_method)
                VALUES (?, 'expense', ?, ?, ?, 'bank_transfer')
            """, (transaction_date.isoformat(), category, amount, description))
    
    print(f"  ✓ Added financial transactions")
    
    conn.commit()
    
    # ==================== INVOICES ====================
    cursor.execute("SELECT id, customer_id, total_amount, order_date FROM sales_orders WHERE status = 'delivered' LIMIT 20")
    orders_for_invoices = cursor.fetchall()
    
    invoice_number = 1000
    for order_id, customer_id, total, order_date in orders_for_invoices:
        cursor.execute("""
            INSERT INTO invoices (invoice_number, customer_id, invoice_date, subtotal, vat_amount, total, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (f'INV-{invoice_number}', customer_id, order_date, 
              total * 0.91, total * 0.09, total, 'paid'))
        
        invoice_id = cursor.lastrowid
        
        # Get order items
        cursor.execute("""
            SELECT product_id, quantity, unit_price, subtotal 
            FROM order_items WHERE order_id = ?
        """, (order_id,))
        items = cursor.fetchall()
        
        for product_id, qty, price, subtotal in items:
            cursor.execute("""
                INSERT INTO invoice_items (invoice_id, product_id, quantity, unit_price, line_total)
                VALUES (?, ?, ?, ?, ?)
            """, (invoice_id, product_id, qty, price, subtotal))
        
        invoice_number += 1
    
    print(f"  ✓ Added {invoice_number - 1000} invoices")
    
    # ==================== PACKAGING MATERIALS ====================
    packaging = [
        ('330ml Can', 'can', 5000, 'pcs', 1500, 1000),
        ('500ml Can', 'can', 3000, 'pcs', 1800, 500),
        ('330ml Bottle', 'bottle', 2000, 'pcs', 2500, 500),
        ('500ml Bottle', 'bottle', 1500, 'pcs', 3000, 300),
        ('Crowler 32oz', 'can', 500, 'pcs', 5000, 100),
        ('Keg 50L', 'keg', 20, 'pcs', 3500000, 5),
        ('6-Pack Carrier', 'carrier', 800, 'pcs', 3000, 200),
        ('12-Pack Box', 'box', 400, 'pcs', 5000, 100),
        ('Case Box', 'box', 200, 'pcs', 8000, 50),
    ]
    
    for name, ptype, qty, unit, cost, reorder in packaging:
        cursor.execute("""
            INSERT INTO packaging_materials (name, type, quantity, unit, cost_per_unit, reorder_level)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, ptype, qty, unit, cost, reorder))
    
    print(f"  ✓ Added {len(packaging)} packaging materials")
    
    # ==================== DAILY TASKS ====================
    for days_ago in range(7, -1, -1):
        task_date = date.today() - timedelta(days=days_ago)
        
        tasks = [
            ('production', 'Morning brew check', 'Check brewhouse temperature and mash progress', 'normal'),
            ('quality', 'Gravity reading', 'Take gravity readings for fermenting batches', 'high'),
            ('maintenance', 'CIP fermenter', 'Clean-in-place for fermenter #2', 'normal'),
            ('inventory', 'Stock check', 'Verify hop inventory levels', 'normal'),
            ('sales', 'Follow up orders', 'Contact pending order customers', 'high'),
        ]
        
        for task_type, title, description, priority in tasks:
            assigned_to = random.choice(brewer_ids) if brewer_ids else None
            status = 'completed' if days_ago > 0 else random.choice(['pending', 'in_progress', 'completed'])
            
            cursor.execute("""
                INSERT INTO daily_tasks (task_date, task_type, title, description, assigned_to, priority, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (task_date.isoformat(), task_type, title, description, assigned_to, priority, status))
    
    print(f"  ✓ Added daily tasks")
    
    # ==================== STAFF SCHEDULE ====================
    cursor.execute("SELECT id FROM staff")
    all_staff = [row[0] for row in cursor.fetchall()]
    
    for days_ago in range(14, -1, -1):
        schedule_date = date.today() - timedelta(days=days_ago)
        
        # Skip weekends for some staff
        if schedule_date.weekday() >= 5:
            continue
        
        for staff_id in all_staff[:6]:  # First 6 staff work shifts
            shift = random.choice(['morning', 'afternoon', 'evening'])
            
            if shift == 'morning':
                start_time, end_time = '06:00', '14:00'
            elif shift == 'afternoon':
                start_time, end_time = '14:00', '22:00'
            else:
                start_time, end_time = '22:00', '06:00'
            
            cursor.execute("""
                INSERT INTO staff_schedule (staff_id, schedule_date, shift, start_time, end_time)
                VALUES (?, ?, ?, ?, ?)
            """, (staff_id, schedule_date.isoformat(), shift, start_time, end_time))
    
    print(f"  ✓ Added staff schedules")
    
    # ==================== PERFORMANCE METRICS ====================
    for months_ago in range(3, 0, -1):
        metrics = [
            ('production', 'Batch Completion Rate', random.uniform(85, 98), '%', 95),
            ('production', 'Average Batch Time', random.uniform(14, 21), 'days', 18),
            ('quality', 'First Pass Quality Rate', random.uniform(92, 99), '%', 95),
            ('sales', 'Order Fulfillment Rate', random.uniform(88, 97), '%', 95),
            ('sales', 'Customer Satisfaction', random.uniform(4.0, 4.8), 'stars', 4.5),
            ('inventory', 'Stock Turnover', random.uniform(3, 6), 'times', 4),
            ('finance', 'Gross Margin', random.uniform(35, 55), '%', 45),
            ('finance', 'Revenue Growth', random.uniform(5, 20), '%', 10),
        ]
        
        for category, name, value, unit, target in metrics:
            metric_date = date.today() - timedelta(days=months_ago * 30)
            cursor.execute("""
                INSERT INTO performance_metrics (metric_date, category, metric_name, value, unit, target)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (metric_date.isoformat(), category, name, round(value, 1), unit, target))
    
    print(f"  ✓ Added performance metrics")
    
    # ==================== TRAINING RECORDS ====================
    cursor.execute("SELECT id FROM staff")
    all_staff = [row[0] for row in cursor.fetchall()]
    
    training_topics = [
        ('Food Safety Certification', 'Vietfood', 8),
        ('Brewing Science Fundamentals', 'Nguyễn Văn Minh', 16),
        ('Quality Control Procedures', 'Phạm Thị Mai', 4),
        ('Equipment Maintenance', 'External Trainer', 6),
        ('Customer Service Excellence', 'Hoàng Văn Đức', 4),
        ('Fire Safety Training', 'Fire Department', 2),
    ]
    
    for staff_id in all_staff[:5]:
        for topic, trainer, hours in random.sample(training_topics, 3):
            training_date = date.today() - timedelta(days=random.randint(30, 180))
            cursor.execute("""
                INSERT INTO training_records (staff_id, training_date, topic, trainer, duration_hours, result)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (staff_id, training_date.isoformat(), topic, trainer, hours, 
                  random.choice(['passed', 'passed', 'passed', 'excellent'])))
    
    print(f"  ✓ Added training records")
    
    # ==================== NOTIFICATIONS ====================
    cursor.execute("SELECT id FROM users")
    user_ids = [row[0] for row in cursor.fetchall()]
    
    notifications = [
        ('Low Stock Alert', 'Pale Malt 2-Row is running low (100 kg remaining)', 'warning', '/inventory'),
        ('Batch Complete', 'Batch B0005 has completed fermentation', 'success', '/production'),
        ('New Order', 'New order from Craft Beer Saigon', 'info', '/sales'),
        ('Quality Alert', 'Batch B0008 failed gravity check', 'danger', '/quality'),
        ('Maintenance Due', 'Fermenter #3 cleaning due tomorrow', 'warning', '/maintenance'),
    ]
    
    for user_id in user_ids[:2]:
        for title, message, ntype, link in notifications:
            created_at = datetime.now() - timedelta(hours=random.randint(1, 48))
            is_read = 1 if random.random() > 0.5 else 0
            cursor.execute("""
                INSERT INTO notifications (user_id, title, message, type, is_read, link, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, title, message, ntype, is_read, link, created_at.isoformat()))
    
    print(f"  ✓ Added notifications")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Database seeding complete!")
    print("\n📊 Summary:")
    print(f"   - {len(raw_materials)} raw materials")
    print(f"   - {len(products)} products")
    print(f"   - {len(staff_members)} staff members")
    print(f"   - {len(customers)} customers")
    print(f"   - {len(yeast_strains)} yeast strains")
    print(f"   - {len(recipes_data[:5])} recipes")
    print(f"   - {batch_number - 1} production batches")
    print(f"   - {order_number - 1000} sales orders")
    print(f"   - {invoice_number - 1000} invoices")
    print(f"   - Plus financial transactions, quality records, schedules, etc.")

if __name__ == '__main__':
    seed_database()
