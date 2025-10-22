# -*- coding: utf-8 -*-

# hal_data.py

import requests
import pandas as pd
from Levenshtein import distance as levenshtein_distance
from mapping import map_doc_type, map_domain, get_domain_code, get_type_code, get_linked_types, get_hal_filter_for_post_processing
from config import DEFAULT_THRESHOLD

def is_same_author_levenshtein(title_csv, title_hal, threshold=DEFAULT_THRESHOLD):
    """
    Compare a CSV title with a title found in HAL.
    Also supports a fallback comparison using 'nom prenom' format for backward compatibility.
    
    Args:
        title_csv (str): Title or author name from the CSV file.
        title_hal (str): Title or author name found in HAL results.
        threshold (int): Acceptable Levenshtein distance threshold for similarity.
    
    Returns:
        bool: True if the two titles or names are considered similar enough.
    """
    # If one of the inputs is missing, no comparison can be made
    if not title_hal or not title_csv:
        return False 
    
    # Normalize both strings (lowercase, remove leading/trailing spaces)
    title_csv_clean = title_csv.lower().strip()
    title_hal_clean = title_hal.lower().strip()
    
    # Compute direct Levenshtein distance between both strings
    dist_direct = levenshtein_distance(title_csv_clean, title_hal_clean)
    
    # If direct match is within threshold, consider them as the same
    if dist_direct <= threshold:
        return True
    
    # Split strings into individual parts (for multi-word titles or names)
    csv_parts = title_csv_clean.split()
    hal_parts = title_hal_clean.split()
    
    # If both contain at least two words, perform name-based comparison
    if len(csv_parts) >= 2 and len(hal_parts) >= 2:
        # Separate first and last names for normal order
        csv_first = csv_parts[0]
        csv_last = " ".join(csv_parts[1:])
        hal_first = hal_parts[0]
        hal_last = " ".join(hal_parts[1:])
        
        # Compute distances for normal order (first name - last name)
        dist_first_normal = levenshtein_distance(csv_first, hal_first)
        dist_last_normal = levenshtein_distance(csv_last, hal_last)
        
        # Also check the inverted order (last name - first name)
        hal_first_inv = hal_parts[-1]
        hal_last_inv = " ".join(hal_parts[:-1])
        
        dist_first_inverted = levenshtein_distance(csv_first, hal_first_inv)
        dist_last_inverted = levenshtein_distance(csv_last, hal_last_inv)
        
        # Determine if either normal or inverted orders are within threshold
        normal_match = (dist_first_normal <= threshold and dist_last_normal <= threshold)
        inverted_match = (dist_first_inverted <= threshold and dist_last_inverted <= threshold)
        
        # Return True if either matching strategy succeeds
        return normal_match or inverted_match
    
    # If none of the above conditions matched, return False
    return False

