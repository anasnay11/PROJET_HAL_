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
    
    # Clean and normalize strings
    title_csv_clean = title_csv.lower().strip()
    title_hal_clean = title_hal.lower().strip()
    
    # Calculate direct distance
    dist_direct = levenshtein_distance(title_csv_clean, title_hal_clean)
    
    # Direct match
    if dist_direct <= threshold:
        return True
    
    # For backward compatibility, also try name-based matching
    # If title_csv looks like "firstname lastname" format
    csv_parts = title_csv_clean.split()
    hal_parts = title_hal_clean.split()
    
    if len(csv_parts) >= 2 and len(hal_parts) >= 2:
        # Try normal order (first last) vs (first last)
        csv_first = csv_parts[0]
        csv_last = " ".join(csv_parts[1:])
        hal_first = hal_parts[0] 
        hal_last = " ".join(hal_parts[1:])
        
        dist_first_normal = levenshtein_distance(csv_first, hal_first)
        dist_last_normal = levenshtein_distance(csv_last, hal_last)
        
        # Try inverted order (first last) vs (last first)
        hal_first_inv = hal_parts[-1]
        hal_last_inv = " ".join(hal_parts[:-1])
        
        dist_first_inverted = levenshtein_distance(csv_first, hal_first_inv)
        dist_last_inverted = levenshtein_distance(csv_last, hal_last_inv)
        
        # Match if either order works
        normal_match = (dist_first_normal <= threshold and dist_last_normal <= threshold)
        inverted_match = (dist_first_inverted <= threshold and dist_last_inverted <= threshold)
        
        return normal_match or inverted_match
    
    return False

