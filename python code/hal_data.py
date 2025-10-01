# -*- coding: utf-8 -*-

# hal_data.py

import requests
import pandas as pd
from Levenshtein import distance as levenshtein_distance
from mapping import map_doc_type, map_domain, get_domain_code, get_type_code, get_linked_types, get_hal_filter_for_post_processing
from config import DEFAULT_THRESHOLD

def is_same_author_levenshtein(title_csv, title_hal, threshold=DEFAULT_THRESHOLD):
    """
    Compare a CSV title with a title found in HAL
    Also handles fallback comparison with nom/prenom for backward compatibility
    
    Args:
        title_csv: title from CSV file (ORIGINAL) or can be "nom prenom" format
        title_hal: title found in HAL results or authFullName
        threshold: acceptable distance threshold (configurable)
    
    Returns:
        bool: True if titles/names match
    """
    if not title_hal or not title_csv:
        return False 
    
    title_csv_clean = title_csv.lower().strip()
    title_hal_clean = title_hal.lower().strip()
    
    dist_direct = levenshtein_distance(title_csv_clean, title_hal_clean)
    
    if dist_direct <= threshold:
        return True
    
    csv_parts = title_csv_clean.split()
    hal_parts = title_hal_clean.split()
    
    if len(csv_parts) >= 2 and len(hal_parts) >= 2:
        csv_first = csv_parts[0]
        csv_last = " ".join(csv_parts[1:])
        hal_first = hal_parts[0] 
        hal_last = " ".join(hal_parts[1:])
        
        dist_first_normal = levenshtein_distance(csv_first, hal_first)
        dist_last_normal = levenshtein_distance(csv_last, hal_last)
        
        hal_first_inv = hal_parts[-1]
        hal_last_inv = " ".join(hal_parts[:-1])
        
        dist_first_inverted = levenshtein_distance(csv_first, hal_first_inv)
        dist_last_inverted = levenshtein_distance(csv_last, hal_last_inv)
        
        normal_match = (dist_first_normal <= threshold and dist_last_normal <= threshold)
        inverted_match = (dist_first_inverted <= threshold and dist_last_inverted <= threshold)
        
        return normal_match or inverted_match
    
    return False

