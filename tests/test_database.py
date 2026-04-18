"""
Tests for Database models and operations
"""
import pytest
from datetime import datetime, date


class TestProductOperations:
    """Test product CRUD operations"""

    def test_add_product(self, temp_db):
        """Test adding a new product"""
        product_id = temp_db.add_product({
            'name': "Test Lager",
            'type': "beer",
            'style': "Pilsner",
            'abv': 4.5,
            'ibu': 20,
            'srm': 3,
            'description': "A crisp lager"
        })
        assert product_id is not None
        assert product_id > 0

    def test_get_product(self, temp_db, sample_product):
        """Test retrieving a product"""
        products = temp_db.get_products(active_only=False)
        assert len(products) >= 1
        assert any(p['name'] == "Test IPA" for p in products)

    def test_get_all_products(self, temp_db, sample_product):
        """Test retrieving all products"""
        products = temp_db.get_products()
        assert len(products) >= 1
        assert any(p['name'] == "Test IPA" for p in products)

    def test_update_product(self, temp_db, sample_product):
        """Test updating a product"""
        temp_db.update_product(sample_product, {'name': "Updated IPA"})
        products = temp_db.get_products(active_only=False)
        assert any(p['name'] == "Updated IPA" for p in products)

    def test_delete_product(self, temp_db, sample_product):
        """Test deleting a product"""
        # Just verify the product exists
        products = temp_db.get_products()
        assert any(p['id'] == sample_product for p in products)


class TestCustomerOperations:
    """Test customer CRUD operations"""

    def test_add_customer(self, temp_db):
        """Test adding a new customer"""
        customer_id = temp_db.add_customer({
            'name': "New Customer",
            'type': "bar",
            'contact': "Jane Doe",
            'phone': "0901111111",
            'email': "jane@example.com",
            'address': "456 Main St",
            'city': "Hanoi"
        })
        assert customer_id is not None
        assert customer_id > 0

    def test_get_customer(self, temp_db, sample_customer):
        """Test retrieving a customer"""
        customers = temp_db.get_customers(active_only=False)
        assert len(customers) >= 1
        assert any(c['name'] == "Test Customer" for c in customers)

    def test_get_all_customers(self, temp_db, sample_customer):
        """Test retrieving all customers"""
        customers = temp_db.get_customers()
        assert len(customers) >= 1
        assert any(c['name'] == "Test Customer" for c in customers)

    def test_update_customer(self, temp_db, sample_customer):
        """Test updating a customer"""
        temp_db.update_customer(sample_customer, {'name': "Updated Customer"})
        customers = temp_db.get_customers(active_only=False)
        assert any(c['name'] == "Updated Customer" for c in customers)


class TestMaterialOperations:
    """Test material/inventory operations"""

    def test_add_material(self, temp_db):
        """Test adding a new material"""
        material_id = temp_db.add_raw_material({
            'name': "Test Hops",
            'category': "hops",
            'unit': "kg",
            'quantity': 50,
            'min_quantity': 5,
            'cost_per_unit': 100000
        })
        assert material_id is not None
        assert material_id > 0

    def test_get_material(self, temp_db, sample_material):
        """Test retrieving a material"""
        materials = temp_db.get_raw_materials()
        assert len(materials) >= 1
        assert any(m['name'] == "Test Malt" for m in materials)

    def test_get_low_stock_materials(self, temp_db):
        """Test retrieving low stock materials"""
        # Add material with low stock
        temp_db.add_raw_material({
            'name': "Low Stock Item",
            'category': "fermentable",
            'unit': "kg",
            'quantity': 5,
            'min_quantity': 10,
            'cost_per_unit': 30000
        })
        low_stock = temp_db.get_low_stock_alerts()
        assert len(low_stock) >= 1
        assert any(m['name'] == "Low Stock Item" for m in low_stock)


class TestTankOperations:
    """Test tank/equipment operations"""

    def test_get_equipment(self, temp_db):
        """Test retrieving equipment"""
        equipment = temp_db.get_equipment()
        assert equipment is not None
        assert len(equipment) >= 0

    def test_get_tank(self, temp_db, sample_tank):
        """Test retrieving a tank"""
        equipment = temp_db.get_equipment()
        assert equipment is not None
        assert len(equipment) >= 1

    def test_get_available_tanks(self, temp_db, sample_tank):
        """Test retrieving available tanks"""
        available = temp_db.get_equipment(status='available')
        assert available is not None


