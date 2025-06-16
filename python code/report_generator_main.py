# -*- coding: utf-8 -*-

# report_generator_main.py

from datetime import datetime
import os
import webbrowser

def create_report_folder():
    """Create a folder named 'rapports' to store generated reports"""
    report_directory = os.path.join(os.getcwd(), "rapports")  
    if not os.path.exists(report_directory):
        os.makedirs(report_directory)
    return report_directory

def generate_html_report(nom_fichier_csv):
    """
    Generate an elegant HTML report optimized for PDF conversion
    
    Args:
        nom_fichier_csv (str): CSV file name (with or without extension)
    
    Returns:
        str: Path to generated HTML file
    """
    report_directory = create_report_folder()
    if nom_fichier_csv.endswith('.csv'):
        nom_fichier_csv = nom_fichier_csv.replace('.csv', '')
    output_path = os.path.join(report_directory, f"{nom_fichier_csv}.html")

    # Define image paths
    image_paths = [
        "png/pubs_by_year.png",
        "png/type_distribution.png", 
        "png/keywords_distribution.png",
        "png/domain_distribution.png",
        "png/top_authors.png",
        "png/structures_stacked.png",
        "png/publication_trends.png",
        "png/employer_distribution.png",
        "png/theses_hdr_by_year.png",
        "png/theses_keywords_wordcloud.png"
    ]

    # Check that all images exist
    missing_images = []
    for img in image_paths:
        if not os.path.exists(img):
            missing_images.append(img)
    
    if missing_images:
        print(f"⚠️  Attention : Images manquantes :")
        for img in missing_images:
            print(f"   - {img}")
        print("Les graphiques manquants ne seront pas inclus dans le rapport.")

    # Adapt image paths to be relative to HTML file
    relative_image_paths = [os.path.relpath(img, start=report_directory) for img in image_paths]

    current_date = datetime.now().strftime("%d %B %Y")
    
    # HTML content generation
    html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport des Publications HAL - {nom_fichier_csv}</title>
    <style>
        /* General styles */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            color: #2c3e50;
            background-color: #f8f9fa;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        /* Header */
        .header {{
            background: linear-gradient(135deg, #3498db, #2c3e50);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }}
        
        .title {{
            font-size: 2.5em;
            font-weight: 700;
            margin-bottom: 15px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }}
        
        .subtitle {{
            font-size: 1.1em;
            opacity: 0.9;
            margin: 8px 0;
        }}
        
        /* Instructions (hidden on print) */
        .instructions {{
            background: #e3f2fd;
            border-left: 5px solid #2196f3;
            margin: 30px;
            padding: 25px;
            border-radius: 8px;
        }}
        
        .instructions h3 {{
            color: #1976d2;
            margin-bottom: 15px;
            font-size: 1.3em;
        }}
        
        .instructions ol {{
            margin-left: 20px;
        }}
        
        .instructions li {{
            margin: 8px 0;
            font-size: 1.05em;
        }}
        
        kbd {{
            background: #f5f5f5;
            border: 1px solid #ccc;
            border-radius: 4px;
            padding: 2px 6px;
            font-family: monospace;
            font-weight: bold;
        }}
        
        /* Graph sections */
        .content {{
            padding: 30px;
        }}
        
        .graph-section {{
            margin: 40px 0;
            text-align: center;
            page-break-inside: avoid;
        }}
        
        .graph-section h2 {{
            color: #2c3e50;
            font-size: 1.8em;
            margin-bottom: 25px;
            padding-bottom: 10px;
            border-bottom: 3px solid #3498db;
            display: inline-block;
        }}
        
        .graph-section img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }}
        
        .graph-section img:hover {{
            transform: scale(1.02);
        }}
        
        .missing-graph {{
            background: #fff3e0;
            border: 2px dashed #ff9800;
            border-radius: 8px;
            padding: 40px;
            color: #f57c00;
            font-style: italic;
        }}
        
        /* Footer */
        .footer {{
            background: #34495e;
            color: white;
            text-align: center;
            padding: 20px;
            font-size: 0.9em;
        }}
        
        /* Print styles */
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            
            .container {{
                box-shadow: none;
                border-radius: 0;
            }}
            
            .instructions {{
                display: none;
            }}
            
            .graph-section {{
                page-break-before: always;
                margin-top: 0;
            }}
            
            .graph-section:first-child {{
                page-break-before: auto;
            }}
            
            .header {{
                page-break-after: always;
            }}
            
            .graph-section img:hover {{
                transform: none;
            }}
        }}
        
        /* Responsive */
        @media (max-width: 768px) {{
            .title {{
                font-size: 2em;
            }}
            
            .header, .content, .instructions {{
                padding: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="title">📊 Rapport des Publications HAL</h1>
            <p class="subtitle">📁 Source des données : {nom_fichier_csv}.csv</p>
            <p class="subtitle">📅 Généré le {current_date}</p>
        </div>
        
        <div class="instructions">
            <h3>📄 Comment générer un PDF à partir de ce rapport :</h3>
            <ol>
                <li>Appuyez sur <kbd>Ctrl+P</kbd> (ou <kbd>Cmd+P</kbd> sur Mac)</li>
                <li>Dans la fenêtre d'impression, sélectionnez <strong>"Enregistrer au format PDF"</strong></li>
                <li>Choisissez vos options d'impression (orientation, marges, etc.)</li>
                <li>Cliquez sur <strong>"Enregistrer"</strong> et choisissez l'emplacement</li>
            </ol>
            <p style="margin-top: 15px; font-style: italic; color: #666;">
                Conseil : Pour un meilleur rendu, utilisez l'orientation "Portrait" et des marges "Normales"
            </p>
        </div>
        
        <div class="content">"""

    # Title definitions and image existence checking
    graph_titles = [
        "1. Nombre de publications par année",
        "2. Répartition des types de documents", 
        "3. Top 10 des mots-clés les plus fréquents",
        "4. Top 10 des domaines les plus fréquents",
        "5. Top 10 des auteurs les plus prolifiques",
        "6. Publications par structure et par année",
        "7. Tendances des publications par année",
        "8. Répartition des publications par employeur",
        "9. Thèses et HDR soutenues par année",
        "10. Nuage de mots-clés des thèses/HDR"
    ]

    # Add graph sections
    for i, (title, img_path, rel_path) in enumerate(zip(graph_titles, image_paths, relative_image_paths)):
        html_content += f"""
            <div class="graph-section">
                <h2>{title}</h2>"""
        
        if os.path.exists(img_path):
            html_content += f"""
                <img src="{rel_path}" alt="{title}" loading="lazy">"""
        else:
            html_content += f"""
                <div class="missing-graph">
                    <p>Graphique non disponible</p>
                    <p>Le fichier {os.path.basename(img_path)} est introuvable.</p>
                    <p>Assurez-vous d'avoir généré les graphiques avant le rapport.</p>
                </div>"""
        
        html_content += """
            </div>"""

    # End of HTML
    html_content += """
        </div>
        
        <div class="footer">
            <p>Rapport généré automatiquement par l'outil d'analyse des publications HAL</p>
            <p>Pour plus d'informations, consultez la documentation du projet</p>
        </div>
    </div>
</body>
</html>"""

    # File writing
    with open(output_path, "w", encoding="utf-8") as file:
        file.write(html_content)
        
    # Automatic browser opening
    try:
        webbrowser.open(f"file://{os.path.abspath(output_path)}")
    except Exception as e:
        print(f"⚠️  Impossible d'ouvrir automatiquement le navigateur : {e}")
        print(f"📂 Ouvrez manuellement le fichier : {output_path}")
    
    return output_path

def generate_latex_report(nom_fichier_csv):
    """
    Generate a LaTeX report (function kept for compatibility)
    
    Args:
        nom_fichier_csv (str): CSV file name (with or without extension)
    
    Returns:
        str: Path to generated LaTeX file
    """
    report_directory = create_report_folder()
    if nom_fichier_csv.endswith('.csv'):
        nom_fichier_csv = nom_fichier_csv.replace('.csv', '')
    output_path = os.path.join(report_directory, f"{nom_fichier_csv}.tex")

    # Absolute image paths
    image_paths = [
        "png/pubs_by_year.png",
        "png/type_distribution.png",
        "png/keywords_distribution.png",
        "png/domain_distribution.png",
        "png/top_authors.png",
        "png/structures_stacked.png",
        "png/publication_trends.png",
        "png/employer_distribution.png",
        "png/theses_hdr_by_year.png",
        "png/theses_keywords_wordcloud.png"
    ]

    # Check that all images exist
    missing_images = []
    for img in image_paths:
        if not os.path.exists(img):
            missing_images.append(img)
    
    if missing_images:
        print(f"  Attention : Images manquantes pour le rapport LaTeX :")
        for img in missing_images:
            print(f"   - {img}")

    # Adapt image paths to be relative to .tex file
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
    \newpage

    \subsection*{{8. Répartition des publications par employeur}}
    \includegraphics[width=\textwidth]{{{relative_image_paths[7]}}}
    \newpage

    \subsection*{{9. Thèses et HDR soutenues par année}}
    \includegraphics[width=\textwidth]{{{relative_image_paths[8]}}}
    \newpage

    \subsection*{{10. Nuage de mots-clés des thèses/HDR}}
    \includegraphics[width=\textwidth]{{{relative_image_paths[9]}}}

    \end{{document}}
    """
    # Write content to .tex file
    with open(output_path, "w", encoding="utf-8") as file:
        file.write(content)
    print(f" Rapport LaTeX généré avec succès dans : {output_path}")
    return output_path

def generate_pdf_report(nom_fichier_csv):
    """
    Compatibility function (old name) - redirects to generate_html_report
    
    Args:
        nom_fichier_csv (str): CSV file name
    
    Returns:
        str: Path to generated HTML file
    """
    return generate_html_report(nom_fichier_csv)