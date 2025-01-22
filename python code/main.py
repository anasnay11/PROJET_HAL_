# main.py

from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import argparse
from hal_data import get_hal_data
from utils import generate_filename
from mapping import list_domains, list_types
from graphics import (
    plot_publications_by_year,
    plot_document_types,
    plot_keywords,
    plot_top_domains,
    plot_publications_by_author,
    plot_structures_stacked,
    plot_publications_trends,
)
from dashboard_generator import create_dashboard
from report_generator_main import generate_pdf_report, generate_latex_report
import webbrowser
import os
from tqdm import tqdm


def list_csv_files():
    current_directory = os.path.dirname(os.path.abspath(__file__))
    data_directory = os.path.join(current_directory, "data gdrmacs")
    if not os.path.exists(data_directory):
        raise FileNotFoundError(f"Le dossier '{data_directory}' est introuvable.")

    csv_files = [f for f in os.listdir(data_directory) if f.endswith(".csv")]
    if not csv_files:
        raise FileNotFoundError(f"Aucun fichier CSV trouvé dans le dossier '{data_directory}'.")
    return data_directory, csv_files


def get_user_selected_csv():
    try:
        data_directory, csv_files = list_csv_files()
        print("Fichiers CSV disponibles :")
        for i, file in enumerate(csv_files, start=1):
            print(f"{i}. {file}")

        choice = int(input("\nEntrez le numéro du fichier que vous souhaitez utiliser : "))
        if 1 <= choice <= len(csv_files):
            selected_file = os.path.join(data_directory, csv_files[choice - 1])
            print(f"Vous avez sélectionné : {csv_files[choice - 1]}")
            return selected_file
        else:
            print("Choix invalide. Veuillez relancer le programme.")
            exit(1)
    except ValueError:
        print("Entrée invalide. Veuillez entrer un numéro valide.")
        exit(1)


def create_extraction_folder():
    current_directory = os.path.dirname(os.path.abspath(__file__))
    extraction_directory = os.path.join(current_directory, "extraction")

    if not os.path.exists(extraction_directory):
        os.makedirs(extraction_directory)

    return extraction_directory


def fetch_data(row):
    return get_hal_data(
        row["nom"], row["prenom"], period=args.year, domain_filter=args.domain, type_filter=args.type
    )


def main():
    # Chargement des données scientifiques
    try:
        csv_file_path = get_user_selected_csv()
        scientists_df = pd.read_csv(csv_file_path)
    except FileNotFoundError as e:
        print(e)
        exit(1)

    # Ajout des arguments pour la ligne de commande
    parser = argparse.ArgumentParser(
        description=(
            "Ce fichier permet l'extraction de données scientifiques depuis la base de données HAL.\n"
            "Possibilité de filtrer les publications par période, domaine scientifique, et type de document."
        ),
        epilog=(
            'Exemple : python main.py --year 2019-2024 --domain "Mathématiques" --type "Thèse"\n'
            'Permettra de récupérer les données de 2019 à 2024 de domaine "Mathématiques" et de type "Thèse".'
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "--year", help="Filtrer les publications par période (format : YYYY-YYYY). Exemple : 2019-2024.", type=str
    )
    parser.add_argument(
        "--domain",
        help='Filtrer les publications par domaine scientifique. Exemple : "Mathématiques".',
        type=str,
    )
    parser.add_argument(
        "--type", help='Filtrer les publications par type de document. Exemple : "Thèse".', type=str
    )
    parser.add_argument(
        "--list-domains", help="Afficher la liste complète des domaines disponibles pour le filtrage.", action="store_true"
    )
    parser.add_argument(
        "--list-types", help="Afficher la liste complète des types de documents disponibles pour le filtrage.", action="store_true"
    )

    global args
    args = parser.parse_args()

    # Afficher la liste des domaines si demandé
    if args.list_domains:
        domains = list_domains()
        print("Liste des domaines disponibles pour le filtrage :\n")
        for code, name in domains.items():
            print(f"{code} : {name}")
        exit()

    # Afficher la liste des types si demandé
    if args.list_types:
        types = list_types()
        print("Liste des types de documents disponibles pour le filtrage :\n")
        for code, name in types.items():
            print(f"{code} : {name}")
        exit()

    # Extraction des données
    pbar = tqdm(total=len(scientists_df), desc="Extraction en cours")

    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_row = {
            executor.submit(fetch_data, row): row for index, row in scientists_df.iterrows()
        }

        for future in as_completed(future_to_row):
            results.append(future.result())
            pbar.update(1)

    pbar.close()

    all_results = pd.concat(results, ignore_index=True)

    # Sauvegarde des résultats
    extraction_directory = create_extraction_folder()
    filename = generate_filename(args.year, args.domain, args.type)
    output_path = os.path.join(extraction_directory, filename)
    all_results.to_csv(output_path, index=False)
    print(f"Extraction terminée. Les résultats ont été enregistrés dans : {output_path}")

    # Affichage des graphiques
    user_input_graphs = input("Souhaitez-vous afficher des graphiques ? (Oui/Non) ").strip().lower()
    if user_input_graphs == "oui":
        try:
            plot_publications_by_year(output_path, output_html="html/pubs_by_year.html", output_png="png/pubs_by_year.png")
            plot_document_types(output_path, output_html="html/type_distribution.html", output_png="png/type_distribution.png")
            plot_keywords(output_path, output_html="html/keywords_distribution.html", output_png="png/keywords_distribution.png")
            plot_top_domains(output_path, output_html="html/domain_distribution.html", output_png="png/domain_distribution.png")
            plot_publications_by_author(output_path, output_html="html/top_authors.html", output_png="png/top_authors.png")
            plot_structures_stacked(output_path, output_html="html/structures_stacked.html", output_png="png/structures_stacked.png")
            plot_publications_trends(output_path, output_html="html/publication_trends.html", output_png="png/publication_trends.png")

            dashboard_file = create_dashboard()
            webbrowser.open("file://" + os.path.realpath(dashboard_file))
        except Exception as e:
            print(f"Erreur lors de la génération des graphiques : {e}")

    # Génération de rapport
    user_input_report = input("Souhaitez-vous générer un rapport ? (Oui/Non) ").strip().lower()
    if user_input_report == "oui":
        format_choisi = input("Choisissez le format du rapport : PDF ou LaTeX ? ").strip().lower()
        if format_choisi == "pdf":
            generate_pdf_report(filename)
        elif format_choisi == "latex":
            generate_latex_report(filename)
        else:
            print("Format non reconnu. Le rapport n'a pas été généré.")


if __name__ == "__main__":
    main()

