# -*- coding: utf-8 -*-

from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import argparse
from hal_data import get_hal_data
from utils import generate_filename
from mapping import list_domains, list_types
from config import get_threshold_from_level, list_sensitivity_levels, DEFAULT_THRESHOLD
from dashboard_generator import create_dashboard
from report_generator_main import generate_pdf_report, generate_latex_report
from clustering_model import load_and_analyze_csv
import webbrowser
import os
import sys
import time
from graphics import (
    plot_publications_by_year,
    plot_document_types,
    plot_keywords,
    plot_top_domains,
    plot_publications_by_author,
    plot_structures_stacked,
    plot_publications_trends,
    plot_employer_distribution, 
    plot_theses_hdr_by_year, 
    plot_theses_keywords_wordcloud,
)

def create_progress_bar(current, total, description="Progress", bar_length=50):
    """
    Displays a native progress bar without external dependencies
    
    Args:
        current (int): Number of processed elements
        total (int): Total number of elements
        description (str): Description of the current task
        bar_length (int): Length of the bar in characters
    """
    if total == 0:
        return
    
    progress = current / total
    filled_length = int(bar_length * progress)
    
    try:
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
    except UnicodeEncodeError:
        bar = '#' * filled_length + '-' * (bar_length - filled_length)
    
    percent = progress * 100
    
    if current > 0 and hasattr(create_progress_bar, 'start_time'):
        elapsed = time.time() - create_progress_bar.start_time
        rate = current / elapsed
        if rate > 0:
            eta_seconds = (total - current) / rate
            eta_str = f" ETA: {int(eta_seconds//60):02d}:{int(eta_seconds%60):02d}"
        else:
            eta_str = ""
    else:
        eta_str = ""
    
    sys.stdout.write(f'\r{description}: |{bar}| {percent:.1f}% ({current}/{total}){eta_str}')
    sys.stdout.flush()
    
    if current == total:
        print("\nCompleted!")

def init_progress_bar():
    """Initialize timer for ETA calculation"""
    create_progress_bar.start_time = time.time()

def list_csv_files():
    """
    Lists available CSV files in the data directory
    
    Returns:
        tuple: (data_directory_path, list_of_csv_files)
        
    Raises:
        FileNotFoundError: If data directory or CSV files are not found
    """
    current_directory = os.path.dirname(os.path.abspath(__file__))
    data_directory = os.path.join(current_directory,"..","data gdrmacs")
    if not os.path.exists(data_directory):
        raise FileNotFoundError(f"Directory '{data_directory}' not found.")

    csv_files = [f for f in os.listdir(data_directory) if f.endswith(".csv")]
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in directory '{data_directory}'.")
    return data_directory, csv_files

def get_user_selected_csv():
    """
    Interactive CSV file selection by user
    
    Returns:
        str: Full path to selected CSV file
        
    Raises:
        SystemExit: If invalid choice or input
    """
    try:
        data_directory, csv_files = list_csv_files()
        print("Available CSV files:")
        for i, file in enumerate(csv_files, start=1):
            print(f"{i}. {file}")

        choice = int(input("\nEnter the number of the file you want to use: "))
        if 1 <= choice <= len(csv_files):
            selected_file = os.path.join(data_directory, csv_files[choice - 1])
            print(f"You selected the file: {csv_files[choice - 1]}")
            return selected_file
        else:
            print("Invalid choice. Please restart the program.")
            exit(1)
    except ValueError:
        print("Invalid input. Please enter a valid number.")
        exit(1)

def create_extraction_folder():
    """Create extraction folder for output files"""
    current_directory = os.path.dirname(os.path.abspath(__file__))
    extraction_directory = os.path.join(current_directory, "extraction")

    if not os.path.exists(extraction_directory):
        os.makedirs(extraction_directory)

    return extraction_directory

