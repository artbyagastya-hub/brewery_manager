"""
Brewery Manager - Recipe Calculator Utilities
Advanced brewing calculations for recipes
"""

import math
from typing import List, Dict, Optional, Tuple


class RecipeCalculator:
    """Advanced recipe calculations for brewing"""
    
    # Standard constants
    GRAVITY_POINTS_PER_POUND_GALLON = 46  # PPG for 100% efficient extraction
    LITERS_PER_GALLON = 3.78541
    POUNDS_PER_KG = 2.20462
    GALLONS_PER_LITER = 0.264172
    
    @staticmethod
    def calculate_og(fermentables: List[Dict], batch_size: float, efficiency: float = 75) -> float:
        """
        Calculate Original Gravity from fermentables
        
        Args:
            fermentables: List of fermentable dicts with 'amount' (kg) and 'potential' (PPG)
            batch_size: Batch size in liters
            efficiency: Brewhouse efficiency (0-100)
        
        Returns:
            Original Gravity (e.g., 1.050)
        """
        total_points = 0
        batch_gallons = batch_size * RecipeCalculator.GALLONS_PER_LITER
        
        for fermentable in fermentables:
            amount_lbs = fermentable['amount'] * RecipeCalculator.POUNDS_PER_KG
            potential = fermentable.get('potential', 37)  # Default PPG for base malt
            points = amount_lbs * potential * (efficiency / 100)
            total_points += points
        
        if batch_gallons > 0:
            gravity_points = total_points / batch_gallons
            return 1 + (gravity_points / 1000)
        return 1.000
    
    @staticmethod
    def calculate_fg(og: float, attenuation: float = 75) -> float:
        """
        Calculate Final Gravity
        
        Args:
            og: Original Gravity
            attenuation: Apparent attenuation (0-100)
        
        Returns:
            Final Gravity
        """
        og_points = (og - 1) * 1000
        fg_points = og_points * (1 - attenuation / 100)
        return 1 + (fg_points / 1000)
    
    @staticmethod
    def calculate_abv(og: float, fg: float) -> float:
        """
        Calculate Alcohol By Volume
        
        Args:
            og: Original Gravity
            fg: Final Gravity
        
        Returns:
            ABV percentage
        """
        return (og - fg) * 131.25
    
    @staticmethod
    def calculate_abw(og: float, fg: float) -> float:
        """
        Calculate Alcohol By Weight
        
        Args:
            og: Original Gravity
            fg: Final Gravity
        
        Returns:
            ABW percentage
        """
        abv = RecipeCalculator.calculate_abv(og, fg)
        return abv * 0.79336
    
    @staticmethod
    def calculate_ibu_tinseth(hops: List[Dict], batch_size: float, og: float) -> float:
        """
        Calculate IBU using Tinseth formula
        
        Args:
            hops: List of hop dicts with 'amount' (g), 'alpha_acid', 'boil_time'
            batch_size: Batch size in liters
            og: Original Gravity
        
        Returns:
            IBU value
        """
        total_ibu = 0
        batch_gallons = batch_size * RecipeCalculator.GALLONS_PER_LITER
        
        for hop in hops:
            if hop.get('use_type') != 'boil':
                continue
                
            amount_oz = hop['amount'] / 28.3495  # Convert grams to ounces
            alpha_acid = hop.get('alpha_acid', 5) / 100
            boil_time = hop.get('boil_time', 60)
            
            # Bigness factor
            bigness = 1.65 * math.pow(0.000125, (og - 1))
            
            # Boil time factor
            boil_factor = (1 - math.exp(-0.04 * boil_time)) / 4.15
            
            # Utilization
            utilization = bigness * boil_factor
            
            # IBU contribution
            ibu = (amount_oz * alpha_acid * utilization * 7489) / batch_gallons
            total_ibu += ibu
        
        return total_ibu
    
    @staticmethod
    def calculate_ibu_rager(hops: List[Dict], batch_size: float, og: float) -> float:
        """
        Calculate IBU using Rager formula
        
        Args:
            hops: List of hop dicts
            batch_size: Batch size in liters
            og: Original Gravity
        
        Returns:
            IBU value
        """
        total_ibu = 0
        batch_gallons = batch_size * RecipeCalculator.GALLONS_PER_LITER
        
        for hop in hops:
            if hop.get('use_type') != 'boil':
                continue
                
            amount_oz = hop['amount'] / 28.3495
            alpha_acid = hop.get('alpha_acid', 5) / 100
            boil_time = hop.get('boil_time', 60)
            
            # Utilization
            if boil_time <= 5:
                utilization = 0.05
            elif boil_time <= 10:
                utilization = 0.06
            elif boil_time <= 15:
                utilization = 0.08
            elif boil_time <= 20:
                utilization = 0.101
            elif boil_time <= 25:
                utilization = 0.121
            elif boil_time <= 30:
                utilization = 0.153
            elif boil_time <= 35:
                utilization = 0.188
            elif boil_time <= 40:
                utilization = 0.228
            elif boil_time <= 45:
                utilization = 0.269
            elif boil_time <= 50:
                utilization = 0.281
            elif boil_time <= 60:
                utilization = 0.300
            elif boil_time <= 70:
                utilization = 0.311
            elif boil_time <= 80:
                utilization = 0.320
            elif boil_time <= 90:
                utilization = 0.325
            else:
                utilization = 0.330
            
            # Gravity adjustment
            if og > 1.050:
                ga = 1 + ((og - 1.050) / 0.2)
            else:
                ga = 1
            
            # IBU
            ibu = (amount_oz * utilization * alpha_acid * 7489) / (batch_gallons * ga)
            total_ibu += ibu
        
        return total_ibu
    
    @staticmethod
    def calculate_srm_morey(fermentables: List[Dict], batch_size: float) -> float:
        """
        Calculate SRM color using Morey equation
        
        Args:
            fermentables: List of fermentable dicts with 'amount' (kg) and 'color' (Lovibond)
            batch_size: Batch size in liters
        
        Returns:
            SRM value
        """
        total_mcu = 0
        batch_gallons = batch_size * RecipeCalculator.GALLONS_PER_LITER
        
        for fermentable in fermentables:
            amount_lbs = fermentable['amount'] * RecipeCalculator.POUNDS_PER_KG
            color_lovibond = fermentable.get('color', 2)
            mcu = (amount_lbs * color_lovibond) / batch_gallons
            total_mcu += mcu
        
        # Morey equation
        srm = 1.4922 * math.pow(total_mcu, 0.6859)
        return srm
    
    @staticmethod
    def srm_to_ebc(srm: float) -> float:
        """Convert SRM to EBC"""
        return srm * 1.97
    
    @staticmethod
    def ebc_to_srm(ebc: float) -> float:
        """Convert EBC to SRM"""
        return ebc / 1.97
    
    @staticmethod
    def srm_to_hex(srm: float) -> str:
        """
        Convert SRM to approximate hex color
        
        Args:
            srm: SRM value
        
        Returns:
            Hex color string
        """
        # Approximate SRM to RGB conversion
        r = min(255, max(0, int(255 * math.exp(-0.1 * srm))))
        g = min(255, max(0, int(200 * math.exp(-0.1 * srm))))
        b = min(255, max(0, int(100 * math.exp(-0.1 * srm))))
        return f"#{r:02x}{g:02x}{b:02x}"
    
    @staticmethod
    def calculate_real_extract(og: float, fg: float) -> float:
        """
        Calculate real extract (actual sugar content)
        
        Args:
            og: Original Gravity
            fg: Final Gravity
        
        Returns:
            Real extract percentage
        """
        oe = (og - 1) * 1000 / 4  # Original extract
        re = 0.1808 * oe + 0.8192 * ((fg - 1) * 1000 / 4)
        return re
    
    @staticmethod
    def calculate_attenuation(og: float, fg: float) -> float:
        """
        Calculate apparent attenuation
        
        Args:
            og: Original Gravity
            fg: Final Gravity
        
        Returns:
            Apparent attenuation percentage
        """
        og_points = (og - 1) * 1000
        fg_points = (fg - 1) * 1000
        return ((og_points - fg_points) / og_points) * 100
    
    @staticmethod
    def calculate_calories(og: float, fg: float) -> float:
        """
        Calculate calories per 12oz serving
        
        Args:
            og: Original Gravity
            fg: Final Gravity
        
        Returns:
            Calories per 12oz
        """
        abw = RecipeCalculator.calculate_abw(og, fg)
        re = RecipeCalculator.calculate_real_extract(og, fg)
        calories = (abw * 6.9 + re * 4.0) * 3.55  # 3.55 dL per 12oz
        return calories