def extract_author_id_with_candidates(title, nom=None, prenom=None, threshold=2):
    """
    Extract a HAL author ID using multiple query and matching strategies.
    
    Args:
        title (str): Full name or title from the CSV file
        nom (str): Last name (fallback)
        prenom (str): First name (fallback)  
        threshold (int): Maximum acceptable Levenshtein distance
    
    Returns:
        dict: {
            'IdHAL': str,              # Best candidate (or ' ' if no results)
            'Candidats': str,          # Comma-separated list of alternative candidates
            'ID_Atypique': str,        # OUI or NON (does not resemble name)
            'Details': str             # JSON string for debugging information
        }
    """
    
    # If no title is provided, fall back to using first and last name
    if not title or not title.strip():
        if nom and prenom:
            title = f"{prenom} {nom}"
        else:
            return {
                'IdHAL': ' ',
                'Candidats': '',
                'ID_Atypique': 'NON',
                'Details': '{}'
            }
    
    title_clean = title.strip()
    
    # Handle cases with duplicate names (e.g., "Dupont Dupont")
    title_parts = title_clean.lower().split()
    is_duplicate_name = (len(title_parts) == 2 and title_parts[0] == title_parts[1])
    
    # Dictionaries for counting occurrences and storing candidate details
    all_candidates_count = {}     # {id: count}
    all_candidates_details = {}   # {id: {'strategy': int, 'hal_full': str}}
    
    # ===== DUPLICATE NAME HANDLING =====
    if is_duplicate_name:
        threshold = min(threshold, 1)
        
        prenom_part = title_parts[0]
        nom_part = title_parts[1]
        query_url = f'https://api.archives-ouvertes.fr/search/?q=authFirstName_s:"{prenom_part}" AND authLastName_s:"{nom_part}"&fl=authIdHal_s,authFirstName_s,authLastName_s,authFullName_s&wt=json&rows=50'
        
        try:
            response = requests.get(query_url)
            if response.status_code == 200:
                data = response.json()
                publications = data.get("response", {}).get("docs", [])
                
                for pub in publications:
                    auth_ids = pub.get("authIdHal_s", [])
                    auth_first_names = pub.get("authFirstName_s", [])
                    auth_last_names = pub.get("authLastName_s", [])
                    auth_full_names = pub.get("authFullName_s", [])
                    
                    if len(auth_ids) == len(auth_first_names) == len(auth_last_names):
                        for i, auth_id in enumerate(auth_ids):
                            if auth_id and not auth_id.lower().startswith("hal"):
                                hal_first = auth_first_names[i] if i < len(auth_first_names) else ""
                                hal_last = auth_last_names[i] if i < len(auth_last_names) else ""
                                hal_full = auth_full_names[i] if i < len(auth_full_names) else ""
                                
                                first_match = levenshtein_distance(prenom_part, hal_first.lower()) <= threshold
                                last_match = levenshtein_distance(nom_part, hal_last.lower()) <= threshold
                                
                                expected_full_name = f"{prenom_part} {nom_part}".lower()
                                full_name_match = False
                                if hal_full:
                                    full_name_match = levenshtein_distance(expected_full_name, hal_full.lower()) <= threshold
                                
                                if first_match and last_match and (full_name_match or not hal_full):
                                    all_candidates_count[auth_id] = all_candidates_count.get(auth_id, 0) + 1
                                    if auth_id not in all_candidates_details:
                                        all_candidates_details[auth_id] = {
                                            'strategy': 0,
                                            'hal_full': hal_full
                                        }
        except Exception:
            pass
    
    # ===== STANDARD SEARCH STRATEGIES =====
    if is_duplicate_name:
        query_strategies = [
            f'https://api.archives-ouvertes.fr/search/?q=authFullName_s:"{title_clean}"&fl=authIdHal_s,authFirstName_s,authLastName_s,authFullName_s&wt=json&rows=100',
            f'https://api.archives-ouvertes.fr/search/?q=authFullName_t:"{title_clean}"&fl=authIdHal_s,authFirstName_s,authLastName_s,authFullName_s&wt=json&rows=100'
        ]
    else:
        query_strategies = [
            f'https://api.archives-ouvertes.fr/search/?q=authFullName_s:"{title_clean}"&fl=authIdHal_s,authFirstName_s,authLastName_s,authFullName_s&wt=json&rows=100',
            f'https://api.archives-ouvertes.fr/search/?q=authFullName_t:"{title_clean}"&fl=authIdHal_s,authFirstName_s,authLastName_s,authFullName_s&wt=json&rows=100',
            f'https://api.archives-ouvertes.fr/search/?q=text:"{title_clean}"&fl=authIdHal_s,authFirstName_s,authLastName_s,authFullName_s&wt=json&rows=100'
        ]
    
    for strategy_index, query_url in enumerate(query_strategies):
        try:
            response = requests.get(query_url)
            if response.status_code != 200:
                continue
            
            data = response.json()
            publications = data.get("response", {}).get("docs", [])
            
            if not publications:
                continue
            
            for pub in publications:
                auth_ids = pub.get("authIdHal_s", [])
                auth_first_names = pub.get("authFirstName_s", [])
                auth_last_names = pub.get("authLastName_s", [])
                auth_full_names = pub.get("authFullName_s", [])
                
                if len(auth_ids) == len(auth_first_names) == len(auth_last_names):
                    for i, auth_id in enumerate(auth_ids):
                        if auth_id and not auth_id.lower().startswith("hal"):
                            hal_first_name = auth_first_names[i] if i < len(auth_first_names) else ""
                            hal_last_name = auth_last_names[i] if i < len(auth_last_names) else ""
                            hal_full_name = auth_full_names[i] if i < len(auth_full_names) else ""
                            
                            title_match = is_same_author_levenshtein(title_clean, hal_full_name, threshold)
                            
                            name_match = False
                            if not title_match and nom and prenom:
                                name_match = is_same_author_levenshtein(f"{prenom} {nom}", hal_full_name, threshold)
                            
                            if title_match or name_match:
                                all_candidates_count[auth_id] = all_candidates_count.get(auth_id, 0) + 1
                                if auth_id not in all_candidates_details:
                                    all_candidates_details[auth_id] = {
                                        'strategy': strategy_index + 1,
                                        'hal_full': hal_full_name
                                    }
            
            # Early exit if candidates found
            if all_candidates_count:
                if is_duplicate_name and strategy_index < 1:
                    break
                elif not is_duplicate_name and strategy_index < 2:
                    break
                    
        except Exception:
            continue
    
    # ===== FALLBACK METHOD (for regular names only) =====
    if not all_candidates_count and not is_duplicate_name:
        title_words = title_clean.lower().split()
        if len(title_words) >= 2:
            potential_prenom = title_words[0]
            potential_nom = " ".join(title_words[1:])
        elif nom and prenom:
            potential_prenom = prenom.lower()
            potential_nom = nom.lower()
        else:
            return {
                'IdHAL': ' ',
                'Candidats': '',
                'ID_Atypique': 'NON',
                'Details': '{}'
            }
        
        query_urls = [
            f'https://api.archives-ouvertes.fr/search/?q=authFullName_t:"{potential_prenom} {potential_nom}"&fl=authIdHal_s&wt=json&rows=100',
            f'https://api.archives-ouvertes.fr/search/?q=authFullName_t:"{potential_nom} {potential_prenom}"&fl=authIdHal_s&wt=json&rows=100'
        ]
        
        all_author_ids = set()
        
        for query_url in query_urls:
            try:
                response = requests.get(query_url)
                if response.status_code != 200:
                    continue
                
                data = response.json()
                publications = data.get("response", {}).get("docs", [])
                
                for pub in publications:
                    auth_ids = pub.get("authIdHal_s", [])
                    for auth_id in auth_ids:
                        if auth_id and not auth_id.lower().startswith("hal"):
                            all_author_ids.add(auth_id)
            except Exception:
                continue
        
        if all_author_ids:
            # Create name variants for flexible matching
            def create_variants(text):
                variants = set()
                text_clean = text.strip().lower()
                variants.add(text_clean)
                variants.add(text_clean.replace('-', ''))
                variants.add(text_clean.replace(' ', '-'))
                variants.add(text_clean.replace(' ', ''))
                
                if ' ' in text_clean:
                    words = text_clean.split()
                    variants.add('-'.join(words))
                    variants.add(''.join(words))
                    for word in words:
                        if len(word) > 1:
                            variants.add(word)
                
                if '-' in text_clean:
                    words = text_clean.split('-')
                    for word in words:
                        if len(word) > 1:
                            variants.add(word)
                
                return variants
            
            nom_variants = create_variants(potential_nom)
            prenom_variants = create_variants(potential_prenom)
            
            # Validate author IDs against name variants
            for auth_id in all_author_ids:
                if _validate_id_with_variants(auth_id, prenom_variants, nom_variants, threshold):
                    all_candidates_count[auth_id] = all_candidates_count.get(auth_id, 0) + 1
                    if auth_id not in all_candidates_details:
                        all_candidates_details[auth_id] = {
                            'strategy': 99,
                            'hal_full': ''
                        }
    
    # ===== RESULT ANALYSIS =====
    if not all_candidates_count:
        return {
            'IdHAL': ' ',
            'Candidats': '',
            'ID_Atypique': 'NON',
            'Details': '{}'
        }
    
    # Sort candidates by occurrence count (descending) then by strategy
    sorted_candidates = sorted(
        all_candidates_count.items(),
        key=lambda x: (x[1], -all_candidates_details[x[0]]['strategy']),
        reverse=True
    )
    
    # Best candidate
    best_id = sorted_candidates[0][0]
    best_count = sorted_candidates[0][1]
    
    # Other top candidates (up to 5)
    other_candidates = [cand[0] for cand in sorted_candidates[1:6] if cand[0] != best_id]
    candidats_str = ', '.join(other_candidates) if other_candidates else ''
    
    # Check if the best ID is atypical (does not resemble the name)
    id_atypique = _is_atypical_id(best_id, prenom or title_parts[0], nom or title_parts[-1])
    
    # Build JSON string for debug details
    import json
    details_dict = {
        'count': best_count,
        'total_candidates': len(all_candidates_count),
        'strategy': all_candidates_details[best_id]['strategy'],
        'all_counts': dict(sorted_candidates[:10])
    }
    details_str = json.dumps(details_dict, ensure_ascii=False)
    
    return {
        'IdHAL': best_id,
        'Candidats': candidats_str,
        'ID_Atypique': 'OUI' if id_atypique else 'NON',
        'Details': details_str
    }

