# train_model.py
# -*- coding: utf-8 -*-

"""
Fichier standalone pour l'entraînement du modèle de clustering
Sépare complètement l'entraînement de l'utilisation du modèle
"""

import os
import sys
import pandas as pd
from clustering_model import DuplicateHomonymClusteringModel

def list_extraction_csv_files():
    """
    Liste les fichiers CSV disponibles dans le dossier extraction
    
    Returns:
        tuple: (extraction_directory_path, list_of_csv_files)
        
    Raises:
        FileNotFoundError: Si le dossier extraction ou les fichiers CSV ne sont pas trouvés
    """
    current_directory = os.path.dirname(os.path.abspath(__file__))
    extraction_directory = os.path.join(current_directory, "extraction")
    
    if not os.path.exists(extraction_directory):
        raise FileNotFoundError(f"Le dossier 'extraction' n'existe pas dans {current_directory}")

    csv_files = [f for f in os.listdir(extraction_directory) if f.endswith(".csv")]
    if not csv_files:
        raise FileNotFoundError(f"Aucun fichier CSV trouvé dans le dossier 'extraction'")
    
    return extraction_directory, csv_files

def select_training_csv():
    """
    Sélection interactive d'un fichier CSV pour l'entraînement
    
    Returns:
        str: Chemin complet vers le fichier CSV sélectionné
        
    Raises:
        SystemExit: Si choix invalide ou entrée incorrecte
    """
    try:
        extraction_directory, csv_files = list_extraction_csv_files()
        
        print("\n" + "="*60)
        print("SÉLECTION DU FICHIER D'ENTRAÎNEMENT")
        print("="*60)
        print("Fichiers CSV disponibles dans 'extraction/' :")
        print("-" * 60)
        
        for i, file in enumerate(csv_files, start=1):
            # Afficher des informations sur le fichier
            file_path = os.path.join(extraction_directory, file)
            file_size = os.path.getsize(file_path)
            size_mb = file_size / (1024 * 1024)
            
            # Estimer le nombre de lignes
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    line_count = sum(1 for _ in f) - 1  # -1 pour l'en-tête
            except:
                line_count = "?"
            
            print(f"{i:2d}. {file:<40} ({size_mb:.1f} MB, ~{line_count} publications)")

        print("="*60)
        choice = int(input(f"\nSélectionnez le fichier d'entraînement (1-{len(csv_files)}): "))
        
        if 1 <= choice <= len(csv_files):
            selected_file = os.path.join(extraction_directory, csv_files[choice - 1])
            print(f"\nFichier sélectionné: {csv_files[choice - 1]}")
            return selected_file
        else:
            print("Choix invalide. Veuillez relancer le programme.")
            sys.exit(1)
            
    except ValueError:
        print("Entrée invalide. Veuillez entrer un nombre.")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"Erreur: {e}")
        sys.exit(1)

def check_existing_model():
    """
    Vérifie si un modèle existe déjà et demande confirmation pour le remplacer
    
    Returns:
        bool: True si on peut continuer, False sinon
    """
    model_path = 'clustering_model.pkl'
    
    if os.path.exists(model_path):
        print("\n" + "="*60)
        print("MODÈLE EXISTANT DÉTECTÉ")
        print("="*60)
        
        try:
            # Charger temporairement le modèle pour obtenir les infos
            temp_model = DuplicateHomonymClusteringModel()
            temp_model.load_model(model_path)
            
            print("Un modèle entraîné existe déjà :")
            print(f"   Publications d'entraînement: {temp_model.training_stats['total_publications']}")
            print(f"   Clusters de doublons: {temp_model.training_stats['duplicate_clusters']}")
            print(f"   Clusters d'homonymes: {temp_model.training_stats['homonym_clusters']}")
            
        except Exception as e:
            print(f"Un modèle existe mais il y a une erreur: {str(e)}")
        
        print("\nVoulez-vous le remplacer par un nouveau modèle ?")
        response = input("(o/n): ").lower()
        
        if response not in ['o', 'oui', 'y', 'yes']:
            print("Entraînement annulé.")
            return False
    
    return True

def train_model():
    """
    Fonction principale d'entraînement du modèle
    """
    print("="*60)
    print("ENTRAÎNEMENT DU MODÈLE DE CLUSTERING")
    print("="*60)
    print("Ce script va créer un modèle de détection des doublons et homonymes")
    print("Le modèle sera sauvegardé comme 'clustering_model.pkl'")
    
    # Vérifier si on peut continuer
    if not check_existing_model():
        return False
    
    # Sélectionner le fichier d'entraînement
    training_file = select_training_csv()
    
    # Afficher les informations sur l'entraînement
    print("\n" + "="*60)
    print("INFORMATIONS SUR L'ENTRAÎNEMENT")
    print("="*60)
    
    try:
        # Charger le fichier pour obtenir des statistiques
        df = pd.read_csv(training_file)
        unique_authors = df['Nom'].str.cat(df['Prenom'], sep=' ').nunique()
        
        print(f"Fichier d'entraînement: {os.path.basename(training_file)}")
        print(f"Nombre de publications: {len(df)}")
        print(f"Nombre d'auteurs uniques: {unique_authors}")
        print(f"Période couverte: {df['Année de Publication'].min()}-{df['Année de Publication'].max()}")
        
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier: {e}")
        return False
    
    # Confirmation finale
    print("\n" + "-"*60)
    print("ATTENTION: L'entraînement peut prendre plusieurs minutes")
    print("selon la taille du fichier.")
    print("-"*60)
    
    confirm = input("\nConfirmer l'entraînement ? (o/n): ").lower()
    if confirm not in ['o', 'oui', 'y', 'yes']:
        print("Entraînement annulé.")
        return False
    
    # Lancer l'entraînement
    print("\n" + "="*60)
    print("DÉMARRAGE DE L'ENTRAÎNEMENT")
    print("="*60)
    
    try:
        # Créer et entraîner le modèle
        model = DuplicateHomonymClusteringModel()
        print("Modèle initialisé.")
        
        print("Entraînement en cours...")
        training_stats = model.train_model(training_file)
        
        # Sauvegarder le modèle
        model.save_model('clustering_model.pkl')
        
        # Afficher les résultats
        print("\n" + "="*60)
        print("ENTRAÎNEMENT TERMINÉ AVEC SUCCÈS")
        print("="*60)
        print(f"Publications traitées: {training_stats['total_publications']}")
        print(f"Clusters de doublons: {training_stats['duplicate_clusters']}")
        print(f"Clusters d'homonymes: {training_stats['homonym_clusters']}")
        print(f"Modèle sauvegardé: clustering_model.pkl")
        
        print("\n" + "="*60)
        print("UTILISATION DU MODÈLE")
        print("="*60)
        print("Le modèle est maintenant prêt à l'emploi.")
        print("Utilisez les commandes suivantes pour analyser des fichiers :")
        print("  python main.py --analyse")
        print("  python app.py  (interface graphique)")
        
        return True
        
    except Exception as e:
        print(f"\nERREUR lors de l'entraînement: {str(e)}")
        print("Vérifiez que le fichier CSV est valide et contient les colonnes requises.")
        return False

if __name__ == "__main__":
    print("SCRIPT D'ENTRAÎNEMENT DU MODÈLE DE CLUSTERING")
    print("=" * 60)
    
    try:
        success = train_model()
        
        if success:
            print("\nEntraînement réussi !")
            sys.exit(0)
        else:
            print("\nEntraînement échoué.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nEntraînement interrompu par l'utilisateur.")
        sys.exit(1)
    except Exception as e:
        print(f"\nErreur inattendue: {str(e)}")
        sys.exit(1)