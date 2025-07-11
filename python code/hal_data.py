#hal_data.py

# -*- coding: utf-8 -*-

import requests
import pandas as pd
from Levenshtein import distance as levenshtein_distance
from mapping import map_doc_type, map_domain, get_domain_code, get_type_code, get_linked_types, get_hal_filter_for_post_processing
from config import DEFAULT_THRESHOLD

def is_same_author_levenshtein(nom_csv, prenom_csv, nom_hal, prenom_hal, threshold=DEFAULT_THRESHOLD):
    """
    Directly compare a CSV author with an author found in HAL
    Handles cases where HAL metadata has inverted first/last name fields
    
    Args:
        nom_csv, prenom_csv: last name and first name from CSV file (ORIGINAL)
        nom_hal, prenom_hal: last name and first name found in HAL results
        threshold: acceptable distance threshold (configurable)
    
    Returns:
        bool: True if authors match
    """
    if not nom_hal or not prenom_hal:
        return False
    
    # Calculate distances
    # Test 1: Normal order (CSV nom with HAL nom, CSV prenom with HAL prenom)
    dist_nom_normal = levenshtein_distance(nom_csv.lower(), nom_hal.lower())
    dist_prenom_normal = levenshtein_distance(prenom_csv.lower(), prenom_hal.lower())
    
    # Test 2: Inverted order (CSV nom with HAL prenom, CSV prenom with HAL nom)
    # This handles cases where HAL has authLastName_s and authFirstName_s swapped
    dist_nom_inverted = levenshtein_distance(nom_csv.lower(), prenom_hal.lower())
    dist_prenom_inverted = levenshtein_distance(prenom_csv.lower(), nom_hal.lower())
    
    # Match if either order works
    normal_match = (dist_nom_normal <= threshold and dist_prenom_normal <= threshold)
    inverted_match = (dist_nom_inverted <= threshold and dist_prenom_inverted <= threshold)
    
    return normal_match or inverted_match

def extract_author_id_simple(nom, prenom, threshold=DEFAULT_THRESHOLD):
    """
    Extract HAL identifier with verification - with double query (prenom nom + nom prenom)
    
    Handles complex cases:
    - Hyphens in last names/first names 
    - Removed spaces 
    - Compound last name or first name 
    - Partial IDs (e.g: last name only)
    - Short formats (e.g: initials)
    - Different name orders (Prenom Nom vs Nom Prenom)
    
    Args:
        nom (str): Nom de famille
        prenom (str): Prénom
        threshold (int): Seuil de distance Levenshtein acceptable
    
    Returns:
        str: authIdHal_s if found and verified, otherwise "Id non disponible"
    """
    
    # Double query to handle both name orders
    query_urls = [
        f'https://api.archives-ouvertes.fr/search/?q=authFullName_t:"{prenom} {nom}"&fl=authIdHal_s,authFirstName_s,authLastName_s,authFullName_s&wt=json&rows=100',
        f'https://api.archives-ouvertes.fr/search/?q=authFullName_t:"{nom} {prenom}"&fl=authIdHal_s,authFirstName_s,authLastName_s,authFullName_s&wt=json&rows=100'
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
                    if auth_id:
                        all_author_ids.add(auth_id)
                        
        except Exception:
            continue  # Try next query
    
    # If no IDs found from either query
    if not all_author_ids:
        return "Id non disponible"
                
    # ===========================
    # AUTHOR VARIANTS PREPARATION
    # ===========================
    
    # Normalize last name and first name (lowercase, no multiple spaces)
    nom_clean = nom.strip().lower()
    prenom_clean = prenom.strip().lower()
    
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
    
    # =====================
    # STEP 1: STRICT METHOD
    # =====================
    
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
    
    # ==========================================
    # STEP 2: FALLBACK METHOD - PARTIAL MATCHING
    # ==========================================
    
    matching_ids_partial = []
    
    for auth_id in all_author_ids:
        if not auth_id or auth_id == "Id non disponible":
            continue
        
        auth_id_lower = auth_id.lower()
        
        # =====================================================
        # STRATEGY 1: ONLY last name must be found for fallback
        # =====================================================
        
        partial_match_found = False
        
        # Test if a variant of the last name is contained in the ID
        for nom_var in nom_variants:
            if len(nom_var) >= 3 and nom_var in auth_id_lower:  # At least 3 characters to avoid false positives
                partial_match_found = True
                break
        
        # ====================
        # STRATEGY 2: Initials
        # ====================
        
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
        
        # ===============================================
        # STRATEGY 3: Approximate matching of complete ID
        # ===============================================
        
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

def get_hal_data(nom, prenom, period=None, domain_filter=None, type_filter=None, threshold=DEFAULT_THRESHOLD):
    """
    🔧 ENHANCED: Main function with granular thesis/HDR filtering
    
    Args:
        nom (str): Nom de famille
        prenom (str): Prénom
        period (str): Période au format "YYYY-YYYY"
        domain_filter (list): Liste des domaines à filtrer
        type_filter (list): Liste des types de documents à filtrer
        threshold (int): Seuil de distance Levenshtein acceptable
    
    Returns:
        pd.DataFrame: DataFrame contenant les publications trouvées
    """
    
    # ==============================
    # STEP 1: SEPARATE ID EXTRACTION
    # ==============================
    
    author_id = extract_author_id_simple(nom, prenom, threshold)
    
    # =====================================
    # STEP 2: DOUBLE QUERY FOR PUBLICATIONS
    # =====================================
    
    # Build base queries for both name orders
    name_variants = [f"{prenom} {nom}", f"{nom} {prenom}"]
    query_urls = []
    
    for name in name_variants:
        query_url = f'https://api.archives-ouvertes.fr/search/?q=authFullName_t:"{name}"'
        
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
    
    # ======================================
    # STEP 3: EXECUTE BOTH QUERIES AND MERGE
    # ======================================
    
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

    # ===============================
    # STEP 4: ENHANCED POST-FILTERING
    # ===============================
    
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
                
                # Test both interpretations
                match_1 = is_same_author_levenshtein(nom, prenom, nom_hal_1, prenom_hal_1, threshold)
                match_2 = is_same_author_levenshtein(nom, prenom, nom_hal_2, prenom_hal_2, threshold)
                
                if match_1 or match_2:
                    publication_match_found = True
                    break  # One author matches, keep this publication
            else:
                continue
        
        # If a match was found for this publication, add it
        if publication_match_found:
            authors = pub.get("authIdHal_s", [])
            authors_sorted = sorted(authors) if authors else ["Id non disponible"]

            scientist_data.append({
                "Nom": nom,  
                "Prenom": prenom,  
                "IdHAL de l'Auteur": author_id,  # ID EXTRACTED SEPARATELY
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