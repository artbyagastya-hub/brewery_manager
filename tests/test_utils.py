"""
Tests for utility functions
"""
import pytest
from decimal import Decimal
from utils.i18n import get_i18n, format_currency
from utils.tax import get_tax_calculator
from utils.recipe_calculator import RecipeCalculator


class TestI18n:
    """Test internationalization utilities"""

    def test_translate_english(self, i18n):
        """Test English translation"""
        result = i18n.get('dashboard.title', language='en')
        assert result == "Dashboard"

    def test_translate_vietnamese(self, i18n):
        """Test Vietnamese translation"""
        result = i18n.get('dashboard.title', language='vi')
        assert result == "Bảng Điều Khiển"

    def test_translate_with_kwargs(self, i18n):
        """Test translation with format parameters"""
        result = i18n.get('dashboard.low_stock_alerts', language='en')
        assert result is not None

    def test_get_available_languages(self, i18n):
        """Test getting available languages"""
        languages = i18n.get_available_languages()
        assert len(languages) >= 2
        assert 'en' in [lang['code'] for lang in languages]


class TestTaxCalculator:
    """Test Vietnamese tax calculations"""

    def test_calculate_vat(self, tax_calc):
        """Test VAT calculation"""
        vat = tax_calc.calculate_vat(Decimal('1000000'), Decimal('0'))
        assert vat == Decimal('100000')  # 10% VAT

    def test_calculate_total_with_vat(self, tax_calc):
        """Test total calculation with VAT"""
        result = tax_calc.calculate_total_tax(Decimal('1000000'))
        assert result.total > Decimal('1000000')  # Total should be more than base

    def test_calculate_excise_tax(self, tax_calc):
        """Test excise tax calculation for beer"""
        excise = tax_calc.calculate_sct(Decimal('1000000'))
        assert excise == Decimal('650000')  # 65% excise for beer

    def test_format_currency_vnd(self):
        """Test VND currency formatting"""
        formatted = format_currency(1000000, language='vi')
        assert 'VNĐ' in formatted

    def test_get_tax_summary(self, tax_calc):
        """Test tax summary generation"""
        summary = tax_calc.calculate_total_tax(Decimal('1000000'))
        assert summary.subtotal == Decimal('1000000')
        assert summary.sct_amount > Decimal('0')
        assert summary.vat_amount > Decimal('0')
        assert summary.total > Decimal('1000000')


class TestRecipeCalculator:
    """Test recipe calculation utilities"""

    def test_calculate_og(self):
        """Test original gravity calculation"""
        og = RecipeCalculator.calculate_og(
            [{'amount': 10, 'potential': 37}],
            batch_size=20
        )
        assert og > 1.000

    def test_calculate_fg(self):
        """Test final gravity calculation"""
        fg = RecipeCalculator.calculate_fg(1.065, 75)
        assert fg < 1.065
        assert fg > 1.000

    def test_calculate_abv(self):
        """Test ABV calculation"""
        abv = RecipeCalculator.calculate_abv(1.065, 1.012)
        assert abv > 0
        assert abv < 20

    def test_calculate_ibu_tinseth(self):
        """Test IBU calculation using Tinseth formula"""
        ibu = RecipeCalculator.calculate_ibu_tinseth(
            [{'amount': 50, 'alpha_acid': 12, 'boil_time': 60, 'use_type': 'boil'}],
            batch_size=20,
            og=1.065
        )
        assert ibu > 0

    def test_calculate_srm_morey(self):
        """Test SRM color calculation using Morey equation"""
        srm = RecipeCalculator.calculate_srm_morey(
            [{'amount': 5, 'color': 10}],
            batch_size=20
        )
        assert srm > 0

    def test_calculate_abw(self):
        """Test ABW calculation"""
        abw = RecipeCalculator.calculate_abw(1.065, 1.012)
        assert abw > 0

    def test_calculate_attenuation(self):
        """Test attenuation calculation"""
        atten = RecipeCalculator.calculate_attenuation(1.065, 1.012)
        assert atten > 0
        assert atten < 100

    def test_calculate_calories(self):
        """Test calorie calculation"""
        cal = RecipeCalculator.calculate_calories(1.065, 1.012)
        assert cal > 0

    def test_srm_to_hex(self):
        """Test SRM to hex color conversion"""
        hex_color = RecipeCalculator.srm_to_hex(10)
        assert hex_color.startswith('#')
        assert len(hex_color) == 7