def extract_author_id_simple(title, nom=None, prenom=None, threshold=2):
    """
    Extract HAL identifier using title as primary method, with nom/prenom as fallback
    
    Handles complex cases:
    - Title-based matching
    - Fallback to name-based matching
    - Hyphens in names
    - Compound names
    - Partial IDs
    - Short formats (initials)
    - Duplicate names
    
    Args:
        title (str): Title/full name from CSV
        nom (str): Last name (fallback)
        prenom (str): First name (fallback)  
        threshold (int): Acceptable Levenshtein distance threshold
    
    Returns:
        str: authIdHal_s if found and verified, otherwise "Id non disponible"
    """
    
    # If no title provided, fall back to nom/prenom
    if not title or not title.strip():
        if nom and prenom:
            title = f"{prenom} {nom}"
        else:
            return "Id non disponible"
    
    title_clean = title.strip()
    
    # Special handling for cases where title looks like duplicate name (first name equals last name)
    title_parts = title_clean.lower().split()
    is_duplicate_name = (len(title_parts) == 2 and title_parts[0] == title_parts[1])
    
    if is_duplicate_name:
        # Use stricter threshold for duplicate names
        threshold = min(threshold, 1)
        
        # Specialized Handling for Duplicate Names
        prenom_part = title_parts[0]
        nom_part = title_parts[1]
        query_url = f'https://api.archives-ouvertes.fr/search/?q=authFirstName_s:"{prenom_part}" AND authLastName_s:"{nom_part}"&fl=authIdHal_s,authFirstName_s,authLastName_s,authFullName_s&wt=json&rows=50'
        
        try:
            response = requests.get(query_url)
            if response.status_code == 200:
                data = response.json()
                publications = data.get("response", {}).get("docs", [])
                
                valid_candidates = []
                
                for pub in publications:
                    auth_ids = pub.get("authIdHal_s", [])
                    auth_first_names = pub.get("authFirstName_s", [])
                    auth_last_names = pub.get("authLastName_s", [])
                    auth_full_names = pub.get("authFullName_s", [])
                    
                    # Verification with all available fields
                    if len(auth_ids) == len(auth_first_names) == len(auth_last_names):
                        for i, auth_id in enumerate(auth_ids):
                            if auth_id and not auth_id.lower().startswith("hal"):
                                hal_first = auth_first_names[i] if i < len(auth_first_names) else ""
                                hal_last = auth_last_names[i] if i < len(auth_last_names) else ""
                                hal_full = auth_full_names[i] if i < len(auth_full_names) else ""
                                
                                # Very strict validation for identical names
                                first_match = levenshtein_distance(prenom_part, hal_first.lower()) <= threshold
                                last_match = levenshtein_distance(nom_part, hal_last.lower()) <= threshold
                                
                                # Additional validation with full name
                                expected_full_name = f"{prenom_part} {nom_part}".lower()
                                full_name_match = False
                                if hal_full:
                                    full_name_match = levenshtein_distance(expected_full_name, hal_full.lower()) <= threshold
                                
                                # All conditions must be true for duplicate names
                                if first_match and last_match and (full_name_match or not hal_full):
                                    confidence_score = int(first_match) + int(last_match) + int(full_name_match)
                                    valid_candidates.append({
                                        'id': auth_id,
                                        'confidence': confidence_score
                                    })
                
                if valid_candidates:
                    # Return candidate with highest confidence
                    valid_candidates.sort(key=lambda x: x['confidence'], reverse=True)
                    return valid_candidates[0]['id']
                    
        except Exception:
            pass
    
    # STANDARD HANDLING FOR REGULAR TITLES/NAMES (or fallback for duplicate names)
    
    # Multiple query strategies for better precision
    if is_duplicate_name:
        # For duplicate names, use only the most precise strategies
        query_strategies = [
            f'https://api.archives-ouvertes.fr/search/?q=authFullName_s:"{title_clean}"&fl=authIdHal_s,authFirstName_s,authLastName_s,authFullName_s&wt=json&rows=100',
            f'https://api.archives-ouvertes.fr/search/?q=authFullName_t:"{title_clean}"&fl=authIdHal_s,authFirstName_s,authLastName_s,authFullName_s&wt=json&rows=100'
        ]
    else:
        # For regular titles/names, use all strategies
        query_strategies = [
            # Strategy 1: Search by authFullName (most precise)
            f'https://api.archives-ouvertes.fr/search/?q=authFullName_s:"{title_clean}"&fl=authIdHal_s,authFirstName_s,authLastName_s,authFullName_s&wt=json&rows=100',
            
            # Strategy 2: Exact string match in fullname text
            f'https://api.archives-ouvertes.fr/search/?q=authFullName_t:"{title_clean}"&fl=authIdHal_s,authFirstName_s,authLastName_s,authFullName_s&wt=json&rows=100',
            
            # Strategy 3: Fallback to general text search
            f'https://api.archives-ouvertes.fr/search/?q=text:"{title_clean}"&fl=authIdHal_s,authFirstName_s,authLastName_s,authFullName_s&wt=json&rows=100'
        ]
    
    all_candidates = []
    
    for strategy_index, query_url in enumerate(query_strategies):
        try:
            response = requests.get(query_url)
            if response.status_code != 200:
                continue
            
            data = response.json()
            publications = data.get("response", {}).get("docs", [])
            
            if not publications:
                continue
            
            # Collect candidates with verification
            for pub in publications:
                auth_ids = pub.get("authIdHal_s", [])
                auth_first_names = pub.get("authFirstName_s", [])
                auth_last_names = pub.get("authLastName_s", [])
                auth_full_names = pub.get("authFullName_s", [])
                
                # Verify that lists have the same length
                if len(auth_ids) == len(auth_first_names) == len(auth_last_names):
                    for i, auth_id in enumerate(auth_ids):
                        # Exclude document-like IDs such as "hal-xxxxxxx"
                        if auth_id and not auth_id.lower().startswith("hal"):
                            hal_first_name = auth_first_names[i] if i < len(auth_first_names) else ""
                            hal_last_name = auth_last_names[i] if i < len(auth_last_names) else ""
                            hal_full_name = auth_full_names[i] if i < len(auth_full_names) else ""
                            
                            # Primary verification with title matching
                            title_match = is_same_author_levenshtein(title_clean, hal_full_name, threshold)
                            
                            # Secondary verification for backward compatibility
                            name_match = False
                            if not title_match and nom and prenom:
                                name_match = is_same_author_levenshtein(f"{prenom} {nom}", hal_full_name, threshold)
                            
                            if title_match or name_match:
                                all_candidates.append({
                                    'id': auth_id,
                                    'hal_first': hal_first_name,
                                    'hal_last': hal_last_name,
                                    'hal_full': hal_full_name,
                                    'strategy': strategy_index + 1
                                })
            
            # For duplicate names, stop early if we find candidates with precise strategies
            if is_duplicate_name and all_candidates and strategy_index < 1:
                break
            # For regular names, stop early if we find candidates with strategy 1 or 2
            elif not is_duplicate_name and all_candidates and strategy_index < 2:
                break
                    
        except Exception:
            continue
    
    if all_candidates:
        # Prioritize results from the most precise strategies
        all_candidates.sort(key=lambda x: x['strategy'])
        return all_candidates[0]['id']
    
    # If no candidates found with structured queries, fall back to complex matching
    # This is only for regular names (not duplicate names to avoid false positives)
    if is_duplicate_name:
        return "Id non disponible"
    
    # COMPLEX FALLBACK METHOD FOR REGULAR TITLES/NAMES ONLY
    
    # Parse title into potential name components
    title_words = title_clean.lower().split()
    if len(title_words) >= 2:
        potential_prenom = title_words[0]
        potential_nom = " ".join(title_words[1:])
    elif nom and prenom:
        potential_prenom = prenom.lower()
        potential_nom = nom.lower()
    else:
        return "Id non disponible"
    
    # Double query to handle both name orders  
    query_urls = [
        f'https://api.archives-ouvertes.fr/search/?q=authFullName_t:"{potential_prenom} {potential_nom}"&fl=authIdHal_s,authFirstName_s,authLastName_s,authFullName_s&wt=json&rows=100',
        f'https://api.archives-ouvertes.fr/search/?q=authFullName_t:"{potential_nom} {potential_prenom}"&fl=authIdHal_s,authFirstName_s,authLastName_s,authFullName_s&wt=json&rows=100'
    ]
    
    all_author_ids = set()  # Use a set to avoid duplicates across both queries
    
    for query_url in query_urls:
        try:
            response = requests.get(query_url)
            if response.status_code != 200:
                continue  # Try next query
            
            data = response.json()
            publications = data.get("response", {}).get("docs", [])
            
            # Collect ALL found authIdHal_s from this query
            for pub in publications:
                auth_ids = pub.get("authIdHal_s", [])
                for auth_id in auth_ids:
                    # Exclude document-like IDs such as "hal-xxxxxxx"
                    if auth_id and not auth_id.lower().startswith("hal"):
                        all_author_ids.add(auth_id)
                        
        except Exception:
            continue  # Try next query
    
    # If no IDs found from either query
    if not all_author_ids:
        return "Id non disponible"
            
    # AUTHOR VARIANTS PREPARATION
    
    # Normalize names (lowercase, no multiple spaces)
    nom_clean = potential_nom.strip()
    prenom_clean = potential_prenom.strip()
    
    # Create all possible variants of last name/first name
    def create_variants(text):
        """Creates variants of a last name/first name for comparison"""
        variants = set()
        
        # Original version
        variants.add(text)
        
        # Version without hyphens
        variants.add(text.replace('-', ''))
        
        # Version with spaces replaced by hyphens
        variants.add(text.replace(' ', '-'))
        
        # Version without spaces
        variants.add(text.replace(' ', ''))
        
        # If text contains spaces, separate into words
        if ' ' in text:
            words = text.split()
            # Join with hyphens
            variants.add('-'.join(words))
            # Join without separator
            variants.add(''.join(words))
            
            # Add each word individually
            for word in words:
                variants.add(word)
        
        # If text contains hyphens, separate by hyphens too
        if '-' in text:
            words = text.split('-')
            for word in words:
                variants.add(word)
        
        return variants
    
    nom_variants = create_variants(nom_clean)
    prenom_variants = create_variants(prenom_clean)
    
    # STEP 1: STRICT METHOD
    
    matching_ids_strict = []
    
    for auth_id in all_author_ids:
        if not auth_id or auth_id == "Id non disponible":
            continue
        
        # Extract parts of HAL ID
        parts = auth_id.split('-')
        if len(parts) < 2:
            continue
        
        # Test different combinations of parts
        id_matches = False
        
        # APPROACH 1: INDIVIDUAL PARTS
        for i in range(len(parts)):
            for j in range(i + 1, len(parts)):
                part1 = parts[i]
                part2 = parts[j]
                
                # Test: part1=first name, part2=last name
                for prenom_var in prenom_variants:
                    for nom_var in nom_variants:
                        if (levenshtein_distance(prenom_var, part1) <= threshold and 
                            levenshtein_distance(nom_var, part2) <= threshold):
                            id_matches = True
                            break
                    if id_matches:
                        break
                if id_matches:
                    break
                
                # Test: part1=last name, part2=first name
                if not id_matches:
                    for prenom_var in prenom_variants:
                        for nom_var in nom_variants:
                            if (levenshtein_distance(nom_var, part1) <= threshold and 
                                levenshtein_distance(prenom_var, part2) <= threshold):
                                id_matches = True
                                break
                        if id_matches:
                            break
                if id_matches:
                    break
            if id_matches:
                break
        
        # APPROACH 2: COMBINED PARTS
        if not id_matches:
            for split_point in range(1, len(parts)):
                first_part = ''.join(parts[:split_point])
                second_part = ''.join(parts[split_point:])
                
                # Test: first_part=first name, second_part=last name
                for prenom_var in prenom_variants:
                    for nom_var in nom_variants:
                        if (levenshtein_distance(prenom_var, first_part) <= threshold and 
                            levenshtein_distance(nom_var, second_part) <= threshold):
                            id_matches = True
                            break
                    if id_matches:
                        break
                if id_matches:
                    break
                
                # Test: first_part=last name, second_part=first name
                if not id_matches:
                    for prenom_var in prenom_variants:
                        for nom_var in nom_variants:
                            if (levenshtein_distance(nom_var, first_part) <= threshold and 
                                levenshtein_distance(prenom_var, second_part) <= threshold):
                                id_matches = True
                                break
                        if id_matches:
                            break
                if id_matches:
                    break
        
        if id_matches:
            matching_ids_strict.append(auth_id)
    
    # If strict method worked, return the result
    if matching_ids_strict:
        return matching_ids_strict[0]
    
    # STEP 2: FALLBACK METHOD - PARTIAL MATCHING
    
    matching_ids_partial = []
    
    for auth_id in all_author_ids:
        if not auth_id or auth_id == "Id non disponible":
            continue
        
        auth_id_lower = auth_id.lower()
        
        # STRATEGY 1: ONLY last name must be found for fallback
        
        partial_match_found = False
        
        # Test if a variant of the last name is contained in the ID
        for nom_var in nom_variants:
            if len(nom_var) >= 3 and nom_var in auth_id_lower:  # At least 3 characters to avoid false positives
                partial_match_found = True
                break
        
        # STRATEGY 2: Initials
        
        if not partial_match_found:
            # Create possible initials
            initiales_possibles = set()
            
            # Initials first name + last name
            if prenom_clean and nom_clean:
                # First letter of first name + first letter of last name
                initiales_possibles.add(prenom_clean[0] + nom_clean[0])
                
                # If last name contains spaces, use first letters of each word
                if ' ' in nom_clean:
                    nom_words = nom_clean.split()
                    initiales = prenom_clean[0] + ''.join([word[0] for word in nom_words])
                    initiales_possibles.add(initiales)
                
                # If last name contains hyphens, use first letters of each part
                if '-' in nom_clean:
                    nom_words = nom_clean.split('-')
                    initiales = prenom_clean[0] + ''.join([word[0] for word in nom_words])
                    initiales_possibles.add(initiales)
            
            # Test initials (exact match only)
            for initiales in initiales_possibles:
                if len(initiales) >= 2 and initiales == auth_id_lower:
                    partial_match_found = True
                    break
        
        # STRATEGY 3: Approximate matching of complete ID
        
        if not partial_match_found:
            # Create "compact" versions of full name
            nom_prenom_compact = nom_clean.replace(' ', '').replace('-', '') + prenom_clean.replace(' ', '').replace('-', '')
            prenom_nom_compact = prenom_clean.replace(' ', '').replace('-', '') + nom_clean.replace(' ', '').replace('-', '')
            auth_id_compact = auth_id_lower.replace('-', '')
            
            # Distance test on compact versions
            if (levenshtein_distance(nom_prenom_compact, auth_id_compact) <= threshold + 1 or
                levenshtein_distance(prenom_nom_compact, auth_id_compact) <= threshold + 1):
                partial_match_found = True
        
        if partial_match_found:
            matching_ids_partial.append(auth_id)
    
    # Return first ID found with fallback method
    if matching_ids_partial:
        return matching_ids_partial[0]
    else:
        return "Id non disponible"