class WaterChemistry:
    """Water chemistry calculations for brewing"""
    
    # Ideal ranges for different beer styles (in ppm)
    STYLE_PROFILES = {
        'pilsner': {
            'calcium': 10, 'magnesium': 3, 'sodium': 2,
            'sulfate': 5, 'chloride': 5, 'bicarbonate': 15
        },
        'pale_ale': {
            'calcium': 50, 'magnesium': 10, 'sodium': 10,
            'sulfate': 100, 'chloride': 50, 'bicarbonate': 50
        },
        'ipa': {
            'calcium': 75, 'magnesium': 10, 'sodium': 10,
            'sulfate': 200, 'chloride': 50, 'bicarbonate': 25
        },
        'stout': {
            'calcium': 100, 'magnesium': 20, 'sodium': 30,
            'sulfate': 50, 'chloride': 100, 'bicarbonate': 200
        },
        'wheat': {
            'calcium': 50, 'magnesium': 10, 'sodium': 10,
            'sulfate': 50, 'chloride': 75, 'bicarbonate': 75
        },
        'belgian': {
            'calcium': 75, 'magnesium': 15, 'sodium': 20,
            'sulfate': 100, 'chloride': 100, 'bicarbonate': 100
        }
    }
    
    @staticmethod
    def calculate_mash_ph(water_profile: Dict, grain_bill: List[Dict], 
                          target_ph: float = 5.4) -> Dict:
        """
        Estimate mash pH and recommend adjustments
        
        Args:
            water_profile: Dict with Ca, Mg, Na, SO4, Cl, HCO3 in ppm
            grain_bill: List of grain dicts with 'amount' (kg) and 'color' (Lovibond)
            target_ph: Target mash pH
        
        Returns:
            Dict with estimated pH and recommendations
        """
        # Simplified pH estimation based on grain color and water alkalinity
        total_grain_kg = sum(g['amount'] for g in grain_bill)
        avg_color = sum(g['amount'] * g.get('color', 2) for g in grain_bill) / total_grain_kg if total_grain_kg > 0 else 2
        
        # Rough pH estimation (simplified)
        bicarbonate = water_profile.get('bicarbonate', 50)
        calcium = water_profile.get('calcium', 50)
        
        # Higher bicarbonate = higher pH, darker grain = lower pH
        estimated_ph = 5.7 + (bicarbonate / 200) - (avg_color / 100) - (calcium / 500)
        estimated_ph = max(4.5, min(6.5, estimated_ph))
        
        # Recommendations
        recommendations = []
        if estimated_ph > target_ph + 0.1:
            recommendations.append("Add acid malt (1-2%) or lactic acid to lower pH")
            recommendations.append("Consider adding more calcium salts")
        elif estimated_ph < target_ph - 0.1:
            recommendations.append("Add baking soda to raise pH")
            recommendations.append("Reduce dark malts or add calcium carbonate")
        else:
            recommendations.append("Water profile looks good for this grain bill")
        
        return {
            'estimated_ph': round(estimated_ph, 2),
            'target_ph': target_ph,
            'difference': round(estimated_ph - target_ph, 2),
            'recommendations': recommendations
        }
    
    @staticmethod
    def calculate_salt_additions(water_volume: float, current_profile: Dict,
                                 target_profile: Dict) -> Dict:
        """
        Calculate salt additions needed to reach target water profile
        
        Args:
            water_volume: Volume in liters
            current_profile: Current water mineral profile (ppm)
            target_profile: Target water mineral profile (ppm)
        
        Returns:
            Dict with salt additions in grams
        """
        # Salt composition factors (ppm per gram per liter)
        # CaSO4 (Gypsum): 23.2% Ca, 55.8% SO4
        # CaCl2: 36.1% Ca, 63.9% Cl
        # MgSO4 (Epsom): 9.9% Mg, 39.0% SO4
        # NaHCO3 (Baking soda): 27.4% Na, 72.6% HCO3
        # NaCl (Table salt): 39.3% Na, 60.7% Cl
        
        additions = {}
        
        # Calculate calcium needs
        ca_deficit = target_profile.get('calcium', 0) - current_profile.get('calcium', 0)
        if ca_deficit > 0:
            # Prefer gypsum for sulfate-forward styles
            gypsum_g = (ca_deficit * water_volume) / (1000 * 0.232)
            additions['gypsum_caso4'] = round(gypsum_g, 2)
        
        # Calculate sulfate needs
        so4_deficit = target_profile.get('sulfate', 0) - current_profile.get('sulfate', 0)
        if so4_deficit > 0:
            gypsum_so4 = additions.get('gypsum_caso4', 0) * 0.558 * 1000 / water_volume
            remaining_so4 = so4_deficit - gypsum_so4
            if remaining_so4 > 0:
                epsom_g = (remaining_so4 * water_volume) / (1000 * 0.390)
                additions['epsom_salt_mgso4'] = round(epsom_g, 2)
        
        # Calculate chloride needs
        cl_deficit = target_profile.get('chloride', 0) - current_profile.get('chloride', 0)
        if cl_deficit > 0:
            cacl2_g = (cl_deficit * water_volume) / (1000 * 0.639)
            additions['calcium_chloride_cacl2'] = round(cacl2_g, 2)
        
        # Calculate sodium needs
        na_deficit = target_profile.get('sodium', 0) - current_profile.get('sodium', 0)
        if na_deficit > 0:
            nahco3_g = (na_deficit * water_volume) / (1000 * 0.274)
            additions['baking_soda_nahco3'] = round(nahco3_g, 2)
        
        return additions
    
    @staticmethod
    def calculate_sulfate_chloride_ratio(profile: Dict) -> Dict:
        """
        Calculate sulfate to chloride ratio for flavor prediction
        
        Args:
            profile: Water mineral profile
        
        Returns:
            Dict with ratio and flavor description
        """
        sulfate = profile.get('sulfate', 0)
        chloride = profile.get('chloride', 0)
        
        if chloride == 0:
            ratio = float('inf') if sulfate > 0 else 1
        else:
            ratio = sulfate / chloride
        
        if ratio > 2:
            flavor = "Very dry, crisp, accentuates hop bitterness"
        elif ratio > 1.5:
            flavor = "Dry, hop-forward"
        elif ratio > 1:
            flavor = "Balanced, slightly hop-forward"
        elif ratio > 0.5:
            flavor = "Balanced"
        elif ratio > 0:
            flavor = "Full, malty, accentuates malt sweetness"
        else:
            flavor = "Very full, round, malt-forward"
        
        return {
            'ratio': round(ratio, 2),
            'sulfate': sulfate,
            'chloride': chloride,
            'flavor_profile': flavor
        }
    
    @staticmethod
    def get_style_recommendation(style: str) -> Dict:
        """
        Get recommended water profile for a beer style
        
        Args:
            style: Beer style key
        
        Returns:
            Recommended water profile
        """
        return WaterChemistry.STYLE_PROFILES.get(style.lower(), 
                                                  WaterChemistry.STYLE_PROFILES['pale_ale'])


