# -*- coding: utf-8 -*-
"""
Created on Thu Jan 16 13:58:36 2025


"""
import os
from fpdf import FPDF
from datetime import datetime

# report_generator_app.py

# Fonction pour créer un dossier 'rapport' pour y ranger les rapports générés
def create_report_folder():
    # Obtient le chemin du dossier où le script Python est exécuté
    current_directory = os.path.dirname(os.path.abspath(__file__))
    report_directory = os.path.join(current_directory, 'rapports')

    # Vérifie si le dossier 'rapport' existe déjà, sinon le crée
    if not os.path.exists(report_directory):
        os.makedirs(report_directory)

    return report_directory
def generate_pdf_report(output_path, nom_fichier_csv):
    report_directory = create_report_folder()
    output_path = os.path.join(report_directory, f"{nom_fichier_csv}.pdf")
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)

   # Page de titre
    pdf.add_page()
    pdf.set_font("Arial", style="B", size=16)
    pdf.cell(200, 10, txt="Rapport des publications HAL", ln=True, align="C")
    pdf.ln(10)  # Espace après le titre principal

    # Nom du fichier CSV
    pdf.set_font("Arial", style="I", size=12)
    pdf.cell(200, 10, txt=f"Source des données : {nom_fichier_csv}.csv", ln=True, align="C")
    pdf.ln(10)  # Espace après le nom du fichier

    # Date de création du rapport
    from datetime import datetime
    current_date = datetime.now().strftime("%d %B %Y")
    pdf.cell(200, 10, txt=f"Date de création : {current_date}", ln=True, align="C")
    pdf.ln(20)  # Espace avant la description

    # Description du contenu
    pdf.multi_cell(0, 10, txt="Ce document contient une analyse graphique des données extraites, incluant des informations sur les publications, les types de documents, les mots-clés les plus fréquents, les domaines, les auteurs prolifiques, et les tendances des publications par année.", align="C")

    # Insertion des graphiques, un par page
    def add_chart(pdf, title, image_path):
        pdf.add_page()
        pdf.set_font("Arial", style="B", size=14)
        pdf.cell(0, 10, title, ln=True)
        pdf.ln(10)
        pdf.image(image_path, x=10, w=180)

    # Ajouter chaque graphique sur une nouvelle page
    add_chart(pdf, "1. Nombre de publications par année", "png/pubs_by_year.png")
    add_chart(pdf, "2. Répartition des types de documents", "png/type_distribution.png")
    add_chart(pdf, "3. Top 10 des mots-clés les plus fréquents", "png/keywords_distribution.png")
    add_chart(pdf, "4. Top 10 des domaines les plus fréquents", "png/domain_distribution.png")
    add_chart(pdf, "5. Top 10 des auteurs les plus prolifiques", "png/top_authors.png")
    add_chart(pdf, "6. Publications par structure et par année", "png/structures_stacked.png")
    add_chart(pdf, "7. Tendances des publications par année", "png/publication_trends.png")

    # Sauvegarde finale
    pdf.output(output_path)


def generate_latex_report(output_path, nom_fichier_csv):
    current_date = datetime.now().strftime("%d %B %Y")
    
    report_directory = create_report_folder()
    output_path = os.path.join(report_directory, f"{nom_fichier_csv}.tex")
    
    content = rf"""
    \documentclass{{article}}
    \usepackage[utf8]{{inputenc}}
    \usepackage{{graphicx}}
    \title{{Rapport des Publications HAL - {nom_fichier_csv}}}
    \date{{Créé le {current_date}}}
    \begin{{document}}

    \maketitle

    \begin{{center}}
    Source des données: {nom_fichier_csv}.csv\\
    \vspace{{1cm}}
    Ce document contient une analyse graphique des données extraites, incluant des informations sur les publications, les types de documents, les mots-clés les plus fréquents, les domaines, les auteurs prolifiques, et les tendances des publications par année.
    \end{{center}}

    \newpage

    \section*{{Graphiques}}

    \subsection*{{1. Nombre de publications par année}}
    \includegraphics[width=\textwidth]{{png/pubs_by_year.png}}
    \newpage

    \subsection*{{2. Répartition des types de documents}}
    \includegraphics[width=\textwidth]{{png/type_distribution.png}}
    \newpage

    \subsection*{{3. Top 10 des mots-clés les plus fréquents}}
    \includegraphics[width=\textwidth]{{png/keywords_distribution.png}}
    \newpage

    \subsection*{{4. Top 10 des domaines les plus fréquents}}
    \includegraphics[width=\textwidth]{{png/domain_distribution.png}}
    \newpage

    \subsection*{{5. Top 10 des auteurs les plus prolifiques}}
    \includegraphics[width=\textwidth]{{png/top_authors.png}}
    \newpage

    \subsection*{{6. Publications par structure et par année}}
    \includegraphics[width=\textwidth]{{png/structures_stacked.png}}
    \newpage

    \subsection*{{7. Tendances des publications par année}}
    \includegraphics[width=\textwidth]{{png/publication_trends.png}}

    \end{{document}}
    """
    # Sauvegarde du fichier LaTeX
    with open(output_path, "w", encoding="utf-8") as file:
        file.write(content)