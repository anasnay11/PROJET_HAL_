# -*- coding: utf-8 -*-

# main.py

from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import argparse
from hal_data import get_hal_data, extract_author_id_simple
from utils import generate_filename
from mapping import list_domains, list_types
from config import get_threshold_from_level, list_sensitivity_levels, DEFAULT_THRESHOLD
from dashboard_generator import create_dashboard
from report_generator_main import generate_pdf_report, generate_latex_report
from detection_doublons_homonymes import DuplicateHomonymDetector
import webbrowser
import os
import sys
import time
import json
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
    plot_temporal_evolution_by_team,
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
        bar = '█' * filled_length + '▒' * (bar_length - filled_length)
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
    """
    Create extraction folder for output files
    
    Returns:
        str: Path to extraction directory
    """
    current_directory = os.path.dirname(os.path.abspath(__file__))
    extraction_directory = os.path.join(current_directory, "extraction")

    if not os.path.exists(extraction_directory):
        os.makedirs(extraction_directory)

    return extraction_directory

def extract_hal_ids_step1(scientists_df, threshold=DEFAULT_THRESHOLD):
    """
    STEP 1: Extract HAL identifiers for all scientists in the DataFrame
    Creates a new CSV file with IdHAL column added
    
    Args:
        scientists_df (pd.DataFrame): DataFrame containing scientist data with nom/prenom
        threshold (int): Threshold for name matching sensitivity
        
    Returns:
        str: Path to the created CSV file with IdHAL column
    """
    print("\n" + "="*60)
    print("STEP 1: HAL IDENTIFIER EXTRACTION")
    print("="*60)
    print(f"Processing {len(scientists_df)} authors...")
    
    init_progress_bar()
    
    result_df = scientists_df.copy()
    result_df['IdHAL'] = ''
    
    total_scientists = len(scientists_df)
    completed = 0
    
    with ThreadPoolExecutor(max_workers=100) as executor:
        future_to_index = {
            executor.submit(
                extract_author_id_simple, 
                row.get('title', ''), 
                row.get('nom', ''), 
                row.get('prenom', ''),
                threshold=threshold
            ): index 
            for index, row in scientists_df.iterrows()
        }
        
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                hal_id = future.result()
                result_df.at[index, 'IdHAL'] = hal_id
            except Exception as e:
                result_df.at[index, 'IdHAL'] = " "
                print(f"\nError for index {index}: {str(e)}")
            
            completed += 1
            create_progress_bar(completed, total_scientists, "Extracting HAL IDs")
    
    extraction_directory = create_extraction_folder()
    timestamp = int(time.time())
    filename = f"step1_hal_identifiers_{timestamp}.csv"
    output_path = os.path.join(extraction_directory, filename)
    
    result_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    
    found_ids = len(result_df[result_df['IdHAL'].str.strip() != ''])
    success_rate = (found_ids / total_scientists) * 100 if total_scientists > 0 else 0
    
    print(f"\n\nStep 1 completed!")
    print(f"  • Total authors processed: {total_scientists}")
    print(f"  • HAL identifiers found: {found_ids}")
    print(f"  • Success rate: {success_rate:.1f}%")
    print(f"  • File saved: {output_path}")
    
    return output_path

def list_extraction_csv_files():
    """
    Lists available CSV files in the extraction directory
    
    Returns:
        tuple: (extraction_directory_path, list_of_csv_files)
        
    Raises:
        FileNotFoundError: If extraction directory or CSV files are not found
    """
    current_directory = os.path.dirname(os.path.abspath(__file__))
    extraction_directory = os.path.join(current_directory, "extraction")
    
    if not os.path.exists(extraction_directory):
        raise FileNotFoundError(f"The 'extraction' folder does not exist in {current_directory}")

    csv_files = [f for f in os.listdir(extraction_directory) if f.endswith(".csv")]
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in 'extraction' folder")
    
    return extraction_directory, csv_files

