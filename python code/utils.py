# -*- coding: utf-8 -*-
"""
Created on Mon Dec  2 16:44:16 2024


"""

# utils.py

def generate_filename(year, domain, type_filter=None):
    parts = ["all_data"]
    if domain:
        safe_domain = domain.replace(" ", "_").replace("é", "e").replace("è", "e").replace("à", "a")
        parts.append(safe_domain)
    if year:
        parts.append(year)
    if type_filter:
        safe_type = type_filter.replace(" ", "_").replace("é", "e").replace("è", "e").replace("à", "a")
        parts.append(safe_type)
    return "_".join(parts) + ".csv"