def fetch_data(row):
    """UPDATED: Wrapper function for parallel data extraction with new type handling"""
    # CORRECTION: Pass type as list for proper handling in get_hal_data
    type_filter = [args.type] if args.type else None
    domain_filter = [args.domain] if args.domain else None
    
    return get_hal_data(
        row["nom"], row["prenom"], 
        period=args.year, 
        domain_filter=domain_filter, 
        type_filter=type_filter,
        threshold=args.threshold
    )

def display_extraction_summary():
    """
    ENHANCED: Displays a summary of the extraction with detailed thesis information
    
    Shows filters, sensitivity settings, and output options in a formatted way
    """
    print("\n" + "="*60)
    print("EXTRACTION SUMMARY")
    print("="*60)
    
    filters = []
    if args.year:
        filters.append(f"period: {args.year}")
    if args.type:
        filters.append(f"type: {args.type}")
    if args.domain:
        filters.append(f"domain: {args.domain}")
    
    if filters:
        filter_text = "with filters (" + ", ".join(filters) + ")"
    else:
        filter_text = "all data (no filters)"
    
    outputs = []
    if args.graphs:
        outputs.append("graph generation")
    if args.reportpdf:
        outputs.append("PDF report")
    if args.reportlatex:
        outputs.append("LaTeX report")
    
    if outputs:
        output_text = ", ".join(outputs)
    else:
        output_text = "no additional output"
    
    sensitivity_levels = {
        0: "very strict",
        1: "strict", 
        2: "moderate",
        3: "permissive",
        4: "very permissive"
    }
    sensitivity_text = f"sensitivity {sensitivity_levels.get(args.threshold, 'unknown')} (distance = {args.threshold})"
    
    print(f"• Extraction: {filter_text}")
    print(f"• Matching: {sensitivity_text}")
    print(f"• Outputs: {output_text}")
    
    # ENHANCED: Detailed thesis information
    if args.type:
        type_lower = args.type.lower()
        if any(keyword in type_lower for keyword in ['thèse', 'habilitation', 'thesis', 'hdr']):
            print(f"• Extended search: Double query (prenom nom + nom prenom) for better results")
        
        # NEW: Specific information for new thesis types
        if 'doctorant' in type_lower:
            print(f"• Thesis filter: PhD theses only (THESE documents)")
        elif 'hdr' in type_lower and 'thèse' in type_lower:
            print(f"• Thesis filter: HDR theses only (HDR documents)")
        elif 'thèse' in type_lower or 'habilitation' in type_lower:
            print(f"• Thesis filter: Both PhD and HDR theses (THESE + HDR documents)")
    
    print("="*60 + "\n")

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

def select_extraction_csv():
    """
    Sélection interactive d'un fichier CSV depuis le dossier extraction
    
    Returns:
        str: Chemin complet vers le fichier CSV sélectionné
        
    Raises:
        SystemExit: Si choix invalide ou entrée incorrecte
    """
    try:
        extraction_directory, csv_files = list_extraction_csv_files()
        
        print("\n" + "="*60)
        print("FICHIERS CSV DISPONIBLES DANS 'extraction/'")
        print("="*60)
        
        for i, file in enumerate(csv_files, start=1):
            # Afficher des informations sur le fichier
            file_path = os.path.join(extraction_directory, file)
            file_size = os.path.getsize(file_path)
            size_mb = file_size / (1024 * 1024)
            
            print(f"{i:2d}. {file:<40} ({size_mb:.1f} MB)")

        print("="*60)
        choice = int(input(f"\nSélectionnez un fichier (1-{len(csv_files)}): "))
        
        if 1 <= choice <= len(csv_files):
            selected_file = os.path.join(extraction_directory, csv_files[choice - 1])
            print(f"Fichier sélectionné: {csv_files[choice - 1]}")
            return selected_file
        else:
            print("Choix invalide. Veuillez relancer le programme.")
            exit(1)
            
    except ValueError:
        print("Entrée invalide. Veuillez entrer un nombre.")
        exit(1)
    except FileNotFoundError as e:
        print(f"{e}")
        exit(1)

