"""
Four Sides Canonical Mapping
=============================
Maps all 16 MBTI types to their Ego, Subconscious, Unconscious, and Superego (Shadow).
Based on CS Joseph's MBTI framework.

Usage:
    from src.services.four_sides_map import get_four_sides, FOUR_SIDES_MAP
    
    sides = get_four_sides("ENFP")
    # Returns: {"ego": "ENFP", "subconscious": "ISTJ", "unconscious": "INFJ", "superego": "ESTP"}
"""

FOUR_SIDES_MAP = {
    "ENFP": {
        "ego": "ENFP",
        "subconscious": "ISTJ",
        "unconscious": "INFJ",
        "superego": "ESTP",
        "functions": {
            "ego": ["Ne", "Fi", "Te", "Si"],
            "subconscious": ["Si", "Te", "Fi", "Ne"],
            "unconscious": ["Ni", "Fe", "Ti", "Se"],
            "superego": ["Se", "Ti", "Fe", "Ni"]
        }
    },
    "INFJ": {
        "ego": "INFJ",
        "subconscious": "ESTP",
        "unconscious": "ENFP",
        "superego": "ISTJ",
        "functions": {
            "ego": ["Ni", "Fe", "Ti", "Se"],
            "subconscious": ["Se", "Ti", "Fe", "Ni"],
            "unconscious": ["Ne", "Fi", "Te", "Si"],
            "superego": ["Si", "Te", "Fi", "Ne"]
        }
    },
    "ISTJ": {
        "ego": "ISTJ",
        "subconscious": "ENFP",
        "unconscious": "ESTP",
        "superego": "INFJ",
        "functions": {
            "ego": ["Si", "Te", "Fi", "Ne"],
            "subconscious": ["Ne", "Fi", "Te", "Si"],
            "unconscious": ["Se", "Ti", "Fe", "Ni"],
            "superego": ["Ni", "Fe", "Ti", "Se"]
        }
    },
    "ESTP": {
        "ego": "ESTP",
        "subconscious": "INFJ",
        "unconscious": "ISTJ",
        "superego": "ENFP",
        "functions": {
            "ego": ["Se", "Ti", "Fe", "Ni"],
            "subconscious": ["Ni", "Fe", "Ti", "Se"],
            "unconscious": ["Si", "Te", "Fi", "Ne"],
            "superego": ["Ne", "Fi", "Te", "Si"]
        }
    },
    "INTJ": {
        "ego": "INTJ",
        "subconscious": "ESFP",
        "unconscious": "ISTP",
        "superego": "ENFJ",
        "functions": {
            "ego": ["Ni", "Te", "Fi", "Se"],
            "subconscious": ["Se", "Fi", "Te", "Ni"],
            "unconscious": ["Ti", "Se", "Ni", "Fe"],
            "superego": ["Fe", "Ni", "Se", "Ti"]
        }
    },
    "ESFP": {
        "ego": "ESFP",
        "subconscious": "INTJ",
        "unconscious": "ENFJ",
        "superego": "ISTP",
        "functions": {
            "ego": ["Se", "Fi", "Te", "Ni"],
            "subconscious": ["Ni", "Te", "Fi", "Se"],
            "unconscious": ["Fe", "Ni", "Se", "Ti"],
            "superego": ["Ti", "Se", "Ni", "Fe"]
        }
    },
    "ISTP": {
        "ego": "ISTP",
        "subconscious": "ENFJ",
        "unconscious": "INTJ",
        "superego": "ESFP",
        "functions": {
            "ego": ["Ti", "Se", "Ni", "Fe"],
            "subconscious": ["Fe", "Ni", "Se", "Ti"],
            "unconscious": ["Ni", "Te", "Fi", "Se"],
            "superego": ["Se", "Fi", "Te", "Ni"]
        }
    },
    "ENFJ": {
        "ego": "ENFJ",
        "subconscious": "ISTP",
        "unconscious": "ESFP",
        "superego": "INTJ",
        "functions": {
            "ego": ["Fe", "Ni", "Se", "Ti"],
            "subconscious": ["Ti", "Se", "Ni", "Fe"],
            "unconscious": ["Se", "Fi", "Te", "Ni"],
            "superego": ["Ni", "Te", "Fi", "Se"]
        }
    },
    "ENTP": {
        "ego": "ENTP",
        "subconscious": "ISFJ",
        "unconscious": "INTP",
        "superego": "ESFJ",
        "functions": {
            "ego": ["Ne", "Ti", "Fe", "Si"],
            "subconscious": ["Si", "Fe", "Ti", "Ne"],
            "unconscious": ["Ti", "Ne", "Si", "Fe"],
            "superego": ["Fe", "Si", "Ne", "Ti"]
        }
    },
    "ISFJ": {
        "ego": "ISFJ",
        "subconscious": "ENTP",
        "unconscious": "ESFJ",
        "superego": "INTP",
        "functions": {
            "ego": ["Si", "Fe", "Ti", "Ne"],
            "subconscious": ["Ne", "Ti", "Fe", "Si"],
            "unconscious": ["Fe", "Si", "Ne", "Ti"],
            "superego": ["Ti", "Ne", "Si", "Fe"]
        }
    },
    "INTP": {
        "ego": "INTP",
        "subconscious": "ESFJ",
        "unconscious": "ENTP",
        "superego": "ISFJ",
        "functions": {
            "ego": ["Ti", "Ne", "Si", "Fe"],
            "subconscious": ["Fe", "Si", "Ne", "Ti"],
            "unconscious": ["Ne", "Ti", "Fe", "Si"],
            "superego": ["Si", "Fe", "Ti", "Ne"]
        }
    },
    "ESFJ": {
        "ego": "ESFJ",
        "subconscious": "INTP",
        "unconscious": "ISFJ",
        "superego": "ENTP",
        "functions": {
            "ego": ["Fe", "Si", "Ne", "Ti"],
            "subconscious": ["Ti", "Ne", "Si", "Fe"],
            "unconscious": ["Si", "Fe", "Ti", "Ne"],
            "superego": ["Ne", "Ti", "Fe", "Si"]
        }
    },
    "ENTJ": {
        "ego": "ENTJ",
        "subconscious": "ISFP",
        "unconscious": "ESTJ",
        "superego": "INFP",
        "functions": {
            "ego": ["Te", "Ni", "Se", "Fi"],
            "subconscious": ["Fi", "Se", "Ni", "Te"],
            "unconscious": ["Te", "Si", "Ne", "Fi"],
            "superego": ["Fi", "Ne", "Si", "Te"]
        }
    },
    "ISFP": {
        "ego": "ISFP",
        "subconscious": "ENTJ",
        "unconscious": "INFP",
        "superego": "ESTJ",
        "functions": {
            "ego": ["Fi", "Se", "Ni", "Te"],
            "subconscious": ["Te", "Ni", "Se", "Fi"],
            "unconscious": ["Fi", "Ne", "Si", "Te"],
            "superego": ["Te", "Si", "Ne", "Fi"]
        }
    },
    "ESTJ": {
        "ego": "ESTJ",
        "subconscious": "INFP",
        "unconscious": "ENTJ",
        "superego": "ISFP",
        "functions": {
            "ego": ["Te", "Si", "Ne", "Fi"],
            "subconscious": ["Fi", "Ne", "Si", "Te"],
            "unconscious": ["Te", "Ni", "Se", "Fi"],
            "superego": ["Fi", "Se", "Ni", "Te"]
        }
    },
    "INFP": {
        "ego": "INFP",
        "subconscious": "ESTJ",
        "unconscious": "ISFP",
        "superego": "ENTJ",
        "functions": {
            "ego": ["Fi", "Ne", "Si", "Te"],
            "subconscious": ["Te", "Si", "Ne", "Fi"],
            "unconscious": ["Fi", "Se", "Ni", "Te"],
            "superego": ["Te", "Ni", "Se", "Fi"]
        }
    }
}


def get_four_sides(mbti_type: str) -> dict:
    """
    Get the four sides for a given MBTI type.
    
    Args:
        mbti_type: 4-letter MBTI type (e.g., "ENFP", "INTJ")
        
    Returns:
        Dictionary with ego, subconscious, unconscious, superego types and functions
        Returns None if type not found
        
    Example:
        >>> sides = get_four_sides("ENFP")
        >>> print(sides["subconscious"])
        "ISTJ"
    """
    mbti_type = mbti_type.upper().strip()
    return FOUR_SIDES_MAP.get(mbti_type)


def get_all_types() -> list:
    """Get list of all 16 MBTI types."""
    return list(FOUR_SIDES_MAP.keys())


def validate_type(mbti_type: str) -> bool:
    """Check if a string is a valid MBTI type."""
    return mbti_type.upper().strip() in FOUR_SIDES_MAP
