"""
MBTI Reference Data Validator

Validates extracted metadata against authoritative reference data from reference_data.json.
Provides auto-correction for common variations and comprehensive validation logging.

Author: InnerVerse Team
Created: 2025-11-08
"""

import json
import re
from typing import List, Dict, Set, Tuple, Optional


class ReferenceValidator:
    """Validates MBTI metadata against authoritative reference data"""
    
    def __init__(self, reference_data_path: str = 'src/data/reference_data.json'):
        """
        Initialize validator with reference data
        
        Args:
            reference_data_path: Path to reference_data.json
        """
        try:
            with open(reference_data_path, 'r') as f:
                raw_data = json.load(f)
                # Convert new structure (types array) to old structure (mbti_types dict) for backward compatibility
                if 'types' in raw_data and isinstance(raw_data['types'], list):
                    self.reference_data = {'mbti_types': {t['code']: t for t in raw_data['types']}}
                else:
                    self.reference_data = raw_data
            
            self._extract_valid_values()
            print(f"✅ [VALIDATOR] Loaded reference data: {len(self.valid_types)} types, "
                  f"{len(self.valid_function_codes)} function codes, "
                  f"{len(self.valid_quadras)} quadras")
            
        except FileNotFoundError:
            print(f"⚠️ [VALIDATOR] Reference data not found at {reference_data_path}")
            self.reference_data = {}
            self.valid_types = set()
            self.valid_functions = set()
            self.valid_function_codes = set()
            self.valid_temperaments = set()
            self.valid_quadras = set()
            self.valid_interaction_styles = set()
    
    def _extract_valid_values(self):
        """Extract all valid values from reference data"""
        mbti_types = self.reference_data.get('mbti_types', {})
        
        # Valid MBTI types (uppercase 4-letter codes)
        self.valid_types: Set[str] = set(mbti_types.keys())
        
        # Valid cognitive functions (full format and codes)
        self.valid_functions: Set[str] = set()
        self.valid_function_codes: Set[str] = set()
        
        for type_data in mbti_types.values():
            # Handle both old format (function_stack) and new format (four_sides.ego.functions)
            functions = type_data.get('function_stack', [])
            if not functions and 'four_sides' in type_data:
                ego_functions = type_data.get('four_sides', {}).get('ego', {}).get('functions', [])
                for func_obj in ego_functions:
                    if isinstance(func_obj, dict):
                        func_code = func_obj.get('function', '')
                        self.valid_function_codes.add(func_code)
            else:
                for func in functions:
                    self.valid_functions.add(func)
                    code = func.split(' - ')[0] if ' - ' in func else func
                    self.valid_function_codes.add(code)
        
        # Valid temperaments - handle both old and new format
        self.valid_temperaments: Set[str] = set()
        for type_data in mbti_types.values():
            temp = type_data.get('temperament') or type_data.get('categories', {}).get('temperament')
            if temp:
                self.valid_temperaments.add(temp)
        
        # Valid quadras - handle both old and new format
        self.valid_quadras: Set[str] = set()
        for type_data in mbti_types.values():
            quadra = type_data.get('quadra') or type_data.get('categories', {}).get('quadra')
            if quadra:
                self.valid_quadras.add(quadra)
        
        # Valid interaction styles - handle both old and new format
        self.valid_interaction_styles: Set[str] = set()
        for type_data in mbti_types.values():
            style = type_data.get('interaction_style') or type_data.get('categories', {}).get('interaction_style')
            if style:
                self.valid_interaction_styles.add(style)
    
    def validate_mbti_type(self, type_code: str) -> Tuple[Optional[str], str]:
        """
        Validate and normalize MBTI type code
        
        Args:
            type_code: Type code to validate (e.g., "INFJ", "infj", "INFJ-A")
            
        Returns:
            Tuple of (normalized_code, status_message)
            - normalized_code is None if invalid
            - status_message explains what happened
        """
        if not type_code or not isinstance(type_code, str):
            return None, "Empty or non-string type code"
        
        original = type_code
        
        # Normalize: uppercase and strip whitespace
        normalized = type_code.strip().upper()
        
        # Remove common suffixes (e.g., INFJ-A, INFJ-T from 16personalities)
        normalized = re.sub(r'-[AT]$', '', normalized)
        
        # Check if valid
        if normalized in self.valid_types:
            if normalized != original:
                return normalized, f"Auto-corrected '{original}' → '{normalized}'"
            return normalized, "Valid"
        
        # Try pattern matching for typos (must be 4 letters matching MBTI pattern)
        if re.match(r'^[IE][NS][FT][JP]$', normalized):
            return None, f"Invalid type '{normalized}' (matches pattern but not in valid set)"
        
        return None, f"Invalid type '{original}' (doesn't match MBTI format)"
    
    def validate_cognitive_function(self, function: str) -> Tuple[Optional[str], str]:
        """
        Validate cognitive function
        
        Args:
            function: Function to validate (e.g., "Ni", "Fe - Extraverted Feeling", "fe")
            
        Returns:
            Tuple of (normalized_function, status_message)
        """
        if not function or not isinstance(function, str):
            return None, "Empty or non-string function"
        
        original = function.strip()
        
        # Check full format first (e.g., "Ni - Introverted Intuition (Hero)")
        if original in self.valid_functions:
            return original, "Valid (full format)"
        
        # Check if it's just a code (e.g., "Ni", "Fe", "fe")
        code = original.split(' - ')[0].strip() if ' - ' in original else original
        
        # Check exact match first
        if code in self.valid_function_codes:
            if code != original:
                return code, f"Normalized to code '{code}'"
            return code, "Valid (code format)"
        
        # Try case-insensitive match (e.g., "fe" → "Fe", "NI" → "Ni")
        for valid_code in self.valid_function_codes:
            if valid_code.lower() == code.lower():
                return valid_code, f"Auto-corrected case: '{code}' → '{valid_code}'"
        
        return None, f"Invalid function '{original}'"
    
    def validate_temperament(self, temperament: str) -> Tuple[Optional[str], str]:
        """Validate temperament"""
        if not temperament or not isinstance(temperament, str):
            return None, "Empty or non-string temperament"
        
        normalized = temperament.strip()
        
        if normalized in self.valid_temperaments:
            return normalized, "Valid"
        
        # Try case-insensitive match
        for valid in self.valid_temperaments:
            if valid.lower() == normalized.lower():
                return valid, f"Auto-corrected case: '{normalized}' → '{valid}'"
        
        return None, f"Invalid temperament '{normalized}'"
    
    def validate_quadra(self, quadra: str) -> Tuple[Optional[str], str]:
        """Validate quadra"""
        if not quadra or not isinstance(quadra, str):
            return None, "Empty or non-string quadra"
        
        normalized = quadra.strip()
        
        if normalized in self.valid_quadras:
            return normalized, "Valid"
        
        # Try case-insensitive match
        for valid in self.valid_quadras:
            if valid.lower() == normalized.lower():
                return valid, f"Auto-corrected case: '{normalized}' → '{valid}'"
        
        return None, f"Invalid quadra '{normalized}'"
    
    def validate_interaction_style(self, style: str) -> Tuple[Optional[str], str]:
        """Validate interaction style"""
        if not style or not isinstance(style, str):
            return None, "Empty or non-string interaction style"
        
        normalized = style.strip()
        
        if normalized in self.valid_interaction_styles:
            return normalized, "Valid"
        
        # Try case-insensitive match
        for valid in self.valid_interaction_styles:
            if valid.lower() == normalized.lower():
                return valid, f"Auto-corrected case: '{normalized}' → '{valid}'"
        
        return None, f"Invalid interaction style '{normalized}'"
    
    def validate_types_list(self, types_list: List[str]) -> Tuple[List[str], Dict[str, str]]:
        """
        Validate list of MBTI types
        
        Args:
            types_list: List of type codes to validate
            
        Returns:
            Tuple of (valid_types, validation_log)
            - valid_types: List of validated type codes
            - validation_log: Dict mapping original → status message
        """
        if not isinstance(types_list, list):
            return [], {"error": "Input is not a list"}
        
        valid_types = []
        validation_log = {}
        
        for type_code in types_list:
            validated, message = self.validate_mbti_type(type_code)
            
            if validated:
                valid_types.append(validated)
                validation_log[type_code] = message
            else:
                validation_log[type_code] = f"❌ {message}"
        
        return valid_types, validation_log
    
    def validate_functions_list(self, functions_list: List[str]) -> Tuple[List[str], Dict[str, str]]:
        """
        Validate list of cognitive functions
        
        Args:
            functions_list: List of functions to validate
            
        Returns:
            Tuple of (valid_functions, validation_log)
        """
        if not isinstance(functions_list, list):
            return [], {"error": "Input is not a list"}
        
        valid_functions = []
        validation_log = {}
        
        for function in functions_list:
            validated, message = self.validate_cognitive_function(function)
            
            if validated:
                valid_functions.append(validated)
                validation_log[function] = message
            else:
                validation_log[function] = f"❌ {message}"
        
        return valid_functions, validation_log
    
    def validate_structured_metadata(self, metadata: Dict) -> Tuple[Dict, Dict]:
        """
        Validate complete structured metadata from auto-tagging
        
        Args:
            metadata: Structured metadata dict from GPT
            
        Returns:
            Tuple of (validated_metadata, validation_report)
            - validated_metadata: Cleaned metadata with only valid values
            - validation_report: Detailed validation log
        """
        validated = {}
        report = {}
        
        # Validate types_discussed
        if 'types_discussed' in metadata:
            valid_types, type_log = self.validate_types_list(metadata['types_discussed'])
            validated['types_discussed'] = valid_types
            report['types_discussed'] = type_log
        
        # Validate functions_covered
        if 'functions_covered' in metadata:
            valid_funcs, func_log = self.validate_functions_list(metadata['functions_covered'])
            validated['functions_covered'] = valid_funcs
            report['functions_covered'] = func_log
        
        # Validate quadra
        if 'quadra' in metadata:
            valid_quadra, quadra_msg = self.validate_quadra(metadata['quadra'])
            if valid_quadra:
                validated['quadra'] = valid_quadra
                report['quadra'] = quadra_msg
            else:
                validated['quadra'] = 'none'
                report['quadra'] = f"❌ {quadra_msg} - defaulting to 'none'"
        
        # Validate temperament
        if 'temperament' in metadata:
            valid_temp, temp_msg = self.validate_temperament(metadata['temperament'])
            if valid_temp:
                validated['temperament'] = valid_temp
                report['temperament'] = temp_msg
            else:
                validated['temperament'] = 'none'
                report['temperament'] = f"❌ {temp_msg} - defaulting to 'none'"
        
        # Validate interaction_style
        if 'interaction_style' in metadata:
            valid_style, style_msg = self.validate_interaction_style(metadata['interaction_style'])
            if valid_style:
                validated['interaction_style'] = valid_style
                report['interaction_style'] = style_msg
            else:
                validated['interaction_style'] = 'none'
                report['interaction_style'] = f"❌ {style_msg} - defaulting to 'none'"
        
        # Pass through non-validated fields (including ENTERPRISE V2 fields)
        # These fields don't need validation against reference data - they're context-specific
        for key in [
            # Original fields
            'content_type', 'difficulty', 'primary_category', 'relationship_type', 
            'temple', 'topics', 'use_case',
            # ENTERPRISE V2 FIELDS (Added 2025-11-27 - Bug Fix)
            'octagram_states',           # CS Joseph octagram framework
            'archetypes',                # Paladin, Gladiator, Bard, etc.
            'key_concepts',              # Semantic concepts for RAG search
            'pair_dynamics',             # Golden pair, Pedagogue, etc.
            'function_positions',        # Ni_hero, Te_parent, etc.
            'interaction_style_details', # Get things going, In charge, etc.
            'teaching_focus',            # Theoretical, practical, case_study
            'prerequisite_knowledge',    # Prerequisites for understanding
            'target_audience',           # Beginner, intermediate, advanced
            'season_number',             # Season number from filename
            'episode_number',            # Episode number from filename
            'tag_confidence',            # Confidence score for auto-tagging
            'content_density'            # Content density metric
        ]:
            if key in metadata:
                validated[key] = metadata[key]
        
        return validated, report
    
    def get_reference_summary(self) -> Dict:
        """Get summary of valid reference values for prompt injection"""
        return {
            "valid_types": sorted(list(self.valid_types)),
            "valid_function_codes": sorted(list(self.valid_function_codes)),
            "valid_temperaments": sorted(list(self.valid_temperaments)),
            "valid_quadras": sorted(list(self.valid_quadras)),
            "valid_interaction_styles": sorted(list(self.valid_interaction_styles))
        }


# Global validator instance (loaded once at module level)
try:
    VALIDATOR = ReferenceValidator()
except Exception as e:
    print(f"⚠️ [VALIDATOR] Failed to initialize: {e}")
    VALIDATOR = None