def _validate_id_with_variants(auth_id, prenom_variants, nom_variants, threshold):
    """Validate an ID against possible name variants"""
    if not auth_id:
        return False
    
    auth_id_lower = auth_id.lower()
    parts = auth_id_lower.split('-')
    
    # Test individual parts
    for i in range(len(parts)):
        for j in range(i + 1, len(parts)):
            part1 = parts[i]
            part2 = parts[j]
            
            for prenom_var in prenom_variants:
                for nom_var in nom_variants:
                    if (levenshtein_distance(prenom_var, part1) <= threshold and 
                        levenshtein_distance(nom_var, part2) <= threshold):
                        return True
                    if (levenshtein_distance(nom_var, part1) <= threshold and 
                        levenshtein_distance(prenom_var, part2) <= threshold):
                        return True
    
    # Test combined parts
    for split_point in range(1, len(parts)):
        first_part = ''.join(parts[:split_point])
        second_part = ''.join(parts[split_point:])
        
        for prenom_var in prenom_variants:
            for nom_var in nom_variants:
                if (levenshtein_distance(prenom_var, first_part) <= threshold and 
                    levenshtein_distance(nom_var, second_part) <= threshold):
                    return True
                if (levenshtein_distance(nom_var, first_part) <= threshold and 
                    levenshtein_distance(prenom_var, second_part) <= threshold):
                    return True
    
    # Test partial name match
    for nom_var in nom_variants:
        if len(nom_var) >= 3 and nom_var in auth_id_lower:
            return True
    
    return False