def execute_hal_query(query_url):
    """
    Execute a single HAL API query and return results
    
    Args:
        query_url (str): Complete HAL API query URL
    
    Returns:
        list: List of publication documents, empty list if error
    """
    try:
        response = requests.get(query_url)
        if response.status_code != 200:
            return []
        
        data = response.json()
        return data.get("response", {}).get("docs", [])
        
    except Exception:
        return []

def get_hal_data(nom, prenom, title=None, period=None, domain_filter=None, type_filter=None, threshold=DEFAULT_THRESHOLD):
    """
    Main function with title-based search as primary method and name/firstname as fallback
    
    Args:
        nom (str): Nom de famille
        prenom (str): Prénom  
        title (str): Title from CSV (primary search method)
        period (str): Période au format "YYYY-YYYY"
        domain_filter (list): Liste des domaines à filtrer
        type_filter (list): Liste des types de documents à filtrer
        threshold (int): Seuil de distance Levenshtein acceptable
    
    Returns:
        pd.DataFrame: DataFrame contenant les publications trouvées
    """
    
    # STEP 1: ID EXTRACTION - prioritize title, fallback to nom/prenom
    
    if title and title.strip():
        author_id = extract_author_id_simple(title, nom, prenom, threshold)
        search_term = title.strip()
    elif nom and prenom:
        author_id = extract_author_id_simple(f"{prenom} {nom}", nom, prenom, threshold)
        search_term = f"{prenom} {nom}"
    else:
        print("Either title or nom/prenom must be provided.")
        return pd.DataFrame()
    
    # STEP 2: DOUBLE QUERY FOR PUBLICATIONS
    
    # Build base queries - primary with title/search_term, secondary with name variants
    query_urls = []
    
    # Primary query with main search term
    query_url = f'https://api.archives-ouvertes.fr/search/?q=authFullName_t:"{search_term}"'
    
    if period:
        try:
            start_year, end_year = period.split("-")
            query_url += f"&fq=publicationDateY_i:[{start_year} TO {end_year}]"
        except ValueError:
            print("Period format must be YYYY-YYYY.")
            return pd.DataFrame()

    if domain_filter:
        domain_codes = [get_domain_code(d) for d in domain_filter if get_domain_code(d)]
        if domain_codes:
            query_url += f"&fq=domain_s:({' OR '.join(domain_codes)})"

    if type_filter:
        type_codes = [get_type_code(t) for t in type_filter if get_type_code(t)]
        if type_codes:
            # Use enhanced linking function
            linked_type_codes = get_linked_types(type_codes)
            query_url += f"&fq=docType_s:({' OR '.join(linked_type_codes)})"

    # Fields for publications
    query_url += "&fl=authIdHal_s,authFirstName_s,authLastName_s,authFullName_s,docid,title_s,publicationDateY_i,docType_s,domain_s,keyword_s,labStructName_s&wt=json&rows=100"
    
    query_urls.append(query_url)
    
    # Secondary query with inverted name order (if we have nom/prenom)
    if nom and prenom:
        inverted_search = f"{nom} {prenom}"
        if inverted_search != search_term:  # Avoid duplicate queries
            query_url2 = f'https://api.archives-ouvertes.fr/search/?q=authFullName_t:"{inverted_search}"'
            
            if period:
                try:
                    start_year, end_year = period.split("-")
                    query_url2 += f"&fq=publicationDateY_i:[{start_year} TO {end_year}]"
                except ValueError:
                    pass

            if domain_filter:
                domain_codes = [get_domain_code(d) for d in domain_filter if get_domain_code(d)]
                if domain_codes:
                    query_url2 += f"&fq=domain_s:({' OR '.join(domain_codes)})"

            if type_filter:
                type_codes = [get_type_code(t) for t in type_filter if get_type_code(t)]
                if type_codes:
                    linked_type_codes = get_linked_types(type_codes)
                    query_url2 += f"&fq=docType_s:({' OR '.join(linked_type_codes)})"

            query_url2 += "&fl=authIdHal_s,authFirstName_s,authLastName_s,authFullName_s,docid,title_s,publicationDateY_i,docType_s,domain_s,keyword_s,labStructName_s&wt=json&rows=100"
            query_urls.append(query_url2)
    
    # STEP 3: EXECUTE BOTH QUERIES AND MERGE
    
    all_publications = []
    seen_docids = set()  # To avoid duplicates between the two queries
    
    for query_url in query_urls:
        publications = execute_hal_query(query_url)
        
        for pub in publications:
            docid = pub.get("docid", "")
            # Only add if we haven't seen this document ID before
            if docid not in seen_docids:
                all_publications.append(pub)
                seen_docids.add(docid)
    
    if not all_publications:
        return pd.DataFrame()

    # STEP 4: POST-FILTERING
    
    # Get the precise HAL types to accept
    accepted_hal_types = get_hal_filter_for_post_processing(type_filter)
    
    scientist_data = []
    
    for pub in all_publications:
        # Granular post-filtering by document type
        if accepted_hal_types is not None:
            doc_type = pub.get("docType_s", "")
            if doc_type not in accepted_hal_types:
                continue  # Skip this publication, doesn't match the precise filter
        
        # Extract names/first names of authors from this publication
        auth_full_names = pub.get("authFullName_s", [])
        
        # Check if this publication contains our author
        publication_match_found = False
        
        for full_name in auth_full_names:
            if not full_name:
                continue
            
            # Primary matching: use title if available
            if title and title.strip():
                if is_same_author_levenshtein(title.strip(), full_name, threshold):
                    publication_match_found = True
                    break
            
            # Secondary matching: try with name components
            if not publication_match_found:
                # Separate first name/last name from authFullName_s
                name_parts = full_name.split()
                if len(name_parts) >= 2:
                    # Try both interpretations
                    # Interpretation 1: First word = first name, rest = last name
                    prenom_hal_1 = name_parts[0]
                    nom_hal_1 = " ".join(name_parts[1:])
                    
                    # Interpretation 2: Last word = first name, rest = last name  
                    prenom_hal_2 = name_parts[-1]
                    nom_hal_2 = " ".join(name_parts[:-1])
                    
                    # Test both interpretations with our search terms
                    if nom and prenom:
                        # Traditional name matching
                        match_1 = (levenshtein_distance(nom.lower(), nom_hal_1.lower()) <= threshold and 
                                 levenshtein_distance(prenom.lower(), prenom_hal_1.lower()) <= threshold)
                        match_2 = (levenshtein_distance(nom.lower(), nom_hal_2.lower()) <= threshold and 
                                 levenshtein_distance(prenom.lower(), prenom_hal_2.lower()) <= threshold)
                        
                        # Also try inverted matching  
                        match_3 = (levenshtein_distance(nom.lower(), prenom_hal_1.lower()) <= threshold and 
                                 levenshtein_distance(prenom.lower(), nom_hal_1.lower()) <= threshold)
                        match_4 = (levenshtein_distance(nom.lower(), prenom_hal_2.lower()) <= threshold and 
                                 levenshtein_distance(prenom.lower(), nom_hal_2.lower()) <= threshold)
                        
                        if match_1 or match_2 or match_3 or match_4:
                            publication_match_found = True
                            break
                    
                    # If no traditional name match, try with search_term as full name
                    if not publication_match_found:
                        if is_same_author_levenshtein(search_term, full_name, threshold):
                            publication_match_found = True
                            break
        
        # If a match was found for this publication, add it
        if publication_match_found:
            authors = pub.get("authIdHal_s", [])
            authors_sorted = sorted(authors) if authors else ["Id non disponible"]

            scientist_data.append({
                "Nom": nom,  
                "Prenom": prenom,  
                "Title": title if title else f"{prenom} {nom}",  # Add title to output
                "IdHAL de l'Auteur": author_id,  # ID EXTRACTED USING TITLE OR NAME
                "IdHAL des auteurs de la publication": authors_sorted,
                "Titre": pub.get("title_s", "Titre non disponible"),
                "Docid": pub.get("docid", "Id non disponible"),
                "Année de Publication": pub.get("publicationDateY_i", "Année non disponible"),
                "Type de Document": map_doc_type(pub.get("docType_s", "Type non défini")),
                "Domaine": map_domain(pub.get("domain_s", "Domaine non défini")),
                "Mots-clés": pub.get("keyword_s", []),
                "Laboratoire de Recherche": pub.get("labStructName_s", "Non disponible"),
            })
    
    return pd.DataFrame(scientist_data)