class YeastCalculator:
    """Yeast pitching and propagation calculations"""
    
    # Cell density: ~1 billion cells per mL of yeast slurry
    CELLS_PER_ML_SLURRY = 1e9
    
    @staticmethod
    def calculate_pitch_rate(batch_size: float, og: float, 
                            yeast_type: str = 'ale') -> Dict:
        """
        Calculate recommended yeast pitch rate
        
        Args:
            batch_size: Batch size in liters
            og: Original Gravity
            yeast_type: 'ale' or 'lager'
        
        Returns:
            Dict with pitch rate info
        """
        # Target cells per mL per degree Plato
        if yeast_type == 'lager':
            target_cells_per_ml_plato = 1.5e6
        else:
            target_cells_per_ml_plato = 0.75e6
        
        # Convert OG to Plato
        plato = (-1 * 616.868) + (1111.14 * og) - (630.272 * og**2) + (135.997 * og**3)
        
        # Calculate total cells needed
        batch_ml = batch_size * 1000
        total_cells = target_cells_per_ml_plato * plato * batch_ml
        
        # Starter size for 100B cell pack
        starter_size_l = (total_cells - 100e9) / (3e9) if total_cells > 100e9 else 0
        
        return {
            'total_cells_needed': int(total_cells),
            'total_cells_billions': round(total_cells / 1e9, 1),
            'starter_size_liters': round(max(0, starter_size_l), 2),
            'plato': round(plato, 1),
            'pitch_rate_type': yeast_type
        }
    
    @staticmethod
    def calculate_starter_size(cells_needed: float, cells_available: float,
                              stir_plate: bool = True) -> Dict:
        """
        Calculate starter size for yeast propagation
        
        Args:
            cells_needed: Total cells needed (billions)
            cells_available: Cells available in pack (billions)
            stir_plate: Whether using stir plate
        
        Returns:
            Starter calculation details
        """
        # Growth rate: ~3x with stir plate, ~2x without
        growth_rate = 3.0 if stir_plate else 2.0
        
        if cells_available >= cells_needed:
            return {
                'starter_needed': False,
                'starter_size_liters': 0,
                'cells_available': cells_available,
                'cells_needed': cells_needed
            }
        
        # Calculate starter size (assuming 100g DME per liter)
        # Each liter produces ~3B cells with stir plate
        cells_deficit = cells_needed - cells_available
        starter_size = cells_deficit / (growth_rate * 1e9)
        
        return {
            'starter_needed': True,
            'starter_size_liters': round(starter_size, 2),
            'dme_grams': round(starter_size * 100, 1),
            'cells_available': cells_available,
            'cells_needed': cells_needed,
            'growth_rate': growth_rate
        }
    
    @staticmethod
    def estimate_generation_attenuation(generation: int, 
                                        base_attenuation: float = 75) -> float:
        """
        Estimate attenuation based on yeast generation
        
        Args:
            generation: Yeast generation (1 = fresh pack)
            base_attenuation: Base attenuation of yeast strain
        
        Returns:
            Estimated attenuation
        """
        # Attenuation typically increases slightly with generation
        # then drops off after generation 5-6
        if generation <= 1:
            return base_attenuation
        elif generation <= 4:
            return min(base_attenuation + (generation - 1) * 1.5, base_attenuation + 5)
        elif generation <= 6:
            return base_attenuation + 3
        else:
            return max(base_attenuation - (generation - 6) * 2, base_attenuation - 10)