def select_extraction_csv():
    """
    Interactive selection of a CSV file from the extraction directory
    
    Returns:
        str: Full path to the selected CSV file
        
    Raises:
        SystemExit: If invalid choice or incorrect input
    """
    try:
        extraction_directory, csv_files = list_extraction_csv_files()
        
        print("\n" + "="*60)
        print("AVAILABLE CSV FILES IN 'extraction/' FOLDER")
        print("="*60)
        
        for i, file in enumerate(csv_files, start=1):
            file_path = os.path.join(extraction_directory, file)
            file_size = os.path.getsize(file_path)
            size_mb = file_size / (1024 * 1024)
            
            print(f"{i:2d}. {file:<40} ({size_mb:.1f} MB)")

        print("="*60)
        choice = int(input(f"\nSelect a file (1-{len(csv_files)}): "))
        
        if 1 <= choice <= len(csv_files):
            selected_file = os.path.join(extraction_directory, csv_files[choice - 1])
            print(f"Selected file: {csv_files[choice - 1]}")
            return selected_file
        else:
            print("Invalid choice. Please restart the program.")
            exit(1)
            
    except ValueError:
        print("Invalid input. Please enter a number.")
        exit(1)
    except FileNotFoundError as e:
        print(f"{e}")
        exit(1)

def fetch_data_with_idhal(row, period, domain_filter, type_filter, threshold):
    """
    Wrapper function for parallel data extraction with IdHAL support
    Uses HAL identifier if available, falls back to full name otherwise
    
    Args:
        row: DataFrame row containing author information
        period: Time period filter
        domain_filter: List of domains to filter
        type_filter: List of document types to filter
        threshold: Name matching sensitivity threshold
        
    Returns:
        pd.DataFrame: Extracted publications for this author
    """
    nom = row.get("nom", "")
    prenom = row.get("prenom", "")
    title = row.get("title", "")
    author_id = row.get("IdHAL", "")
    
    return get_hal_data(
        nom=nom,
        prenom=prenom,
        title=title if title else None,
        author_id=author_id if author_id and str(author_id).strip() and author_id != " " else None,
        period=period, 
        domain_filter=domain_filter, 
        type_filter=type_filter,
        threshold=threshold
    )

def extract_publications_step2(scientists_df, period=None, domain_filter=None, type_filter=None, threshold=DEFAULT_THRESHOLD):
    """
    STEP 2: Extract publications using CSV file with IdHAL column
    Uses HAL identifiers when available for optimal extraction
    
    Args:
        scientists_df (pd.DataFrame): DataFrame with IdHAL column
        period (str): Time period filter (format: YYYY-YYYY)
        domain_filter (str): Domain to filter
        type_filter (str): Document type to filter
        threshold (int): Name matching sensitivity threshold
        
    Returns:
        str: Path to the extraction results file
    """
    print("\n" + "="*60)
    print("STEP 2: PUBLICATION EXTRACTION")
    print("="*60)
    
    has_idhal = 'IdHAL' in scientists_df.columns
    has_title = 'title' in scientists_df.columns
    
    if has_idhal:
        idhal_count = len(scientists_df[scientists_df['IdHAL'].str.strip() != ''])
        print(f"Extraction method: HAL identifier-based (optimal)")
        print(f"  • {idhal_count} authors with HAL identifiers")
        print(f"  • {len(scientists_df) - idhal_count} authors will use fallback method")
    elif has_title:
        print(f"Extraction method: Full name-based (standard)")
    else:
        print(f"Extraction method: nom/prenom-based (basic)")
    
    filters_applied = []
    if period:
        filters_applied.append(f"period: {period}")
    if type_filter:
        filters_applied.append(f"type: {type_filter}")
    if domain_filter:
        filters_applied.append(f"domain: {domain_filter}")
    
    if filters_applied:
        print(f"Filters: {', '.join(filters_applied)}")
    else:
        print(f"Filters: none (full extraction)")
    
    print(f"Processing {len(scientists_df)} authors...")
    
    init_progress_bar()
    
    results = []
    total_tasks = len(scientists_df)
    completed_tasks = 0
    
    domain_list = [domain_filter] if domain_filter else None
    type_list = [type_filter] if type_filter else None
    
    with ThreadPoolExecutor(max_workers=100) as executor:
        future_to_row = {
            executor.submit(
                fetch_data_with_idhal, 
                row, 
                period, 
                domain_list, 
                type_list, 
                threshold
            ): row 
            for index, row in scientists_df.iterrows()
        }

        for future in as_completed(future_to_row):
            results.append(future.result())
            completed_tasks += 1
            create_progress_bar(completed_tasks, total_tasks, "Extracting publications")

    all_results = pd.concat(results, ignore_index=True)

    extraction_directory = create_extraction_folder()
    filename = generate_filename(period, domain_filter, type_filter)
    output_path = os.path.join(extraction_directory, filename)
    all_results.to_csv(output_path, index=False, encoding='utf-8-sig')
    
    print(f"\n\nStep 2 completed!")
    print(f"  • Publications found: {len(all_results)}")
    print(f"  • File saved: {output_path}")
    
    if not all_results.empty and 'Type de Document' in all_results.columns:
        type_counts = all_results['Type de Document'].value_counts()
        print(f"\nDocument types distribution:")
        for doc_type, count in type_counts.head(5).items():
            print(f"  • {doc_type}: {count}")
    
    return output_path

