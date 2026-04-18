"""
Brewery Manager - Internationalization (i18n) Utility
Supports Vietnamese and English with toggle functionality
"""

import json
import os
from functools import lru_cache


class I18n:
    """Internationalization handler for Brewery Manager"""
    
    SUPPORTED_LANGUAGES = ['vi', 'en']
    DEFAULT_LANGUAGE = 'vi'
    
    def __init__(self, translations_dir=None):
        if translations_dir is None:
            translations_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'translations'
            )
        self.translations_dir = translations_dir
        self._translations = {}
        self._load_translations()
    
    def _load_translations(self):
        """Load all translation files"""
        for lang in self.SUPPORTED_LANGUAGES:
            filepath = os.path.join(self.translations_dir, f'{lang}.json')
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    self._translations[lang] = json.load(f)
            except FileNotFoundError:
                print(f"Warning: Translation file not found: {filepath}")
                self._translations[lang] = {}
            except json.JSONDecodeError as e:
                print(f"Error parsing translation file {filepath}: {e}")
                self._translations[lang] = {}
    
    def get(self, key, language=None, **kwargs):
        """
        Get translated text by dot-notation key
        
        Args:
            key: Dot-notation key (e.g., 'nav.dashboard')
            language: Language code ('vi' or 'en'), defaults to DEFAULT_LANGUAGE
            **kwargs: Format parameters for string interpolation
        
        Returns:
            Translated string or key if not found
        """
        if language is None:
            language = self.DEFAULT_LANGUAGE
        
        if language not in self._translations:
            language = self.DEFAULT_LANGUAGE
        
        # Navigate through nested dictionary
        keys = key.split('.')
        value = self._translations.get(language, {})
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                value = None
                break
        
        if value is None:
            # Fallback to default language
            value = self._translations.get(self.DEFAULT_LANGUAGE, {})
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                else:
                    value = None
                    break
        
        if value is None:
            return key  # Return key if translation not found
        
        # Apply string formatting if kwargs provided
        if kwargs and isinstance(value, str):
            try:
                value = value.format(**kwargs)
            except (KeyError, IndexError):
                pass
        
        return value
    
    def get_language_name(self, lang_code):
        """Get display name for language code"""
        names = {
            'vi': 'Tiếng Việt',
            'en': 'English'
        }
        return names.get(lang_code, lang_code)
    
    def get_available_languages(self):
        """Get list of available languages with their display names"""
        return [
            {'code': code, 'name': self.get_language_name(code)}
            for code in self.SUPPORTED_LANGUAGES
        ]


# Global instance
_i18n = None


def get_i18n():
    """Get global i18n instance"""
    global _i18n
    if _i18n is None:
        _i18n = I18n()
    return _i18n


def t(key, language=None, fallback=None, **kwargs):
    """
    Shorthand translation function
    
    Usage:
        from brewery_manager.utils.i18n import t
        text = t('nav.dashboard', language='vi')
        text = t('nav.dashboard', fallback='Dashboard')  # With fallback
    """
    result = get_i18n().get(key, language, **kwargs)
    # If translation not found (returns the key), use fallback if provided
    if result == key and fallback is not None:
        return fallback
    return result


def format_currency(amount, language=None):
    """
    Format currency based on language
    
    Args:
        amount: Numeric amount
        language: Language code
    
    Returns:
        Formatted currency string
    """
    if amount is None:
        amount = 0
    
    # Vietnamese format: 1.000.000 VNĐ
    # English format: 1,000,000 VND
    if language == 'vi':
        # Use dots as thousand separators
        formatted = f"{amount:,.0f}".replace(',', '.')
        return f"{formatted} VNĐ"
    else:
        # Use commas as thousand separators
        formatted = f"{amount:,.0f}"
        return f"{formatted} VND"


def format_date(date_obj, language=None):
    """
    Format date based on language
    
    Args:
        date_obj: datetime object or date string
        language: Language code
    
    Returns:
        Formatted date string
    """
    from datetime import datetime
    
    if isinstance(date_obj, str):
        try:
            date_obj = datetime.strptime(date_obj, '%Y-%m-%d')
        except ValueError:
            return date_obj
    
    if language == 'vi':
        # Vietnamese format: DD/MM/YYYY
        return date_obj.strftime('%d/%m/%Y')
    else:
        # English format: YYYY-MM-DD
        return date_obj.strftime('%Y-%m-%d')


def number_to_words_vietnamese(number):
    """
    Convert number to Vietnamese words (for invoices)
    
    Args:
        number: Integer number
    
    Returns:
        Number in Vietnamese words
    """
    if number == 0:
        return "không"
    
    ones = ["", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]
    tens = ["", "", "hai mươi", "ba mươi", "bốn mươi", "năm mươi", 
            "sáu mươi", "bảy mươi", "tám mươi", "chín mươi"]
    
    def read_hundreds(n):
        result = ""
        hundred = n // 100
        remainder = n % 100
        
        if hundred > 0:
            result += ones[hundred] + " trăm"
            if remainder > 0:
                result += " "
        
        if remainder > 0:
            ten = remainder // 10
            one = remainder % 10
            
            if ten == 0:
                if hundred > 0:
                    result += "lẻ "
                result += ones[one]
            elif ten == 1:
                result += "mười"
                if one > 0:
                    result += " " + ones[one]
            else:
                result += tens[ten]
                if one > 0:
                    if one == 1:
                        result += " mốt"
                    elif one == 5:
                        result += " lăm"
                    else:
                        result += " " + ones[one]
        
        return result
    
    if number < 0:
        return "âm " + number_to_words_vietnamese(-number)
    
    if number < 1000:
        return read_hundreds(number)
    
    # Handle larger numbers
    units = ["", "nghìn", "triệu", "tỷ"]
    result_parts = []
    unit_index = 0
    
    while number > 0:
        if number % 1000 > 0:
            part = read_hundreds(number % 1000)
            if unit_index > 0:
                part += " " + units[unit_index]
            result_parts.insert(0, part)
        number //= 1000
        unit_index += 1
    
    return " ".join(result_parts).strip() + " đồng"