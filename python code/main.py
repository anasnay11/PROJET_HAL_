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
    """🔧 UPDATED: Wrapper function for parallel data extraction with new type handling"""
    # 🔧 CORRECTION: Pass type as list for proper handling in get_hal_data
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
    🔧 ENHANCED: Displays a summary of the extraction with detailed thesis information
    
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
    
    # 🔧 ENHANCED: Detailed thesis information
    if args.type:
        type_lower = args.type.lower()
        if any(keyword in type_lower for keyword in ['thèse', 'habilitation', 'thesis', 'hdr']):
            print(f"• Extended search: Double query (prenom nom + nom prenom) for better results")
        
        # 🆕 NEW: Specific information for new thesis types
        if 'doctorant' in type_lower:
            print(f"• Thesis filter: PhD theses only (THESE documents)")
        elif 'hdr' in type_lower and 'thèse' in type_lower:
            print(f"• Thesis filter: HDR theses only (HDR documents)")
        elif 'thèse' in type_lower or 'habilitation' in type_lower:
            print(f"• Thesis filter: Both PhD and HDR theses (THESE + HDR documents)")
    
    print("="*60 + "\n")

def main():
    """
    Main function that handles command line arguments and orchestrates the entire 
    HAL data extraction and analysis workflow.
    
    Supports filtering by year, domain, document type, configurable name matching
    sensitivity, and automatic generation of graphs and reports.
    """
    parser = argparse.ArgumentParser(
        description=(
            "This file allows scientific data extraction from the HAL database.\n"
            "Possibility to filter publications by period, scientific domain, document type,\n"
            "and configure the sensitivity of author name matching.\n\n"
            "🆕 NEW THESIS TYPES:\n"
            "- 'Thèse (Doctorant)' : PhD theses only (THESE documents)\n"
            "- 'Thèse (HDR)' : HDR theses only (HDR documents)\n"
            "- 'Thèse' : Both PhD and HDR theses (THESE + HDR documents)\n\n"
            "IMPORTANT: The system uses double queries (prenom nom + nom prenom) for better results."
        ),
        epilog=(
            'Examples:\n'
            'python main.py --year 2019-2024 --domain "Mathematics" --type "Thèse (Doctorant)"\n'
            'python main.py --type "Thèse (HDR)" --graphs\n'
            'python main.py --type "Thèse" --threshold 1\n'
            'python main.py --threshold 3 --reportpdf\n'
            'python main.py --graphs --reportpdf --reportlatex\n\n'
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

    global args
    args = parser.parse_args()

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
        print("🔧 ENHANCED: List of available document types for filtering:\n")
        
        # 🆕 NEW: Group thesis types for better display
        thesis_types = []
        other_types = []
        
        for code, name in types.items():
            if 'thèse' in name.lower() or 'habilitation' in name.lower():
                thesis_types.append((code, name))
            else:
                other_types.append((code, name))
        
        if thesis_types:
            print("📚 THESIS TYPES:")
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
        
        print("📄 OTHER DOCUMENT TYPES:")
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
    
    # 🔧 ENHANCED: Detailed statistics display
    if not all_results.empty:
        print(f"\nExtraction completed: {len(all_results)} publications found")
        
        # Display document type statistics if available
        if 'Type de Document' in all_results.columns:
            type_counts = all_results['Type de Document'].value_counts()
            print("\nDocument types found:")
            for doc_type, count in type_counts.items():
                print(f"  {doc_type}: {count} publications")
            
            # 🆕 NEW: Special message for thesis extractions
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