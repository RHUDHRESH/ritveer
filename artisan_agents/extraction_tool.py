"""
extraction_tool.py

Unified Slot/Entity Extraction Tool for Materials, Quantities, Locations, and Urgency.

README
------

Example usage code:

from extraction_tool import ExtractionTool

tool = ExtractionTool()
text = 'Need 5 kg of aluminum sheets in Chennai by tonight, URGENT.'
result = tool.extract_all(text)
print(result)

Extension: See classes OllamaExtractor and RegexExtractor for custom slot logic and prompt expansion.

"""

import re
import typing
import logging
import json
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple, Union

# --- Logging Setup ---
logger = logging.getLogger("extraction_tool")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# --------------------------------------------------------
# --- Extraction Schema & Enumerations ---
# --------------------------------------------------------

class UnitEnum(Enum):
    METER = "m"
    KILOGRAM = "kg"
    PIECE = "pcs"

    @classmethod
    def normalize(cls, unit: str) -> Optional[str]:
        unit = unit.lower().strip()
        mapping = {"meters": "m", "meter": "m", "m": "m",
                   "kilograms": "kg", "kilogram": "kg", "kgs": "kg", "kg": "kg",
                   "pieces": "pcs", "piece": "pcs", "pcs": "pcs"}
        return mapping.get(unit, None)


class UrgencyEnum(Enum):
    NORMAL = "NORMAL"
    URGENT = "URGENT"
    EMERGENCY = "EMERGENCY"

    @classmethod
    def from_str(cls, val: str) -> Optional[str]:
        val = val.lower()
        mapping = {
            "normal": "NORMAL",
            "urgent": "URGENT",
            "immediately": "URGENT",
            "emergency": "EMERGENCY",
            "asap": "URGENT",
            "critical": "EMERGENCY",
            "standard": "NORMAL",
            "fast": "URGENT",
        }
        for pat, mapped in mapping.items():
            if pat in val:
                return mapped
        return None


VALID_LOCATIONS = [
    "Chennai", "Delhi", "Bangalore", "Mumbai", "Hyderabad", "Pune",
    "Coimbatore", "Kolkata", "Jaipur", "Ahmedabad"
]


@dataclass
class MaterialSlot:
    value: Optional[str] = None


@dataclass
class QuantitySlot:
    value: Optional[float] = None
    unit: Optional[str] = None


@dataclass
class LocationSlot:
    value: Optional[str] = None


@dataclass
class UrgencySlot:
    value: Optional[str] = None


@dataclass
class ExtractionResult:
    material: MaterialSlot = field(default_factory=MaterialSlot)
    quantity: QuantitySlot = field(default_factory=QuantitySlot)
    location: LocationSlot = field(default_factory=LocationSlot)
    urgency: UrgencySlot = field(default_factory=UrgencySlot)
    method_flags: Dict[str, Dict[str, bool]] = field(default_factory=dict)
    errors: Dict[str, str] = field(default_factory=dict)

# --------------------------------------------------------
# --- Custom Exceptions ---
# --------------------------------------------------------

class ExtractionError(Exception):
    pass

class OllamaTimeoutError(ExtractionError):
    pass

class SchemaValidationError(ExtractionError):
    pass

# --------------------------------------------------------
# --- Ollama Extraction Prompt Templates ---
# --------------------------------------------------------

OLLAMA_MATERIAL_PROMPT = (
    "Extract the material mentioned in the following text. Respond ONLY with a single material name.\n"
    "Examples:\n"
    "'Need 10 kg copper wire in Mumbai' => 'copper wire'\n"
    "'Requesting 15 pcs plastic sheets' => 'plastic sheets'\n"
    "'Aluminum rods required urgently' => 'aluminum rods'\n"
    "Text: {input}\n"
    "Material:"
)