def display_workflow_menu():
    """
    Display the two-step workflow menu
    
    Returns:
        int: User's choice (1 or 2)
    """
    print("\n" + "="*60)
    print("HAL DATA EXTRACTION - TWO-STEP WORKFLOW")
    print("="*60)
    print("\nPlease choose your starting point:")
    print("\n1. STEP 1: Extract HAL identifiers")
    print("   - Start with a CSV file containing 'nom' and 'prenom'")
    print("   - Extracts HAL identifiers for all authors")
    print("   - Creates a new CSV with 'IdHAL' column added")
    print("\n2. STEP 2: Extract publications")
    print("   - Start with a CSV file containing 'IdHAL' column")
    print("   - Uses HAL identifiers for optimal extraction")
    print("   - Can apply filters (period, domain, type)")
    print("\n" + "="*60)
    
    while True:
        try:
            choice = int(input("\nEnter your choice (1 or 2): "))
            if choice in [1, 2]:
                return choice
            else:
                print("Invalid choice. Please enter 1 or 2.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def analyze_csv_cli():
    """
    Command line interface for CSV file analysis with duplicate/homonym detection
    """
    print("\n" + "="*60)
    print("DUPLICATE & HOMONYM DETECTION ANALYSIS")
    print("="*60)
    print("Method based on authIdPerson_i from HAL API")
    print("="*60)
    
    analysis_file = select_extraction_csv()
    
    print(f"\nLaboratory file (optional):")
    print("A file with 'nom', 'prenom', 'unite_de_recherche' columns")
    print("improves homonym detection accuracy.")
    
    use_lab_file = input("Use a laboratory file? (y/n): ").lower()
    laboratory_file = None
    
    if use_lab_file in ['y', 'yes']:
        try:
            lab_files = [f for f in os.listdir('.') if f.endswith('.csv')]
            if lab_files:
                print("\nAvailable CSV files:")
                for i, file in enumerate(lab_files, 1):
                    print(f"{i}. {file}")
                
                choice = int(input("Choose a file (number): "))
                if 1 <= choice <= len(lab_files):
                    laboratory_file = lab_files[choice - 1]
                    print(f"Laboratory file selected: {laboratory_file}")
            else:
                print("No CSV files found in current directory.")
        except (ValueError, IndexError):
            print("Invalid choice. Analysis without laboratory file.")
    
    print(f"\nAnalyzing file: {os.path.basename(analysis_file)}")
    if laboratory_file:
        print(f"Laboratory file: {laboratory_file}")
    
    print("\nAnalysis in progress... (querying HAL API)")
    
    try:
        detector = DuplicateHomonymDetector()
        results = detector.analyze_csv_file(analysis_file, laboratory_file)
        
        detector.display_results(results)
        
        base_name = os.path.splitext(os.path.basename(analysis_file))[0]
        results_file = f'detection_results_{base_name}.json'
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\nResults saved in: {results_file}")
        
        propose_actions(results, analysis_file)
        
    except Exception as e:
        print(f"\nERROR during analysis: {str(e)}")

def propose_actions(results, analysis_file):
    """
    Proposes actions to the user after analysis
    
    Args:
        results: Dictionary containing analysis results
        analysis_file: Path to the analyzed file
    """
    print(f"\n" + "="*60)
    print("AVAILABLE ACTIONS")
    print("="*60)
    
    print("1. Automatically process data")
    print("2. Export detailed results")
    print("3. Display more details")
    print("4. Exit")
    
    while True:
        try:
            choice = int(input(f"\nChoose an action (1-4): "))
            
            if choice == 1:
                treat_data_cli(results, analysis_file)
                break
            elif choice == 2:
                export_results_cli(results, analysis_file)
                break
            elif choice == 3:
                display_detailed_results(results)
                continue
            elif choice == 4:
                print("Analysis completed.")
                break
            else:
                print("Invalid choice. Please choose between 1 and 4.")
                
        except ValueError:
            print("Invalid input. Please enter a number.")

def treat_data_cli(results, analysis_file):
    """
    Automatically processes problematic data
    
    Args:
        results: Dictionary containing analysis results
        analysis_file: Path to the analyzed file
    """
    print(f"\n" + "="*50)
    print("AUTOMATIC DATA PROCESSING")
    print("="*50)
    
    summary = results['summary']
    
    print(f"Processing impact:")
    print(f"   • Duplicates to remove: {summary['duplicate_publications']} cases")
    print(f"   • Homonyms detected: {summary['homonym_publications']} cases")
    print(f"   • Collaborations: {len(results['collaborator_cases'])} cases")
    print(f"   • Multi-theses: {summary['multi_thesis_publications']} cases")
    
    print(f"\nProcessing options:")
    print(f"1. Remove duplicates only")
    print(f"2. Remove duplicates + collaborations")
    print(f"3. Complete processing (maximum cleaning)")
    print(f"4. Custom processing")
    
    try:
        choice = int(input(f"\nChoose processing type (1-4): "))
        
        original_df = pd.read_csv(analysis_file)
        processed_df = original_df.copy()
        
        actions_performed = []
        indices_to_remove = set()
        
        if choice == 1 or choice == 2 or choice == 3:
            if results['duplicate_cases']:
                for case in results['duplicate_cases']:
                    indices_to_remove.add(case['publication2']['index'])
                
                actions_performed.append(f"Removed {len(results['duplicate_cases'])} duplicates")
        
        if choice == 2 or choice == 3:
            if results['collaborator_cases']:
                for case in results['collaborator_cases']:
                    collab_data = case['collaboration']['row_data']
                    if hasattr(collab_data, 'name'):
                        indices_to_remove.add(collab_data.name)
                
                actions_performed.append(f"Removed {len(results['collaborator_cases'])} collaborations")
        
        if choice == 4:
            print(f"\nCustom processing:")
            
            if results['duplicate_cases']:
                remove_dup = input("Remove duplicates? (y/n): ").lower()
                if remove_dup in ['y', 'yes']:
                    for case in results['duplicate_cases']:
                        indices_to_remove.add(case['publication2']['index'])
                    actions_performed.append(f"Removed {len(results['duplicate_cases'])} duplicates")
            
            if results['collaborator_cases']:
                remove_collab = input("Remove collaborations? (y/n): ").lower()
                if remove_collab in ['y', 'yes']:
                    for case in results['collaborator_cases']:
                        collab_data = case['collaboration']['row_data']
                        if hasattr(collab_data, 'name'):
                            indices_to_remove.add(collab_data.name)
                    actions_performed.append(f"Removed {len(results['collaborator_cases'])} collaborations")
        
        if indices_to_remove:
            processed_df = processed_df.drop(indices_to_remove).reset_index(drop=True)
        
        base_name = os.path.splitext(os.path.basename(analysis_file))[0]
        processed_filename = f"{base_name}_cleaned.csv"
        processed_path = os.path.join('extraction', processed_filename)
        
        processed_df.to_csv(processed_path, index=False, encoding='utf-8-sig')
        
        print(f"\nPROCESSING COMPLETED")
        print(f"Original publications: {len(original_df)}")
        print(f"Processed publications: {len(processed_df)}")
        print(f"Removed publications: {len(original_df) - len(processed_df)}")
        print(f"File saved: {processed_path}")
        
        if actions_performed:
            print(f"\nActions performed:")
            for action in actions_performed:
                print(f"   • {action}")
        
    except ValueError:
        print("Invalid input.")
    except Exception as e:
        print(f"Error during processing: {str(e)}")

def export_results_cli(results, analysis_file):
    """
    Exports detailed results to CSV files
    
    Args:
        results: Dictionary containing analysis results
        analysis_file: Path to the analyzed file
    """
    print(f"\n" + "="*50)
    print("RESULTS EXPORT")
    print("="*50)
    
    base_name = os.path.splitext(os.path.basename(analysis_file))[0]
    export_dir = 'extraction'
    
    try:
        exported_files = []
        
        if results['duplicate_cases']:
            dup_df = pd.DataFrame([
                {
                    'Author': case['author'],
                    'Type': case['type'],
                    'Title_1': case['publication1']['title'],
                    'Title_2': case['publication2']['title'],
                    'Year_1': case['publication1']['year'],
                    'Year_2': case['publication2']['year'],
                    'Similarity': case['similarity_score'],
                    'Year_gap': case['year_gap'],
                    'Docid_1': case['publication1']['docid'],
                    'Docid_2': case['publication2']['docid']
                }
                for case in results['duplicate_cases']
            ])
            dup_path = os.path.join(export_dir, f'{base_name}_duplicates.csv')
            dup_df.to_csv(dup_path, index=False, encoding='utf-8-sig')
            exported_files.append(dup_path)
        
        if results['homonym_cases']:
            hom_df = pd.DataFrame([
                {
                    'Author': case['author'],
                    'Type': case['type'],
                    'Title_1': case['publication1']['title'],
                    'Title_2': case['publication2']['title'],
                    'Year_1': case['publication1']['year'],
                    'Year_2': case['publication2']['year'],
                    'Domain_1': case['publication1']['domain'],
                    'Domain_2': case['publication2']['domain'],
                    'Lab_1': case['publication1']['lab'],
                    'Lab_2': case['publication2']['lab']
                }
                for case in results['homonym_cases']
            ])
            hom_path = os.path.join(export_dir, f'{base_name}_homonyms.csv')
            hom_df.to_csv(hom_path, index=False, encoding='utf-8-sig')
            exported_files.append(hom_path)
        
        if results['collaborator_cases']:
            collab_df = pd.DataFrame([
                {
                    'Author': case['author'],
                    'Type': case['type'],
                    'Main_thesis_year': case['main_thesis']['row_data']['Année de Publication'],
                    'Main_thesis_title': case['main_thesis']['row_data']['Titre'],
                    'Collaboration_year': case['collaboration']['row_data']['Année de Publication'],
                    'Collaboration_title': case['collaboration']['row_data']['Titre']
                }
                for case in results['collaborator_cases']
            ])
            collab_path = os.path.join(export_dir, f'{base_name}_collaborations.csv')
            collab_df.to_csv(collab_path, index=False, encoding='utf-8-sig')
            exported_files.append(collab_path)
        
        summary_path = os.path.join(export_dir, f'{base_name}_summary.txt')
        with open(summary_path, 'w', encoding='utf-8') as f:
            summary = results['summary']
            f.write("ANALYSIS SUMMARY\n")
            f.write("="*50 + "\n\n")
            f.write(f"Analyzed file: {os.path.basename(analysis_file)}\n")
            f.write(f"Analysis date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("GLOBAL STATISTICS:\n")
            f.write(f"Total publications: {summary['total_publications']}\n")
            f.write(f"Authors with multiple publications: {summary['authors_with_multiple_pubs']}\n\n")
            f.write("DETECTIONS:\n")
            f.write(f"Duplicates: {summary['duplicate_publications']}\n")
            f.write(f"Homonyms: {summary['homonym_publications']}\n")
            f.write(f"Multi-theses: {summary['multi_thesis_publications']}\n")
            f.write(f"Collaborations: {len(results['collaborator_cases'])}\n")
            f.write(f"Technical issues: {len(results['no_authid_cases'])}\n\n")
            f.write("METHOD USED:\n")
            f.write("• Algorithm based on HAL authIdPerson_i\n")
            f.write("• Title similarity threshold: 0.8\n")
            f.write("• Temporal gap threshold: 2 years\n")
            f.write("• Automatic collaboration detection\n")
            f.write("• Robust handling of missing authIdPerson_i\n")
        
        exported_files.append(summary_path)
        
        print(f"Results successfully exported:")
        for file_path in exported_files:
            print(f"   {os.path.basename(file_path)}")
        
        print(f"\nExport directory: {export_dir}")
        
    except Exception as e:
        print(f"Error during export: {str(e)}")

def display_detailed_results(results):
    """
    Displays detailed analysis results
    
    Args:
        results: Dictionary containing analysis results
    """
    print(f"\n" + "="*60)
    print("DETAILED RESULTS")
    print("="*60)
    
    if results['duplicate_cases']:
        print(f"\nALL DUPLICATES ({len(results['duplicate_cases'])}):")
        print("-" * 50)
        for i, case in enumerate(results['duplicate_cases'], 1):
            print(f"\n{i:2d}. {case['author']}")
            print(f"    Score: {case['similarity_score']:.3f}")
            print(f"    Title 1 ({case['publication1']['year']}): {case['publication1']['title']}")
            print(f"    Title 2 ({case['publication2']['year']}): {case['publication2']['title']}")
    
    if results['homonym_cases']:
        print(f"\nALL HOMONYMS ({len(results['homonym_cases'])}):")
        print("-" * 50)
        for i, case in enumerate(results['homonym_cases'], 1):
            print(f"\n{i:2d}. {case['author']}")
            print(f"    Domains: {case['publication1']['domain']} / {case['publication2']['domain']}")
            print(f"    Title 1 ({case['publication1']['year']}): {case['publication1']['title']}")
            print(f"    Title 2 ({case['publication2']['year']}): {case['publication2']['title']}")

def add_detection_arguments(parser):
    """
    Adds arguments for duplicate and homonym detection
    
    Args:
        parser: ArgumentParser instance to add arguments to
    """
    parser.add_argument(
        "--analyse",
        help="Launch duplicate and homonym analysis on a CSV file from extraction folder",
        action="store_true"
    )

def main():
    """
    Main function that orchestrates the two-step HAL data extraction workflow
    
    STEP 1: Extract HAL identifiers from CSV with nom/prenom
    STEP 2: Extract publications using CSV with IdHAL column
    
    Also supports detection analysis, graph generation, and report creation
    """
    parser = argparse.ArgumentParser(
        description=(
            "HAL DATA EXTRACTION - TWO-STEP WORKFLOW\n\n"
            "STEP 1: Extract HAL identifiers\n"
            "  - Input: CSV with 'nom' and 'prenom' columns\n"
            "  - Output: CSV with added 'IdHAL' column\n"
            "  - Purpose: Get HAL identifiers for optimal extraction\n\n"
            "STEP 2: Extract publications\n"
            "  - Input: CSV with 'IdHAL' column (from Step 1)\n"
            "  - Output: Full publication data\n"
            "  - Purpose: Extract complete publication information\n"
            "  - Supports filters: period, domain, document type\n\n"
            "DETECTION ANALYSIS:\n"
            "  - Analyze CSV files for duplicates and homonyms\n"
            "  - Method based on HAL authIdPerson_i\n"
            "  - Automatic data cleaning and export\n\n"
            "The two-step approach ensures optimal extraction by using\n"
            "HAL identifiers when available, with fallback to name matching."
        ),
        epilog=(
            'Examples:\n\n'
            'Interactive mode (recommended):\n'
            '  python main.py\n\n'
            'Step 2 with filters:\n'
            '  python main.py --year 2019-2024 --domain "Mathematics"\n'
            '  python main.py --type "Thèse" --threshold 1\n\n'
            'Step 2 with outputs:\n'
            '  python main.py --graphs\n'
            '  python main.py --graphs --reportpdf\n\n'
            'Detection analysis:\n'
            '  python main.py --analyse\n\n'
            'List available options:\n'
            '  python main.py --list-types\n'
            '  python main.py --list-domains\n'
            '  python main.py --list-sensitivity'
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument("--year", help="Filter publications by period (format: YYYY-YYYY). Example: 2019-2024.", type=str)
    parser.add_argument("--domain", help='Filter publications by scientific domain. Example: "Mathematics".', type=str)
    parser.add_argument("--type", help='Filter publications by document type. Example: "Thèse", "Article de journal"', type=str)
    parser.add_argument("--threshold", help=f"Sensitivity threshold for name matching (0-4). Default: {DEFAULT_THRESHOLD}\n0 = very strict (exact match only)\n1 = strict (1 character difference maximum)\n2 = moderate (2 characters difference maximum) - Default\n3 = permissive (3 characters difference maximum)\n4 = very permissive (4 characters difference maximum)", type=int, choices=[0, 1, 2, 3, 4], default=DEFAULT_THRESHOLD)
    parser.add_argument("--list-domains", help="Display the complete list of available domains for filtering.", action="store_true")
    parser.add_argument("--list-types", help="Display the complete list of available document types for filtering.", action="store_true")
    parser.add_argument("--list-sensitivity", help="Display the list of available sensitivity levels.", action="store_true")
    parser.add_argument("--graphs", help="Automatically generate graphs after extraction.", action="store_true")
    parser.add_argument("--reportpdf", help="Automatically generate a PDF report after extraction.", action="store_true")
    parser.add_argument("--reportlatex", help="Automatically generate a LaTeX report after extraction.", action="store_true")

    add_detection_arguments(parser)

    global args
    args = parser.parse_args()

    if args.analyse:
        print("Duplicate and homonym detection mode activated")
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
        print("List of available document types for filtering:\n")
        
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
                print(f"  {code}: {name}")
            print()
        
        print("OTHER DOCUMENT TYPES:")
        for code, name in other_types:
            print(f"  {code}: {name}")
        
        exit()

    workflow_choice = display_workflow_menu()
    
    if workflow_choice == 1:
        try:
            csv_file_path = get_user_selected_csv()
            scientists_df = pd.read_csv(csv_file_path, encoding='utf-8-sig')
            
            required_columns = ['nom', 'prenom']
            missing_columns = [col for col in required_columns if col not in scientists_df.columns]
            
            if missing_columns:
                print(f"\nERROR: Missing required columns: {', '.join(missing_columns)}")
                print("The CSV file must contain 'nom' and 'prenom' columns.")
                exit(1)
            
            sensitivity_names = {0: "very strict", 1: "strict", 2: "moderate", 3: "permissive", 4: "very permissive"}
            print(f"\nSensitivity threshold: {args.threshold} ({sensitivity_names[args.threshold]})")
            
            output_file = extract_hal_ids_step1(scientists_df, threshold=args.threshold)
            
            print(f"\n{'='*60}")
            print("NEXT STEP:")
            print(f"{'='*60}")
            print("Use the generated file for Step 2 (publication extraction)")
            print(f"Run: python main.py")
            print("Then select option 2 and choose the file:")
            print(f"  {os.path.basename(output_file)}")
            
        except FileNotFoundError as e:
            print(e)
            exit(1)
        except Exception as e:
            print(f"Error during Step 1: {str(e)}")
            exit(1)
    
    elif workflow_choice == 2:
        try:
            csv_file_path = select_extraction_csv()
            scientists_df = pd.read_csv(csv_file_path, encoding='utf-8-sig')
            
            required_columns = ['nom', 'prenom']
            missing_columns = [col for col in required_columns if col not in scientists_df.columns]
            
            if missing_columns:
                print(f"\nERROR: Missing required columns: {', '.join(missing_columns)}")
                print("The CSV file must contain at minimum 'nom' and 'prenom' columns.")
                exit(1)
            
            has_idhal = 'IdHAL' in scientists_df.columns
            if not has_idhal:
                print("\nWARNING: No 'IdHAL' column found in the file.")
                print("Extraction will use basic name matching (less optimal).")
                proceed = input("Continue anyway? (y/n): ").lower()
                if proceed not in ['y', 'yes']:
                    print("Extraction cancelled.")
                    exit(0)
            
            sensitivity_names = {0: "very strict", 1: "strict", 2: "moderate", 3: "permissive", 4: "very permissive"}
            print(f"\nSensitivity threshold: {args.threshold} ({sensitivity_names[args.threshold]})")
            
            output_path = extract_publications_step2(
                scientists_df,
                period=args.year,
                domain_filter=args.domain,
                type_filter=args.type,
                threshold=args.threshold
            )
            
            if args.graphs:
                try:
                    print("\n" + "="*60)
                    print("GENERATING GRAPHS")
                    print("="*60)
                    
                    os.makedirs("html", exist_ok=True)
                    os.makedirs("png", exist_ok=True)
                    
                    print("Creating visualizations...")
                    
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
                    plot_temporal_evolution_by_team(output_path, output_html="html/temporal_evolution_teams.html", output_png="png/temporal_evolution_teams.png")
                    
                    dashboard_file = create_dashboard()
                    webbrowser.open("file://" + os.path.realpath(dashboard_file))
                    print("Graphs generated and opened in browser.")
                    
                except Exception as e:
                    print(f"Error during graph generation: {e}")

            if args.reportpdf:
                try:
                    print("\nGenerating PDF report...")
                    nom_fichier_csv = os.path.basename(output_path).replace(".csv", "")
                    generate_pdf_report(nom_fichier_csv)
                    print("PDF report generated successfully.")
                except Exception as e:
                    print(f"Error during PDF report generation: {e}")

            if args.reportlatex:
                try:
                    print("\nGenerating LaTeX report...")
                    nom_fichier_csv = os.path.basename(output_path).replace(".csv", "")
                    generate_latex_report(nom_fichier_csv)
                    print("LaTeX report generated successfully.")
                except Exception as e:
                    print(f"Error during LaTeX report generation: {e}")
            
            print(f"\n{'='*60}")
            print("EXTRACTION COMPLETED")
            print(f"{'='*60}")
            print(f"Results file: {output_path}")
            
        except FileNotFoundError as e:
            print(e)
            exit(1)
        except Exception as e:
            print(f"Error during Step 2: {str(e)}")
            exit(1)
            
if __name__ == "__main__":
    main()