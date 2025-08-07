# -*- coding: utf-8 -*-

# detection_doublons_homonymes.py

import pandas as pd
import requests
import time
import sys
from difflib import SequenceMatcher
from collections import defaultdict
import re
import ast
from typing import Dict, List, Tuple, Optional

class DuplicateHomonymDetector:
    """
    Duplicate and homonym detector based on HAL API and authIdPerson_i
    """
    
    def __init__(self):
        self.api_delay = 0.05  # Delay between API requests - reduced to speed up
        self.similarity_threshold = 0.8  # Title similarity threshold
        self.year_gap_threshold = 2  # Maximum year gap for duplicates
        self.stop_requested = False  # Stop flag for this instance
    
    def set_stop_flag(self, stop_flag):
        """
        Sets the stop flag for this instance
        
        Args:
            stop_flag (bool): Flag to stop processing
        """
        self.stop_requested = stop_flag
        
    def extract_main_title(self, title_field):
        """
        Extracts the main title from a HAL title field
        
        Args:
            title_field: Title field from HAL data
            
        Returns:
            str: Cleaned main title
        """
        if pd.isna(title_field) or title_field == '':
            return ''
            
        title_str = str(title_field)
        
        if title_str.startswith('['):
            try:
                title_list = ast.literal_eval(title_str)
                if isinstance(title_list, list) and len(title_list) > 0:
                    return str(title_list[0]).strip()
            except:
                match = re.search(r'\[\'([^\']+)\'', title_str)
                if match:
                    return match.group(1).strip()
                    
        return title_str.strip()
    
    def calculate_title_similarity(self, title1: str, title2: str) -> float:
        """
        Calculates similarity between two titles
        
        Args:
            title1 (str): First title
            title2 (str): Second title
            
        Returns:
            float: Similarity score between 0 and 1
        """
        if not title1 or not title2:
            return 0.0
        
        # Clean titles
        title1_clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', title1.lower())
        title2_clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', title2.lower())
        
        title1_clean = re.sub(r'\s+', ' ', title1_clean).strip()
        title2_clean = re.sub(r'\s+', ' ', title2_clean).strip()
        
        return SequenceMatcher(None, title1_clean, title2_clean).ratio()
    
    def query_hal_by_docid(self, docid: str) -> Optional[Dict]:
        """
        Queries HAL API with a specific docid
        
        Args:
            docid (str): HAL document ID
            
        Returns:
            Optional[Dict]: Document information or None if not found
        """
        # Check for stop request before each API call
        if self.stop_requested:
            return None
            
        if not docid or docid == "Id non disponible":
            return None
            
        try:
            url = f"https://api.archives-ouvertes.fr/search/?q=docid:\"{docid}\"&fl=authIdPerson_i,title_s,publicationDateY_i,docType_s,domain_s,keyword_s,labStructName_s,authFullName_s&wt=json"
            
            response = requests.get(url)
            time.sleep(self.api_delay)  # Respect API limits
            
            if response.status_code == 200:
                data = response.json()
                docs = data.get("response", {}).get("docs", [])
                if docs:
                    return docs[0]  # First document found
            
            return None
            
        except Exception as e:
            print(f"Erreur lors de la requête HAL pour docid {docid}: {e}")
            return None
    
    def extract_laboratory_info(self, csv_row: pd.Series, laboratory_df: Optional[pd.DataFrame] = None) -> str:
        """
        Extracts laboratory information from input file or data
        
        Args:
            csv_row (pd.Series): CSV row with author data
            laboratory_df (Optional[pd.DataFrame]): Optional DataFrame containing laboratory information
            
        Returns:
            str: Laboratory information or empty string
        """
        # From results file
        if 'Laboratoire de Recherche' in csv_row and pd.notna(csv_row['Laboratoire de Recherche']):
            return str(csv_row['Laboratoire de Recherche'])
        
        # From input file if provided
        if laboratory_df is not None:
            matching_rows = laboratory_df[
                (laboratory_df['nom'].str.lower() == csv_row['Nom'].lower()) & 
                (laboratory_df['prenom'].str.lower() == csv_row['Prenom'].lower())
            ]
            if not matching_rows.empty:
                if 'unite_de_recherche' in matching_rows.columns:
                    return str(matching_rows.iloc[0]['unite_de_recherche'])
        
        return ""
    
    def analyze_csv_file(self, csv_file_path: str, laboratory_file_path: Optional[str] = None) -> Dict:
        """
        Analyzes a CSV file to detect duplicates and homonyms
        
        Args:
            csv_file_path (str): Path to the CSV file to analyze
            laboratory_file_path (Optional[str]): Optional path to laboratory file
            
        Returns:
            Dict: Dictionary containing analysis results
        """
        print("="*60)
        print("ANALYSE DES DOUBLONS ET HOMONYMES")
        print("="*60)
        
        # Check for stop request at the beginning
        if self.stop_requested:
            print("Analyse arrêtée avant le début")
            return self._create_empty_results()
        
        # Load data
        df = pd.read_csv(csv_file_path)
        laboratory_df = None
        if laboratory_file_path:
            try:
                laboratory_df = pd.read_csv(laboratory_file_path)
                print(f"Fichier laboratoire chargé: {len(laboratory_df)} entrées")
            except Exception as e:
                print(f"Impossible de charger le fichier laboratoire: {e}")
        
        print(f"Fichier CSV chargé: {len(df)} publications")
        
        # Group by (nom, prénom)
        author_groups = df.groupby(['Nom', 'Prenom'])
        
        results = {
            'duplicate_cases': [],
            'homonym_cases': [],
            'multi_thesis_cases': [],
            'no_authid_cases': [],
            'collaborator_cases': [],
            'summary': {
                'total_publications': len(df),
                'authors_with_multiple_pubs': 0,
                'duplicate_publications': 0,
                'homonym_publications': 0,
                'multi_thesis_publications': 0
            }
        }
        
        processed_authors = 0
        total_authors = len([group for _, group in author_groups if len(group) >= 2])
        
        for (nom, prenom), group in author_groups:
            if len(group) < 2:
                continue  # Skip authors with single publication
            
            # Check for stop request at each iteration
            if self.stop_requested:
                print(f"\nAnalyse interrompue après {processed_authors} auteurs traités")
                break
            
            processed_authors += 1
            results['summary']['authors_with_multiple_pubs'] += 1
            
            print(f"Analyse de {nom} {prenom} ({len(group)} publications) - {processed_authors}/{total_authors}...", end='\r')
            sys.stdout.flush()  # Force immediate display
            
            # Enrich data with HAL information
            enriched_data = []
            for idx, row in group.iterrows():
                # Check for stop request even during enrichment
                if self.stop_requested:
                    print(f"\nAnalyse interrompue pendant l'enrichissement de {nom} {prenom}")
                    break
                    
                hal_data = self.query_hal_by_docid(row['Docid'])
                lab_info = self.extract_laboratory_info(row, laboratory_df)
                
                enriched_data.append({
                    'original_index': idx,
                    'row_data': row,
                    'hal_data': hal_data,
                    'laboratory_info': lab_info,
                    'main_title': self.extract_main_title(row['Titre'])
                })
            
            # If stop requested, exit main loop
            if self.stop_requested:
                break
            
            # Analyze this author group
            group_analysis = self.analyze_author_group(nom, prenom, enriched_data)
            
            # Integrate results
            results['duplicate_cases'].extend(group_analysis['duplicates'])
            results['homonym_cases'].extend(group_analysis['homonyms'])
            results['multi_thesis_cases'].extend(group_analysis['multi_thesis'])
            results['no_authid_cases'].extend(group_analysis['no_authid'])
            results['collaborator_cases'].extend(group_analysis['collaborators'])
        
        # Calculate final statistics
        results['summary']['duplicate_publications'] = len(results['duplicate_cases'])
        results['summary']['homonym_publications'] = len(results['homonym_cases'])
        results['summary']['multi_thesis_publications'] = len(results['multi_thesis_cases'])
        
        if self.stop_requested:
            print(f"\nAnalyse INTERROMPUE après traitement de {processed_authors} auteurs")
        else:
            print(f"\nAnalyse terminée pour {processed_authors} auteurs avec publications multiples")
        
        return results
    
    def _create_empty_results(self):
        """
        Creates empty results structure for interrupted analyses
        
        Returns:
            Dict: Empty results structure
        """
        return {
            'duplicate_cases': [],
            'homonym_cases': [],
            'multi_thesis_cases': [],
            'no_authid_cases': [],
            'collaborator_cases': [],
            'summary': {
                'total_publications': 0,
                'authors_with_multiple_pubs': 0,
                'duplicate_publications': 0,
                'homonym_publications': 0,
                'multi_thesis_publications': 0
            }
        }
    
    def analyze_author_group(self, nom: str, prenom: str, enriched_data: List[Dict]) -> Dict:
        """
        Analyzes a group of publications for the same author (nom, prénom)
        
        Args:
            nom (str): Last name
            prenom (str): First name
            enriched_data (List[Dict]): List of enriched data for this author
            
        Returns:
            Dict: Dictionary with detected cases for this author
        """
        group_results = {
            'duplicates': [],
            'homonyms': [],
            'multi_thesis': [],
            'no_authid': [],
            'collaborators': []
        }
        
        # Separate based on authIdPerson_i availability
        with_authid = []
        without_authid = []
        
        for data in enriched_data:
            hal_data = data['hal_data']
            if hal_data and 'authIdPerson_i' in hal_data and hal_data['authIdPerson_i']:
                # Extract author IDs
                auth_ids = hal_data['authIdPerson_i']
                if isinstance(auth_ids, list) and auth_ids:
                    data['auth_ids'] = auth_ids
                    with_authid.append(data)
                else:
                    without_authid.append(data)
            else:
                without_authid.append(data)
        
        # Analyze those with authIdPerson_i
        if len(with_authid) >= 2:
            authid_analysis = self.analyze_with_authid(nom, prenom, with_authid)
            group_results['duplicates'].extend(authid_analysis['duplicates'])
            group_results['homonyms'].extend(authid_analysis['homonyms'])
            group_results['multi_thesis'].extend(authid_analysis['multi_thesis'])
            group_results['collaborators'].extend(authid_analysis['collaborators'])
        
        # Analyze those without authIdPerson_i
        if len(without_authid) >= 2:
            no_authid_analysis = self.analyze_without_authid(nom, prenom, without_authid)
            group_results['duplicates'].extend(no_authid_analysis['duplicates'])
            group_results['no_authid'].extend(no_authid_analysis['no_authid'])
        
        # Analyze mixed cases (with and without authIdPerson_i)
        if with_authid and without_authid:
            mixed_analysis = self.analyze_mixed_cases(nom, prenom, with_authid, without_authid)
            group_results['homonyms'].extend(mixed_analysis['homonyms'])
            group_results['no_authid'].extend(mixed_analysis['no_authid'])
        
        return group_results
    
    def analyze_with_authid(self, nom: str, prenom: str, data_list: List[Dict]) -> Dict:
        """
        Analyzes publications with available authIdPerson_i
        
        Args:
            nom (str): Last name
            prenom (str): First name
            data_list (List[Dict]): List of data with authIdPerson_i
            
        Returns:
            Dict: Analysis results for this group
        """
        results = {
            'duplicates': [],
            'homonyms': [],
            'multi_thesis': [],
            'collaborators': []
        }
        
        # Group by authIdPerson_i
        authid_groups = defaultdict(list)
        
        for data in data_list:
            auth_ids = data['auth_ids']
            # Create key based on author IDs (sorted for consistency)
            authid_key = tuple(sorted(auth_ids))
            authid_groups[authid_key].append(data)
        
        # Analyze each authIdPerson_i group
        all_authid_keys = list(authid_groups.keys())
        
        for authid_key, group in authid_groups.items():
            if len(group) >= 2:
                # Same authIdPerson_i: duplicates or multi-thesis
                same_authid_analysis = self.analyze_same_authid_group(nom, prenom, group)
                results['duplicates'].extend(same_authid_analysis['duplicates'])
                results['multi_thesis'].extend(same_authid_analysis['multi_thesis'])
                results['collaborators'].extend(same_authid_analysis['collaborators'])
        
        # Compare different authIdPerson_i groups to detect homonyms
        for i in range(len(all_authid_keys)):
            for j in range(i + 1, len(all_authid_keys)):
                key1, key2 = all_authid_keys[i], all_authid_keys[j]
                
                # Check if authIdPerson_i are truly different
                if not set(key1).intersection(set(key2)):  # No common IDs
                    # Homonyms detected
                    for data1 in authid_groups[key1]:
                        for data2 in authid_groups[key2]:
                            results['homonyms'].append({
                                'author': f"{nom} {prenom}",
                                'publication1': {
                                    'index': data1['original_index'],
                                    'title': data1['main_title'],
                                    'year': data1['row_data']['Année de Publication'],
                                    'domain': data1['row_data']['Domaine'],
                                    'lab': data1['laboratory_info'],
                                    'authids': data1['auth_ids']
                                },
                                'publication2': {
                                    'index': data2['original_index'],
                                    'title': data2['main_title'],
                                    'year': data2['row_data']['Année de Publication'],
                                    'domain': data2['row_data']['Domaine'],
                                    'lab': data2['laboratory_info'],
                                    'authids': data2['auth_ids']
                                },
                                'type': 'HOMONYME_AUTHID_DIFFERENT'
                            })
        
        return results
    
    def analyze_same_authid_group(self, nom: str, prenom: str, group: List[Dict]) -> Dict:
        """
        Analyzes a group of publications with the same authIdPerson_i
        
        Args:
            nom (str): Last name
            prenom (str): First name
            group (List[Dict]): List of publications with same authIdPerson_i
            
        Returns:
            Dict: Analysis results for this group
        """
        results = {
            'duplicates': [],
            'multi_thesis': [],
            'collaborators': []
        }
        
        # Compare all pairs
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                data1, data2 = group[i], group[j]
                
                # Calculate similarity
                title_sim = self.calculate_title_similarity(
                    data1['main_title'], 
                    data2['main_title']
                )
                
                year1 = data1['row_data']['Année de Publication']
                year2 = data2['row_data']['Année de Publication']
                year_gap = abs(year1 - year2) if pd.notna(year1) and pd.notna(year2) else 999
                
                # Decision criteria
                if title_sim >= self.similarity_threshold and year_gap <= self.year_gap_threshold:
                    # Probable duplicate
                    results['duplicates'].append({
                        'author': f"{nom} {prenom}",
                        'publication1': {
                            'index': data1['original_index'],
                            'title': data1['main_title'],
                            'year': year1,
                            'domain': data1['row_data']['Domaine'],
                            'docid': data1['row_data']['Docid']
                        },
                        'publication2': {
                            'index': data2['original_index'],
                            'title': data2['main_title'],
                            'year': year2,
                            'domain': data2['row_data']['Domaine'],
                            'docid': data2['row_data']['Docid']
                        },
                        'similarity_score': title_sim,
                        'year_gap': year_gap,
                        'type': 'DOUBLON_MEME_AUTHID'
                    })
                
                elif year_gap > 3:  # Significant year gap
                    # Check if it's a collaborator vs main author
                    is_collaborator = self.check_if_collaborator(data1, data2, nom, prenom)
                    
                    if is_collaborator:
                        results['collaborators'].append({
                            'author': f"{nom} {prenom}",
                            'main_thesis': data1 if year1 < year2 else data2,
                            'collaboration': data2 if year1 < year2 else data1,
                            'type': 'COLLABORATEUR_THESE'
                        })
                    else:
                        # Multi-thesis (rare but possible)
                        results['multi_thesis'].append({
                            'author': f"{nom} {prenom}",
                            'publication1': {
                                'index': data1['original_index'],
                                'title': data1['main_title'],
                                'year': year1,
                                'domain': data1['row_data']['Domaine']
                            },
                            'publication2': {
                                'index': data2['original_index'],
                                'title': data2['main_title'],
                                'year': year2,
                                'domain': data2['row_data']['Domaine']
                            },
                            'year_gap': year_gap,
                            'similarity_score': title_sim,
                            'type': 'MULTI_THESES'
                        })
        
        return results
    
    def check_if_collaborator(self, data1: Dict, data2: Dict, nom: str, prenom: str) -> bool:
        """
        Checks if one of the publications corresponds to a collaboration
        rather than a main thesis by the author
        
        Args:
            data1 (Dict): First publication data
            data2 (Dict): Second publication data
            nom (str): Last name
            prenom (str): First name
            
        Returns:
            bool: True if collaboration detected, False otherwise
        """
        # Heuristics to detect collaborations:
        
        # 1. Check if author appears in author list
        for data in [data1, data2]:
            hal_data = data['hal_data']
            if hal_data and 'authFullName_s' in hal_data:
                auth_names = hal_data['authFullName_s']
                if isinstance(auth_names, list):
                    # Check author position in list
                    author_full_name = f"{prenom} {nom}"
                    author_positions = []
                    
                    for i, full_name in enumerate(auth_names):
                        if self.names_match(full_name, author_full_name):
                            author_positions.append(i)
                    
                    # If author is not in first position, it's probably a collaboration
                    if author_positions and min(author_positions) > 0:
                        return True
        
        # 2. Significant differences in domain/laboratory
        domain1 = data1['row_data']['Domaine']
        domain2 = data2['row_data']['Domaine']
        lab1 = data1['laboratory_info']
        lab2 = data2['laboratory_info']
        
        if domain1 != domain2 and lab1 != lab2:
            return True
        
        return False
    
    def names_match(self, full_name: str, target_name: str) -> bool:
        """
        Checks if two names match approximately
        
        Args:
            full_name (str): Full name from publication
            target_name (str): Target name to match
            
        Returns:
            bool: True if names match, False otherwise
        """
        if not full_name or not target_name:
            return False
        
        # Normalize names
        full_clean = re.sub(r'[^a-zA-Z\s]', ' ', full_name.lower())
        target_clean = re.sub(r'[^a-zA-Z\s]', ' ', target_name.lower())
        
        full_clean = re.sub(r'\s+', ' ', full_clean).strip()
        target_clean = re.sub(r'\s+', ' ', target_clean).strip()
        
        # Check if all words in target name are in full name
        target_words = set(target_clean.split())
        full_words = set(full_clean.split())
        
        return target_words.issubset(full_words)
    
    def analyze_without_authid(self, nom: str, prenom: str, data_list: List[Dict]) -> Dict:
        """
        Analyzes publications without authIdPerson_i (fallback on title similarity)
        
        Args:
            nom (str): Last name
            prenom (str): First name
            data_list (List[Dict]): List of publications without authIdPerson_i
            
        Returns:
            Dict: Analysis results for this group
        """
        results = {
            'duplicates': [],
            'no_authid': []
        }
        
        # Compare all pairs
        for i in range(len(data_list)):
            for j in range(i + 1, len(data_list)):
                data1, data2 = data_list[i], data_list[j]
                
                title_sim = self.calculate_title_similarity(
                    data1['main_title'], 
                    data2['main_title']
                )
                
                year1 = data1['row_data']['Année de Publication']
                year2 = data2['row_data']['Année de Publication']
                year_gap = abs(year1 - year2) if pd.notna(year1) and pd.notna(year2) else 999
                
                # Stricter criteria without authIdPerson_i
                if title_sim >= 0.9 and year_gap <= 1:
                    results['duplicates'].append({
                        'author': f"{nom} {prenom}",
                        'publication1': {
                            'index': data1['original_index'],
                            'title': data1['main_title'],
                            'year': year1,
                            'docid': data1['row_data']['Docid']
                        },
                        'publication2': {
                            'index': data2['original_index'],
                            'title': data2['main_title'],
                            'year': year2,
                            'docid': data2['row_data']['Docid']
                        },
                        'similarity_score': title_sim,
                        'year_gap': year_gap,
                        'type': 'DOUBLON_SANS_AUTHID'
                    })
                else:
                    results['no_authid'].append({
                        'author': f"{nom} {prenom}",
                        'publications': [data1, data2],
                        'type': 'SANS_AUTHID_AMBIGUOUS'
                    })
        
        return results
    
    def analyze_mixed_cases(self, nom: str, prenom: str, with_authid: List[Dict], without_authid: List[Dict]) -> Dict:
        """
        Analyzes cases where some publications have authIdPerson_i and others don't
        
        Args:
            nom (str): Last name
            prenom (str): First name
            with_authid (List[Dict]): Publications with authIdPerson_i
            without_authid (List[Dict]): Publications without authIdPerson_i
            
        Returns:
            Dict: Analysis results for mixed cases
        """
        results = {
            'homonyms': [],
            'no_authid': []
        }
        
        # For now, mark as cases to examine manually
        for data_no_authid in without_authid:
            results['no_authid'].append({
                'author': f"{nom} {prenom}",
                'publication_without_authid': data_no_authid,
                'publications_with_authid': with_authid,
                'type': 'MIXED_AUTHID_AVAILABILITY'
            })
        
        return results
    
    def display_results(self, results: Dict):
        """
        Displays analysis results
        
        Args:
            results (Dict): Results dictionary from analysis
        """
        print("\n" + "="*60)
        print("RÉSULTATS DE L'ANALYSE")
        print("="*60)
        
        summary = results['summary']
        print(f"Publications totales: {summary['total_publications']}")
        print(f"Auteurs avec publications multiples: {summary['authors_with_multiple_pubs']}")
        print(f"Cas de doublons détectés: {summary['duplicate_publications']}")
        print(f"Cas d'homonymes détectés: {summary['homonym_publications']}")
        print(f"Cas de multi-thèses détectés: {summary['multi_thesis_publications']}")
        
        if results['duplicate_cases']:
            print(f"\n{'='*50}")
            print("DOUBLONS DÉTECTÉS")
            print("="*50)
            for i, case in enumerate(results['duplicate_cases'][:10], 1):
                print(f"\n{i}. {case['author']} (Score: {case['similarity_score']:.3f})")
                print(f"   Titre 1: {case['publication1']['title'][:70]}...")
                print(f"   Titre 2: {case['publication2']['title'][:70]}...")
                print(f"   Années: {case['publication1']['year']} / {case['publication2']['year']}")
            
            if len(results['duplicate_cases']) > 10:
                print(f"\n... et {len(results['duplicate_cases']) - 10} autres doublons")
        
        if results['homonym_cases']:
            print(f"\n{'='*50}")
            print("HOMONYMES DÉTECTÉS")
            print("="*50)
            for i, case in enumerate(results['homonym_cases'][:10], 1):
                print(f"\n{i}. {case['author']}")
                print(f"   Titre 1: {case['publication1']['title'][:70]}...")
                print(f"   Titre 2: {case['publication2']['title'][:70]}...")
                print(f"   Années: {case['publication1']['year']} / {case['publication2']['year']}")
                print(f"   Domaines: {case['publication1']['domain']} / {case['publication2']['domain']}")
            
            if len(results['homonym_cases']) > 10:
                print(f"\n... et {len(results['homonym_cases']) - 10} autres homonymes")
        
        if results['collaborator_cases']:
            print(f"\n{'='*50}")
            print("COLLABORATIONS DÉTECTÉES")
            print("="*50)
            for i, case in enumerate(results['collaborator_cases'][:5], 1):
                print(f"\n{i}. {case['author']}")
                print(f"   Thèse principale: {case['main_thesis']['row_data']['Année de Publication']}")
                print(f"   Collaboration: {case['collaboration']['row_data']['Année de Publication']}")

