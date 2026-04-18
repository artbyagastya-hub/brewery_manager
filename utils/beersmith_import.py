"""
BeerSmith Recipe Import Utility
Parses .bsmx (XML) files exported from BeerSmith and imports recipes into the brewery manager.
"""

import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
import os
import re


class BeerSmithParser:
    """Parser for BeerSmith .bsmx recipe files"""
    
    def __init__(self):
        self.ns = {'bs': 'http://www.beersmith.com'}
    
    def _clean_xml(self, xml_content: str) -> str:
        """Clean XML content to handle undefined entities and other issues"""
        # Remove DOCTYPE declarations that reference undefined entities
        xml_content = re.sub(r'<!DOCTYPE[^>]*>', '', xml_content)
        
        # Remove XML declaration if present (we'll add it back if needed)
        xml_content = re.sub(r'<\?xml[^?]*\?>', '', xml_content)
        
        # Define standard XML entities
        standard_entities = {'amp', 'lt', 'gt', 'quot', 'apos'}
        
        # Find all entity references
        def replace_entity(match):
            entity_name = match.group(1)
            # Keep standard XML entities as-is
            if entity_name in standard_entities:
                return match.group(0)
            # Replace undefined entities with their literal text
            return entity_name
        
        # Replace undefined entity references
        xml_content = re.sub(r'&([a-zA-Z_][a-zA-Z0-9_.-]*);', replace_entity, xml_content)
        
        # Fix common encoding issues
        xml_content = xml_content.replace('\x00', '')  # Remove null bytes
        
        # Add XML declaration back
        if not xml_content.strip().startswith('<?xml'):
            xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_content
        
        return xml_content
    
    def parse_file(self, file_path: str) -> List[Dict]:
        """Parse a BeerSmith .bsmx file and return list of recipes"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            # First try direct parsing
            tree = ET.parse(file_path)
            root = tree.getroot()
        except ET.ParseError:
            # If that fails, read and clean the XML
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                xml_content = f.read()
            
            xml_content = self._clean_xml(xml_content)
            root = ET.fromstring(xml_content)
        
        recipes = []
        for recipe_elem in root.findall('.//Recipe'):
            recipe = self._parse_recipe(recipe_elem)
            if recipe:
                recipes.append(recipe)
        
        return recipes
    
    def parse_string(self, xml_string: str) -> List[Dict]:
        """Parse BeerSmith XML string and return list of recipes"""
        try:
            root = ET.fromstring(xml_string)
        except ET.ParseError:
            xml_string = self._clean_xml(xml_string)
            root = ET.fromstring(xml_string)
        
        recipes = []
        for recipe_elem in root.findall('.//Recipe'):
            recipe = self._parse_recipe(recipe_elem)
            if recipe:
                recipes.append(recipe)
        
        return recipes
    
    def _parse_recipe(self, recipe_elem) -> Optional[Dict]:
        """Parse a single recipe element"""
        try:
            recipe = {
                'name': self._get_text(recipe_elem, 'Name', 'Unnamed Recipe'),
                'style': self._parse_style(recipe_elem.find('Style')),
                'batch_size': self._get_float(recipe_elem, 'Batch_Size', 20),
                'boil_time': self._get_float(recipe_elem, 'Boil_Time', 60),
                'efficiency': self._get_float(recipe_elem, 'Efficiency', 75),
                'target_og': self._get_float(recipe_elem, 'OG', 1.050),
                'target_fg': self._get_float(recipe_elem, 'FG', 1.010),
                'target_abv': self._get_float(recipe_elem, 'ABV', 5.0),
                'target_ibu': self._get_float(recipe_elem, 'IBU', 25),
                'target_srm': self._get_float(recipe_elem, 'Color', 10),
                'notes': self._get_text(recipe_elem, 'Notes', ''),
                'fermentables': self._parse_fermentables(recipe_elem),
                'hops': self._parse_hops(recipe_elem),
                'yeasts': self._parse_yeasts(recipe_elem),
                'mash_steps': self._parse_mash_steps(recipe_elem),
                'other_ingredients': self._parse_other_ingredients(recipe_elem),
            }
            return recipe
        except Exception as e:
            print(f"Error parsing recipe: {e}")
            return None
    
    def _parse_style(self, style_elem) -> str:
        """Parse style element"""
        if style_elem is None:
            return 'Unknown'
        return self._get_text(style_elem, 'Name', 'Unknown')
    
    def _parse_fermentables(self, recipe_elem) -> List[Dict]:
        """Parse fermentables from recipe"""
        fermentables = []
        for elem in recipe_elem.findall('.//Fermentable'):
            fermentable = {
                'name': self._get_text(elem, 'Name', 'Unknown'),
                'amount_kg': self._get_float(elem, 'Amount', 0),
                'yield_pct': self._get_float(elem, 'Yield', 75),
                'color_srm': self._get_float(elem, 'Color', 2),
                'grain_type': self._get_text(elem, 'Type', 'Grain'),
                'origin': self._get_text(elem, 'Origin', ''),
                'supplier': self._get_text(elem, 'Supplier', ''),
                'notes': self._get_text(elem, 'Notes', ''),
            }
            fermentables.append(fermentable)
        return fermentables
    
    def _parse_hops(self, recipe_elem) -> List[Dict]:
        """Parse hops from recipe"""
        hops = []
        for elem in recipe_elem.findall('.//Hop'):
            hop = {
                'name': self._get_text(elem, 'Name', 'Unknown'),
                'amount_kg': self._get_float(elem, 'Amount', 0),
                'alpha_acid': self._get_float(elem, 'Alpha', 5.0),
                'boil_time_min': self._get_float(elem, 'Time', 60),
                'use_type': self._get_text(elem, 'Use', 'Boil'),
                'form': self._get_text(elem, 'Form', 'Pellet'),
                'origin': self._get_text(elem, 'Origin', ''),
                'notes': self._get_text(elem, 'Notes', ''),
            }
            hops.append(hop)
        return hops
    
    def _parse_yeasts(self, recipe_elem) -> List[Dict]:
        """Parse yeasts from recipe"""
        yeasts = []
        for elem in recipe_elem.findall('.//Yeast'):
            yeast = {
                'name': self._get_text(elem, 'Name', 'Unknown'),
                'lab': self._get_text(elem, 'Lab', ''),
                'product_id': self._get_text(elem, 'Product_ID', ''),
                'attenuation': self._get_float(elem, 'Attenuation', 75),
                'flocculation': self._get_text(elem, 'Flocculation', 'Medium'),
                'min_temp': self._get_float(elem, 'Min_Temp', 15),
                'max_temp': self._get_float(elem, 'Max_Temp', 22),
                'notes': self._get_text(elem, 'Notes', ''),
            }
            yeasts.append(yeast)
        return yeasts
    
    def _parse_mash_steps(self, recipe_elem) -> List[Dict]:
        """Parse mash steps from recipe"""
        steps = []
        mash_elem = recipe_elem.find('Mash')
        if mash_elem is None:
            return steps
        
        for elem in mash_elem.findall('.//MashStep'):
            step = {
                'step_name': self._get_text(elem, 'Name', 'Mash Step'),
                'temperature': self._get_float(elem, 'Step_Temp', 67),
                'duration_min': self._get_float(elem, 'Step_Time', 60),
                'step_type': self._get_text(elem, 'Type', 'Infusion'),
                'infuse_amount': self._get_float(elem, 'Infuse_Amount', 0),
                'notes': self._get_text(elem, 'Notes', ''),
            }
            steps.append(step)
        return steps
    
    def _parse_other_ingredients(self, recipe_elem) -> List[Dict]:
        """Parse other ingredients (spices, fruits, etc.)"""
        ingredients = []
        for elem in recipe_elem.findall('.//Misc'):
            ingredient = {
                'name': self._get_text(elem, 'Name', 'Unknown'),
                'ingredient_type': self._get_text(elem, 'Type', 'Spice'),
                'amount': self._get_float(elem, 'Amount', 0),
                'unit': 'kg' if self._get_text(elem, 'Amount_Is_Weight', '0') == '1' else 'unit',
                'use_time': self._get_float(elem, 'Time', 0),
                'use_stage': self._get_text(elem, 'Use', 'Boil'),
                'notes': self._get_text(elem, 'Notes', ''),
            }
            ingredients.append(ingredient)
        return ingredients
    
    def _get_text(self, elem, tag: str, default: str = '') -> str:
        """Safely get text from an element"""
        child = elem.find(tag)
        if child is not None and child.text:
            return child.text.strip()
        return default
    
    def _get_float(self, elem, tag: str, default: float = 0.0) -> float:
        """Safely get float from an element"""
        text = self._get_text(elem, tag, '')
        if not text:
            return default
        try:
            return float(text)
        except ValueError:
            return default


def validate_recipe(recipe: Dict) -> List[str]:
    """Validate a parsed recipe and return list of warnings"""
    warnings = []
    
    if not recipe.get('name'):
        warnings.append("Recipe has no name")
    
    if not recipe.get('fermentables'):
        warnings.append("Recipe has no fermentables")
    
    if not recipe.get('hops'):
        warnings.append("Recipe has no hops")
    
    if not recipe.get('yeasts'):
        warnings.append("Recipe has no yeast")
    
    if recipe.get('batch_size', 0) <= 0:
        warnings.append("Invalid batch size")
    
    return warnings