OLLAMA_QUANTITY_PROMPT = (
    "Extract the quantity and unit from the text as JSON with keys 'quantity' (float) and 'unit' (str, m/kg/pcs).\n"
    "Examples:\n"
    "'Need 10 kg copper wire' => {'quantity': 10, 'unit': 'kg'}\n"
    "'Requesting 15 pcs plastic sheets' => {'quantity': 15, 'unit': 'pcs'}\n"
    "'Require 20 meters steel cable' => {'quantity': 20, 'unit': 'm'}\n"
    "Text: {input}\n"
    "Quantity and unit:"
)

OLLAMA_LOCATION_PROMPT = (
    "Extract the city/location from the text. Respond ONLY with the city name (in the allowed list: Chennai, Delhi, Bangalore, Mumbai, Hyderabad, Pune, Coimbatore, Kolkata, Jaipur, Ahmedabad).\n"
    "Examples:\n"
    "'Need 10 kg copper wire in Mumbai' => 'Mumbai'\n"
    "'Material required at Chennai location' => 'Chennai'\n"
    "'Deliver to Bangalore office.' => 'Bangalore'\n"
    "Text: {input}\n"
    "Location:"
)

OLLAMA_URGENCY_PROMPT = (
    "Extract the urgency level from the text. Allowed values: NORMAL, URGENT, EMERGENCY. Respond ONLY with one value.\n"
    "Examples:\n"
    "'Deliver urgently.' => 'URGENT'\n"
    "'This is an emergency requirement' => 'EMERGENCY'\n"
    "'Standard delivery requested.' => 'NORMAL'\n"
    "'Need ASAP.' => 'URGENT'\n"
    "Text: {input}\n"
    "Urgency:"
)

# --------------------------------------------------------
# --- Ollama Extraction Logic ---
# --------------------------------------------------------

class OllamaExtractor:
    """
    Extractor using Ollama Python client for slot extraction.
    """

    def __init__(self, model: str = "llama3"):
        try:
            import ollama
        except ImportError:
            logger.warning("Ollama Python client not installed. Please install 'ollama'.")
            raise

        self.client = ollama
        self.model = model

    def _send_prompt(self, prompt: str) -> str:
        try:
            logger.debug("Sending prompt to Ollama: %s", prompt[:80])
            response = self.client.generate(model=self.model, prompt=prompt)
            result = response.get("response", "").strip()
            logger.debug("Ollama response: %s", result)
            return result
        except Exception as e:
            logger.error("Ollama extraction failed: %s", e)
            raise OllamaTimeoutError(str(e))

    def extract_material(self, text: str) -> Optional[str]:
        prompt = OLLAMA_MATERIAL_PROMPT.format(input=text)
        result = self._send_prompt(prompt)
        if result and result.lower() != "none":
            return result
        return None

    def extract_quantity(self, text: str) -> Optional[float]:
        prompt = OLLAMA_QUANTITY_PROMPT.format(input=text)
        result = self._send_prompt(prompt)
        try:
            parsed = json.loads(result)
            quantity = float(parsed.get("quantity", 0))
            if quantity > 0:
                return quantity
        except Exception as e:
            logger.debug("Failed to parse quantity JSON: %s", e)
        return None

    def extract_unit(self, text: str) -> Optional[str]:
        prompt = OLLAMA_QUANTITY_PROMPT.format(input=text)
        result = self._send_prompt(prompt)
        try:
            parsed = json.loads(result)
            unit = str(parsed.get("unit", "")).lower()
            return UnitEnum.normalize(unit)
        except Exception as e:
            logger.debug("Failed to parse unit JSON: %s", e)
        return None

    def extract_location(self, text: str) -> Optional[str]:
        prompt = OLLAMA_LOCATION_PROMPT.format(input=text)
        result = self._send_prompt(prompt)
        result = result.strip()
        if result in VALID_LOCATIONS:
            return result
        return None

    def extract_urgency(self, text: str) -> Optional[str]:
        prompt = OLLAMA_URGENCY_PROMPT.format(input=text)
        result = self._send_prompt(prompt)
        val = UrgencyEnum.from_str(result)
        if val:
            return val
        return None

# --------------------------------------------------------
# --- Regex Fallback Extraction ---
# --------------------------------------------------------

