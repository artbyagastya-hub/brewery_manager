"""
Brewery Manager - CLI Interface
Comprehensive command-line interface for brewery management in Vietnam
"""

import sys
import os
from datetime import datetime, date
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import Database


class BreweryCLI:
    """Main CLI class for brewery management"""

    def __init__(self):
        self.db = Database()
        self.running = True

    def clear_screen(self):
        """Clear terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self):
        """Print application header"""
        print("\n" + "=" * 60)
        print("  🍺 BREWERY MANAGER - Vietnam Edition")
        print("  Comprehensive Brewery Management System")
        print("=" * 60)

    def print_menu(self, title: str, options: list):
        """Print a formatted menu"""
        print(f"\n📋 {title}")
        print("-" * 40)
        for i, option in enumerate(options, 1):
            print(f"  {i}. {option}")
        print(f"  0. Back / Exit")
        print("-" * 40)

    def get_input(self, prompt: str, required: bool = True, default: str = None) -> Optional[str]:
        """Get user input with optional default"""
        while True:
            if default:
                value = input(f"  {prompt} [{default}]: ").strip()
                if not value:
                    return default
            else:
                value = input(f"  {prompt}: ").strip()

            if not required or value:
                return value if value else None
            print("  ⚠️  This field is required!")

    def get_number(self, prompt: str, default: float = 0, num_type: type = float) -> float:
        """Get numeric input"""
        while True:
            value = input(f"  {prompt} [{default}]: ").strip()
            if not value:
                return default
            try:
                return num_type(value)
            except ValueError:
                print("  ⚠️  Please enter a valid number!")

    def pause(self):
        """Pause for user input"""
        input("\n  Press Enter to continue...")

    # ==================== DASHBOARD ====================

    def show_dashboard(self):
        """Show main dashboard"""
        self.clear_screen()
        self.print_header()

        data = self.db.get_dashboard_data()

        print("\n📊 DASHBOARD")
        print("=" * 60)

        print(f"\n  🏭 Production:")
        print(f"     Active Batches:      {data['active_batches']}")
        print(f"     Active Products:     {data['total_products']}")

        print(f"\n  📦 Inventory:")
        print(f"     Low Stock Alerts:    {data['low_stock_materials']}")

        print(f"\n  📝 Orders:")
        print(f"     Pending Orders:      {data['pending_orders']}")

        print(f"\n  💰 Finance (This Month):")
        print(f"     Revenue:             {data['monthly_revenue']:,.0f} VND")
        print(f"     Expenses:            {data['monthly_expenses']:,.0f} VND")
        print(f"     Profit:              {data['monthly_profit']:,.0f} VND")

        print(f"\n  👥 Business:")
        print(f"     Total Customers:     {data['total_customers']}")
        print(f"     Total Staff:         {data['total_staff']}")

        # Show alerts
        low_stock = self.db.get_low_stock_alerts()
        if low_stock:
            print("\n  ⚠️  LOW STOCK ALERTS:")
            for item in low_stock[:5]:
                print(f"     - {item['name']}: {item['quantity']} {item['unit']} (min: {item['min_quantity']})")

        expiring = self.db.get_expiring_materials(30)
        if expiring:
            print("\n  ⏰ EXPIRING SOON:")
            for item in expiring[:5]:
                print(f"     - {item['name']}: {item['days_remaining']:.0f} days remaining")

        print("\n" + "=" * 60)
        self.pause()

    # ==================== INVENTORY ====================

    def inventory_menu(self):
        """Inventory management menu"""
        while True:
            self.clear_screen()
            self.print_header()
            self.print_menu("INVENTORY MANAGEMENT", [
                "View All Materials",
                "View by Category",
                "View Low Stock",
                "Add New Material",
                "Update Material",
                "Adjust Stock",
                "View Expiring Materials"
            ])

            choice = input("\n  Select option: ").strip()

            if choice == "0":
                break
            elif choice == "1":
                self.view_materials()
            elif choice == "2":
                self.view_materials_by_category()
            elif choice == "3":
                self.view_low_stock()
            elif choice == "4":
                self.add_material()
            elif choice == "5":
                self.update_material()
            elif choice == "6":
                self.adjust_stock()
            elif choice == "7":
                self.view_expiring()

    def view_materials(self):
        """View all materials"""
        self.clear_screen()
        print("\n📦 ALL RAW MATERIALS")
        print("=" * 80)

        materials = self.db.get_raw_materials()
        if not materials:
            print("  No materials found.")
        else:
            print(f"\n  {'ID':<4} {'Name':<25} {'Category':<12} {'Qty':<10} {'Unit':<8} {'Cost/Unit':<12}")
            print("  " + "-" * 75)
            for m in materials:
                print(f"  {m['id']:<4} {m['name']:<25} {m['category']:<12} {m['quantity']:<10} {m['unit']:<8} {m['cost_per_unit']:<12,.0f}")

        self.pause()

    def view_materials_by_category(self):
        """View materials by category"""
        self.clear_screen()
        print("\n📦 VIEW BY CATEGORY")
        print("-" * 30)
        print("  1. Hops")
        print("  2. Malt")
        print("  3. Yeast")
        print("  4. Adjuncts")
        print("  5. Packaging")

        choice = input("\n  Select category: ").strip()
        categories = {"1": "hops", "2": "malt", "3": "yeast", "4": "adjuncts", "5": "packaging"}

        if choice in categories:
            materials = self.db.get_raw_materials(category=categories[choice])
            print(f"\n  {categories[choice].upper()} MATERIALS:")
            print("  " + "-" * 60)
            for m in materials:
                print(f"  - {m['name']}: {m['quantity']} {m['unit']} (Supplier: {m['supplier'] or 'N/A'})")

        self.pause()

    def view_low_stock(self):
        """View low stock items"""
        self.clear_screen()
        print("\n⚠️  LOW STOCK ALERTS")
        print("=" * 60)

        items = self.db.get_low_stock_alerts()
        if not items:
            print("  ✅ All materials are adequately stocked!")
        else:
            for item in items:
                print(f"\n  🔴 {item['name']}")
                print(f"     Current: {item['quantity']} {item['unit']}")
                print(f"     Minimum: {item['min_quantity']} {item['unit']}")
                print(f"     Shortage: {item['shortage']} {item['unit']}")
                print(f"     Supplier: {item['supplier'] or 'Not specified'}")

        self.pause()

    def add_material(self):
        """Add new material"""
        self.clear_screen()
        print("\n➕ ADD NEW RAW MATERIAL")
        print("-" * 40)

        name = self.get_input("Material name")
        if not name:
            return

        print("\n  Categories: hops, malt, yeast, adjuncts, packaging")
        category = self.get_input("Category")

        print("\n  Units: kg, liters, pieces")
        unit = self.get_input("Unit")

        quantity = self.get_number("Initial quantity", 0)
        min_quantity = self.get_number("Minimum stock level", 0)
        cost = self.get_number("Cost per unit (VND)", 0)
        supplier = self.get_input("Supplier", required=False)
        origin = self.get_input("Origin", required=False)
        expiry = self.get_input("Expiry date (YYYY-MM-DD)", required=False)
        location = self.get_input("Storage location", required=False)
        notes = self.get_input("Notes", required=False)

        data = {
            'name': name, 'category': category, 'unit': unit,
            'quantity': quantity, 'min_quantity': min_quantity,
            'cost_per_unit': cost, 'supplier': supplier, 'origin': origin,
            'expiry_date': expiry, 'storage_location': location, 'notes': notes
        }

        material_id = self.db.add_raw_material(data)
        print(f"\n  ✅ Material added successfully! (ID: {material_id})")
        self.pause()

    def update_material(self):
        """Update material"""
        self.clear_screen()
        print("\n✏️  UPDATE MATERIAL")
        print("-" * 40)

        materials = self.db.get_raw_materials()
        for m in materials:
            print(f"  {m['id']}. {m['name']} ({m['category']})")

        material_id = self.get_number("Enter material ID to update", 0, int)
        if material_id == 0:
            return

        print("\n  Leave blank to keep current value")
        data = {}

        name = self.get_input("New name", required=False)
        if name:
            data['name'] = name

        quantity = self.get_input("New quantity", required=False)
        if quantity:
            data['quantity'] = float(quantity)

        cost = self.get_input("New cost per unit", required=False)
        if cost:
            data['cost_per_unit'] = float(cost)

        supplier = self.get_input("New supplier", required=False)
        if supplier:
            data['supplier'] = supplier

        if data:
            self.db.update_raw_material(int(material_id), data)
            print("\n  ✅ Material updated successfully!")
        else:
            print("\n  No changes made.")

        self.pause()

    def adjust_stock(self):
        """Adjust stock quantity"""
        self.clear_screen()
        print("\n📊 ADJUST STOCK")
        print("-" * 40)

        materials = self.db.get_raw_materials()
        for m in materials:
            print(f"  {m['id']}. {m['name']}: {m['quantity']} {m['unit']}")

        material_id = self.get_number("Enter material ID", 0, int)
        if material_id == 0:
            return

        change = self.get_number("Quantity change (+/-)", 0)
        reason = self.get_input("Reason for adjustment", required=False)

        self.db.adjust_inventory(int(material_id), change, reason or "")
        print("\n  ✅ Stock adjusted successfully!")
        self.pause()

    def view_expiring(self):
        """View expiring materials"""
        self.clear_screen()
        print("\n⏰ EXPIRING MATERIALS (Next 30 days)")
        print("=" * 60)

        items = self.db.get_expiring_materials(30)
        if not items:
            print("  ✅ No materials expiring soon!")
        else:
            for item in items:
                print(f"\n  ⚠️  {item['name']}")
                print(f"     Expires: {item['expiry_date']} ({item['days_remaining']:.0f} days)")
                print(f"     Quantity: {item['quantity']} {item['unit']}")

        self.pause()

    # ==================== PRODUCTION ====================

    def production_menu(self):
        """Production management menu"""
        while True:
            self.clear_screen()
            self.print_header()
            self.print_menu("PRODUCTION MANAGEMENT", [
                "View All Batches",
                "View Active Batches",
                "Create New Batch",
                "Update Batch Status",
                "Add Batch Ingredients",
                "Add Quality Record",
                "View Quality Records",
                "Manage Products"
            ])

            choice = input("\n  Select option: ").strip()

            if choice == "0":
                break
            elif choice == "1":
                self.view_batches()
            elif choice == "2":
                self.view_batches(status="brewing")
            elif choice == "3":
                self.create_batch()
            elif choice == "4":
                self.update_batch_status()
            elif choice == "5":
                self.add_batch_ingredients()
            elif choice == "6":
                self.add_quality_record()
            elif choice == "7":
                self.view_quality_records()
            elif choice == "8":
                self.manage_products()

    def view_batches(self, status: str = None):
        """View production batches"""
        self.clear_screen()
        title = f"PRODUCTION BATCHES" + (f" - {status.upper()}" if status else "")
        print(f"\n🏭 {title}")
        print("=" * 80)

        batches = self.db.get_batches(status=status)
        if not batches:
            print("  No batches found.")
        else:
            print(f"\n  {'Batch #':<20} {'Product':<20} {'Status':<12} {'Planned':<10} {'Actual':<10}")
            print("  " + "-" * 75)
            for b in batches:
                actual = f"{b['actual_quantity']}" if b['actual_quantity'] else "N/A"
                print(f"  {b['batch_number']:<20} {b['product_name']:<20} {b['status']:<12} {b['planned_quantity']:<10} {actual:<10}")

        self.pause()

    def create_batch(self):
        """Create new production batch"""
        self.clear_screen()
        print("\n➕ CREATE NEW BATCH")
        print("-" * 40)

        products = self.db.get_products()
        if not products:
            print("  No products available. Please create a product first.")
            self.pause()
            return

        print("\n  Available Products:")
        for p in products:
            print(f"  {p['id']}. {p['name']} ({p['style']})")

        product_id = self.get_number("Select product ID", 0, int)
        if product_id == 0:
            return

        planned_qty = self.get_number("Planned quantity (liters)", 0)
        start_date = self.get_input("Start date (YYYY-MM-DD)", default=date.today().isoformat())

        staff = self.db.get_staff(department="brewing")
        if staff:
            print("\n  Available Brewers:")
            for s in staff:
                print(f"  {s['id']}. {s['name']}")
            brewer_id = self.get_number("Select brewer ID", 0, int)
        else:
            brewer_id = None

        equipment = self.get_input("Equipment to use", required=False)
        notes = self.get_input("Notes", required=False)

        data = {
            'product_id': int(product_id),
            'planned_quantity': planned_qty,
            'start_date': start_date,
            'brewer_id': int(brewer_id) if brewer_id else None,
            'equipment_used': equipment,
            'notes': notes
        }

        batch_id = self.db.create_batch(data)
        print(f"\n  ✅ Batch created successfully! (ID: {batch_id})")
        self.pause()

    def update_batch_status(self):
        """Update batch status"""
        self.clear_screen()
        print("\n✏️  UPDATE BATCH STATUS")
        print("-" * 40)

        batches = self.db.get_batches()
        for b in batches:
            print(f"  {b['id']}. {b['batch_number']} - {b['product_name']} ({b['status']})")

        batch_id = self.get_number("Enter batch ID", 0, int)
        if batch_id == 0:
            return

        print("\n  Statuses: planned, brewing, fermenting, conditioning, packaging, completed, cancelled")
        status = self.get_input("New status")

        actual_qty = None
        if status == "completed":
            actual_qty = self.get_number("Actual quantity produced (liters)", 0)

        self.db.update_batch_status(int(batch_id), status, actual_qty)
        print("\n  ✅ Batch status updated!")
        self.pause()

    def add_batch_ingredients(self):
        """Add ingredients to a batch"""
        self.clear_screen()
        print("\n➕ ADD BATCH INGREDIENTS")
        print("-" * 40)

        batches = self.db.get_batches(status="planned")
        if not batches:
            print("  No planned batches found.")
            self.pause()
            return

        for b in batches:
            print(f"  {b['id']}. {b['batch_number']} - {b['product_name']}")

        batch_id = self.get_number("Select batch ID", 0, int)
        if batch_id == 0:
            return

        materials = self.db.get_raw_materials()
        print("\n  Available Materials:")
        for m in materials:
            print(f"  {m['id']}. {m['name']}: {m['quantity']} {m['unit']}")

        ingredients = []
        while True:
            print("\n  Add ingredient (enter 0 to finish)")
            mat_id = self.get_number("Material ID", 0, int)
            if mat_id == 0:
                break

            qty = self.get_number("Quantity to use", 0)
            cost = self.get_number("Cost at time (VND)", 0)

            ingredients.append({
                'material_id': int(mat_id),
                'quantity_used': qty,
                'cost_at_time': cost
            })

        if ingredients:
            self.db.add_batch_ingredients(int(batch_id), ingredients)
            print(f"\n  ✅ {len(ingredients)} ingredients added and inventory updated!")
        else:
            print("\n  No ingredients added.")

        self.pause()

    def add_quality_record(self):
        """Add quality control record"""
        self.clear_screen()
        print("\n➕ ADD QUALITY RECORD")
        print("-" * 40)

        batches = self.db.get_batches()
        for b in batches:
            print(f"  {b['id']}. {b['batch_number']} - {b['product_name']}")

        batch_id = self.get_number("Select batch ID", 0, int)
        if batch_id == 0:
            return

        print("\n  Check types: gravity, ph, temperature, taste, visual")
        check_type = self.get_input("Check type")
        value = self.get_number("Value", 0)
        unit = self.get_input("Unit", required=False)
        passed = self.get_input("Passed? (y/n)", default="y")
        inspector = self.get_input("Inspector name", required=False)
        notes = self.get_input("Notes", required=False)

        data = {
            'batch_id': int(batch_id),
            'check_type': check_type,
            'value': value,
            'unit': unit,
            'passed': 1 if passed.lower() == 'y' else 0,
            'inspector': inspector,
            'notes': notes
        }

        record_id = self.db.add_quality_record(data)
        print(f"\n  ✅ Quality record added! (ID: {record_id})")
        self.pause()

    def view_quality_records(self):
        """View quality records"""
        self.clear_screen()
        print("\n📋 QUALITY RECORDS")
        print("=" * 80)

        records = self.db.get_quality_records()
        if not records:
            print("  No quality records found.")
        else:
            for r in records[:20]:
                status = "✅ PASS" if r['passed'] else "❌ FAIL"
                print(f"\n  {r['batch_number']} - {r['product_name']}")
                print(f"     Check: {r['check_type']} | Value: {r['value']} {r['unit'] or ''} | {status}")
                print(f"     Inspector: {r['inspector'] or 'N/A'} | {r['check_date']}")

        self.pause()

    def manage_products(self):
        """Manage products menu"""
        while True:
            self.clear_screen()
            self.print_header()
            self.print_menu("PRODUCT MANAGEMENT", [
                "View All Products",
                "Add New Product",
                "Update Product"
            ])

            choice = input("\n  Select option: ").strip()

            if choice == "0":
                break
            elif choice == "1":
                self.view_products()
            elif choice == "2":
                self.add_product()
            elif choice == "3":
                self.update_product()

    def view_products(self):
        """View all products"""
        self.clear_screen()
        print("\n🍺 ALL PRODUCTS")
        print("=" * 70)

        products = self.db.get_products(active_only=False)
        if not products:
            print("  No products found.")
        else:
            for p in products:
                status = "🟢 Active" if p['is_active'] else "🔴 Inactive"
                print(f"\n  {p['id']}. {p['name']} ({p['style'] or 'N/A'}) - {status}")
                print(f"     ABV: {p['abv'] or 'N/A'}% | IBU: {p['ibu'] or 'N/A'}")
                print(f"     Price: {p['price_per_unit']:,.0f} VND/{p['unit']}")

        self.pause()

    def add_product(self):
        """Add new product"""
        self.clear_screen()
        print("\n➕ ADD NEW PRODUCT")
        print("-" * 40)

        name = self.get_input("Product name")
        style = self.get_input("Style (IPA, Lager, Stout, etc.)", required=False)
        abv = self.get_number("ABV (%)", 0)
        ibu = self.get_number("IBU", 0, int)
        description = self.get_input("Description", required=False)
        price = self.get_number("Price per unit (VND)", 0)

        data = {
            'name': name, 'style': style, 'abv': abv, 'ibu': ibu,
            'description': description, 'price_per_unit': price
        }

        product_id = self.db.add_product(data)
        print(f"\n  ✅ Product added successfully! (ID: {product_id})")
        self.pause()

    def update_product(self):
        """Update product"""
        self.clear_screen()
        print("\n✏️  UPDATE PRODUCT")
        print("-" * 40)

        products = self.db.get_products(active_only=False)
        for p in products:
            print(f"  {p['id']}. {p['name']}")

        product_id = self.get_number("Enter product ID", 0, int)
        if product_id == 0:
            return

        data = {}
        price = self.get_input("New price", required=False)
        if price:
            data['price_per_unit'] = float(price)

        if data:
            self.db.update_product(int(product_id), data)
            print("\n  ✅ Product updated!")
        else:
            print("\n  No changes made.")

        self.pause()

    # ==================== SALES ====================

    def sales_menu(self):
        """Sales management menu"""
        while True:
            self.clear_screen()
            self.print_header()
            self.print_menu("SALES MANAGEMENT", [
                "View All Orders",
                "View Pending Orders",
                "Create New Order",
                "Update Order Status",
                "Update Payment Status",
                "View Order Details",
                "Manage Customers"
            ])

            choice = input("\n  Select option: ").strip()

            if choice == "0":
                break
            elif choice == "1":
                self.view_orders()
            elif choice == "2":
                self.view_orders(status="pending")
            elif choice == "3":
                self.create_order()
            elif choice == "4":
                self.update_order_status()
            elif choice == "5":
                self.update_payment_status()
            elif choice == "6":
                self.view_order_details()
            elif choice == "7":
                self.manage_customers()

    def view_orders(self, status: str = None):
        """View sales orders"""
        self.clear_screen()
        title = "SALES ORDERS" + (f" - {status.upper()}" if status else "")
        print(f"\n📝 {title}")
        print("=" * 80)

        orders = self.db.get_sales_orders(status=status)
        if not orders:
            print("  No orders found.")
        else:
            print(f"\n  {'Order #':<18} {'Customer':<20} {'Date':<12} {'Total':<15} {'Status':<12} {'Payment':<10}")
            print("  " + "-" * 85)
            for o in orders:
                print(f"  {o['order_number']:<18} {o['customer_name']:<20} {o['order_date']:<12} {o['total_amount']:<15,.0f} {o['status']:<12} {o['payment_status']:<10}")

        self.pause()

    def create_order(self):
        """Create new sales order"""
        self.clear_screen()
        print("\n➕ CREATE NEW ORDER")
        print("-" * 40)

        customers = self.db.get_customers()
        if not customers:
            print("  No customers found. Please add a customer first.")
            self.pause()
            return

        print("\n  Customers:")
        for c in customers:
            print(f"  {c['id']}. {c['name']} ({c['type']}) - {c['city'] or 'N/A'}")

        customer_id = self.get_number("Select customer ID", 0, int)
        if customer_id == 0:
            return

        order_date = self.get_input("Order date (YYYY-MM-DD)", default=date.today().isoformat())
        delivery_date = self.get_input("Delivery date (YYYY-MM-DD)", required=False)
        notes = self.get_input("Notes", required=False)

        products = self.db.get_products()
        print("\n  Products:")
        for p in products:
            print(f"  {p['id']}. {p['name']} - {p['price_per_unit']:,.0f} VND/{p['unit']}")

        items = []
        while True:
            print("\n  Add item (enter 0 to finish)")
            prod_id = self.get_number("Product ID", 0, int)
            if prod_id == 0:
                break

            qty = self.get_number("Quantity", 0)
            price = self.get_number("Unit price (VND)", 0)
            discount = self.get_number("Discount (%)", 0)

            items.append({
                'product_id': int(prod_id),
                'quantity': qty,
                'unit_price': price,
                'discount': discount
            })

        if not items:
            print("\n  No items added. Order cancelled.")
            self.pause()
            return

        data = {
            'customer_id': int(customer_id),
            'order_date': order_date,
            'delivery_date': delivery_date,
            'notes': notes,
            'items': items
        }

        order_id = self.db.create_sales_order(data)
        print(f"\n  ✅ Order created successfully! (ID: {order_id})")
        self.pause()

    def update_order_status(self):
        """Update order status"""
        self.clear_screen()
        print("\n✏️  UPDATE ORDER STATUS")
        print("-" * 40)

        orders = self.db.get_sales_orders()
        for o in orders:
            print(f"  {o['id']}. {o['order_number']} - {o['customer_name']} ({o['status']})")

        order_id = self.get_number("Enter order ID", 0, int)
        if order_id == 0:
            return

        print("\n  Statuses: pending, confirmed, preparing, delivered, cancelled")
        status = self.get_input("New status")

        self.db.update_order_status(int(order_id), status)
        print("\n  ✅ Order status updated!")
        self.pause()

    def update_payment_status(self):
        """Update payment status"""
        self.clear_screen()
        print("\n💰 UPDATE PAYMENT STATUS")
        print("-" * 40)

        orders = self.db.get_sales_orders()
        for o in orders:
            print(f"  {o['id']}. {o['order_number']} - {o['total_amount']:,.0f} VND ({o['payment_status']})")

        order_id = self.get_number("Enter order ID", 0, int)
        if order_id == 0:
            return

        print("\n  Statuses: unpaid, partial, paid")
        status = self.get_input("New payment status")

        self.db.update_payment_status(int(order_id), status)
        print("\n  ✅ Payment status updated!")
        self.pause()

    def view_order_details(self):
        """View order details"""
        self.clear_screen()
        print("\n📋 ORDER DETAILS")
        print("-" * 40)

        orders = self.db.get_sales_orders()
        for o in orders:
            print(f"  {o['id']}. {o['order_number']}")

        order_id = self.get_number("Enter order ID", 0, int)
        if order_id == 0:
            return

        order = self.db.get_order_details(int(order_id))

        self.clear_screen()
        print(f"\n📋 ORDER: {order['order_number']}")
        print("=" * 60)
        print(f"  Customer:    {order['customer_name']}")
        print(f"  Address:     {order['address'] or 'N/A'}")
        print(f"  Phone:       {order['phone'] or 'N/A'}")
        print(f"  Order Date:  {order['order_date']}")
        print(f"  Delivery:    {order['delivery_date'] or 'N/A'}")
        print(f"  Status:      {order['status']}")
        print(f"  Payment:     {order['payment_status']}")

        print(f"\n  ITEMS:")
        print(f"  {'Product':<25} {'Qty':<10} {'Price':<12} {'Total':<15}")
        print("  " + "-" * 60)
        for item in order['items']:
            print(f"  {item['product_name']:<25} {item['quantity']:<10} {item['unit_price']:<12,.0f} {item['total']:<15,.0f}")

        print(f"\n  Subtotal:    {order['subtotal']:,.0f} VND")
        print(f"  Tax (10%):   {order['tax_amount']:,.0f} VND")
        print(f"  TOTAL:       {order['total_amount']:,.0f} VND")

        self.pause()

    def manage_customers(self):
        """Manage customers menu"""
        while True:
            self.clear_screen()
            self.print_header()
            self.print_menu("CUSTOMER MANAGEMENT", [
                "View All Customers",
                "Add New Customer",
                "Update Customer",
                "View Top Customers"
            ])

            choice = input("\n  Select option: ").strip()

            if choice == "0":
                break
            elif choice == "1":
                self.view_customers()
            elif choice == "2":
                self.add_customer()
            elif choice == "3":
                self.update_customer()
            elif choice == "4":
                self.view_top_customers()

    def view_customers(self):
        """View all customers"""
        self.clear_screen()
        print("\n👥 ALL CUSTOMERS")
        print("=" * 80)

        customers = self.db.get_customers(active_only=False)
        if not customers:
            print("  No customers found.")
        else:
            print(f"\n  {'ID':<4} {'Name':<25} {'Type':<12} {'City':<15} {'Phone':<15}")
            print("  " + "-" * 70)
            for c in customers:
                print(f"  {c['id']:<4} {c['name']:<25} {c['type']:<12} {c['city'] or 'N/A':<15} {c['phone'] or 'N/A':<15}")

        self.pause()

    def add_customer(self):
        """Add new customer"""
        self.clear_screen()
        print("\n➕ ADD NEW CUSTOMER")
        print("-" * 40)

        name = self.get_input("Customer name")
        print("\n  Types: retail, wholesale, distributor, bar, restaurant")
        ctype = self.get_input("Customer type", default="retail")
        contact = self.get_input("Contact person", required=False)
        phone = self.get_input("Phone", required=False)
        email = self.get_input("Email", required=False)
        address = self.get_input("Address", required=False)
        city = self.get_input("City", required=False)
        province = self.get_input("Province", required=False)
        credit = self.get_number("Credit limit (VND)", 0)
        terms = self.get_input("Payment terms", default="COD")

        data = {
            'name': name, 'type': ctype, 'contact_person': contact,
            'phone': phone, 'email': email, 'address': address,
            'city': city, 'province': province, 'credit_limit': credit,
            'payment_terms': terms
        }

        customer_id = self.db.add_customer(data)
        print(f"\n  ✅ Customer added successfully! (ID: {customer_id})")
        self.pause()

    def update_customer(self):
        """Update customer"""
        self.clear_screen()
        print("\n✏️  UPDATE CUSTOMER")
        print("-" * 40)

        customers = self.db.get_customers(active_only=False)
        for c in customers:
            print(f"  {c['id']}. {c['name']}")

        customer_id = self.get_number("Enter customer ID", 0, int)
        if customer_id == 0:
            return

        data = {}
        phone = self.get_input("New phone", required=False)
        if phone:
            data['phone'] = phone

        if data:
            self.db.update_customer(int(customer_id), data)
            print("\n  ✅ Customer updated!")
        else:
            print("\n  No changes made.")

        self.pause()

    def view_top_customers(self):
        """View top customers"""
        self.clear_screen()
        print("\n🏆 TOP CUSTOMERS BY REVENUE")
        print("=" * 60)

        customers = self.db.get_top_customers(10)
        if not customers:
            print("  No sales data available.")
        else:
            for i, c in enumerate(customers, 1):
                print(f"\n  {i}. {c['name']} ({c['type']})")
                print(f"     City: {c['city'] or 'N/A'}")
                print(f"     Orders: {c['order_count']} | Total: {c['total_spent']:,.0f} VND")

        self.pause()

    # ==================== FINANCE ====================

    def finance_menu(self):
        """Finance management menu"""
        while True:
            self.clear_screen()
            self.print_header()
            self.print_menu("FINANCIAL MANAGEMENT", [
                "View Financial Summary",
                "Add Transaction",
                "View Transactions",
                "View Income",
                "View Expenses",
                "Production Report",
                "Sales Report"
            ])

            choice = input("\n  Select option: ").strip()

            if choice == "0":
                break
            elif choice == "1":
                self.view_financial_summary()
            elif choice == "2":
                self.add_transaction()
            elif choice == "3":
                self.view_transactions()
            elif choice == "4":
                self.view_transactions(type_filter="income")
            elif choice == "5":
                self.view_transactions(type_filter="expense")
            elif choice == "6":
                self.view_production_report()
            elif choice == "7":
                self.view_sales_report()

    def view_financial_summary(self):
        """View financial summary"""
        self.clear_screen()
        print("\n💰 FINANCIAL SUMMARY")
        print("=" * 60)

        start = self.get_input("Start date (YYYY-MM-DD)", required=False)
        end = self.get_input("End date (YYYY-MM-DD)", required=False)

        summary = self.db.get_financial_summary(start, end)

        print(f"\n  Total Income:    {summary['total_income']:>15,.0f} VND")
        print(f"  Total Expenses:  {summary['total_expense']:>15,.0f} VND")
        print(f"  ─────────────────────────────────────")
        print(f"  Net Profit:      {summary['net_profit']:>15,.0f} VND")

        if summary['categories']:
            print(f"\n  BREAKDOWN BY CATEGORY:")
            for cat in summary['categories']:
                sign = "+" if cat['type'] == 'income' else "-"
                print(f"    {sign} {cat['category']:<20} {cat['total']:>12,.0f} VND")

        self.pause()

    def add_transaction(self):
        """Add financial transaction"""
        self.clear_screen()
        print("\n➕ ADD TRANSACTION")
        print("-" * 40)

        print("\n  Type: income, expense")
        ttype = self.get_input("Transaction type")

        print("\n  Categories:")
        if ttype == "income":
            print("    sales, other")
        else:
            print("    raw_materials, equipment, salaries, utilities, maintenance, marketing, other")

        category = self.get_input("Category")
        amount = self.get_number("Amount (VND)", 0)
        tdate = self.get_input("Date (YYYY-MM-DD)", default=date.today().isoformat())
        description = self.get_input("Description", required=False)

        print("\n  Payment methods: cash, bank_transfer, card")
        payment = self.get_input("Payment method", required=False)

        data = {
            'transaction_date': tdate,
            'type': ttype,
            'category': category,
            'amount': amount,
            'description': description,
            'payment_method': payment
        }

        trans_id = self.db.add_transaction(data)
        print(f"\n  ✅ Transaction added! (ID: {trans_id})")
        self.pause()

    def view_transactions(self, type_filter: str = None):
        """View transactions"""
        self.clear_screen()
        title = "TRANSACTIONS"
        if type_filter:
            title = f"{type_filter.upper()} TRANSACTIONS"
        print(f"\n💰 {title}")
        print("=" * 80)

        start = self.get_input("Start date (YYYY-MM-DD)", required=False)
        end = self.get_input("End date (YYYY-MM-DD)", required=False)

        transactions = self.db.get_transactions(start, end, type_filter)

        if not transactions:
            print("  No transactions found.")
        else:
            total = 0
            print(f"\n  {'Date':<12} {'Type':<8} {'Category':<18} {'Amount':<15} {'Description':<25}")
            print("  " + "-" * 80)
            for t in transactions:
                sign = "+" if t['type'] == 'income' else "-"
                print(f"  {t['transaction_date']:<12} {t['type']:<8} {t['category']:<18} {sign}{t['amount']:<14,.0f} {(t['description'] or '')[:25]}")
                total += t['amount'] if t['type'] == 'income' else -t['amount']

            print(f"\n  Net Total: {total:,.0f} VND")

        self.pause()

    def view_production_report(self):
        """View production report"""
        self.clear_screen()
        print("\n📊 PRODUCTION REPORT")
        print("=" * 70)

        start = self.get_input("Start date (YYYY-MM-DD)", required=False)
        end = self.get_input("End date (YYYY-MM-DD)", required=False)

        report = self.db.get_production_report(start, end)

        if not report:
            print("  No completed batches found.")
        else:
            print(f"\n  {'Product':<25} {'Style':<15} {'Batches':<10} {'Planned':<12} {'Actual':<12}")
            print("  " + "-" * 70)
            for r in report:
                print(f"  {r['name']:<25} {r['style'] or 'N/A':<15} {r['batch_count']:<10} {r['planned'] or 0:<12,.0f} {r['actual'] or 0:<12,.0f}")

        self.pause()

    def view_sales_report(self):
        """View sales report"""
        self.clear_screen()
        print("\n📊 SALES REPORT")
        print("=" * 70)

        start = self.get_input("Start date (YYYY-MM-DD)", required=False)
        end = self.get_input("End date (YYYY-MM-DD)", required=False)

        report = self.db.get_sales_report(start, end)

        if not report:
            print("  No sales data found.")
        else:
            print(f"\n  {'Product':<25} {'Style':<15} {'Quantity':<12} {'Revenue':<15} {'Orders':<10}")
            print("  " + "-" * 75)
            for r in report:
                print(f"  {r['name']:<25} {r['style'] or 'N/A':<15} {r['total_quantity']:<12,.0f} {r['total_revenue']:<15,.0f} {r['order_count']:<10}")

        self.pause()

    # ==================== STAFF ====================

    def staff_menu(self):
        """Staff management menu"""
        while True:
            self.clear_screen()
            self.print_header()
            self.print_menu("STAFF MANAGEMENT", [
                "View All Staff",
                "Add Staff Member",
                "Update Staff",
                "View Schedule",
                "Add Schedule"
            ])

            choice = input("\n  Select option: ").strip()

            if choice == "0":
                break
            elif choice == "1":
                self.view_staff()
            elif choice == "2":
                self.add_staff()
            elif choice == "3":
                self.update_staff()
            elif choice == "4":
                self.view_schedule()
            elif choice == "5":
                self.add_schedule()

    def view_staff(self):
        """View all staff"""
        self.clear_screen()
        print("\n👥 ALL STAFF")
        print("=" * 80)

        staff = self.db.get_staff(active_only=False)
        if not staff:
            print("  No staff found.")
        else:
            print(f"\n  {'ID':<4} {'Name':<25} {'Position':<20} {'Department':<12} {'Phone':<15}")
            print("  " + "-" * 75)
            for s in staff:
                print(f"  {s['id']:<4} {s['name']:<25} {s['position']:<20} {s['department'] or 'N/A':<12} {s['phone'] or 'N/A':<15}")

        self.pause()

    def add_staff(self):
        """Add staff member"""
        self.clear_screen()
        print("\n➕ ADD STAFF MEMBER")
        print("-" * 40)

        name = self.get_input("Full name")
        position = self.get_input("Position")
        print("\n  Departments: brewing, packaging, sales, admin, delivery")
        department = self.get_input("Department", required=False)
        phone = self.get_input("Phone", required=False)
        email = self.get_input("Email", required=False)
        hire_date = self.get_input("Hire date (YYYY-MM-DD)", required=False)
        salary = self.get_number("Salary (VND/month)", 0)
        emergency = self.get_input("Emergency contact", required=False)

        data = {
            'name': name, 'position': position, 'department': department,
            'phone': phone, 'email': email, 'hire_date': hire_date,
            'salary': salary, 'emergency_contact': emergency
        }

        staff_id = self.db.add_staff(data)
        print(f"\n  ✅ Staff member added! (ID: {staff_id})")
        self.pause()

    def update_staff(self):
        """Update staff"""
        self.clear_screen()
        print("\n✏️  UPDATE STAFF")
        print("-" * 40)

        staff = self.db.get_staff(active_only=False)
        for s in staff:
            print(f"  {s['id']}. {s['name']} - {s['position']}")

        staff_id = self.get_number("Enter staff ID", 0, int)
        if staff_id == 0:
            return

        data = {}
        salary = self.get_input("New salary", required=False)
        if salary:
            data['salary'] = float(salary)

        if data:
            self.db.update_staff(int(staff_id), data)
            print("\n  ✅ Staff updated!")
        else:
            print("\n  No changes made.")

        self.pause()

    def view_schedule(self):
        """View staff schedule"""
        self.clear_screen()
        print("\n📅 STAFF SCHEDULE")
        print("-" * 40)

        schedule_date = self.get_input("Date (YYYY-MM-DD)", default=date.today().isoformat())

        schedule = self.db.get_schedule(date=schedule_date)

        if not schedule:
            print(f"  No schedule found for {schedule_date}")
        else:
            print(f"\n  Schedule for {schedule_date}:")
            print(f"  {'Name':<25} {'Position':<20} {'Shift':<12} {'Time':<15} {'Status':<10}")
            print("  " + "-" * 80)
            for s in schedule:
                time_str = f"{s['start_time'] or ''}-{s['end_time'] or ''}"
                print(f"  {s['name']:<25} {s['position']:<20} {s['shift']:<12} {time_str:<15} {s['status']:<10}")

        self.pause()

    def add_schedule(self):
        """Add schedule entry"""
        self.clear_screen()
        print("\n➕ ADD SCHEDULE")
        print("-" * 40)

        staff = self.db.get_staff()
        for s in staff:
            print(f"  {s['id']}. {s['name']} ({s['department']})")

        staff_id = self.get_number("Select staff ID", 0, int)
        if staff_id == 0:
            return

        schedule_date = self.get_input("Date (YYYY-MM-DD)")
        print("\n  Shifts: morning, afternoon, night")
        shift = self.get_input("Shift")
        start_time = self.get_input("Start time (HH:MM)", required=False)
        end_time = self.get_input("End time (HH:MM)", required=False)
        notes = self.get_input("Notes", required=False)

        data = {
            'staff_id': int(staff_id),
            'schedule_date': schedule_date,
            'shift': shift,
            'start_time': start_time,
            'end_time': end_time,
            'notes': notes
        }

        schedule_id = self.db.add_schedule(data)
        print(f"\n  ✅ Schedule added! (ID: {schedule_id})")
        self.pause()

    # ==================== MAIN LOOP ====================

    def run(self):
        """Main application loop"""
        while self.running:
            self.clear_screen()
            self.print_header()

            # Show quick alerts
            dashboard = self.db.get_dashboard_data()
            alerts = []
            if dashboard['low_stock_materials'] > 0:
                alerts.append(f"⚠️  {dashboard['low_stock_materials']} low stock items")
            if dashboard['pending_orders'] > 0:
                alerts.append(f"📝 {dashboard['pending_orders']} pending orders")

            if alerts:
                print("\n  ALERTS: " + " | ".join(alerts))

            self.print_menu("MAIN MENU", [
                "📊 Dashboard",
                "📦 Inventory Management",
                "🏭 Production Management",
                "📝 Sales Management",
                "💰 Financial Management",
                "👥 Staff Management"
            ])

            choice = input("\n  Select option: ").strip()

            if choice == "0":
                self.running = False
                print("\n  👋 Goodbye! Chúc bạn kinh doanh phát đạt!")
            elif choice == "1":
                self.show_dashboard()
            elif choice == "2":
                self.inventory_menu()
            elif choice == "3":
                self.production_menu()
            elif choice == "4":
                self.sales_menu()
            elif choice == "5":
                self.finance_menu()
            elif choice == "6":
                self.staff_menu()

        self.db.close()


def main():
    """Entry point"""
    cli = BreweryCLI()
    cli.run()


if __name__ == "__main__":
    main()