def _is_atypical_id(auth_id, prenom, nom):
    """
    Determines whether an ID is atypical (does not resemble the name or surname).
    
    Improved version that handles:
    - Standard formats: first-last, last-first
    - Compound first names: jean-luc-ray
    - Variations: initials, compact forms
    
    Args:
        auth_id (str): The HAL author identifier to check
        prenom (str): Author's first name
        nom (str): Author's last name
    
    Returns:
        bool: True if the ID does NOT match ANY recognized pattern (i.e., is atypical)
    """
    if not auth_id or not prenom or not nom:
        return False
    
    auth_id_lower = auth_id.lower()
    prenom_lower = prenom.lower().replace(' ', '-').replace("'", '')
    nom_lower = nom.lower().replace(' ', '-').replace("'", '')
    
    # Clean multiple hyphens
    prenom_clean = prenom_lower.replace('-', '')
    nom_clean = nom_lower.replace('-', '')
    
    # === PATTERN 1: Standard format first-last (hyphens preserved) ===
    expected_format_1 = f"{prenom_lower}-{nom_lower}"
    expected_format_2 = f"{nom_lower}-{prenom_lower}"
    
    if auth_id_lower == expected_format_1 or auth_id_lower == expected_format_2:
        return False  # Standard format, not atypical
    
    # === PATTERN 2: Compact format (without hyphens) ===
    auth_id_compact = auth_id_lower.replace('-', '')
    expected_compact_1 = f"{prenom_clean}{nom_clean}"
    expected_compact_2 = f"{nom_clean}{prenom_clean}"
    
    if auth_id_compact == expected_compact_1 or auth_id_compact == expected_compact_2:
        return False
    
    # === PATTERN 3: Substantial presence of the surname ===
    # At least 4 characters from the surname appear in the ID
    if len(nom_clean) >= 4 and nom_clean[:4] in auth_id_lower:
        return False
    
    # === PATTERN 4: Substantial presence of the first name ===
    # At least 3 characters from the first name appear in the ID
    if len(prenom_clean) >= 3 and prenom_clean[:3] in auth_id_lower:
        return False
    
    # === PATTERN 5: Initial-lastname format ===
    # Example: j-ray, jray
    if len(prenom_clean) > 0:
        initial_format_1 = f"{prenom_clean[0]}-{nom_lower}"
        initial_format_2 = f"{prenom_clean[0]}{nom_clean}"
        
        if auth_id_lower == initial_format_1 or auth_id_compact == initial_format_2:
            return False
    
    # === PATTERN 6: Initials ===
    if len(prenom_clean) > 0 and len(nom_clean) > 0:
        initials = prenom_clean[0] + nom_clean[0]
        if initials in auth_id_lower and len(auth_id_lower) <= 4:
            return False
    
    # === PATTERN 7: Parts of a compound first name ===
    if '-' in prenom_lower:
        prenom_parts = prenom_lower.split('-')
        for part in prenom_parts:
            if len(part) >= 3:
                part_nom_format = f"{part}-{nom_lower}"
                if auth_id_lower == part_nom_format:
                    return False
    
    # If no pattern matches, the ID is likely atypical
    return True