# Convenience functions
def calculate_recipe_stats(recipe: Dict) -> Dict:
    """
    Calculate all stats for a recipe
    
    Args:
        recipe: Recipe dict with fermentables, hops, yeast, batch_size, efficiency
    
    Returns:
        Dict with OG, FG, ABV, IBU, SRM, calories
    """
    batch_size = recipe.get('batch_size', 20)
    efficiency = recipe.get('efficiency', 75)
    fermentables = recipe.get('fermentables', [])
    hops = recipe.get('hops', [])
    yeast = recipe.get('yeast', {})
    
    # Calculate OG
    og = RecipeCalculator.calculate_og(fermentables, batch_size, efficiency)
    
    # Get attenuation from yeast
    attenuation = yeast.get('attenuation', 75) if yeast else 75
    
    # Calculate FG
    fg = RecipeCalculator.calculate_fg(og, attenuation)
    
    # Calculate other stats
    abv = RecipeCalculator.calculate_abv(og, fg)
    ibu = RecipeCalculator.calculate_ibu_tinseth(hops, batch_size, og)
    srm = RecipeCalculator.calculate_srm_morey(fermentables, batch_size)
    calories = RecipeCalculator.calculate_calories(og, fg)
    
    return {
        'og': round(og, 3),
        'fg': round(fg, 3),
        'abv': round(abv, 1),
        'ibu': round(ibu, 1),
        'srm': round(srm, 1),
        'calories': round(calories, 0),
        'color_hex': RecipeCalculator.srm_to_hex(srm)
    }