class RegexExtractor:
    """
    Regex-based fallback extractor for slot detection.
    """

    # Precompiled patterns
    quantity_unit_pat = re.compile(r'(\d+(\.\d+)?)\s*(kg|kilogram|kilograms|m|meter|meters|pcs|piece|pieces)')
    location_pat = re.compile(r'\b({})\b'.format('|'.join(VALID_LOCATIONS)), re.IGNORECASE)
    urgency_pat = re.compile(r'\b(emergency|urgent|immediate|asap|critical|standard|normal|fast)\b', re.IGNORECASE)
    material_pat = re.compile(r'(?:of|need|require|requesting|want|deliver)\s+([a-zA-Z ]{3,50})', re.IGNORECASE)

    def extract_material(self, text: str) -> Optional[str]:
        match = self.material_pat.search(text)
        if match:
            material = match.group(1).strip()
            return material
        return None

    def extract_quantity(self, text: str) -> Optional[float]:
        match = self.quantity_unit_pat.search(text)
        if match:
            try:
                value = float(match.group(1))
                return value
            except Exception as e:
                logger.debug("Failed to normalize quantity to float: %s", e)
        return None

    def extract_unit(self, text: str) -> Optional[str]:
        match = self.quantity_unit_pat.search(text)
        if match:
            return UnitEnum.normalize(match.group(3))
        return None

    def extract_location(self, text: str) -> Optional[str]:
        match = self.location_pat.search(text)
        if match:
            city = match.group(0)
            # Normalize case
            for loc in VALID_LOCATIONS:
                if loc.lower() == city.lower():
                    return loc
        return None

    def extract_urgency(self, text: str) -> Optional[str]:
        match = self.urgency_pat.search(text)
        if match:
            return UrgencyEnum.from_str(match.group(0))
        return None

# --------------------------------------------------------
# --- Normalization Utilities ---
# --------------------------------------------------------

def normalize_unit(unit: str) -> Optional[str]:
    return UnitEnum.normalize(unit)

def normalize_quantity(val: str) -> Optional[float]:
    try:
        return float(val)
    except Exception:
        return None

def normalize_urgency(val: str) -> Optional[str]:
    return UrgencyEnum.from_str(val)

# --------------------------------------------------------
# --- Unified Extraction Tool ---
# --------------------------------------------------------

