"""
Intake Agent Tools - Comprehensive toolset for processing customer requests
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

class TextProcessingTools:
    """Text processing utilities for intake agent."""
    
    @staticmethod
    def extract_phone_numbers(text: str) -> List[str]:
        """Extract phone numbers from text."""
        patterns = [
            r'(\+91[\-\s]?)?[0]?(91)?[789]\d{9}',  # Indian mobile
            r'(\+91[\-\s]?)?[0]?[1-9]\d{8,10}',    # Indian landline
        ]
        
        phones = []
        for pattern in patterns:
            phones.extend(re.findall(pattern, text))
        
        return list(set([phone.strip() for phone in phones if phone.strip()]))
    
    @staticmethod
    def extract_amounts(text: str) -> List[Dict[str, Any]]:
        """Extract monetary amounts from text."""
        patterns = [
            r'₹\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',  # ₹ symbol
            r'(?:rs|rupees?)\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',  # rs/rupees
            r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:rs|rupees?)',  # number + rs/rupees
            r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',  # Dollar
        ]
        
        amounts = []
        for i, pattern in enumerate(patterns):
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                currency = "INR" if i < 3 else "USD"
                amount_str = match.group(1)
                amount = float(amount_str.replace(',', ''))
                
                amounts.append({
                    "amount": amount,
                    "currency": currency,
                    "raw_text": match.group(0)
                })
        
        return amounts
    
    @staticmethod
    def extract_quantities(text: str) -> List[Dict[str, Any]]:
        """Extract quantities with units from text."""
        patterns = [
            r'(\d+(?:\.\d+)?)\s*(kg|kilogram|kilograms)',
            r'(\d+(?:\.\d+)?)\s*(g|gram|grams)',
            r'(\d+(?:\.\d+)?)\s*(ton|tons|tonne|tonnes)',
            r'(\d+(?:\.\d+)?)\s*(ltr|litre|litres|liter|liters)',
            r'(\d+(?:\.\d+)?)\s*(pcs|pieces?|nos?|numbers?)',
            r'(\d+(?:\.\d+)?)\s*(bags?|sacks?)',
            r'(\d+(?:\.\d+)?)\s*(boxes?|cartons?)',
        ]
        
        quantities = []
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                quantity = float(match.group(1))
                unit = match.group(2).lower()
                
                # Normalize units
                unit_mapping = {
                    'kilogram': 'kg', 'kilograms': 'kg',
                    'gram': 'g', 'grams': 'g',
                    'ton': 'tonne', 'tons': 'tonne', 'tonnes': 'tonne',
                    'litre': 'ltr', 'litres': 'ltr', 'liter': 'ltr', 'liters': 'ltr',
                    'pieces': 'pcs', 'piece': 'pcs', 'nos': 'pcs', 'numbers': 'pcs', 'number': 'pcs',
                    'bag': 'bags', 'sack': 'sacks',
                    'box': 'boxes', 'carton': 'cartons'
                }
                
                normalized_unit = unit_mapping.get(unit, unit)
                
                quantities.append({
                    "value": quantity,
                    "unit": normalized_unit,
                    "raw_text": match.group(0)
                })
        
        return quantities
    
    @staticmethod
    def extract_locations(text: str) -> List[Dict[str, Any]]:
        """Extract location information from text."""
        pincode_pattern = r'\b(\d{6})\b'
        pincodes = re.findall(pincode_pattern, text)
        
        # Common Indian city patterns
        indian_cities = [
            'mumbai', 'delhi', 'bangalore', 'hyderabad', 'chennai', 'kolkata',
            'pune', 'ahmedabad', 'jaipur', 'surat', 'lucknow', 'kanpur',
            'nagpur', 'indore', 'thane', 'bhopal', 'visakhapatnam', 'pimpri',
            'patna', 'vadodara', 'ghaziabad', 'ludhiana', 'agra', 'nashik'
        ]
        
        locations = []
        text_lower = text.lower()
        
        for city in indian_cities:
            if city in text_lower:
                locations.append({
                    "type": "city",
                    "value": city.title(),
                    "confidence": 0.8
                })
        
        for pincode in pincodes:
            locations.append({
                "type": "pincode",
                "value": pincode,
                "confidence": 0.9
            })
        
        return locations
    
    @staticmethod
    def detect_urgency(text: str) -> str:
        """Detect urgency level from text."""
        urgent_keywords = ['urgent', 'asap', 'immediately', 'emergency', 'critical']
        high_keywords = ['soon', 'quickly', 'fast', 'priority']
        medium_keywords = ['within', 'by', 'before']
        
        text_lower = text.lower()
        
        if any(keyword in text_lower for keyword in urgent_keywords):
            return "urgent"
        elif any(keyword in text_lower for keyword in high_keywords):
            return "high"
        elif any(keyword in text_lower for keyword in medium_keywords):
            return "medium"
        else:
            return "low"

class ValidationTools:
    """Validation utilities for intake processing."""
    
    @staticmethod
    def validate_business_inquiry(text: str) -> Dict[str, Any]:
        """Validate if the text is a legitimate business inquiry."""
        spam_indicators = [
            'click here', 'free money', 'lottery', 'winner', 'congratulations',
            'claim now', 'limited time', 'act now', 'urgent response required'
        ]
        
        business_indicators = [
            'need', 'want', 'buy', 'purchase', 'sell', 'supply', 'require',
            'quote', 'price', 'cost', 'bulk', 'wholesale', 'quantity'
        ]
        
        text_lower = text.lower()
        
        spam_score = sum(1 for indicator in spam_indicators if indicator in text_lower)
        business_score = sum(1 for indicator in business_indicators if indicator in text_lower)
        
        is_valid = business_score > spam_score and len(text.split()) > 3
        confidence = min((business_score / max(len(business_indicators), 1)) * 0.8 + 0.2, 1.0)
        
        return {
            "is_valid": is_valid,
            "confidence": confidence,
            "spam_score": spam_score,
            "business_score": business_score,
            "word_count": len(text.split())
        }
    
    @staticmethod
    def classify_intent(text: str) -> str:
        """Classify the intent of the message."""
        buy_keywords = ['buy', 'purchase', 'need', 'want', 'require', 'looking for']
        sell_keywords = ['sell', 'selling', 'available', 'supply', 'offer']
        inquiry_keywords = ['price', 'cost', 'quote', 'information', 'details']
        
        text_lower = text.lower()
        
        buy_score = sum(1 for keyword in buy_keywords if keyword in text_lower)
        sell_score = sum(1 for keyword in sell_keywords if keyword in text_lower)
        inquiry_score = sum(1 for keyword in inquiry_keywords if keyword in text_lower)
        
        max_score = max(buy_score, sell_score, inquiry_score)
        
        if max_score == 0:
            return "general"
        elif buy_score == max_score:
            return "buy"
        elif sell_score == max_score:
            return "sell"
        else:
            return "inquire"

# LangChain Tools
@tool
def extract_structured_data(text: str) -> Dict[str, Any]:
    """Extract structured data from customer message."""
    processor = TextProcessingTools()
    validator = ValidationTools()
    
    return {
        "phones": processor.extract_phone_numbers(text),
        "amounts": processor.extract_amounts(text),
        "quantities": processor.extract_quantities(text),
        "locations": processor.extract_locations(text),
        "urgency": processor.detect_urgency(text),
        "validation": validator.validate_business_inquiry(text),
        "intent": validator.classify_intent(text),
        "timestamp": datetime.now().isoformat()
    }

@tool
def categorize_product(product_name: str, description: str = "") -> Dict[str, Any]:
    """Categorize product based on name and description."""
    categories = {
        "raw_materials": ["clay", "sand", "cement", "steel", "iron", "wood", "plastic"],
        "textiles": ["fabric", "cloth", "yarn", "thread", "cotton", "silk", "wool"],
        "electronics": ["mobile", "phone", "computer", "laptop", "cable", "wire"],
        "food_items": ["rice", "wheat", "oil", "spices", "grain", "flour"],
        "chemicals": ["acid", "chemical", "solvent", "paint", "dye"],
        "machinery": ["machine", "equipment", "tool", "motor", "pump"]
    }
    
    text = f"{product_name} {description}".lower()
    
    for category, keywords in categories.items():
        if any(keyword in text for keyword in keywords):
            return {
                "category": category,
                "confidence": 0.8,
                "keywords_matched": [kw for kw in keywords if kw in text]
            }
    
    return {
        "category": "general",
        "confidence": 0.3,
        "keywords_matched": []
    }

# Export tools for LangGraph integration
intake_tools = [extract_structured_data, categorize_product]