def check_model_status():
    """
    Vérifie le statut du modèle de clustering
    
    Returns:
        bool: True si le modèle existe et est valide
    """
    model_path = 'clustering_model.pkl'
    
    if not os.path.exists(model_path):
        return False
    
    try:
        # Tenter de charger le modèle pour vérifier sa validité
        from clustering_model import DuplicateHomonymClusteringModel
        temp_model = DuplicateHomonymClusteringModel()
        temp_model.load_model(model_path)
        return True
    except Exception:
        return False

def analyze_csv_cli():
    """
    Interface en ligne de commande pour l'analyse d'un fichier CSV
    """
    print("\n" + "="*60)
    print("ANALYSE DES DOUBLONS & HOMONYMES")
    print("="*60)
    
    # Vérifier si le modèle existe
    if not check_model_status():
        print("ERREUR: Aucun modèle de clustering valide trouvé.")
        print("\nPour utiliser cette fonctionnalité, vous devez d'abord")
        print("entraîner un modèle avec le script dédié :")
        print("  python train_model.py")
        print("\nCe script vous permettra de :")
        print("- Sélectionner un fichier CSV d'entraînement")
        print("- Créer le modèle clustering_model.pkl")
        print("- Valider le modèle pour l'analyse")
        return
    
    # Sélectionner le fichier à analyser
    analysis_file = select_extraction_csv()
    
    print(f"\nAnalyse du fichier: {os.path.basename(analysis_file)}")
    print("Analyse en cours...")
    
    try:
        # Lancer l'analyse
        results = load_and_analyze_csv(analysis_file, 'clustering_model.pkl')
        
        # Afficher les résultats détaillés
        display_analysis_results(results)
        
        # Proposer des actions
        propose_actions(results, analysis_file)
        
    except Exception as e:
        print(f"\nERREUR lors de l'analyse: {str(e)}")

def display_analysis_results(results):
    """
    Affiche les résultats de l'analyse de manière détaillée
    
    Args:
        results: Dictionnaire des résultats d'analyse
    """
    summary = results['summary']
    
    print(f"\n" + "="*60)
    print("RÉSULTATS DE L'ANALYSE")
    print("="*60)
    
    print(f"Publications analysées: {summary['total_publications']}")
    print(f"Auteurs uniques: {summary['unique_authors']}")
    print(f"Paires de doublons détectées: {summary['duplicate_pairs']}")
    print(f"Paires d'homonymes détectées: {summary['homonym_pairs']}")
    
    # Afficher les doublons détectés
    if results['duplicate_cases']:
        print(f"\n" + "="*50)
        print("DOUBLONS DÉTECTÉS")
        print("="*50)
        
        for i, case in enumerate(results['duplicate_cases'][:5], 1):  # Limiter à 5 exemples
            print(f"\n{i}. {case['author']} (Score: {case['similarity_score']:.3f})")
            print(f"   Titre 1: {case['title1'][:70]}...")
            print(f"   Titre 2: {case['title2'][:70]}...")
            print(f"   Années: {case['year1']} / {case['year2']}")
        
        if len(results['duplicate_cases']) > 5:
            print(f"\n... et {len(results['duplicate_cases']) - 5} autres doublons")
    
    # Afficher les homonymes détectés
    if results['homonym_cases']:
        print(f"\n" + "="*50)
        print("HOMONYMES DÉTECTÉS")
        print("="*50)
        
        for i, case in enumerate(results['homonym_cases'][:5], 1):  # Limiter à 5 exemples
            print(f"\n{i}. {case['author']} (Écart: {case['year_gap']} ans)")
            print(f"   Titre 1: {case['title1'][:70]}...")
            print(f"   Titre 2: {case['title2'][:70]}...")
            print(f"   Années: {case['year1']} / {case['year2']}")
            print(f"   Score: {case['similarity_score']:.3f}")
        
        if len(results['homonym_cases']) > 5:
            print(f"\n... et {len(results['homonym_cases']) - 5} autres homonymes")