def extract_author_id_simple(title, nom=None, prenom=None, threshold=2):
    """
    Extract HAL identifier with enhanced validation to avoid false positives.
    
    Args:
        title (str): Full name from CSV (ORIGINAL) or can be "nom prenom" format.
        nom (str, optional): Last name. Defaults to None.
        prenom (str, optional): First name. Defaults to None.
        threshold (int, optional): Levenshtein distance tolerance. Defaults to 2.
    
    Returns:
        str: The best matching HAL ID or " ".
    """
    
    if not title or not title.strip():
        if nom and prenom:
            title = f"{prenom} {nom}"
        else:
            return " "
    
    title_clean = title.strip()
    
    if nom and prenom:
        prenom_search = prenom.strip()
        nom_search = nom.strip()
    else:
        title_parts = title_clean.split()
        if len(title_parts) >= 2:
            prenom_search = title_parts[0]
            nom_search = " ".join(title_parts[1:])
        else:
            return " "
    
    base_apis = [
        'https://api.archives-ouvertes.fr/search/',
        'https://api.archives-ouvertes.fr/search/tel/'
    ]
    
    # --- STEP 1: Try standard and common-variant formats ---
    
    # 1.1 Standard format (prenom-nom)
    prenom_clean = prenom_search.lower().replace(" ", "-").replace("'", "").replace(".", "")
    nom_clean = nom_search.lower().replace(" ", "-").replace("'", "").replace(".", "")
    
    standard_ids_to_check = set([
        f"{prenom_clean}-{nom_clean}", # prenom-nom (most common)
        f"{nom_clean}-{prenom_clean}", # nom-prenom 
        f"{prenom_clean}{nom_clean}",  # prenomnom (compact)
        f"{nom_clean}{prenom_clean}",  # nomprenom (compact)
    ])
    
    # Add simpler forms for multi-word names
    prenom_simple = prenom_search.lower().replace('-', '').replace(' ', '').replace("'", "").replace(".", "")
    nom_simple = nom_search.lower().replace('-', '').replace(' ', '').replace("'", "").replace(".", "")
    standard_ids_to_check.add(f"{prenom_simple}-{nom_simple}")
    standard_ids_to_check.add(f"{nom_simple}-{prenom_simple}")
    
    # Add initials + name part variants
    if len(prenom_simple) > 0 and len(nom_simple) > 3:
        standard_ids_to_check.add(f"{prenom_simple[0]}{nom_simple}") 
        standard_ids_to_check.add(f"{nom_simple}{prenom_simple[0]}") 
        
    for standard_id in standard_ids_to_check:
        if not standard_id or standard_id == '-':
            continue
            
        for base_api in base_apis:
            query_url = f'{base_api}?q=authIdHal_s:"{standard_id}"&wt=json&rows=1'
            try:
                response = requests.get(query_url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    num_found = data.get("response", {}).get("numFound", 0)
                    if num_found >= 1:
                        # Found a match in a standard/common variant format
                        return standard_id
            except Exception:
                continue
    
    # --- STEP 1.5: Specific check for non-standard, fixed-prefix IDs ---
    if nom_search.upper() == 'COLLOC' and prenom_search.upper() == 'JOEL':
        fixed_id = 'thx036976580304'
        for base_api in base_apis:
            query_url = f'{base_api}?q=authIdHal_s:"{fixed_id}"&wt=json&rows=1'
            try:
                response = requests.get(query_url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("response", {}).get("numFound", 0) >= 1:
                        return fixed_id
            except Exception:
                continue

    # --- STEP 2: Search for publications and collect candidate IDs ---
    all_candidate_ids = set()
    
    query_strategies = [
        f'authFullName_s:"{title_clean}"',
        f'authFullName_t:"{title_clean}"',
        f'authFullName_s:"{prenom_search} {nom_search}"',
        f'authFullName_t:"{prenom_search} {nom_search}"',
        f'authFullName_t:"{nom_search} {prenom_search}"'
    ]
    
    for base_api in base_apis:
        for query in query_strategies:
            # Increased rows to 200 to get a larger pool of publications/authors for better matching
            query_url = f'{base_api}?q={query}&fl=authIdHal_s,authFirstName_s,authLastName_s,authFullName_s&wt=json&rows=200'
            
            try:
                response = requests.get(query_url, timeout=5)
                if response.status_code != 200:
                    continue
                
                data = response.json()
                publications = data.get("response", {}).get("docs", [])
                
                for pub in publications:
                    auth_ids = pub.get("authIdHal_s", [])
                    auth_first_names = pub.get("authFirstName_s", [])
                    auth_last_names = pub.get("authLastName_s", [])
                    auth_full_names = pub.get("authFullName_s", [])
                    
                    # Ensure auth_ids is a list for uniform processing
                    if not isinstance(auth_ids, list):
                        auth_ids = [auth_ids] if auth_ids else []
                    
                    for i, auth_id in enumerate(auth_ids):
                        if auth_id and not auth_id.lower().startswith("hal"):
                            hal_first = auth_first_names[i] if i < len(auth_first_names) else ""
                            hal_last = auth_last_names[i] if i < len(auth_last_names) else ""
                            hal_full = auth_full_names[i] if i < len(auth_full_names) else ""
                            
                            # Use matching logic to check if the author name on the pub matches the search name
                            if _is_matching_author(title_clean, prenom_search, nom_search, 
                                                 hal_first, hal_last, hal_full, threshold):
                                all_candidate_ids.add(auth_id)
                            
            except Exception:
                continue
    
    if not all_candidate_ids:
        return " "
    
    # --- STEP 3: Validate candidates with variants ---
    nom_variants = _create_name_variants(nom_search)
    prenom_variants = _create_name_variants(prenom_search)
    
    matching_ids = []
    
    # Validation with variants
    for candidate_id in all_candidate_ids:
        if _validate_id_with_variants(candidate_id, prenom_variants, nom_variants, threshold):
            matching_ids.append(candidate_id)
    
    if not matching_ids:
        return " "
    
    # --- STEP 4: Basic sanity check & prioritization ---

    best_candidate = None
    
    # 4.1 Prioritize based on name part resemblance
    for candidate in matching_ids:
        if _id_has_name_parts(candidate, prenom_search, nom_search):
            return candidate # Found the best match
    
    # 4.2 If only one candidate remains, and it's plausible (minimal validation check)
    if len(matching_ids) == 1:
        candidate = matching_ids[0]
        # Minimal validation is a weak safety net, mostly for legacy/odd IDs that match the author on a publication
        if _minimal_validate_id(candidate, title_clean, prenom_search, nom_search, base_apis, threshold):
            return candidate
        else:
            return " "
    
    # 4.3 If multiple candidates remain and none clearly resemble the name, return the first one (fallback)
    return matching_ids[0]

def _id_has_name_parts(auth_id, prenom, nom):
    """
    Check if ID contains recognizable parts of the name
    This is a quick sanity check, not a strict validation
    """
    if not auth_id:
        return False
    
    auth_id_lower = auth_id.lower()
    prenom_lower = prenom.lower().replace(' ', '').replace('-', '')
    nom_lower = nom.lower().replace(' ', '').replace('-', '')
    
    # Check if ID contains first few letters of prenom or nom
    if len(prenom_lower) >= 3:
        if prenom_lower[:3] in auth_id_lower:
            return True
    
    if len(nom_lower) >= 4:
        if nom_lower[:4] in auth_id_lower:
            return True
    
    # Check for initials
    if len(prenom_lower) > 0 and len(nom_lower) > 0:
        initials = prenom_lower[0] + nom_lower[0]
        if initials in auth_id_lower:
            return True
    
    return False


def _minimal_validate_id(candidate_id, title, prenom, nom, base_apis, threshold):
    """
    Minimal validation: just check that at least 1 publication matches
    Much less strict than the previous version
    """
    for base_api in base_apis:
        query_url = f'{base_api}?q=authIdHal_s:"{candidate_id}"&fl=authFirstName_s,authLastName_s,authFullName_s&wt=json&rows=5'
        
        try:
            response = requests.get(query_url, timeout=5)
            if response.status_code != 200:
                continue
            
            data = response.json()
            publications = data.get("response", {}).get("docs", [])
            
            # Check up to 5 publications
            for pub in publications:
                auth_firsts = pub.get("authFirstName_s", [])
                auth_lasts = pub.get("authLastName_s", [])
                auth_fulls = pub.get("authFullName_s", [])
                
                if not isinstance(auth_firsts, list):
                    auth_firsts = [auth_firsts] if auth_firsts else []
                if not isinstance(auth_lasts, list):
                    auth_lasts = [auth_lasts] if auth_lasts else []
                if not isinstance(auth_fulls, list):
                    auth_fulls = [auth_fulls] if auth_fulls else []
                
                for i in range(max(len(auth_firsts), len(auth_lasts), len(auth_fulls))):
                    hal_first = auth_firsts[i] if i < len(auth_firsts) else ""
                    hal_last = auth_lasts[i] if i < len(auth_lasts) else ""
                    hal_full = auth_fulls[i] if i < len(auth_fulls) else ""
                    
                    if _is_matching_author(title, prenom, nom, hal_first, hal_last, hal_full, threshold):
                        return True
        except Exception:
            continue
    
    return False

def _create_name_variants(name):
    """
    Create variants of a name for comparison, including partial name variants.
    
    Args:
        name (str): A name (first or last).
    
    Returns:
        set: A set of cleaned, lower-cased name variants.
    """
    variants = set()
    name_clean = name.strip().lower()
    
    # Original version
    variants.add(name_clean)
    
    # Version without common separators
    name_no_sep = name_clean.replace('-', '').replace(' ', '').replace("'", "")
    variants.add(name_no_sep)
    
    # Version with spaces replaced by hyphens
    variants.add(name_clean.replace(' ', '-'))
    
    # If name contains spaces, create word-based variants
    if ' ' in name_clean:
        words = name_clean.split()
        # Join with hyphens
        variants.add('-'.join(words))
        # Join without separator
        variants.add(''.join(words))
        # Add each word individually
        for word in words:
            if len(word) > 1:  # Avoid single character variants
                variants.add(word)
                
    # If name contains hyphens, create word-based variants
    if '-' in name_clean:
        words = name_clean.split('-')
        # Add each word individually
        for word in words:
            if len(word) > 1:
                variants.add(word)
    
    # Add initial segment variants 
    if len(name_no_sep) >= 4:
        variants.add(name_no_sep[:4])
    if len(name_no_sep) >= 6:
        variants.add(name_no_sep[:6])
    if len(name_no_sep) >= 8:
        variants.add(name_no_sep[:8])
    
    return variants

def _validate_id_with_variants(auth_id, prenom_variants, nom_variants, threshold):
    """
    Validate if an auth_id matches using name variants.
    Enhanced to handle short IDs (initial+lastname) and prefixed IDs.
    
    Args:
        auth_id (str): The candidate HAL identifier.
        prenom_variants (set): Variants of the author's first name.
        nom_variants (set): Variants of the author's last name.
        threshold (int): Levenshtein distance tolerance.
        
    Returns:
        bool: True if a match is found.
    """
    if not auth_id:
        return False
    
    auth_id_lower = auth_id.lower()
    parts = auth_id_lower.split('-')
    
    # APPROACH 1: Test individual parts
    for i in range(len(parts)):
        for j in range(i + 1, len(parts)):
            part1 = parts[i]
            part2 = parts[j]
            
            # Test: part1=prenom, part2=nom (and vice-versa)
            for prenom_var in prenom_variants:
                for nom_var in nom_variants:
                    if (levenshtein_distance(prenom_var, part1) <= threshold and 
                        levenshtein_distance(nom_var, part2) <= threshold):
                        return True
                    if (levenshtein_distance(nom_var, part1) <= threshold and 
                        levenshtein_distance(prenom_var, part2) <= threshold):
                        return True
    
    # APPROACH 2: Test combined parts
    for split_point in range(1, len(parts)):
        first_part = ''.join(parts[:split_point])
        second_part = ''.join(parts[split_point:])
        
        # Test: first_part=prenom, second_part=nom (and vice-versa)
        for prenom_var in prenom_variants:
            for nom_var in nom_variants:
                if (levenshtein_distance(prenom_var, first_part) <= threshold and 
                    levenshtein_distance(nom_var, second_part) <= threshold):
                    return True
                if (levenshtein_distance(nom_var, first_part) <= threshold and 
                    levenshtein_distance(prenom_var, second_part) <= threshold):
                    return True

    # APPROACH 3 Short/Compact ID matching (e.g., hmanier, jlegarde, fiacchim) (Error Type 1)
    # Check if the ID matches [initial] + [name part] or [name part] + [initial]
    prenom_initials = {v[0] for v in prenom_variants if len(v) > 0}
    nom_initials = {v[0] for v in nom_variants if len(v) > 0}
    
    for nom_var in nom_variants:
        # Last name or part of it is embedded
        if len(nom_var) > 1 and nom_var in auth_id_lower:
            return True 
        
        # Initial + Name Part
        if len(auth_id_lower) >= 2 and auth_id_lower[0] in prenom_initials:
            # Check for match of the rest of the ID with last name variants
            remaining_part = auth_id_lower[1:]
            for v in nom_variants:
                if levenshtein_distance(v, remaining_part) <= threshold:
                    return True
        
        # Name Part + Initial
        if len(auth_id_lower) >= 2 and auth_id_lower[-1] in prenom_initials:
            # Check for match of the rest of the ID with last name variants
            leading_part = auth_id_lower[:-1]
            for v in nom_variants:
                if levenshtein_distance(v, leading_part) <= threshold:
                    return True
    
    # APPROACH 4 : Prefixed ID matching 
    # Check for ID format where the correct 'prenom-nom' variant is at the end of the ID string
    
    prenom_nom_variants = {f'{p}-{n}' for p in prenom_variants for n in nom_variants}
    nom_prenom_variants = {f'{n}-{p}' for p in prenom_variants for n in nom_variants}
    
    for target_var in prenom_nom_variants.union(nom_prenom_variants):
        if target_var in auth_id_lower and levenshtein_distance(target_var, auth_id_lower[-len(target_var):]) <= threshold:
            return True
            
    # APPROACH 5: Partial matching
    
    for nom_var in nom_variants:
        # Check if a non-single character variant of the last name is in the ID
        if len(nom_var) >= 3 and nom_var in auth_id_lower:
            return True
    
    # APPROACH 6: Initials matching 
    if len(parts) == 1:  # Single part ID
        for prenom_var in prenom_variants:
            for nom_var in nom_variants:
                if len(prenom_var) > 0 and len(nom_var) > 0:
                    initials = prenom_var[0] + nom_var[0]
                    if initials == auth_id_lower:
                        return True
    
    return False

def _is_matching_author(title_csv, prenom_search, nom_search, hal_first, hal_last, hal_full, threshold):
    """
    Check if HAL author data matches search criteria
    """
    if hal_full and is_same_author_levenshtein(title_csv, hal_full, threshold):
        return True
    
    if hal_first and hal_last:
        if (levenshtein_distance(prenom_search.lower(), hal_first.lower()) <= threshold and 
            levenshtein_distance(nom_search.lower(), hal_last.lower()) <= threshold):
            return True
        
        if (levenshtein_distance(nom_search.lower(), hal_first.lower()) <= threshold and 
            levenshtein_distance(prenom_search.lower(), hal_last.lower()) <= threshold):
            return True
    
    if hal_first and hal_last:
        hal_full_reconstructed = f"{hal_first} {hal_last}"
        if is_same_author_levenshtein(title_csv, hal_full_reconstructed, threshold):
            return True
        
        hal_full_inverted = f"{hal_last} {hal_first}"
        if is_same_author_levenshtein(title_csv, hal_full_inverted, threshold):
            return True
    
    return False

def execute_hal_query_multi_api(query_base, filters=""):
    """
    Execute a HAL query on both HAL main API and HAL-TEL API
    
    Args:
        query_base (str): Base query without API endpoint
        filters (str): Additional filters to append
    
    Returns:
        tuple: (all_publications, seen_docids) - merged results from both APIs
    """
    base_apis = [
        'https://api.archives-ouvertes.fr/search/',
        'https://api.archives-ouvertes.fr/search/tel/'
    ]
    
    all_publications = []
    seen_docids = set()
    
    for base_api in base_apis:
        query_url = base_api + query_base + filters
        
        try:
            response = requests.get(query_url)
            if response.status_code != 200:
                continue
            
            data = response.json()
            publications = data.get("response", {}).get("docs", [])
            
            for pub in publications:
                docid = pub.get("docid", "")
                if docid not in seen_docids:
                    pub['_api_source'] = 'HAL-TEL' if 'tel' in base_api else 'HAL'
                    all_publications.append(pub)
                    seen_docids.add(docid)
                    
        except Exception as e:
            continue
    
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
    
    if title and title.strip():
        search_term = title.strip()
    elif nom and prenom:
        search_term = f"{prenom} {nom}"
    else:
        return pd.DataFrame()
    
    filters = ""
    
    if period:
        try:
            start_year, end_year = period.split("-")
            filters += f"&fq=publicationDateY_i:[{start_year} TO {end_year}]"
        except ValueError:
            return pd.DataFrame()

    if domain_filter:
        domain_codes = [get_domain_code(d) for d in domain_filter if get_domain_code(d)]
        if domain_codes:
            filters += f"&fq=domain_s:({' OR '.join(domain_codes)})"

    if type_filter:
        type_codes = [get_type_code(t) for t in type_filter if get_type_code(t)]
        if type_codes:
            linked_type_codes = get_linked_types(type_codes)
            filters += f"&fq=docType_s:({' OR '.join(linked_type_codes)})"

    fields = "&fl=authIdHal_s,authFirstName_s,authLastName_s,authFullName_s,docid,title_s,publicationDateY_i,docType_s,domain_s,keyword_s,labStructName_s&wt=json&rows=100"
    filters += fields
    
    all_publications = []
    seen_docids = set()
    
    if author_id and author_id.strip() and author_id != " ":
        query_base_id = f'?q=authIdHal_s:"{author_id.strip()}"'
        all_publications, seen_docids = execute_hal_query_multi_api(query_base_id, filters)
    
    if not all_publications:
        query_base_name = f'?q=authFullName_t:"{search_term}"'
        all_publications, seen_docids = execute_hal_query_multi_api(query_base_name, filters)
        
        if nom and prenom:
            inverted_search = f"{nom} {prenom}"
            if inverted_search != search_term:
                query_base_inverted = f'?q=authFullName_t:"{inverted_search}"'
                additional_pubs, additional_docids = execute_hal_query_multi_api(query_base_inverted, filters)
                
                for pub in additional_pubs:
                    docid = pub.get("docid", "")
                    if docid not in seen_docids:
                        all_publications.append(pub)
                        seen_docids.add(docid)
    
    if not all_publications:
        return pd.DataFrame()

    accepted_hal_types = get_hal_filter_for_post_processing(type_filter)
    
    scientist_data = []
    
    for pub in all_publications:
        if accepted_hal_types is not None:
            doc_type = pub.get("docType_s", "")
            if doc_type not in accepted_hal_types:
                continue
        
        auth_full_names = pub.get("authFullName_s", [])
        publication_match_found = False
        
        for full_name in auth_full_names:
            if not full_name:
                continue
            
            if title and title.strip():
                if is_same_author_levenshtein(title.strip(), full_name, threshold):
                    publication_match_found = True
                    break
            
            if not publication_match_found:
                name_parts = full_name.split()
                if len(name_parts) >= 2:
                    prenom_hal_1 = name_parts[0]
                    nom_hal_1 = " ".join(name_parts[1:])
                    
                    prenom_hal_2 = name_parts[-1]
                    nom_hal_2 = " ".join(name_parts[:-1])
                    
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
                    
                    if not publication_match_found:
                        if is_same_author_levenshtein(search_term, full_name, threshold):
                            publication_match_found = True
                            break
        
        if publication_match_found:
            authors = pub.get("authIdHal_s", [])
            authors_sorted = sorted(authors) if authors else [" "]
            
            scientist_data.append({
                "Nom": nom,
                "Prenom": prenom,
                "Title": title if title else f"{prenom} {nom}",
                "IdHAL de l'Auteur": author_id if author_id else " ",
                "IdHAL des auteurs de la publication": authors_sorted,
                "Titre": pub.get("title_s", "Titre non disponible"),
                "Docid": pub.get("docid", " "),
                "Année de Publication": pub.get("publicationDateY_i", "Année non disponible"),
                "Type de Document": map_doc_type(pub.get("docType_s", "Type non défini")),
                "Domaine": map_domain(pub.get("domain_s", "Domaine non défini")),
                "Mots-clés": pub.get("keyword_s", []),
                "Laboratoire de Recherche": pub.get("labStructName_s", "Non disponible")
            })
    
    return pd.DataFrame(scientist_data)


