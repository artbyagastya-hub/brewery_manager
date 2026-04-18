"""
Brewery Manager - Vietnamese Tax System
Handles SCT (Special Consumption Tax), VAT, and Environmental Tax
According to Vietnamese regulations for beer production
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from decimal import Decimal, ROUND_HALF_UP


# Vietnamese Tax Rates for Beer Industry
TAX_RATES = {
    'sct': {  # Special Consumption Tax (Thuế Tiêu Thụ Đặc Biệt)
        'beer': 0.65,  # 65% for beer (Vietnamese regulation)
    },
    'vat': {  # Value Added Tax (Thuế Giá Trị Gia Tăng)
        'standard': 0.10,  # 10% standard rate
        'reduced': 0.05,   # 5% reduced rate (for some goods)
    },
    'environmental': {  # Environmental Protection Tax (Thuế Bảo Vệ Môi Trường)
        'beer_per_liter': 1000,  # 1,000 VND per liter
    }
}


@dataclass
class TaxCalculation:
    """Tax calculation result"""
    subtotal: Decimal
    sct_rate: Decimal
    sct_amount: Decimal
    vat_rate: Decimal
    vat_amount: Decimal
    environmental_tax: Decimal
    total_tax: Decimal
    total: Decimal
    
    def to_dict(self) -> Dict:
        return {
            'subtotal': float(self.subtotal),
            'sct_rate': float(self.sct_rate),
            'sct_amount': float(self.sct_amount),
            'vat_rate': float(self.vat_rate),
            'vat_amount': float(self.vat_amount),
            'environmental_tax': float(self.environmental_tax),
            'total_tax': float(self.total_tax),
            'total': float(self.total)
        }


class VietnameseTaxCalculator:
    """Calculator for Vietnamese taxes applicable to beer industry"""
    
    def __init__(self):
        self.sct_rate = Decimal(str(TAX_RATES['sct']['beer']))
        self.vat_rate = Decimal(str(TAX_RATES['vat']['standard']))
        self.env_tax_per_liter = Decimal(str(TAX_RATES['environmental']['beer_per_liter']))
    
    def calculate_sct(self, base_amount: Decimal) -> Decimal:
        """
        Calculate Special Consumption Tax (Thuế Tiêu Thụ Đặc Biệt)
        
        SCT is calculated on the base price before VAT
        For beer: 65% of selling price (excluding VAT)
        """
        return (base_amount * self.sct_rate).quantize(
            Decimal('1'), rounding=ROUND_HALF_UP
        )
    
    def calculate_vat(self, base_amount: Decimal, sct_amount: Decimal) -> Decimal:
        """
        Calculate Value Added Tax (Thuế Giá Trị Gia Tăng)
        
        VAT is calculated on (base price + SCT)
        Standard rate: 10%
        """
        taxable_amount = base_amount + sct_amount
        return (taxable_amount * self.vat_rate).quantize(
            Decimal('1'), rounding=ROUND_HALF_UP
        )
    
    def calculate_environmental_tax(self, quantity_liters: Decimal) -> Decimal:
        """
        Calculate Environmental Protection Tax (Thuế Bảo Vệ Môi Trường)
        
        For beer: 1,000 VND per liter
        """
        return (quantity_liters * self.env_tax_per_liter).quantize(
            Decimal('1'), rounding=ROUND_HALF_UP
        )
    
    def calculate_total_tax(
        self,
        base_amount: Decimal,
        quantity_liters: Decimal = Decimal('0')
    ) -> TaxCalculation:
        """
        Calculate all taxes for a beer sale
        
        Args:
            base_amount: Base price before taxes (VND)
            quantity_liters: Quantity in liters (for environmental tax)
        
        Returns:
            TaxCalculation with all tax components
        """
        # Calculate SCT (65% of base price)
        sct_amount = self.calculate_sct(base_amount)
        
        # Calculate VAT (10% of base + SCT)
        vat_amount = self.calculate_vat(base_amount, sct_amount)
        
        # Calculate Environmental Tax (1,000 VND/liter)
        env_tax = self.calculate_environmental_tax(quantity_liters)
        
        # Total tax
        total_tax = sct_amount + vat_amount + env_tax
        
        # Total amount
        total = base_amount + total_tax
        
        return TaxCalculation(
            subtotal=base_amount,
            sct_rate=self.sct_rate,
            sct_amount=sct_amount,
            vat_rate=self.vat_rate,
            vat_amount=vat_amount,
            environmental_tax=env_tax,
            total_tax=total_tax,
            total=total
        )
    
    def calculate_invoice_totals(
        self,
        items: List[Dict]
    ) -> Dict:
        """
        Calculate totals for an invoice with multiple items
        
        Args:
            items: List of dicts with 'quantity', 'unit_price', 'volume_ml' keys
        
        Returns:
            Dict with subtotal, taxes, and total
        """
        subtotal = Decimal('0')
        total_quantity_liters = Decimal('0')
        
        for item in items:
            quantity = Decimal(str(item['quantity']))
            unit_price = Decimal(str(item['unit_price']))
            volume_ml = Decimal(str(item.get('volume_ml', 0)))
            
            # Line total
            line_total = quantity * unit_price
            subtotal += line_total
            
            # Total volume in liters
            total_quantity_liters += (quantity * volume_ml) / Decimal('1000')
        
        # Calculate taxes
        tax_calc = self.calculate_total_tax(subtotal, total_quantity_liters)
        
        return tax_calc.to_dict()


def get_tax_rates() -> Dict:
    """Get current tax rates"""
    return TAX_RATES


def format_tax_rate(rate: Decimal) -> str:
    """Format tax rate as percentage"""
    return f"{float(rate) * 100:.0f}%"


# Global instance
_tax_calculator = None


def get_tax_calculator() -> VietnameseTaxCalculator:
    """Get global tax calculator instance"""
    global _tax_calculator
    if _tax_calculator is None:
        _tax_calculator = VietnameseTaxCalculator()
    return _tax_calculator