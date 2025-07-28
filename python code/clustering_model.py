# clustering_model.py
# -*- coding: utf-8 -*-

"""
Modèle de clustering pour la détection des doublons et homonymes
dans les publications académiques HAL

Ce modèle utilise du machine learning pour identifier automatiquement :
- Les doublons (même publication référencée plusieurs fois)
- Les homonymes (même nom, personnes différentes)

Version mise à jour : suppression de la détection d'anomalies
"""

import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN, AgglomerativeClustering
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import PCA
import pickle
import os
import re
import ast
from difflib import SequenceMatcher
import warnings
warnings.filterwarnings('ignore')

class DuplicateHomonymClusteringModel:
    """
    Modèle de clustering sophistiqué pour détecter les doublons et homonymes
    
    Utilise deux algorithmes de clustering combinés :
    - DBSCAN pour les doublons (densité)
    - Hierarchical clustering pour les homonymes
    """
    
    def __init__(self):
        """Initialise le modèle avec tous ses composants"""
        
        # Modèles de clustering
        self.duplicate_clusterer = DBSCAN(eps=0.3, min_samples=2)
        self.homonym_clusterer = AgglomerativeClustering(n_clusters=None, distance_threshold=0.7, linkage='ward')
        
        # Preprocessing
        self.scaler = StandardScaler()
        self.title_vectorizer = TfidfVectorizer(max_features=500, stop_words='english', ngram_range=(1, 2))
        self.domain_encoder = LabelEncoder()
        self.lab_encoder = LabelEncoder()
        
        # Réduction de dimensionnalité
        self.pca = PCA(n_components=10)
        
        # Statut du modèle
        self.is_trained = False
        self.training_stats = {}
        
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
    
    def jaccard_similarity(self, str1, str2):
        """Calcule la similarité de Jaccard entre deux chaînes"""
        if not str1 or not str2:
            return 0.0
            
        words1 = set(str1.lower().split())
        words2 = set(str2.lower().split())
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def levenshtein_similarity(self, str1, str2):
        """Calcule la similarité de Levenshtein normalisée"""
        if not str1 or not str2:
            return 0.0
            
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
    
    def extract_features_for_clustering(self, df):
        """
        Extrait les features pour le clustering
        
        Args:
            df: DataFrame des publications HAL
            
        Returns:
            tuple: (features_matrix, metadata_df)
        """
        print(f"Extraction des features pour {len(df)} publications...")
        
        # Préparer les données
        features_list = []
        metadata_list = []
        
        for idx, row in df.iterrows():
            # Données de base
            main_title = self.extract_main_title(row['Titre'])
            author_name = f"{row['Nom']} {row['Prenom']}"
            year = row['Année de Publication'] if pd.notna(row['Année de Publication']) else 2020
            domain = str(row['Domaine']) if pd.notna(row['Domaine']) else 'Unknown'
            lab = str(row['Laboratoire de Recherche']) if pd.notna(row['Laboratoire de Recherche']) else 'Unknown'
            hal_id = str(row['IdHAL de l\'Auteur']) if pd.notna(row['IdHAL de l\'Auteur']) else 'unknown'
            docid = row['Docid'] if pd.notna(row['Docid']) else 0
            
            # Features numériques
            title_length = len(main_title)
            title_word_count = len(main_title.split())
            year_normalized = (year - 2000) / 25  # Normaliser années 2000-2025
            
            # Nettoyer le titre pour TF-IDF
            title_clean = re.sub(r'[^a-zA-Z0-9\s]', ' ', main_title.lower())
            title_clean = re.sub(r'\s+', ' ', title_clean).strip()
            
            features_list.append({
                'title_clean': title_clean,
                'title_length': title_length,
                'title_word_count': title_word_count,
                'year_normalized': year_normalized,
                'domain': domain,
                'lab': lab,
                'hal_id': hal_id,
                'docid': docid
            })
            
            metadata_list.append({
                'index': idx,
                'author': author_name,
                'main_title': main_title,
                'year': year,
                'domain': domain,
                'lab': lab,
                'hal_id': hal_id,
                'docid': docid
            })
        
        features_df = pd.DataFrame(features_list)
        metadata_df = pd.DataFrame(metadata_list)
        
        return features_df, metadata_df
    
    def prepare_clustering_features(self, features_df):
        """
        Prépare les features pour les algorithmes de clustering
        
        Args:
            features_df: DataFrame des features brutes
            
        Returns:
            np.array: Matrice des features pour clustering
        """
        print("Préparation des features pour le clustering...")
        
        # 1. Features textuelles avec TF-IDF
        titles = features_df['title_clean'].fillna('').tolist()
        
        if self.is_trained:
            title_features = self.title_vectorizer.transform(titles)
        else:
            title_features = self.title_vectorizer.fit_transform(titles)
        
        # 2. Features catégorielles
        domains = features_df['domain'].fillna('Unknown').tolist()
        labs = features_df['lab'].fillna('Unknown').tolist()
        
        if self.is_trained:
            # Gérer les nouvelles catégories non vues pendant l'entraînement
            domain_encoded = []
            for domain in domains:
                try:
                    domain_encoded.append(self.domain_encoder.transform([domain])[0])
                except ValueError:
                    domain_encoded.append(-1)  # Catégorie inconnue
            
            lab_encoded = []
            for lab in labs:
                try:
                    lab_encoded.append(self.lab_encoder.transform([lab])[0])
                except ValueError:
                    lab_encoded.append(-1)  # Catégorie inconnue
        else:
            domain_encoded = self.domain_encoder.fit_transform(domains)
            lab_encoded = self.lab_encoder.fit_transform(labs)
        
        # 3. Features numériques
        numeric_features = features_df[['title_length', 'title_word_count', 'year_normalized']].values
        
        # 4. Features spéciales pour les doublons
        docid_features = features_df['docid'].values.reshape(-1, 1)
        
        # 5. Combiner toutes les features
        combined_features = np.hstack([
            title_features.toarray(),
            np.array(domain_encoded).reshape(-1, 1),
            np.array(lab_encoded).reshape(-1, 1),
            numeric_features,
            docid_features
        ])
        
        # 6. Normaliser
        if self.is_trained:
            normalized_features = self.scaler.transform(combined_features)
        else:
            normalized_features = self.scaler.fit_transform(combined_features)
        
        # 7. Réduction de dimensionnalité
        if self.is_trained:
            final_features = self.pca.transform(normalized_features)
        else:
            final_features = self.pca.fit_transform(normalized_features)
        
        return final_features
    
    def compute_author_similarity_matrix(self, metadata_df):
        """
        Calcule une matrice de similarité spécifique pour les auteurs
        
        Args:
            metadata_df: DataFrame des métadonnées
            
        Returns:
            np.array: Matrice de similarité entre auteurs
        """
        print("Calcul de la matrice de similarité des auteurs...")
        
        # Grouper par auteur
        author_groups = metadata_df.groupby('author')
        
        # Créer une matrice de similarité
        n_samples = len(metadata_df)
        similarity_matrix = np.zeros((n_samples, n_samples))
        
        for author, group in author_groups:
            if len(group) < 2:
                continue
                
            indices = group.index.tolist()
            
            # Calculer similarités pour chaque paire du même auteur
            for i, idx1 in enumerate(indices):
                for j, idx2 in enumerate(indices):
                    if i >= j:
                        continue
                        
                    row1 = metadata_df.iloc[idx1]
                    row2 = metadata_df.iloc[idx2]
                    
                    # Similarité de titre
                    title_sim = self.jaccard_similarity(row1['main_title'], row2['main_title'])
                    
                    # Proximité temporelle
                    year_diff = abs(row1['year'] - row2['year'])
                    year_sim = 1.0 / (1.0 + year_diff / 5)  # Normaliser sur 5 ans
                    
                    # Similarité domaine/lab
                    domain_sim = 1.0 if row1['domain'] == row2['domain'] else 0.0
                    lab_sim = 1.0 if row1['lab'] == row2['lab'] else 0.0
                    
                    # Même HAL ID
                    hal_sim = 1.0 if row1['hal_id'] == row2['hal_id'] else 0.0
                    
                    # Même DocID (doublon évident)
                    docid_sim = 1.0 if row1['docid'] == row2['docid'] and row1['docid'] != 0 else 0.0
                    
                    # Score composite
                    composite_score = (
                        title_sim * 0.4 +
                        year_sim * 0.2 +
                        domain_sim * 0.15 +
                        lab_sim * 0.1 +
                        hal_sim * 0.1 +
                        docid_sim * 0.05
                    )
                    
                    similarity_matrix[idx1, idx2] = composite_score
                    similarity_matrix[idx2, idx1] = composite_score
        
        return similarity_matrix
    
    def train_model(self, csv_file_path):
        """
        Entraîne le modèle de clustering sur les données
        
        Args:
            csv_file_path: Chemin vers le fichier CSV d'entraînement
            
        Returns:
            dict: Statistiques d'entraînement
        """
        print("=== ENTRAÎNEMENT DU MODÈLE DE CLUSTERING ===")
        print(f"Fichier d'entraînement: {csv_file_path}")
        
        # Charger les données
        if not os.path.exists(csv_file_path):
            raise FileNotFoundError(f"Le fichier {csv_file_path} n'existe pas.")
        
        df = pd.read_csv(csv_file_path)
        print(f"Données chargées: {len(df)} publications")
        
        # Extraire les features
        features_df, metadata_df = self.extract_features_for_clustering(df)
        
        # Préparer les features pour le clustering
        clustering_features = self.prepare_clustering_features(features_df)
        
        # Calculer la matrice de similarité pour les auteurs
        author_similarity_matrix = self.compute_author_similarity_matrix(metadata_df)
        
        # 1. Entraîner le détecteur de doublons (DBSCAN)
        print("\nEntraînement du détecteur de doublons...")
        duplicate_labels = self.duplicate_clusterer.fit_predict(clustering_features)
        
        # 2. Entraîner le détecteur d'homonymes (Hierarchical)
        print("Entraînement du détecteur d'homonymes...")
        # Utiliser une distance personnalisée basée sur la similarité des auteurs
        distance_matrix = 1 - author_similarity_matrix
        
        # Adapter le clustering hiérarchique
        self.homonym_clusterer = AgglomerativeClustering(
            n_clusters=None, 
            distance_threshold=0.6, 
            linkage='average'
        )
        homonym_labels = self.homonym_clusterer.fit_predict(clustering_features)
        
        # Marquer le modèle comme entraîné
        self.is_trained = True
        
        # Calculer les statistiques d'entraînement
        unique_duplicate_clusters = len(set(duplicate_labels)) - (1 if -1 in duplicate_labels else 0)
        unique_homonym_clusters = len(set(homonym_labels))
        
        self.training_stats = {
            'total_publications': len(df),
            'duplicate_clusters': unique_duplicate_clusters,
            'homonym_clusters': unique_homonym_clusters,
            'duplicate_labels': duplicate_labels,
            'homonym_labels': homonym_labels,
            'metadata': metadata_df,
            'features': clustering_features
        }
        
        print(f"\n=== STATISTIQUES D'ENTRAÎNEMENT ===")
        print(f"Publications traitées: {len(df)}")
        print(f"Clusters de doublons: {unique_duplicate_clusters}")
        print(f"Clusters d'homonymes: {unique_homonym_clusters}")
        print("Modèle entraîné avec succès!")
        
        return self.training_stats
    
    def predict_duplicates_and_homonyms(self, csv_file_path):
        """
        Prédit les doublons et homonymes sur de nouvelles données
        
        Args:
            csv_file_path: Chemin vers le fichier CSV à analyser
            
        Returns:
            dict: Résultats de l'analyse
        """
        if not self.is_trained:
            raise ValueError("Le modèle doit être entraîné avant d'effectuer des prédictions.")
        
        print("=== ANALYSE DES DOUBLONS ET HOMONYMES ===")
        print(f"Fichier à analyser: {csv_file_path}")
        
        # Charger les données
        df = pd.read_csv(csv_file_path)
        print(f"Données chargées: {len(df)} publications")
        
        # Extraire les features
        features_df, metadata_df = self.extract_features_for_clustering(df)
        
        # Préparer les features pour le clustering
        clustering_features = self.prepare_clustering_features(features_df)
        
        # Calculer la matrice de similarité
        author_similarity_matrix = self.compute_author_similarity_matrix(metadata_df)
        
        # Prédictions
        duplicate_labels = self.duplicate_clusterer.fit_predict(clustering_features)
        homonym_labels = self.homonym_clusterer.fit_predict(clustering_features)
        
        # Analyser les résultats
        results = self.analyze_clustering_results(
            duplicate_labels, homonym_labels, metadata_df, author_similarity_matrix
        )
        
        return results
    
    def analyze_clustering_results(self, duplicate_labels, homonym_labels, metadata_df, similarity_matrix):
        """
        Analyse les résultats du clustering
        
        Args:
            duplicate_labels: Labels des clusters de doublons
            homonym_labels: Labels des clusters d'homonymes
            metadata_df: Métadonnées des publications
            similarity_matrix: Matrice de similarité
            
        Returns:
            dict: Résultats analysés
        """
        print("Analyse des résultats du clustering...")
        
        # Identifier les doublons (même cluster, score élevé)
        duplicate_cases = []
        for cluster_id in set(duplicate_labels):
            if cluster_id == -1:  # Ignorer le bruit
                continue
                
            cluster_indices = [i for i, label in enumerate(duplicate_labels) if label == cluster_id]
            if len(cluster_indices) < 2:
                continue
            
            # Analyser les paires dans ce cluster
            for i in range(len(cluster_indices)):
                for j in range(i + 1, len(cluster_indices)):
                    idx1, idx2 = cluster_indices[i], cluster_indices[j]
                    
                    # Vérifier si même auteur
                    if metadata_df.iloc[idx1]['author'] == metadata_df.iloc[idx2]['author']:
                        similarity_score = similarity_matrix[idx1, idx2]
                        
                        if similarity_score > 0.7:  # Seuil pour doublon
                            duplicate_cases.append({
                                'author': metadata_df.iloc[idx1]['author'],
                                'index1': idx1,
                                'index2': idx2,
                                'title1': metadata_df.iloc[idx1]['main_title'],
                                'title2': metadata_df.iloc[idx2]['main_title'],
                                'year1': metadata_df.iloc[idx1]['year'],
                                'year2': metadata_df.iloc[idx2]['year'],
                                'similarity_score': similarity_score,
                                'cluster_id': cluster_id,
                                'type': 'DOUBLON_PROBABLE'
                            })
        
        # Identifier les homonymes (même nom, clusters différents ou score faible)
        homonym_cases = []
        author_groups = metadata_df.groupby('author')
        
        for author, group in author_groups:
            if len(group) < 2:
                continue
                
            indices = group.index.tolist()
            
            # Vérifier les différences entre publications du même auteur
            for i in range(len(indices)):
                for j in range(i + 1, len(indices)):
                    idx1, idx2 = indices[i], indices[j]
                    
                    # Différents clusters d'homonymes ou faible similarité
                    different_clusters = homonym_labels[idx1] != homonym_labels[idx2]
                    low_similarity = similarity_matrix[idx1, idx2] < 0.3
                    large_time_gap = abs(metadata_df.iloc[idx1]['year'] - metadata_df.iloc[idx2]['year']) > 10
                    
                    if different_clusters or (low_similarity and large_time_gap):
                        homonym_cases.append({
                            'author': author,
                            'index1': idx1,
                            'index2': idx2,
                            'title1': metadata_df.iloc[idx1]['main_title'],
                            'title2': metadata_df.iloc[idx2]['main_title'],
                            'year1': metadata_df.iloc[idx1]['year'],
                            'year2': metadata_df.iloc[idx2]['year'],
                            'year_gap': abs(metadata_df.iloc[idx1]['year'] - metadata_df.iloc[idx2]['year']),
                            'similarity_score': similarity_matrix[idx1, idx2],
                            'cluster1': homonym_labels[idx1],
                            'cluster2': homonym_labels[idx2],
                            'type': 'HOMONYME_POTENTIEL'
                        })
        
        results = {
            'duplicate_cases': duplicate_cases,
            'homonym_cases': homonym_cases,
            'summary': {
                'total_publications': len(metadata_df),
                'duplicate_pairs': len(duplicate_cases),
                'homonym_pairs': len(homonym_cases),
                'unique_authors': len(metadata_df['author'].unique())
            },
            'metadata': metadata_df
        }
        
        return results
    
    def save_model(self, model_path='clustering_model.pkl'):
        """Sauvegarde le modèle entraîné"""
        if not self.is_trained:
            raise ValueError("Le modèle doit être entraîné avant d'être sauvegardé.")
        
        model_data = {
            'duplicate_clusterer': self.duplicate_clusterer,
            'homonym_clusterer': self.homonym_clusterer,
            'scaler': self.scaler,
            'title_vectorizer': self.title_vectorizer,
            'domain_encoder': self.domain_encoder,
            'lab_encoder': self.lab_encoder,
            'pca': self.pca,
            'is_trained': self.is_trained,
            'training_stats': self.training_stats
        }
        
        with open(model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"Modèle sauvegardé dans: {model_path}")
    
    def load_model(self, model_path='clustering_model.pkl'):
        """Charge un modèle pré-entraîné"""
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Le modèle {model_path} n'existe pas.")
        
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.duplicate_clusterer = model_data['duplicate_clusterer']
        self.homonym_clusterer = model_data['homonym_clusterer']
        self.scaler = model_data['scaler']
        self.title_vectorizer = model_data['title_vectorizer']
        self.domain_encoder = model_data['domain_encoder']
        self.lab_encoder = model_data['lab_encoder']
        self.pca = model_data['pca']
        self.is_trained = model_data['is_trained']
        self.training_stats = model_data['training_stats']
        
        print(f"Modèle chargé depuis: {model_path}")
        print(f"Modèle entraîné sur {self.training_stats['total_publications']} publications")

# Fonction utilitaire pour analyser un fichier CSV
def load_and_analyze_csv(csv_file_path, model_path='clustering_model.pkl'):
    """
    Charge le modèle et analyse un fichier CSV
    
    Args:
        csv_file_path: Chemin vers le fichier CSV à analyser
        model_path: Chemin vers le modèle sauvegardé
        
    Returns:
        dict: Résultats de l'analyse
    """
    # Charger le modèle
    model = DuplicateHomonymClusteringModel()
    model.load_model(model_path)
    
    # Analyser le fichier
    results = model.predict_duplicates_and_homonyms(csv_file_path)
    
    # Afficher les résultats
    print("\n=== RÉSULTATS DE L'ANALYSE ===")
    summary = results['summary']
    print(f"Publications analysées: {summary['total_publications']}")
    print(f"Auteurs uniques: {summary['unique_authors']}")
    print(f"Paires de doublons: {summary['duplicate_pairs']}")
    print(f"Paires d'homonymes: {summary['homonym_pairs']}")
    
    return results