def get_all_id(scientists_df, threshold=DEFAULT_THRESHOLD):
    """
    Extract HAL identifiers for all scientists in the DataFrame
    
    Args:
        scientists_df (pd.DataFrame): DataFrame containing scientist data with columns:
                                    - 'title' (preferred) or 'nom'/'prenom'
                                    - 'nom': last name
                                    - 'prenom': first name
                                    - other columns will be preserved
        threshold (int): Levenshtein distance threshold for matching
    
    Returns:
        pd.DataFrame: DataFrame with original data plus 'IdHAL' column
    """
    # Create a copy of the input DataFrame to preserve original data
    result_df = scientists_df.copy()
    
    # Initialize the IdHAL column
    result_df['IdHAL'] = ''
    
    # Extract identifiers for each scientist
    for index, row in scientists_df.iterrows():
        try:
            # Get title if available, otherwise use nom/prenom
            title = row.get('title', '').strip() if 'title' in row else ''
            nom = row.get('nom', '').strip() if 'nom' in row else ''
            prenom = row.get('prenom', '').strip() if 'prenom' in row else ''
            
            # Extract HAL identifier
            hal_id = extract_author_id_simple(
                title=title if title else None,
                nom=nom if nom else None,
                prenom=prenom if prenom else None,
                threshold=threshold
            )
            
            # Store the result
            result_df.at[index, 'IdHAL'] = hal_id
            
        except Exception as e:
            # In case of error, mark as unavailable
            result_df.at[index, 'IdHAL'] = "Id non disponible"
            print(f"Erreur lors de l'extraction de l'ID pour la ligne {index}: {str(e)}")
    
    return result_df