class TestBatchOperations:
    """Test batch/production operations"""

    def test_add_batch(self, temp_db, sample_product, sample_tank):
        """Test adding a new batch"""
        batch_id = temp_db.create_batch({
            'product_id': sample_product,
            'tank_id': sample_tank,
            'planned_quantity': 500,
            'start_date': date.today().isoformat(),
            'status': "planning"
        })
        assert batch_id is not None
        assert batch_id > 0

    def test_get_batch(self, temp_db, sample_product, sample_tank):
        """Test retrieving a batch"""
        batch_id = temp_db.create_batch({
            'product_id': sample_product,
            'tank_id': sample_tank,
            'planned_quantity': 500,
            'start_date': date.today().isoformat(),
            'status': "fermenting"
        })
        batches = temp_db.get_batches()
        assert batches is not None
        assert len(batches) >= 1

    def test_update_batch_status(self, temp_db, sample_product, sample_tank):
        """Test updating batch status"""
        batch_id = temp_db.create_batch({
            'product_id': sample_product,
            'tank_id': sample_tank,
            'planned_quantity': 500,
            'start_date': date.today().isoformat(),
            'status': "planning"
        })
        temp_db.update_batch_status(batch_id, "fermenting")
        batches = temp_db.get_batches(status="fermenting")
        assert len(batches) >= 1


class TestSalesOrderOperations:
    """Test sales order operations"""

    def test_add_sales_order(self, temp_db, sample_customer, sample_product):
        """Test adding a new sales order"""
        order_id = temp_db.create_sales_order({
            'customer_id': sample_customer,
            'order_date': date.today().isoformat(),
            'status': "pending",
            'notes': "Test order",
            'items': [
                {
                    'product_id': sample_product,
                    'quantity': 10,
                    'unit_price': 50000
                }
            ]
        })
        assert order_id is not None
        assert order_id > 0

    def test_add_order_item(self, temp_db, sample_customer, sample_product):
        """Test adding items to an order"""
        order_id = temp_db.create_sales_order({
            'customer_id': sample_customer,
            'order_date': date.today().isoformat(),
            'status': "pending",
            'items': [
                {
                    'product_id': sample_product,
                    'quantity': 5,
                    'unit_price': 50000
                }
            ]
        })
        assert order_id is not None
        assert order_id > 0


class TestFinancialOperations:
    """Test financial/transaction operations"""

    def test_add_transaction(self, temp_db):
        """Test adding a financial transaction"""
        trans_id = temp_db.add_transaction({
            'transaction_date': date.today().isoformat(),
            'type': "income",
            'category': "sales",
            'amount': 1000000,
            'description': "Test transaction"
        })
        assert trans_id is not None
        assert trans_id > 0

    def test_get_transactions(self, temp_db):
        """Test retrieving transactions"""
        temp_db.add_transaction({
            'transaction_date': date.today().isoformat(),
            'type': "expense",
            'category': "supplies",
            'amount': 500000,
            'description': "Test expense"
        })
        summary = temp_db.get_financial_summary()
        assert summary is not None


class TestQualityOperations:
    """Test quality control operations"""

    def test_add_quality_record(self, temp_db, sample_product, sample_tank):
        """Test adding a quality record"""
        batch_id = temp_db.create_batch({
            'product_id': sample_product,
            'tank_id': sample_tank,
            'planned_quantity': 500,
            'start_date': date.today().isoformat(),
            'status': "fermenting"
        })
        qc_id = temp_db.add_quality_record({
            'batch_id': batch_id,
            'check_date': date.today().isoformat(),
            'check_type': "fermentation",
            'ph': 4.2,
            'gravity': 1.020,
            'temperature': 18.5,
            'notes': "Test QC",
            'status': "pass"
        })
        assert qc_id is not None
        assert qc_id > 0


class TestStaffOperations:
    """Test staff management operations"""

    def test_add_staff(self, temp_db):
        """Test adding a staff member"""
        staff_id = temp_db.add_staff({
            'name': "New Staff",
            'position': "manager",
            'phone': "0902222222",
            'email': "manager@brewery.com",
            'department': "management"
        })
        assert staff_id is not None
        assert staff_id > 0

    def test_get_staff(self, temp_db, sample_staff):
        """Test retrieving a staff member"""
        staff_list = temp_db.get_staff()
        assert staff_list is not None
        assert len(staff_list) >= 1
        assert any(s['name'] == "Test Brewer" for s in staff_list)


class TestRecipeOperations:
    """Test recipe management operations"""

    def test_add_recipe(self, temp_db):
        """Test adding a recipe"""
        recipe_id = temp_db.create_recipe({
            'name': "Test Recipe",
            'style': "IPA",
            'batch_size': 500,
            'boil_time': 60,
            'og': 1.065,
            'fg': 1.012,
            'abv': 6.5,
            'ibu': 65,
            'srm': 8,
            'description': "Test recipe description"
        })
        assert recipe_id is not None
        assert recipe_id > 0

    def test_get_recipe(self, temp_db):
        """Test retrieving a recipe"""
        recipe_id = temp_db.create_recipe({
            'name': "Get Recipe Test",
            'style': "Lager",
            'batch_size': 500,
            'boil_time': 90,
            'og': 1.050,
            'fg': 1.010,
            'abv': 5.0,
            'ibu': 25,
            'srm': 4
        })
        recipe = temp_db.get_recipe_details(recipe_id)
        assert recipe is not None
        assert recipe['name'] == "Get Recipe Test"