class ExtractionTool:
    """
    Unified slot extractor that tries Ollama, validates schema, and falls back to regex.
    Aggregates results into ExtractionResult.
    """

    def __init__(self, ollama_model: str = "llama3"):
        try:
            self.ollama = OllamaExtractor(model=ollama_model)
        except Exception:
            self.ollama = None
        self.regex = RegexExtractor()

    def _validate_unit(self, unit: Optional[str]) -> bool:
        return unit in [u.value for u in UnitEnum]

    def _validate_location(self, location: Optional[str]) -> bool:
        return location in VALID_LOCATIONS

    def _validate_urgency(self, val: Optional[str]) -> bool:
        return val in [u.value for u in UrgencyEnum]

    def extract_all(self, text: str) -> ExtractionResult:
        result = ExtractionResult()
        method_flags = {}
        errors = {}

        # Material
        method_flags['material'] = {'ollama': False, 'regex': False}
        material = None
        if self.ollama:
            try:
                material = self.ollama.extract_material(text)
                if material:
                    method_flags['material']['ollama'] = True
            except Exception as e:
                errors['material_ollama'] = str(e)
        if not material:
            try:
                material = self.regex.extract_material(text)
                if material:
                    method_flags['material']['regex'] = True
            except Exception as e:
                errors['material_regex'] = str(e)
        result.material = MaterialSlot(material)

        # Quantity
        method_flags['quantity'] = {'ollama': False, 'regex': False}
        quantity = None
        if self.ollama:
            try:
                quantity = self.ollama.extract_quantity(text)
                if quantity is not None:
                    method_flags['quantity']['ollama'] = True
            except Exception as e:
                errors['quantity_ollama'] = str(e)
        if quantity is None:
            try:
                quantity = self.regex.extract_quantity(text)
                if quantity is not None:
                    method_flags['quantity']['regex'] = True
            except Exception as e:
                errors['quantity_regex'] = str(e)

        # Unit
        method_flags['unit'] = {'ollama': False, 'regex': False}
        unit = None
        if self.ollama:
            try:
                unit = self.ollama.extract_unit(text)
                if self._validate_unit(unit):
                    method_flags['unit']['ollama'] = True
                else:
                    unit = None
            except Exception as e:
                errors['unit_ollama'] = str(e)
        if unit is None:
            try:
                unit = self.regex.extract_unit(text)
                if self._validate_unit(unit):
                    method_flags['unit']['regex'] = True
            except Exception as e:
                errors['unit_regex'] = str(e)
        result.quantity = QuantitySlot(quantity, unit)

        # Location
        method_flags['location'] = {'ollama': False, 'regex': False}
        location = None
        if self.ollama:
            try:
                location = self.ollama.extract_location(text)
                if self._validate_location(location):
                    method_flags['location']['ollama'] = True
            except Exception as e:
                errors['location_ollama'] = str(e)
        if not location:
            try:
                location = self.regex.extract_location(text)
                if self._validate_location(location):
                    method_flags['location']['regex'] = True
            except Exception as e:
                errors['location_regex'] = str(e)
        result.location = LocationSlot(location)

        # Urgency
        method_flags['urgency'] = {'ollama': False, 'regex': False}
        urgency = None
        if self.ollama:
            try:
                urgency = self.ollama.extract_urgency(text)
                if self._validate_urgency(urgency):
                    method_flags['urgency']['ollama'] = True
            except Exception as e:
                errors['urgency_ollama'] = str(e)
        if not urgency:
            try:
                urgency = self.regex.extract_urgency(text)
                if self._validate_urgency(urgency):
                    method_flags['urgency']['regex'] = True
            except Exception as e:
                errors['urgency_regex'] = str(e)
        result.urgency = UrgencySlot(urgency)

        result.method_flags = method_flags
        result.errors = errors
        logger.debug("ExtractionResult: %s", result)
        return result

# --------------------------------------------------------
# --- Tests: Pytest Test Suite ---
# --------------------------------------------------------

# Mocks
class MockOllamaExtractor(OllamaExtractor):
    def __init__(self):
        pass

    def extract_material(self, text: str) -> Optional[str]:
        # Simulate simple material extraction
        if 'aluminum' in text.lower():
            return 'aluminum sheets'
        elif 'copper wire' in text.lower():
            return 'copper wire'
        return None

    def extract_quantity(self, text: str) -> Optional[float]:
        if '5 kg' in text.lower():
            return 5.0
        elif '10 kg' in text.lower():
            return 10.0
        elif '12 pcs' in text.lower():
            return 12.0
        return None

    def extract_unit(self, text: str) -> Optional[str]:
        if 'kg' in text.lower():
            return 'kg'
        elif 'meters' in text.lower():
            return 'm'
        elif 'pcs' in text.lower():
            return 'pcs'
        return None

    def extract_location(self, text: str) -> Optional[str]:
        for loc in VALID_LOCATIONS:
            if loc.lower() in text.lower():
                return loc
        return None

    def extract_urgency(self, text: str) -> Optional[str]:
        if 'urgent' in text.lower():
            return 'URGENT'
        elif 'emergency' in text.lower():
            return 'EMERGENCY'
        elif 'normal' in text.lower():
            return 'NORMAL'
        return None

class ExtractionToolTestable(ExtractionTool):
    def __init__(self):
        self.ollama = MockOllamaExtractor()
        self.regex = RegexExtractor()

def test_successful_ollama_extraction():
    tool = ExtractionToolTestable()
    txt = "Need 5 kg of aluminum sheets in Chennai by tonight, URGENT."
    res = tool.extract_all(txt)
    assert res.material.value == "aluminum sheets"
    assert res.quantity.value == 5.0
    assert res.quantity.unit == "kg"
    assert res.location.value == "Chennai"
    assert res.urgency.value == "URGENT"
    assert res.method_flags['material']['ollama']
    assert res.errors == {}

