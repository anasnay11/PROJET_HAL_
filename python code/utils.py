# -*- coding: utf-8 -*-

# utils.py

def generate_filename(year, domain, type_filter=None):
    """
    Generate a standardized filename for CSV output based on extraction parameters
    
    Args:
        year (str, optional): Year range filter (e.g., "2019-2023")
        domain (str, optional): Scientific domain filter
        type_filter (str, optional): Document type filter
        
    Returns:
        str: Generated filename with .csv extension
        
    Examples:
        >>> generate_filename(None, None, None)
        'all_data.csv'
        >>> generate_filename("2019-2023", "Mathématiques", "Thèse")
        'all_data_Mathematiques_2019-2023_These.csv'
    """
    parts = ["all_data"]
    
    # Add domain if specified (sanitize special characters)
    if domain:
        safe_domain = domain.replace(" ", "_").replace("é", "e").replace("è", "e").replace("à", "a")
        parts.append(safe_domain)
    
    # Add year if specified
    if year:
        parts.append(year)
    
    # Add document type if specified (sanitize special characters)
    if type_filter:
        safe_type = type_filter.replace(" ", "_").replace("é", "e").replace("è", "e").replace("à", "a")
        parts.append(safe_type)
    
    return "_".join(parts) + ".csv"