def execute_hal_query_multi_api(query_base, filters=""):
    """
    Execute a HAL query across both the main HAL API and the HAL-TEL API.
    
    This function ensures comprehensive coverage of publications by querying
    both APIs and merging the results without duplicates.
    
    Args:
        query_base (str): Base query string (without the API endpoint).
        filters (str): Additional filters or field selectors to append.
    
    Returns:
        tuple: (all_publications, seen_docids)
            - all_publications (list): Combined list of publications from both APIs.
            - seen_docids (set): Set of unique document IDs used to prevent duplicates.
    """
    
    # Define both API endpoints to query
    base_apis = [
        'https://api.archives-ouvertes.fr/search/',
        'https://api.archives-ouvertes.fr/search/tel/'
    ]
    
    all_publications = []
    seen_docids = set()
    
    # === STEP 1: Iterate through both APIs ===
    for base_api in base_apis:
        query_url = base_api + query_base + filters  # Construct full query URL
        
        try:
            # Send the GET request to the API
            response = requests.get(query_url)
            
            # Skip this API if the request fails
            if response.status_code != 200:
                continue
            
            # Parse JSON response
            data = response.json()
            publications = data.get("response", {}).get("docs", [])
            
            # === STEP 2: Iterate over publications and remove duplicates ===
            for pub in publications:
                docid = pub.get("docid", "")
                
                # Skip if this publication has already been processed
                if docid not in seen_docids:
                    # Tag the publication with its API source for traceability
                    pub['_api_source'] = 'HAL-TEL' if 'tel' in base_api else 'HAL'
                    
                    # Add to final list and mark the docid as seen
                    all_publications.append(pub)
                    seen_docids.add(docid)
        
        except Exception as e:
            # In case of network error, JSON parsing error, etc.
            # We simply skip the current API and continue
            continue
    
    # === STEP 3: Return the combined and deduplicated results ===
    return all_publications, seen_docids