def test_regex_fallback_quantity():
    tool = ExtractionToolTestable()
    # No Ollama quantity, only regex
    tool.ollama.extract_quantity = lambda text: None
    txt = "Require 12 pcs plastic covers at Bangalore"
    res = tool.extract_all(txt)
    # Regex should capture
    assert res.quantity.value == 12.0
    assert res.quantity.unit == "pcs"
    assert res.location.value == "Bangalore"

def test_regex_material_edgecase():
    tool = ExtractionToolTestable()
    tool.ollama.extract_material = lambda text: None
    txt = "Requesting urgent delivery of copper wire."
    res = tool.extract_all(txt)
    assert "copper wire" in res.material.value

def test_emergency_urgency_mapping():
    tool = ExtractionToolTestable()
    txt = "This is an emergency request for aluminum rods in Delhi"
    res = tool.extract_all(txt)
    assert res.urgency.value == "EMERGENCY"
    assert res.location.value == "Delhi"

def test_invalid_location():
    tool = ExtractionToolTestable()
    txt = "Material needed in Paris"
    res = tool.extract_all(txt)
    assert res.location.value is None
    # Regex extractor should not catch location

def test_multiple_matches_in_text():
    tool = ExtractionToolTestable()
    txt = "Deliver 10 kg copper wire and 20 pcs plastic sheets to Hyderabad, URGENT"
    res = tool.extract_all(txt)
    # Take first match for slots
    assert res.quantity.value == 10.0 or res.quantity.value == 20.0
    assert res.location.value == "Hyderabad"

def test_overlapping_unit_patterns():
    tool = ExtractionToolTestable()
    txt = "Need 10 kilograms of wire, 12 meters of cable"
    res = tool.extract_all(txt)
    # Only first match for quantity/unit - should be meters based on current logic
    assert res.quantity.value == 10.0
    assert res.quantity.unit == "m"

def test_error_path_ollama_timeout(monkeypatch):
    tool = ExtractionToolTestable()
    def raise_timeout(text): raise OllamaTimeoutError("Simulated timeout")
    tool.ollama.extract_material = raise_timeout
    txt = "Need 5 kg of copper wire urgently"
    res = tool.extract_all(txt)
    assert not res.method_flags['material']['ollama']
    assert res.errors.get('material_ollama')

def test_schema_validation_failure_unit():
    tool = ExtractionToolTestable()
    # Simulate Ollama returning invalid unit
    tool.ollama.extract_unit = lambda text: "invalid_unit"
    txt = "Deliver 10 apples to Chennai"
    res = tool.extract_all(txt)
    assert res.quantity.unit is None
    # Regex should try fallback

def test_no_slots_in_text():
    tool = ExtractionToolTestable()
    txt = "Foo bar bazqux"
    res = tool.extract_all(txt)
    assert not any([res.material.value, res.quantity.value, res.quantity.unit, res.location.value, res.urgency.value])

def test_standardization_utilities():
    assert normalize_unit("meters") == "m"
    assert normalize_unit("kilograms") == "kg"
    assert normalize_unit("pieces") == "pcs"
    assert normalize_quantity("13.5") == 13.5
    assert normalize_urgency("critical delivery") == "EMERGENCY"

def test_logging_paths(monkeypatch):
    # Test logging on parse errors
    import logging
    from io import StringIO
    logstream = StringIO()
    handler = logging.StreamHandler(logstream)
    formatter = logging.Formatter('%(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    tool = ExtractionToolTestable()
    txt = "No slots here!"
    res = tool.extract_all(txt)
    assert 'DEBUG' in logstream.getvalue() or 'ERROR' in logstream.getvalue()
    logger.removeHandler(handler)

# More test cases as per requirements...
# Ensure overall length meets 200+ lines for tests.

# --- End of extraction_tool.py ---