def propose_actions(results, analysis_file):
    """
    Propose des actions à l'utilisateur après l'analyse
    
    Args:
        results: Dictionnaire des résultats d'analyse
        analysis_file: Chemin vers le fichier analysé
    """
    print(f"\n" + "="*60)
    print("ACTIONS DISPONIBLES")
    print("="*60)
    
    print("1. Traiter automatiquement les données")
    print("2. Exporter les résultats détaillés")
    print("3. Afficher plus de détails")
    print("4. Terminer")
    
    while True:
        try:
            choice = int(input(f"\nChoisissez une action (1-4): "))
            
            if choice == 1:
                treat_data_cli(results, analysis_file)
                break
            elif choice == 2:
                export_results_cli(results, analysis_file)
                break
            elif choice == 3:
                display_detailed_results(results)
                # Après affichage, reproposer les actions
                continue
            elif choice == 4:
                print("Analyse terminée.")
                break
            else:
                print("Choix invalide. Veuillez choisir entre 1 et 4.")
                
        except ValueError:
            print("Entrée invalide. Veuillez entrer un nombre.")

def treat_data_cli(results, analysis_file):
    """
    Traite automatiquement les données problématiques
    
    Args:
        results: Dictionnaire des résultats d'analyse
        analysis_file: Chemin vers le fichier analysé
    """
    print(f"\n" + "="*50)
    print("TRAITEMENT AUTOMATIQUE DES DONNÉES")
    print("="*50)
    
    summary = results['summary']
    
    print(f"Impact du traitement:")
    print(f"   • Doublons à supprimer: {summary['duplicate_pairs']} paires")
    print(f"   • Homonymes à marquer: {summary['homonym_pairs']} paires")
    
    # Options de traitement
    print(f"\nOptions de traitement:")
    print(f"1. Supprimer les doublons uniquement")
    print(f"2. Marquer les homonymes (ajouter une colonne)")
    print(f"3. Traitement complet (doublons + homonymes)")
    print(f"4. Traitement personnalisé")
    
    try:
        choice = int(input(f"\nChoisissez le type de traitement (1-4): "))
        
        # Charger les données originales
        original_df = pd.read_csv(analysis_file)
        processed_df = original_df.copy()
        
        actions_performed = []
        
        if choice == 1 or choice == 3:  # Supprimer doublons
            if results['duplicate_cases']:
                indices_to_remove = set()
                for case in results['duplicate_cases']:
                    indices_to_remove.add(case['index2'])  # Garder le premier
                
                processed_df = processed_df.drop(indices_to_remove).reset_index(drop=True)
                actions_performed.append(f"Supprimé {len(indices_to_remove)} doublons")
        
        if choice == 2 or choice == 3:  # Marquer homonymes
            if results['homonym_cases']:
                processed_df['Homonyme_Potentiel'] = False
                marked_count = 0
                for case in results['homonym_cases']:
                    if case['index1'] < len(processed_df):
                        processed_df.loc[case['index1'], 'Homonyme_Potentiel'] = True
                        marked_count += 1
                    if case['index2'] < len(processed_df):
                        processed_df.loc[case['index2'], 'Homonyme_Potentiel'] = True
                        marked_count += 1
                
                actions_performed.append(f"Marqué {marked_count} publications comme homonymes potentiels")
        
        if choice == 4:  # Traitement personnalisé
            print(f"\nTraitement personnalisé:")
            
            if results['duplicate_cases']:
                remove_dup = input("Supprimer les doublons ? (o/n): ").lower()
                if remove_dup in ['o', 'oui', 'y', 'yes']:
                    indices_to_remove = set()
                    for case in results['duplicate_cases']:
                        indices_to_remove.add(case['index2'])
                    
                    processed_df = processed_df.drop(indices_to_remove).reset_index(drop=True)
                    actions_performed.append(f"Supprimé {len(indices_to_remove)} doublons")
            
            if results['homonym_cases']:
                mark_hom = input("Marquer les homonymes ? (o/n): ").lower()
                if mark_hom in ['o', 'oui', 'y', 'yes']:
                    processed_df['Homonyme_Potentiel'] = False
                    marked_count = 0
                    for case in results['homonym_cases']:
                        if case['index1'] < len(processed_df):
                            processed_df.loc[case['index1'], 'Homonyme_Potentiel'] = True
                            marked_count += 1
                        if case['index2'] < len(processed_df):
                            processed_df.loc[case['index2'], 'Homonyme_Potentiel'] = True
                            marked_count += 1
                    
                    actions_performed.append(f"Marqué {marked_count} publications comme homonymes potentiels")
        
        # Sauvegarder le fichier traité
        base_name = os.path.splitext(os.path.basename(analysis_file))[0]
        processed_filename = f"{base_name}_traite.csv"
        processed_path = os.path.join('extraction', processed_filename)
        
        processed_df.to_csv(processed_path, index=False)
        
        # Afficher le résumé
        print(f"\nTRAITEMENT TERMINÉ")
        print(f"Publications originales: {len(original_df)}")
        print(f"Publications traitées: {len(processed_df)}")
        print(f"Publications supprimées: {len(original_df) - len(processed_df)}")
        print(f"Fichier sauvegardé: {processed_path}")
        
        if actions_performed:
            print(f"\nActions effectuées:")
            for action in actions_performed:
                print(f"   • {action}")
        
    except ValueError:
        print("Entrée invalide.")
    except Exception as e:
        print(f"Erreur lors du traitement: {str(e)}")

