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
    Extract HAL identifier using a two-step approach:
    1. First, try the standard format 'prenom-nom' with direct API query
    2. If no results, fall back to complex variant matching
    
    Args:
        title (str): Title/full name from CSV
        nom (str): Last name (fallback)
        prenom (str): First name (fallback)  
        threshold (int): Acceptable Levenshtein distance threshold
    
    Returns:
        str: authIdHal_s if found and verified, otherwise return None
    """
    
    # If no title provided, fall back to nom/prenom
    if not title or not title.strip():
        if nom and prenom:
            title = f"{prenom} {nom}"
        else:
            return " "
    
    title_clean = title.strip()
    
    # Extract prenom and nom from title or use provided values
    if nom and prenom:
        prenom_search = prenom.strip()
        nom_search = nom.strip()
    else:
        # Parse title to extract potential prenom/nom
        title_parts = title_clean.split()
        if len(title_parts) >= 2:
            prenom_search = title_parts[0]
            nom_search = " ".join(title_parts[1:])
        else:
            return " "
    
    # STEP 1: TRY STANDARD FORMAT 'prenom-nom'
    
    # Construct standard ID format: prenom-nom (lowercase, with hyphens)
    standard_id = [f"{prenom_search.lower()}-{nom_search.lower()}", f"{prenom_search.lower()}{nom_search.lower()}"]
    # Clean the constructed ID (remove spaces, special chars)
    standard_id_clean=[]
    for st_id in standard_id:
        standard_id_clean.append(st_id.replace(" ", "-").replace("'", "").replace(".", ""))
    
    # Test on both APIs with the constructed ID
    base_apis = [
        'https://api.archives-ouvertes.fr/search/',
        'https://api.archives-ouvertes.fr/search/tel/'
    ]
    
    for base_api in base_apis:
        for st_id in standard_id_clean:
            query_url = f'{base_api}?q=authIdHal_s:"{st_id}"&wt=json&rows=1'
            print ("Query", query_url)
        
            try:
                response = requests.get(query_url)
                if response.status_code == 200:
                    data = response.json()
                    num_found = data.get("response", {}).get("numFound", 0)
                
                    # If we found at least one document, the ID exists
                    if num_foun >= 1:
                        return st_id
                    
            except Exception:
                continue
    
    # Search for publications containing the author to get all possible IDs
    all_candidate_ids = set()
    
    # Multiple query strategies to find publications by this author
    query_strategies = [
        f'authFullName_s:"{title_clean}"',
        f'authFullName_t:"{title_clean}"',
        f'authFullName_s:"{prenom_search} {nom_search}"',
        f'authFullName_t:"{prenom_search} {nom_search}"',
        #f'authFirstName_s:"{prenom_search}" AND authLastName_s:"{nom_search}"'
    ]
    
    for base_api in base_apis:
        for query in query_strategies:
            query_url = f'{base_api}?q={query}&fl=authIdHal_s,authFirstName_s,authLastName_s,authFullName_s&wt=json'
            
            try:
                response = requests.get(query_url)
                if response.status_code != 200:
                    continue
                
                data = response.json()
                publications = data.get("response", {}).get("docs", [])
                
                for pub in publications:
                    auth_ids = pub.get("authIdHal_s", [])
                    auth_first_names = pub.get("authFirstName_s", [])
                    auth_last_names = pub.get("authLastName_s", [])
                    auth_full_names = pub.get("authFullName_s", [])
                    
                    # NEW APPROACH: Don't require equal lengths, process each ID individually
                    if isinstance(auth_ids, list):
                        for i, auth_id in enumerate(auth_ids):
                            if auth_id and not auth_id.lower().startswith("hal"):
                                # Get corresponding names if available (with bounds checking)
                                hal_first = auth_first_names[i] if i < len(auth_first_names) else ""
                                hal_last = auth_last_names[i] if i < len(auth_last_names) else ""
                                hal_full = auth_full_names[i] if i < len(auth_full_names) else ""
                                
                                # Verify if this ID corresponds to our author
                                if _is_matching_author(title_clean, prenom_search, nom_search, 
                                                     hal_first, hal_last, hal_full, threshold):
                                    all_candidate_ids.add(auth_id)
                    elif auth_ids:  # Single ID case
                        hal_first = auth_first_names[0] if auth_first_names else ""
                        hal_last = auth_last_names[0] if auth_last_names else ""
                        hal_full = auth_full_names[0] if auth_full_names else ""
                        
                        if _is_matching_author(title_clean, prenom_search, nom_search,
                                             hal_first, hal_last, hal_full, threshold):
                            all_candidate_ids.add(auth_ids)
                            
            except Exception:
                continue
    
    if not all_candidate_ids:
        return " "
    
    # STEP 3: VALIDATE CANDIDATES USING VARIANT MATCHING
    
    # Create name variants for more robust matching
    nom_variants = _create_name_variants(nom_search.lower())
    prenom_variants = _create_name_variants(prenom_search.lower())
    
    matching_ids = []
    
    for candidate_id in all_candidate_ids:
        if _validate_id_with_variants(candidate_id, prenom_variants, nom_variants, threshold):
            matching_ids.append(candidate_id)
    
    if matching_ids:
        return matching_ids[0]  # Return first validated match
    
    return " "


def _is_matching_author(title_csv, prenom_search, nom_search, hal_first, hal_last, hal_full, threshold):
    """
    Check if HAL author data matches our search criteria
    """
    # Primary verification with title matching
    if hal_full and is_same_author_levenshtein(title_csv, hal_full, threshold):
        return True
    
    # Secondary verification with name components
    if hal_first and hal_last:
        # Check normal order (prenom nom)
        if (levenshtein_distance(prenom_search.lower(), hal_first.lower()) <= threshold and 
            levenshtein_distance(nom_search.lower(), hal_last.lower()) <= threshold):
            return True
        
        # Check inverted order (nom prenom)
        if (levenshtein_distance(nom_search.lower(), hal_first.lower()) <= threshold and 
            levenshtein_distance(prenom_search.lower(), hal_last.lower()) <= threshold):
            return True
    
    # Fallback with full name reconstruction
    if hal_first and hal_last:
        hal_full_reconstructed = f"{hal_first} {hal_last}"
        if is_same_author_levenshtein(title_csv, hal_full_reconstructed, threshold):
            return True
        
        # Try inverted reconstruction
        hal_full_inverted = f"{hal_last} {hal_first}"
        if is_same_author_levenshtein(title_csv, hal_full_inverted, threshold):
            return True
    
    return False


def _create_name_variants(name):
    """
    Create variants of a name for comparison
    """
    variants = set()
    name_clean = name.strip().lower()
    
    # Original version
    variants.add(name_clean)
    
    # Version without hyphens
    variants.add(name_clean.replace('-', ''))
    
    # Version with spaces replaced by hyphens
    variants.add(name_clean.replace(' ', '-'))
    
    # Version without spaces
    variants.add(name_clean.replace(' ', ''))
    
    # If name contains spaces, create variants
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
    
    # If name contains hyphens, create variants
    if '-' in name_clean:
        words = name_clean.split('-')
        for word in words:
            if len(word) > 1:
                variants.add(word)
    
    return variants


def _validate_id_with_variants(auth_id, prenom_variants, nom_variants, threshold):
    """
    Validate if an auth_id matches using name variants
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
            
            # Test: part1=prenom, part2=nom
            for prenom_var in prenom_variants:
                for nom_var in nom_variants:
                    if (levenshtein_distance(prenom_var, part1) <= threshold and 
                        levenshtein_distance(nom_var, part2) <= threshold):
                        return True
            
            # Test: part1=nom, part2=prenom
            for prenom_var in prenom_variants:
                for nom_var in nom_variants:
                    if (levenshtein_distance(nom_var, part1) <= threshold and 
                        levenshtein_distance(prenom_var, part2) <= threshold):
                        return True
    
    # APPROACH 2: Test combined parts
    for split_point in range(1, len(parts)):
        first_part = ''.join(parts[:split_point])
        second_part = ''.join(parts[split_point:])
        
        # Test: first_part=prenom, second_part=nom
        for prenom_var in prenom_variants:
            for nom_var in nom_variants:
                if (levenshtein_distance(prenom_var, first_part) <= threshold and 
                    levenshtein_distance(nom_var, second_part) <= threshold):
                    return True
        
        # Test: first_part=nom, second_part=prenom
        for prenom_var in prenom_variants:
            for nom_var in nom_variants:
                if (levenshtein_distance(nom_var, first_part) <= threshold and 
                    levenshtein_distance(prenom_var, second_part) <= threshold):
                    return True
    
    # APPROACH 3: Partial matching (nom must be found)
    for nom_var in nom_variants:
        if len(nom_var) >= 3 and nom_var in auth_id_lower:
            return True
    
    # APPROACH 4: Initials matching
    if len(parts) == 1:  # Single part ID
        # Test if it matches initials
        for prenom_var in prenom_variants:
            for nom_var in nom_variants:
                if len(prenom_var) > 0 and len(nom_var) > 0:
                    initials = prenom_var[0] + nom_var[0]
                    if initials == auth_id_lower:
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
                # Only add if we haven't seen this document ID before
                if docid not in seen_docids:
                    # Add API source information for potential debugging
                    pub['_api_source'] = 'HAL-TEL' if 'tel' in base_api else 'HAL'
                    all_publications.append(pub)
                    seen_docids.add(docid)
                    
        except Exception as e:
            print(f"Error querying {base_api}: {str(e)}")
            continue
    
    return all_publications, seen_docids

