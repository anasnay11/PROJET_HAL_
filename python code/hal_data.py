#hal_data.py

# -*- coding: utf-8 -*-

import requests
import pandas as pd
from Levenshtein import distance as levenshtein_distance
from mapping import map_doc_type, map_domain, get_domain_code, get_type_code
from config import DEFAULT_THRESHOLD

def is_same_author_levenshtein(nom_csv, prenom_csv, nom_hal, prenom_hal, threshold=DEFAULT_THRESHOLD):
    """
    Directly compare a CSV author with an author found in HAL
    
    Args:
        nom_csv, prenom_csv: last name and first name from CSV file (ORIGINAL)
        nom_hal, prenom_hal: last name and first name found in HAL results
        threshold: acceptable distance threshold (configurable)
    
    Returns:
        bool: True if authors match
    """
    if not nom_hal or not prenom_hal:
        return False
    
    # Calculate distances (case-insensitive comparison)
    dist_nom = levenshtein_distance(nom_csv.lower(), nom_hal.lower())
    dist_prenom = levenshtein_distance(prenom_csv.lower(), prenom_hal.lower())
    
    # Match if both distances are acceptable
    return dist_nom <= threshold and dist_prenom <= threshold

def extract_author_id_simple(nom, prenom, threshold=DEFAULT_THRESHOLD):
    """
    Extract HAL identifier with verification
    
    Handles complex cases:
    - Hyphens in last names/first names 
    - Removed spaces 
    - Compound last name or first name 
    - Partial IDs (e.g: last name only)
    - Short formats (e.g: initials)
    
    Args:
        nom (str): Nom de famille
        prenom (str): Prénom
        threshold (int): Seuil de distance Levenshtein acceptable
    
    Returns:
        str: authIdHal_s if found and verified, otherwise "Id non disponible"
    """
    
    # Simple query to retrieve only IDs
    query_url = f'https://api.archives-ouvertes.fr/search/?q=authFullName_t:"{prenom} {nom}"&fl=authIdHal_s,authFirstName_s,authLastName_s,authFullName_s&wt=json&rows=100'
    
    try:
        response = requests.get(query_url)
        if response.status_code != 200:
            return "Id non disponible"
        
        data = response.json()
        publications = data.get("response", {}).get("docs", [])
        
        if not publications:
            return "Id non disponible"
        
        # Collect ALL found authIdHal_s
        all_author_ids = set()  # Use a set to avoid duplicates
        
        for pub in publications:
            auth_ids = pub.get("authIdHal_s", [])
            for auth_id in auth_ids:
                if auth_id:
                    all_author_ids.add(auth_id)
                
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
            # IMPORTANT: We no longer fallback on first name only to avoid
            # collisions with collaborators (e.g: Aubrun Christophe vs jean-christophe-ponsart)
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
                
                # Distance test on compact versions (utilise le threshold configurable + 1 pour la fallback)
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
        
    except Exception :
        return "Id non disponible"

def get_hal_data(nom, prenom, period=None, domain_filter=None, type_filter=None, threshold=DEFAULT_THRESHOLD):
    """
    Main corrected function with separate ID extraction
    
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
    
    # ==============================
    # STEP 2: QUERY FOR PUBLICATIONS
    # ==============================
    
    # Build query for publications
    query_url = f'https://api.archives-ouvertes.fr/search/?q=authFullName_t:"{prenom} {nom}"'
    
    # Apply filters if specified
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
            query_url += f"&fq=docType_s:({' OR '.join(type_codes)})"

    # Fields for publications (without author details for ID)
    query_url += "&fl=authIdHal_s,authFirstName_s,authLastName_s,authFullName_s,docid,title_s,publicationDateY_i,docType_s,domain_s,keyword_s,labStructName_s&wt=json&rows=100"

    # =================================
    # STEP 3: API CALL FOR PUBLICATIONS
    # =================================
    
    response = requests.get(query_url)
    
    if response.status_code != 200:
        return pd.DataFrame()

    data = response.json()
    publications = data.get("response", {}).get("docs", [])
    
    if not publications:
        return pd.DataFrame()

    # =============================================
    # STEP 4: LEVENSHTEIN FILTERING OF PUBLICATIONS
    # =============================================
    
    scientist_data = []
    
    for pub in publications:
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
                prenom_hal = name_parts[0]
                nom_hal = " ".join(name_parts[1:])
            else:
                continue
            
            # =============================================
            # LEVENSHTEIN COMPARISON TO FILTER PUBLICATIONS
            # =============================================
            
            if is_same_author_levenshtein(nom, prenom, nom_hal, prenom_hal, threshold):
                publication_match_found = True
                break  # One author matches, keep this publication
        
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