def get_hal_data(nom, prenom, title=None, author_id=None, period=None, domain_filter=None, type_filter=None, threshold=DEFAULT_THRESHOLD):
    """
    Retrieve HAL publications for an author using HAL identifier (primary method) or full name (fallback).
    Searches both HAL and HAL-TEL APIs transparently.
    
    Args:
        nom (str): Last name of the author
        prenom (str): First name of the author
        title (str): Full name from CSV (used for fallback search)
        author_id (str): HAL identifier (authIdHal_s) - primary search method
        period (str): Period in format "YYYY-YYYY"
        domain_filter (list): List of domains to filter
        type_filter (list): List of document types to filter
        threshold (int): Acceptable Levenshtein distance threshold for name matching
    
    Returns:
        pd.DataFrame: DataFrame containing found publications
    """
    
    # === STEP 1: Determine the search term ===
    # Priority order: title > full name (first + last)
    if title and title.strip():
        search_term = title.strip()
    elif nom and prenom:
        search_term = f"{prenom} {nom}"
    else:
        # Insufficient data to perform a search
        return pd.DataFrame()
    
    # Clean and validate author_id
    author_id_clean = None
    if author_id and isinstance(author_id, str):
        author_id_clean = author_id.strip()
        # Check if it's a valid ID (not empty, not just a space, not 'nan')
        if author_id_clean and author_id_clean != ' ' and author_id_clean.lower() not in ['nan', 'none']:
            author_id_clean = author_id_clean
        else:
            author_id_clean = None
    
    filters = ""
    
    # === STEP 2: Apply optional filters (period, domain, type) ===
    
    # Period filter — restrict search by publication year range
    if period:
        try:
            start_year, end_year = period.split("-")
            filters += f"&fq=publicationDateY_i:[{start_year} TO {end_year}]"
        except ValueError:
            # Invalid period format -> return empty result
            return pd.DataFrame()

    # Domain filter — restrict search by scientific domain
    if domain_filter:
        domain_codes = [get_domain_code(d) for d in domain_filter if get_domain_code(d)]
        if domain_codes:
            filters += f"&fq=domain_s:({' OR '.join(domain_codes)})"

    # Document type filter — restrict by publication type
    if type_filter:
        type_codes = [get_type_code(t) for t in type_filter if get_type_code(t)]
        if type_codes:
            # Some types may be linked to broader categories
            linked_type_codes = get_linked_types(type_codes)
            filters += f"&fq=docType_s:({' OR '.join(linked_type_codes)})"

    # Specify the fields to retrieve from HAL
    fields = "&fl=authIdHal_s,authFirstName_s,authLastName_s,authFullName_s,docid,title_s,publicationDateY_i,docType_s,domain_s,keyword_s,labStructName_s&wt=json&rows=100"
    filters += fields
    
    all_publications = []
    seen_docids = set()
    
    # === STEP 3: Primary search using HAL ID ===
    if author_id_clean:
        query_base_id = f'?q=authIdHal_s:"{author_id_clean}"'
        all_publications, seen_docids = execute_hal_query_multi_api(query_base_id, filters)
    
    # === STEP 4: Fallback search using full name ===
    if not all_publications:
        query_base_name = f'?q=authFullName_t:"{search_term}"'
        all_publications, seen_docids = execute_hal_query_multi_api(query_base_name, filters)
        
        # Try reversed name order if not already tested (Lastname Firstname)
        if nom and prenom:
            inverted_search = f"{nom} {prenom}"
            if inverted_search != search_term:
                query_base_inverted = f'?q=authFullName_t:"{inverted_search}"'
                additional_pubs, additional_docids = execute_hal_query_multi_api(query_base_inverted, filters)
                
                # Merge unique results from the inverted query
                for pub in additional_pubs:
                    docid = pub.get("docid", "")
                    if docid not in seen_docids:
                        all_publications.append(pub)
                        seen_docids.add(docid)
    
    # If no publications found at all, return an empty DataFrame
    if not all_publications:
        return pd.DataFrame()

    # === STEP 5: Post-filtering based on accepted HAL document types ===
    accepted_hal_types = get_hal_filter_for_post_processing(type_filter)
    
    scientist_data = []
    
    # === STEP 6: Process and match each retrieved publication ===
    for pub in all_publications:
        # Skip documents not in the accepted types
        if accepted_hal_types is not None:
            doc_type = pub.get("docType_s", "")
            if doc_type not in accepted_hal_types:
                continue
        
        auth_full_names = pub.get("authFullName_s", [])
        publication_match_found = False
        
        # Try to find a matching author name inside the publication
        for full_name in auth_full_names:
            if not full_name:
                continue
            
            # Direct title-to-name comparison
            if title and title.strip():
                if is_same_author_levenshtein(title.strip(), full_name, threshold):
                    publication_match_found = True
                    break
            
            # Otherwise, compare using different name permutations
            if not publication_match_found:
                name_parts = full_name.split()
                if len(name_parts) >= 2:
                    prenom_hal_1 = name_parts[0]
                    nom_hal_1 = " ".join(name_parts[1:])
                    
                    prenom_hal_2 = name_parts[-1]
                    nom_hal_2 = " ".join(name_parts[:-1])
                    
                    # Compute Levenshtein similarity across multiple arrangements
                    if nom and prenom:
                        match_1 = (levenshtein_distance(nom.lower(), nom_hal_1.lower()) <= threshold and 
                                 levenshtein_distance(prenom.lower(), prenom_hal_1.lower()) <= threshold)
                        match_2 = (levenshtein_distance(nom.lower(), nom_hal_2.lower()) <= threshold and 
                                 levenshtein_distance(prenom.lower(), prenom_hal_2.lower()) <= threshold)
                        
                        match_3 = (levenshtein_distance(nom.lower(), prenom_hal_1.lower()) <= threshold and 
                                 levenshtein_distance(prenom.lower(), nom_hal_1.lower()) <= threshold)
                        match_4 = (levenshtein_distance(nom.lower(), prenom_hal_2.lower()) <= threshold and 
                                 levenshtein_distance(prenom.lower(), nom_hal_2.lower()) <= threshold)
                        
                        if match_1 or match_2 or match_3 or match_4:
                            publication_match_found = True
                            break
                    
                    # Final fallback: full name fuzzy comparison
                    if not publication_match_found:
                        if is_same_author_levenshtein(search_term, full_name, threshold):
                            publication_match_found = True
                            break
        
        # === STEP 7: Store publication metadata if match found ===
        if publication_match_found:
            authors = pub.get("authIdHal_s", [])
            authors_sorted = sorted(authors) if authors else [" "]
            
            scientist_data.append({
                "Nom": nom if nom else "",
                "Prenom": prenom if prenom else "",
                "Title": title if title else f"{prenom} {nom}" if (prenom and nom) else "",
                "IdHAL de l'Auteur": author_id_clean if author_id_clean else " ",
                "IdHAL des auteurs de la publication": authors_sorted,
                "Titre": pub.get("title_s", "Titre non disponible"),
                "Docid": pub.get("docid", " "),
                "Année de Publication": pub.get("publicationDateY_i", "Année non disponible"),
                "Type de Document": map_doc_type(pub.get("docType_s", "Type non défini")),
                "Domaine": map_domain(pub.get("domain_s", "Domaine non défini")),
                "Mots-clés": pub.get("keyword_s", []),
                "Laboratoire de Recherche": pub.get("labStructName_s", "Non disponible")
            })
    
    # === STEP 8: Return the final structured DataFrame ===
    return pd.DataFrame(scientist_data)