def get_hal_data(nom, prenom, title=None, period=None, domain_filter=None, type_filter=None, threshold=DEFAULT_THRESHOLD):
    """
    Main function with title-based search as primary method and name/firstname as fallback
    Now searches both HAL and HAL-TEL APIs transparently
    
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
    # This now uses the modified extract_author_id_simple that queries both APIs
    
    if title and title.strip():
        author_id = extract_author_id_simple(title, nom, prenom, threshold)
        search_term = title.strip()
    elif nom and prenom:
        author_id = extract_author_id_simple(f"{prenom} {nom}", nom, prenom, threshold)
        search_term = f"{prenom} {nom}"
    else:
        print("Either title or nom/prenom must be provided.")
        return pd.DataFrame()
    
    # STEP 2: BUILD QUERY FILTERS
    
    # Build filters string
    filters = ""
    
    if period:
        try:
            start_year, end_year = period.split("-")
            filters += f"&fq=publicationDateY_i:[{start_year} TO {end_year}]"
        except ValueError:
            print("Period format must be YYYY-YYYY.")
            return pd.DataFrame()

    if domain_filter:
        domain_codes = [get_domain_code(d) for d in domain_filter if get_domain_code(d)]
        if domain_codes:
            filters += f"&fq=domain_s:({' OR '.join(domain_codes)})"

    if type_filter:
        type_codes = [get_type_code(t) for t in type_filter if get_type_code(t)]
        if type_codes:
            # Use enhanced linking function
            linked_type_codes = get_linked_types(type_codes)
            filters += f"&fq=docType_s:({' OR '.join(linked_type_codes)})"

    # Fields for publications
    fields = "&fl=authIdHal_s,authFirstName_s,authLastName_s,authFullName_s,docid,title_s,publicationDateY_i,docType_s,domain_s,keyword_s,labStructName_s&wt=json&rows=100"
    filters += fields
    
    # STEP 3: EXECUTE QUERIES ON BOTH APIS
    
    # Primary query with main search term
    query_base_1 = f'?q=authFullName_t:"{search_term}"'
    all_publications, seen_docids = execute_hal_query_multi_api(query_base_1, filters)
    
    # Secondary query with inverted name order (if we have nom/prenom and it's different)
    if nom and prenom:
        inverted_search = f"{nom} {prenom}"
        if inverted_search != search_term:  # Avoid duplicate queries
            query_base_2 = f'?q=authFullName_t:"{inverted_search}"'
            additional_pubs, additional_docids = execute_hal_query_multi_api(query_base_2, filters)
            
            # Merge results, avoiding duplicates
            for pub in additional_pubs:
                docid = pub.get("docid", "")
                if docid not in seen_docids:
                    all_publications.append(pub)
                    seen_docids.add(docid)
    
    if not all_publications:
        print(f"No publications found for {search_term}")
        return pd.DataFrame()

    # STEP 4: POST-FILTERING (same as before)
    
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
            authors_sorted = sorted(authors) if authors else [" "]
            
            # Get API source for information (optional, can be removed)
            api_source = pub.get("_api_source", "HAL")

            scientist_data.append({
                "Nom": nom,  
                "Prenom": prenom,
                "Title": title if title else f"{prenom} {nom}",  # Add title to output
                "IdHAL de l'Auteur": author_id,  # ID EXTRACTED USING TITLE OR NAME FROM BOTH APIs
                "IdHAL des auteurs de la publication": authors_sorted,
                "Titre": pub.get("title_s", "Titre non disponible"),
                "Docid": pub.get("docid", " "),
                "Année de Publication": pub.get("publicationDateY_i", "Année non disponible"),
                "Type de Document": map_doc_type(pub.get("docType_s", "Type non défini")),
                "Domaine": map_domain(pub.get("domain_s", "Domaine non défini")),
                "Mots-clés": pub.get("keyword_s", []),
                "Laboratoire de Recherche": pub.get("labStructName_s", "Non disponible"),
                "Source API": api_source  # Optional: track which API provided the result
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
            result_df.at[index, 'IdHAL'] = " "
            print(f"Erreur lors de l'extraction de l'ID pour la ligne {index}: {str(e)}")
    
    return result_df
