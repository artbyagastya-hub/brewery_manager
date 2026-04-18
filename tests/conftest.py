"""
Pytest configuration and fixtures for Brewery Manager tests
"""
import os
import sys
import tempfile
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import Database
from utils.i18n import get_i18n
from utils.tax import get_tax_calculator


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    fd, path = tempfile.mkstemp(suffix='.db')
    db = Database(db_path=path)
    yield db
    os.close(fd)
    os.unlink(path)


@pytest.fixture
def i18n():
    """Get i18n instance"""
    return get_i18n()


@pytest.fixture
def tax_calc():
    """Get tax calculator instance"""
    return get_tax_calculator()


@pytest.fixture
def sample_product(temp_db):
    """Create a sample product for testing"""
    product_id = temp_db.add_product({
        'name': "Test IPA",
        'type': "beer",
        'style': "American IPA",
        'abv': 6.5,
        'ibu': 65,
        'srm': 8,
        'description': "A test IPA"
    })
    return product_id


@pytest.fixture
def sample_customer(temp_db):
    """Create a sample customer for testing"""
    customer_id = temp_db.add_customer({
        'name': "Test Customer",
        'type': "restaurant",
        'contact': "John Doe",
        'phone': "0901234567",
        'email': "test@example.com",
        'address': "123 Test Street",
        'city': "Ho Chi Minh City"
    })
    return customer_id


@pytest.fixture
def sample_material(temp_db):
    """Create a sample material for testing"""
    material_id = temp_db.add_raw_material({
        'name': "Test Malt",
        'category': "fermentable",
        'unit': "kg",
        'quantity': 100,
        'min_quantity': 10,
        'cost_per_unit': 50000
    })
    return material_id


@pytest.fixture
def sample_tank(temp_db):
    """Create a sample tank for testing"""
    # Get existing equipment (initialized by default)
    equipment = temp_db.get_equipment(equipment_type='fermenter')
    if equipment:
        return equipment[0]['id']
    # If no fermenter exists, update an existing equipment
    all_equipment = temp_db.get_equipment()
    if all_equipment:
        return all_equipment[0]['id']
    return 1  # Default fallback


@pytest.fixture
def sample_staff(temp_db):
    """Create a sample staff member for testing"""
    staff_id = temp_db.add_staff({
        'name': "Test Brewer",
        'position': "brewer",
        'phone': "0909876543",
        'email': "brewer@brewery.com",
        'department': "production"
    })
    return staff_id


@pytest.fixture
def temp_memory():
    """Create a temporary AI memory instance for testing"""
    import tempfile
    from utils.ai_memory import AIMemory
    
    fd, path = tempfile.mkstemp(suffix='.json')
    os.close(fd)
    
    memory = AIMemory()
    memory.memory_file = path
    memory.memory = memory._initialize_memory()
    
    yield memory
    
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def temp_planner(temp_db):
    """Create a temporary AI planner instance for testing"""
    from utils.ai_planner import AIPlanner
    planner = AIPlanner()
    planner.db = temp_db
    return planner


@pytest.fixture
def client(temp_db):
    """Create a test client for Flask app"""
    from web.app import app
    
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture
def auth_headers():
    """Create authentication headers for API requests"""
    return {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
