# config.py 

# -*- coding: utf-8 -*-

# Dictionary of predefined sensitivity levels
SENSITIVITY_LEVELS = {
    "très strict": 0,
    "strict": 1, 
    "modéré": 2,
    "permissif": 3,
    "très permissif": 4
}

# Default threshold
DEFAULT_THRESHOLD = 2

def get_threshold_from_level(level):
    """
    Convert a textual level to numerical value
    
    Args:
        level (str): Textual sensitivity level
        
    Returns:
        int: Corresponding threshold value
    """
    return SENSITIVITY_LEVELS.get(level.lower(), DEFAULT_THRESHOLD)

def get_level_from_threshold(threshold):
    """
    Convert a numerical value to textual level
    
    Args:
        threshold (int): Threshold value
        
    Returns:
        str: Corresponding sensitivity level
    """
    for level, value in SENSITIVITY_LEVELS.items():
        if value == threshold:
            return level
    return "personnalisé"

def list_sensitivity_levels():
    """
    Return the list of available levels with their descriptions
    
    Returns:
        dict: Dictionary of levels with descriptions
    """
    descriptions = {
        "très strict": "Distance = 0 (correspondance exacte uniquement)",
        "strict": "Distance = 1 (1 caractère de différence maximum)", 
        "modéré": "Distance = 2 (2 caractères de différence maximum) - Par défaut",
        "permissif": "Distance = 3 (3 caractères de différence maximum)",
        "très permissif": "Distance = 4 (4 caractères de différence maximum)"
    }
    return descriptions