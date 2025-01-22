# -*- coding: utf-8 -*-
"""
Created on Thu Jan 16 13:54:40 2025


"""
from fpdf import FPDF
from datetime import datetime
import os

# report_generator_main.py

# Fonction de création d'un dossier de nom 'rapports' pour y ranger les rapports générés
def create_report_folder():
    report_directory = os.path.join(os.getcwd(), "rapports")  
    if not os.path.exists(report_directory):
        os.makedirs(report_directory)
    return report_directory

def generate_pdf_report(nom_fichier_csv):
    report_directory = create_report_folder()
    if nom_fichier_csv.endswith('.csv'):
        nom_fichier_csv = nom_fichier_csv.replace('.csv', '')
    output_path = os.path.join(report_directory, f"{nom_fichier_csv}.pdf")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", style="B", size=16)
    pdf.cell(200, 10, txt="Rapport des publications HAL", ln=True, align="C")
    pdf.ln(10)

    # Utilisation du style italique pour la source des données
    pdf.set_font("Arial", style="I", size=12)
    pdf.cell(200, 10, txt=f"Source des données : {nom_fichier_csv}.csv", ln=True, align="C")
    pdf.ln(10)

    current_date = datetime.now().strftime("%d %B %Y")
    pdf.cell(200, 10, txt=f"Date de création : {current_date}", ln=True, align="C")
    pdf.ln(20)

    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, txt="Ce document contient une analyse graphique des données extraites, incluant des informations sur les publications, les types de documents, les mots-clés les plus fréquents, les domaines, les auteurs prolifiques, et les tendances des publications par année.", align="C")
    pdf.ln(10)

    # Ajout des titres des graphiques et insertion des graphiques eux-mêmes
    titles = [
        "1. Nombre de publications par année",
        "2. Répartition des types de documents",
        "3. Top 10 des mots-clés les plus fréquents",
        "4. Top 10 des domaines les plus fréquents",
        "5. Top 10 des auteurs les plus prolifiques",
        "6. Publications par structure et par année",
        "7. Tendances des publications par année"
    ]
    graph_paths = [
        "png/pubs_by_year.png",
        "png/type_distribution.png",
        "png/keywords_distribution.png",
        "png/domain_distribution.png",
        "png/top_authors.png",
        "png/structures_stacked.png",
        "png/publication_trends.png"
    ]

    for title, graph in zip(titles, graph_paths):
        pdf.add_page()
        pdf.set_font("Arial", style="B", size=14)
        pdf.cell(0, 10, title, ln=True)
        pdf.ln(5)
        pdf.image(graph, x=10, w=180)

    pdf.output(output_path)
    print(f"Rapport PDF généré avec succès dans : {output_path}")

def generate_latex_report(nom_fichier_csv):
    report_directory = create_report_folder()
    if nom_fichier_csv.endswith('.csv'):
        nom_fichier_csv = nom_fichier_csv.replace('.csv', '')
    output_path = os.path.join(report_directory, f"{nom_fichier_csv}.tex")

    # Chemin absolu des images
    image_paths = [
        "png/pubs_by_year.png",
        "png/type_distribution.png",
        "png/keywords_distribution.png",
        "png/domain_distribution.png",
        "png/top_authors.png",
        "png/structures_stacked.png",
        "png/publication_trends.png"
    ]

    # Vérification que toutes les images existent
    for img in image_paths:
        if not os.path.exists(img):
            raise FileNotFoundError(f"Image introuvable : {img}. Assurez-vous qu'elle a été générée correctement.")

    # Adapter les chemins des images pour être relatifs au fichier .tex
    relative_image_paths = [os.path.relpath(img, start=report_directory) for img in image_paths]

    current_date = datetime.now().strftime("%d %B %Y")
    content = rf"""
    \documentclass{{article}}
    \usepackage[utf8]{{inputenc}}
    \usepackage{{graphicx}}
    \usepackage[a4paper, margin=1in]{{geometry}}
    \title{{Rapport des Publications HAL - {nom_fichier_csv}}}
    \date{{Créé le {current_date}}}
    \begin{{document}}

    \maketitle

    \begin{{center}}
    \textit{{Source des données: {nom_fichier_csv}.csv}}
    \end{{center}}
    \vspace{{1cm}}

    Ce document contient une analyse graphique des données extraites, incluant :
    \begin{{itemize}}
        \item Nombre de publications par année
        \item Répartition des types de documents
        \item Top 10 des mots-clés les plus fréquents
        \item Top 10 des domaines les plus fréquents
        \item Top 10 des auteurs les plus prolifiques
        \item Publications par structure et par année
        \item Tendances des publications par année
    \end{{itemize}}

    \newpage

    \section*{{Graphiques}}

    \subsection*{{1. Nombre de publications par année}}
    \includegraphics[width=\textwidth]{{{relative_image_paths[0]}}}
    \newpage

    \subsection*{{2. Répartition des types de documents}}
    \includegraphics[width=\textwidth]{{{relative_image_paths[1]}}}
    \newpage

    \subsection*{{3. Top 10 des mots-clés les plus fréquents}}
    \includegraphics[width=\textwidth]{{{relative_image_paths[2]}}}
    \newpage

    \subsection*{{4. Top 10 des domaines les plus fréquents}}
    \includegraphics[width=\textwidth]{{{relative_image_paths[3]}}}
    \newpage

    \subsection*{{5. Top 10 des auteurs les plus prolifiques}}
    \includegraphics[width=\textwidth]{{{relative_image_paths[4]}}}
    \newpage

    \subsection*{{6. Publications par structure et par année}}
    \includegraphics[width=\textwidth]{{{relative_image_paths[5]}}}
    \newpage

    \subsection*{{7. Tendances des publications par année}}
    \includegraphics[width=\textwidth]{{{relative_image_paths[6]}}}

    \end{{document}}
    """
    # Écrire le contenu dans le fichier .tex
    with open(output_path, "w", encoding="utf-8") as file:
        file.write(content)
    print(f"Rapport LaTeX généré avec succès dans : {output_path}")
