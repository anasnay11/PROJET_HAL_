# detection_doublons_homonymes.py
# -*- coding: utf-8 -*-

"""
Détection des doublons et homonymes basée sur authIdPerson_i
"""

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
    Détecteur de doublons et homonymes basé sur l'API HAL et authIdPerson_i
    """
    
    def __init__(self):
        self.api_delay = 0.05  # Délai entre les requêtes API - réduit pour accélérer
        self.similarity_threshold = 0.8  # Seuil de similarité des titres
        self.year_gap_threshold = 2  # Écart maximal d'années pour doublons
        self.stop_requested = False  # NOUVEAU: Flag d'arrêt pour cette instance
    
    def set_stop_flag(self, stop_flag):
        """Définit le flag d'arrêt pour cette instance"""
        self.stop_requested = stop_flag
        
    def extract_main_title(self, title_field):
        """Extrait le titre principal d'un champ titre HAL"""
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
        """Calcule la similarité entre deux titres"""
        if not title1 or not title2:
            return 0.0
        
        # Nettoyer les titres
        title1_clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', title1.lower())
        title2_clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', title2.lower())
        
        title1_clean = re.sub(r'\s+', ' ', title1_clean).strip()
        title2_clean = re.sub(r'\s+', ' ', title2_clean).strip()
        
        return SequenceMatcher(None, title1_clean, title2_clean).ratio()
    
    def query_hal_by_docid(self, docid: str) -> Optional[Dict]:
        """
        Interroge l'API HAL avec un docid spécifique
        MODIFIÉ: Ajout de vérification d'arrêt
        
        Args:
            docid: ID du document HAL
            
        Returns:
            Dict contenant les informations du document ou None
        """
        # Vérifier l'arrêt avant chaque requête API
        if self.stop_requested:
            return None
            
        if not docid or docid == "Id non disponible":
            return None
            
        try:
            url = f"https://api.archives-ouvertes.fr/search/?q=docid:\"{docid}\"&fl=authIdPerson_i,title_s,publicationDateY_i,docType_s,domain_s,keyword_s,labStructName_s,authFullName_s&wt=json"
            
            response = requests.get(url)
            time.sleep(self.api_delay)  # Respecter l'API
            
            if response.status_code == 200:
                data = response.json()
                docs = data.get("response", {}).get("docs", [])
                if docs:
                    return docs[0]  # Premier document trouvé
            
            return None
            
        except Exception as e:
            print(f"Erreur lors de la requête HAL pour docid {docid}: {e}")
            return None
    
    def extract_laboratory_info(self, csv_row: pd.Series, laboratory_df: Optional[pd.DataFrame] = None) -> str:
        """
        Extrait l'information du laboratoire depuis le fichier d'entrée ou les données
        
        Args:
            csv_row: Ligne du CSV avec les données de l'auteur
            laboratory_df: DataFrame optionnel contenant les informations de laboratoire
            
        Returns:
            Information du laboratoire ou chaîne vide
        """
        # Depuis le fichier de résultats
        if 'Laboratoire de Recherche' in csv_row and pd.notna(csv_row['Laboratoire de Recherche']):
            return str(csv_row['Laboratoire de Recherche'])
        
        # Depuis le fichier d'entrée si fourni
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
        Analyse un fichier CSV pour détecter doublons et homonymes
        MODIFIÉ: Ajout de vérifications d'arrêt
        
        Args:
            csv_file_path: Chemin vers le fichier CSV à analyser
            laboratory_file_path: Chemin optionnel vers le fichier des laboratoires
            
        Returns:
            Dictionnaire contenant les résultats de l'analyse
        """
        print("="*60)
        print("ANALYSE DES DOUBLONS ET HOMONYMES")
        print("="*60)
        
        # Vérifier l'arrêt dès le début
        if self.stop_requested:
            print("Analyse arrêtée avant le début")
            return self._create_empty_results()
        
        # Charger les données
        df = pd.read_csv(csv_file_path)
        laboratory_df = None
        if laboratory_file_path:
            try:
                laboratory_df = pd.read_csv(laboratory_file_path)
                print(f"Fichier laboratoire chargé: {len(laboratory_df)} entrées")
            except Exception as e:
                print(f"Impossible de charger le fichier laboratoire: {e}")
        
        print(f"Fichier CSV chargé: {len(df)} publications")
        
        # Grouper par (nom, prénom)
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
                continue  # Ignorer les auteurs avec une seule publication
            
            # NOUVEAU: Vérifier l'arrêt à chaque itération
            if self.stop_requested:
                print(f"\nAnalyse interrompue après {processed_authors} auteurs traités")
                break
            
            processed_authors += 1
            results['summary']['authors_with_multiple_pubs'] += 1
            
            print(f"Analyse de {nom} {prenom} ({len(group)} publications) - {processed_authors}/{total_authors}...", end='\r')
            sys.stdout.flush()  # Force l'affichage immédiat
            
            # Enrichir les données avec les informations HAL
            enriched_data = []
            for idx, row in group.iterrows():
                # NOUVEAU: Vérifier l'arrêt même pendant l'enrichissement
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
            
            # Si arrêt demandé, sortir de la boucle principale
            if self.stop_requested:
                break
            
            # Analyser ce groupe d'auteur
            group_analysis = self.analyze_author_group(nom, prenom, enriched_data)
            
            # Intégrer les résultats
            results['duplicate_cases'].extend(group_analysis['duplicates'])
            results['homonym_cases'].extend(group_analysis['homonyms'])
            results['multi_thesis_cases'].extend(group_analysis['multi_thesis'])
            results['no_authid_cases'].extend(group_analysis['no_authid'])
            results['collaborator_cases'].extend(group_analysis['collaborators'])
        
        # Calculer les statistiques finales
        results['summary']['duplicate_publications'] = len(results['duplicate_cases'])
        results['summary']['homonym_publications'] = len(results['homonym_cases'])
        results['summary']['multi_thesis_publications'] = len(results['multi_thesis_cases'])
        
        if self.stop_requested:
            print(f"\nAnalyse INTERROMPUE après traitement de {processed_authors} auteurs")
        else:
            print(f"\nAnalyse terminée pour {processed_authors} auteurs avec publications multiples")
        
        return results
    
    def _create_empty_results(self):
        """Crée une structure de résultats vide pour les analyses interrompues"""
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
        Analyse un groupe de publications pour un même auteur (nom, prénom)
        
        Args:
            nom, prenom: Nom et prénom de l'auteur
            enriched_data: Liste des données enrichies pour cet auteur
            
        Returns:
            Dictionnaire avec les cas détectés pour cet auteur
        """
        group_results = {
            'duplicates': [],
            'homonyms': [],
            'multi_thesis': [],
            'no_authid': [],
            'collaborators': []
        }
        
        # Séparer selon la disponibilité d'authIdPerson_i
        with_authid = []
        without_authid = []
        
        for data in enriched_data:
            hal_data = data['hal_data']
            if hal_data and 'authIdPerson_i' in hal_data and hal_data['authIdPerson_i']:
                # Extraire les IDs d'auteur
                auth_ids = hal_data['authIdPerson_i']
                if isinstance(auth_ids, list) and auth_ids:
                    data['auth_ids'] = auth_ids
                    with_authid.append(data)
                else:
                    without_authid.append(data)
            else:
                without_authid.append(data)
        
        # Analyser ceux avec authIdPerson_i
        if len(with_authid) >= 2:
            authid_analysis = self.analyze_with_authid(nom, prenom, with_authid)
            group_results['duplicates'].extend(authid_analysis['duplicates'])
            group_results['homonyms'].extend(authid_analysis['homonyms'])
            group_results['multi_thesis'].extend(authid_analysis['multi_thesis'])
            group_results['collaborators'].extend(authid_analysis['collaborators'])
        
        # Analyser ceux sans authIdPerson_i
        if len(without_authid) >= 2:
            no_authid_analysis = self.analyze_without_authid(nom, prenom, without_authid)
            group_results['duplicates'].extend(no_authid_analysis['duplicates'])
            group_results['no_authid'].extend(no_authid_analysis['no_authid'])
        
        # Analyser les cas mixtes (avec et sans authIdPerson_i)
        if with_authid and without_authid:
            mixed_analysis = self.analyze_mixed_cases(nom, prenom, with_authid, without_authid)
            group_results['homonyms'].extend(mixed_analysis['homonyms'])
            group_results['no_authid'].extend(mixed_analysis['no_authid'])
        
        return group_results
    
    def analyze_with_authid(self, nom: str, prenom: str, data_list: List[Dict]) -> Dict:
        """
        Analyse les publications avec authIdPerson_i disponible
        """
        results = {
            'duplicates': [],
            'homonyms': [],
            'multi_thesis': [],
            'collaborators': []
        }
        
        # Grouper par authIdPerson_i
        authid_groups = defaultdict(list)
        
        for data in data_list:
            auth_ids = data['auth_ids']
            # Créer une clé basée sur les IDs d'auteur (triés pour cohérence)
            authid_key = tuple(sorted(auth_ids))
            authid_groups[authid_key].append(data)
        
        # Analyser chaque groupe d'authIdPerson_i
        all_authid_keys = list(authid_groups.keys())
        
        for authid_key, group in authid_groups.items():
            if len(group) >= 2:
                # Même authIdPerson_i : doublons ou multi-thèses
                same_authid_analysis = self.analyze_same_authid_group(nom, prenom, group)
                results['duplicates'].extend(same_authid_analysis['duplicates'])
                results['multi_thesis'].extend(same_authid_analysis['multi_thesis'])
                results['collaborators'].extend(same_authid_analysis['collaborators'])
        
        # Comparer les différents groupes d'authIdPerson_i pour détecter homonymes
        for i in range(len(all_authid_keys)):
            for j in range(i + 1, len(all_authid_keys)):
                key1, key2 = all_authid_keys[i], all_authid_keys[j]
                
                # Vérifier si les authIdPerson_i sont vraiment différents
                if not set(key1).intersection(set(key2)):  # Aucun ID en commun
                    # Homonymes détectés
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
        Analyse un groupe de publications avec le même authIdPerson_i
        """
        results = {
            'duplicates': [],
            'multi_thesis': [],
            'collaborators': []
        }
        
        # Comparer toutes les paires
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                data1, data2 = group[i], group[j]
                
                # Calculer la similarité
                title_sim = self.calculate_title_similarity(
                    data1['main_title'], 
                    data2['main_title']
                )
                
                year1 = data1['row_data']['Année de Publication']
                year2 = data2['row_data']['Année de Publication']
                year_gap = abs(year1 - year2) if pd.notna(year1) and pd.notna(year2) else 999
                
                # Critères de décision
                if title_sim >= self.similarity_threshold and year_gap <= self.year_gap_threshold:
                    # Doublon probable
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
                
                elif year_gap > 3:  # Écart important d'années
                    # Vérifier si c'est un collaborateur vs auteur principal
                    is_collaborator = self.check_if_collaborator(data1, data2, nom, prenom)
                    
                    if is_collaborator:
                        results['collaborators'].append({
                            'author': f"{nom} {prenom}",
                            'main_thesis': data1 if year1 < year2 else data2,
                            'collaboration': data2 if year1 < year2 else data1,
                            'type': 'COLLABORATEUR_THESE'
                        })
                    else:
                        # Multi-thèses (rare mais possible)
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
        Vérifie si l'une des publications correspond à une collaboration
        plutôt qu'à une thèse principale de l'auteur
        """
        # Heuristiques pour détecter les collaborations :
        
        # 1. Vérifier si l'auteur apparaît dans la liste des auteurs
        for data in [data1, data2]:
            hal_data = data['hal_data']
            if hal_data and 'authFullName_s' in hal_data:
                auth_names = hal_data['authFullName_s']
                if isinstance(auth_names, list):
                    # Vérifier la position de l'auteur dans la liste
                    author_full_name = f"{prenom} {nom}"
                    author_positions = []
                    
                    for i, full_name in enumerate(auth_names):
                        if self.names_match(full_name, author_full_name):
                            author_positions.append(i)
                    
                    # Si l'auteur n'est pas en première position, c'est probablement une collaboration
                    if author_positions and min(author_positions) > 0:
                        return True
        
        # 2. Différences significatives de domaine/laboratoire
        domain1 = data1['row_data']['Domaine']
        domain2 = data2['row_data']['Domaine']
        lab1 = data1['laboratory_info']
        lab2 = data2['laboratory_info']
        
        if domain1 != domain2 and lab1 != lab2:
            return True
        
        return False
    
    def names_match(self, full_name: str, target_name: str) -> bool:
        """Vérifie si deux noms correspondent approximativement"""
        if not full_name or not target_name:
            return False
        
        # Normaliser les noms
        full_clean = re.sub(r'[^a-zA-Z\s]', ' ', full_name.lower())
        target_clean = re.sub(r'[^a-zA-Z\s]', ' ', target_name.lower())
        
        full_clean = re.sub(r'\s+', ' ', full_clean).strip()
        target_clean = re.sub(r'\s+', ' ', target_clean).strip()
        
        # Vérifier si tous les mots du nom cible sont dans le nom complet
        target_words = set(target_clean.split())
        full_words = set(full_clean.split())
        
        return target_words.issubset(full_words)
    
    def analyze_without_authid(self, nom: str, prenom: str, data_list: List[Dict]) -> Dict:
        """
        Analyse les publications sans authIdPerson_i (fallback sur similarité des titres)
        """
        results = {
            'duplicates': [],
            'no_authid': []
        }
        
        # Comparer toutes les paires
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
                
                # Critères plus stricts sans authIdPerson_i
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
        Analyse les cas où certaines publications ont authIdPerson_i et d'autres non
        """
        results = {
            'homonyms': [],
            'no_authid': []
        }
        
        # Pour l'instant, marquer comme cas à examiner manuellement
        for data_no_authid in without_authid:
            results['no_authid'].append({
                'author': f"{nom} {prenom}",
                'publication_without_authid': data_no_authid,
                'publications_with_authid': with_authid,
                'type': 'MIXED_AUTHID_AVAILABILITY'
            })
        
        return results
    
    def display_results(self, results: Dict):
        """Affiche les résultats de l'analyse"""
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


def main():
    """Fonction principale pour tester le détecteur"""
    detector = DuplicateHomonymDetector()
    
    # Analyser le fichier
    csv_file = "all_data_These_Doctorant.csv"
    laboratory_file = "exportmbre.csv"  # Optionnel
    
    try:
        results = detector.analyze_csv_file(csv_file, laboratory_file)
        detector.display_results(results)
        
        # Sauvegarder les résultats
        import json
        with open('detection_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\nRésultats sauvegardés dans detection_results.json")
        
    except Exception as e:
        print(f"Erreur lors de l'analyse: {e}")


if __name__ == "__main__":
    main()