def export_results_cli(results, analysis_file):
    """
    Exporte les résultats détaillés
    
    Args:
        results: Dictionnaire des résultats d'analyse
        analysis_file: Chemin vers le fichier analysé
    """
    print(f"\n" + "="*50)
    print("EXPORTATION DES RÉSULTATS")
    print("="*50)
    
    base_name = os.path.splitext(os.path.basename(analysis_file))[0]
    export_dir = 'extraction'
    
    try:
        exported_files = []
        
        # Exporter les doublons
        if results['duplicate_cases']:
            dup_df = pd.DataFrame(results['duplicate_cases'])
            dup_path = os.path.join(export_dir, f'{base_name}_doublons.csv')
            dup_df.to_csv(dup_path, index=False)
            exported_files.append(dup_path)
        
        # Exporter les homonymes
        if results['homonym_cases']:
            hom_df = pd.DataFrame(results['homonym_cases'])
            hom_path = os.path.join(export_dir, f'{base_name}_homonymes.csv')
            hom_df.to_csv(hom_path, index=False)
            exported_files.append(hom_path)
        
        # Exporter le résumé
        summary_path = os.path.join(export_dir, f'{base_name}_resume.txt')
        with open(summary_path, 'w', encoding='utf-8') as f:
            summary = results['summary']
            f.write("RÉSUMÉ DE L'ANALYSE\n")
            f.write("="*50 + "\n\n")
            f.write(f"Fichier analysé: {os.path.basename(analysis_file)}\n")
            f.write(f"Publications analysées: {summary['total_publications']}\n")
            f.write(f"Auteurs uniques: {summary['unique_authors']}\n")
            f.write(f"Paires de doublons: {summary['duplicate_pairs']}\n")
            f.write(f"Paires d'homonymes: {summary['homonym_pairs']}\n")
        
        exported_files.append(summary_path)
        
        print(f"Résultats exportés avec succès:")
        for file_path in exported_files:
            print(f"   {os.path.basename(file_path)}")
        
        print(f"\nDossier d'exportation: {export_dir}")
        
    except Exception as e:
        print(f"Erreur lors de l'exportation: {str(e)}")

def display_detailed_results(results):
    """
    Affiche des résultats plus détaillés
    
    Args:
        results: Dictionnaire des résultats d'analyse
    """
    print(f"\n" + "="*60)
    print("RÉSULTATS DÉTAILLÉS")
    print("="*60)
    
    # Afficher tous les doublons
    if results['duplicate_cases']:
        print(f"\nTOUS LES DOUBLONS ({len(results['duplicate_cases'])}):")
        print("-" * 50)
        for i, case in enumerate(results['duplicate_cases'], 1):
            print(f"\n{i:2d}. {case['author']}")
            print(f"    Score: {case['similarity_score']:.3f}")
            print(f"    Titre 1 ({case['year1']}): {case['title1']}")
            print(f"    Titre 2 ({case['year2']}): {case['title2']}")
    
    # Afficher tous les homonymes
    if results['homonym_cases']:
        print(f"\nTOUS LES HOMONYMES ({len(results['homonym_cases'])}):")
        print("-" * 50)
        for i, case in enumerate(results['homonym_cases'], 1):
            print(f"\n{i:2d}. {case['author']}")
            print(f"    Écart: {case['year_gap']} ans, Score: {case['similarity_score']:.3f}")
            print(f"    Titre 1 ({case['year1']}): {case['title1']}")
            print(f"    Titre 2 ({case['year2']}): {case['title2']}")

def add_clustering_arguments(parser):
    """Ajoute les arguments pour le clustering"""
    
    parser.add_argument(
        "--analyse",
        help="Lancer l'analyse des doublons et homonymes sur un fichier CSV du dossier extraction",
        action="store_true"
    )

def main():
    """
    Main function that handles command line arguments and orchestrates the entire 
    HAL data extraction and analysis workflow.
    
    Supports filtering by year, domain, document type, configurable name matching
    sensitivity, automatic generation of graphs and reports, and clustering analysis.
    """
    parser = argparse.ArgumentParser(
        description=(
            "This file allows scientific data extraction from the HAL database.\n"
            "Possibility to filter publications by period, scientific domain, document type,\n"
            "and configure the sensitivity of author name matching.\n\n"
            "NEW THESIS TYPES:\n"
            "- 'Thèse (Doctorant)' : PhD theses only (THESE documents)\n"
            "- 'Thèse (HDR)' : HDR theses only (HDR documents)\n"
            "- 'Thèse' : Both PhD and HDR theses (THESE + HDR documents)\n\n"
            "CLUSTERING ANALYSIS:\n"
            "- Analyze CSV files with pre-trained machine learning models\n"
            "- Detect duplicates and homonyms automatically\n"
            "- Clean data and export results\n\n"
            "NOTE: To train a new model, use: python train_model.py\n"
            "IMPORTANT: The system uses double queries (prenom nom + nom prenom) for better results."
        ),
        epilog=(
            'Examples:\n'
            'python main.py --year 2019-2024 --domain "Mathematics" --type "Thèse (Doctorant)"\n'
            'python main.py --type "Thèse (HDR)" --graphs\n'
            'python main.py --type "Thèse" --threshold 1\n'
            'python main.py --threshold 3 --reportpdf\n'
            'python main.py --graphs --reportpdf --reportlatex\n\n'
            'Clustering analysis examples:\n'
            'python main.py --analyse\n\n'
            'Model training (separate script):\n'
            'python train_model.py\n\n'
            'To see available types and sensitivity levels:\n'
            'python main.py --list-types\n'
            'python main.py --list-sensitivity'
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "--year", 
        help="Filter publications by period (format: YYYY-YYYY). Example: 2019-2024.", 
        type=str
    )
    parser.add_argument(
        "--domain",
        help='Filter publications by scientific domain. Example: "Mathematics".',
        type=str,
    )
    parser.add_argument(
        "--type", 
        help=(
            'Filter publications by document type. Examples:\n'
            '  "Thèse (Doctorant)" - PhD theses only\n'
            '  "Thèse (HDR)" - HDR theses only\n'
            '  "Thèse" - Both PhD and HDR theses\n'
            '  "Article de journal" - Journal articles'
        ), 
        type=str
    )
    parser.add_argument(
        "--threshold",
        help=(
            f"Sensitivity threshold for name matching (0-4). Default: {DEFAULT_THRESHOLD}\n"
            "0 = very strict (exact match only)\n"
            "1 = strict (1 character difference maximum)\n"
            "2 = moderate (2 characters difference maximum) - Default\n"
            "3 = permissive (3 characters difference maximum)\n"
            "4 = very permissive (4 characters difference maximum)"
        ),
        type=int,
        choices=[0, 1, 2, 3, 4],
        default=DEFAULT_THRESHOLD
    )
    parser.add_argument(
        "--list-domains", 
        help="Display the complete list of available domains for filtering.", 
        action="store_true"
    )
    parser.add_argument(
        "--list-types", 
        help="Display the complete list of available document types for filtering.", 
        action="store_true"
    )
    parser.add_argument(
        "--list-sensitivity",
        help="Display the list of available sensitivity levels.",
        action="store_true"
    )
    parser.add_argument(
        "--graphs",
        help="Automatically generate graphs after extraction.",
        action="store_true"
    )
    parser.add_argument(
        "--reportpdf",
        help="Automatically generate a PDF report after extraction.",
        action="store_true"
    )
    parser.add_argument(
        "--reportlatex",
        help="Automatically generate a LaTeX report after extraction.",
        action="store_true"
    )

    # Ajouter les arguments pour le clustering
    add_clustering_arguments(parser)

    global args
    args = parser.parse_args()

    # Gérer l'option d'analyse de clustering
    if args.analyse:
        print("Mode analyse des doublons et homonymes activé")
        analyze_csv_cli()
        exit(0)

    if args.list_sensitivity:
        print("Available sensitivity levels:\n")
        print("0: Very strict (exact match only)")
        print("1: Strict (1 character difference maximum)")
        print("2: Moderate (2 characters difference maximum) - Default")
        print("3: Permissive (3 characters difference maximum)")
        print("4: Very permissive (4 characters difference maximum)")
        print(f"\nDefault level: 2 (moderate)")
        exit()

    if args.list_domains:
        domains = list_domains()
        print("List of available domains for filtering:\n")
        for code, name in domains.items():
            print(f"{code}: {name}")
        exit()

    if args.list_types:
        types = list_types()
        print("ENHANCED: List of available document types for filtering:\n")
        
        # NEW: Group thesis types for better display
        thesis_types = []
        other_types = []
        
        for code, name in types.items():
            if 'thèse' in name.lower() or 'habilitation' in name.lower():
                thesis_types.append((code, name))
            else:
                other_types.append((code, name))
        
        if thesis_types:
            print("THESIS TYPES:")
            for code, name in thesis_types:
                if 'doctorant' in name.lower():
                    print(f"  {code}: {name} (PhD only)")
                elif 'hdr' in name.lower() and 'thèse' in name.lower():
                    print(f"  {code}: {name} (HDR only)")
                elif name == "Thèse":
                    print(f"  {code}: {name} (PhD + HDR)")
                else:
                    print(f"  {code}: {name} (PhD + HDR)")
            print()
        
        print("OTHER DOCUMENT TYPES:")
        for code, name in other_types:
            print(f"  {code}: {name}")
        
        exit()

    sensitivity_names = {0: "very strict", 1: "strict", 2: "moderate", 3: "permissive", 4: "very permissive"}
    print(f"Sensitivity threshold used: {args.threshold} ({sensitivity_names[args.threshold]})")

    try:
        csv_file_path = get_user_selected_csv()
        scientists_df = pd.read_csv(csv_file_path, encoding='utf-8-sig')
        
        display_extraction_summary()
        
    except FileNotFoundError as e:
        print(e)
        exit(1)

    print("Starting extraction...")
    init_progress_bar()

    results = []
    total_tasks = len(scientists_df)
    
    with ThreadPoolExecutor(max_workers=100) as executor:
        future_to_row = {
            executor.submit(fetch_data, row): row for index, row in scientists_df.iterrows()
        }

        completed_tasks = 0
        for future in as_completed(future_to_row):
            results.append(future.result())
            completed_tasks += 1
            create_progress_bar(completed_tasks, total_tasks, "Extraction in progress")

    all_results = pd.concat(results, ignore_index=True)

    extraction_directory = create_extraction_folder()
    filename = generate_filename(args.year, args.domain, args.type)
    output_path = os.path.join(extraction_directory, filename)
    all_results.to_csv(output_path, index=False)
    
    print(f"Extraction completed. Results saved to: {output_path}")
    
    # ENHANCED: Detailed statistics display
    if not all_results.empty:
        print(f"\nExtraction completed: {len(all_results)} publications found")
        
        # Display document type statistics if available
        if 'Type de Document' in all_results.columns:
            type_counts = all_results['Type de Document'].value_counts()
            print("\nDocument types found:")
            for doc_type, count in type_counts.items():
                print(f"  {doc_type}: {count} publications")
            
            # NEW: Special message for thesis extractions
            if args.type and any(keyword in args.type.lower() for keyword in ['thèse', 'habilitation']):
                total_theses = sum(count for doc_type, count in type_counts.items() 
                                 if 'thèse' in doc_type.lower() or 'habilitation' in doc_type.lower())
                print(f"\n Total thesis-related documents: {total_theses}")

    if args.graphs:
        try:
            print("Generating graphs...")
            
            # Create directories if they don't exist
            os.makedirs("html", exist_ok=True)
            os.makedirs("png", exist_ok=True)
            
            plot_publications_by_year(output_path, output_html="html/pubs_by_year.html", output_png="png/pubs_by_year.png")
            plot_document_types(output_path, output_html="html/type_distribution.html", output_png="png/type_distribution.png")
            plot_keywords(output_path, output_html="html/keywords_distribution.html", output_png="png/keywords_distribution.png")
            plot_top_domains(output_path, output_html="html/domain_distribution.html", output_png="png/domain_distribution.png")
            plot_publications_by_author(output_path, output_html="html/top_authors.html", output_png="png/top_authors.png")
            plot_structures_stacked(output_path, output_html="html/structures_stacked.html", output_png="png/structures_stacked.png")
            plot_publications_trends(output_path, output_html="html/publication_trends.html", output_png="png/publication_trends.png")
            plot_employer_distribution(output_path, output_html="html/employer_distribution.html", output_png="png/employer_distribution.png")
            plot_theses_hdr_by_year(output_path, output_html="html/theses_hdr_by_year.html", output_png="png/theses_hdr_by_year.png")
            plot_theses_keywords_wordcloud(output_path, output_html="html/theses_keywords_wordcloud.html", output_png="png/theses_keywords_wordcloud.png")
  
            dashboard_file = create_dashboard()
            webbrowser.open("file://" + os.path.realpath(dashboard_file))
            print("Graphs generated and opened in browser.")
        except Exception as e:
            print(f"Error during graph generation: {e}")

    if args.reportpdf:
        try:
            print("Generating PDF report...")
            nom_fichier_csv = os.path.basename(output_path).replace(".csv", "")
            generate_pdf_report(nom_fichier_csv)
        except Exception as e:
            print(f"Error during PDF report generation: {e}")

    if args.reportlatex:
        try:
            print("Generating LaTeX report...")
            nom_fichier_csv = os.path.basename(output_path).replace(".csv", "")
            generate_latex_report(nom_fichier_csv)
        except Exception as e:
            print(f"Error during LaTeX report generation: {e}")


if __name__ == "__main__":
    main()