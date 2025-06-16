# -*- coding: utf-8 -*-

# report_generator_app.py

import os
import webbrowser
from datetime import datetime

def create_report_folder():
    """Create reports folder to store generated reports"""
    # Get the path of the directory where the Python script is executed
    current_directory = os.path.dirname(os.path.abspath(__file__))
    report_directory = os.path.join(current_directory, 'rapports')

    # Check if reports folder already exists, otherwise create it
    if not os.path.exists(report_directory):
        os.makedirs(report_directory)

    return report_directory

def generate_html_report_for_app(nom_fichier_csv, open_browser=True):
    """
    Generate an elegant HTML report optimized for the graphical interface
    
    Args:
        nom_fichier_csv (str): CSV file name (with or without extension)
        open_browser (bool): If True, automatically open browser
    
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
    existing_images = []
    
    for img in image_paths:
        if os.path.exists(img):
            existing_images.append(img)
        else:
            missing_images.append(img)

    # Adapt image paths to be relative to HTML file
    relative_image_paths = [os.path.relpath(img, start=report_directory) for img in image_paths]

    current_date = datetime.now().strftime("%d %B %Y")
    
    # HTML content generation with app-adapted design
    html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport HAL - {nom_fichier_csv}</title>
    <style>
        /* Reset and base styles */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #2c3e50;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        /* Styled header */
        .header {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 50px 30px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }}
        
        .header::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="20" cy="20" r="2" fill="rgba(255,255,255,0.1)"/><circle cx="80" cy="40" r="1.5" fill="rgba(255,255,255,0.1)"/><circle cx="40" cy="80" r="1" fill="rgba(255,255,255,0.1)"/></svg>');
            animation: float 20s ease-in-out infinite;
        }}
        
        @keyframes float {{
            0%, 100% {{ transform: translateY(0px); }}
            50% {{ transform: translateY(-20px); }}
        }}
        
        .title {{
            font-size: 2.8em;
            font-weight: 800;
            margin-bottom: 15px;
            text-shadow: 0 4px 8px rgba(0,0,0,0.3);
            position: relative;
            z-index: 1;
        }}
        
        .subtitle {{
            font-size: 1.2em;
            opacity: 0.95;
            margin: 10px 0;
            position: relative;
            z-index: 1;
        }}
        
        /* Interactive instructions */
        .instructions {{
            background: linear-gradient(135deg, #e3f2fd, #f3e5f5);
            border-left: 6px solid #667eea;
            margin: 30px;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.08);
            transition: transform 0.3s ease;
        }}
        
        .instructions:hover {{
            transform: translateY(-5px);
        }}
        
        .instructions h3 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.4em;
            font-weight: 700;
        }}
        
        .instructions ol {{
            margin-left: 25px;
            counter-reset: step-counter;
        }}
        
        .instructions li {{
            margin: 12px 0;
            font-size: 1.1em;
            position: relative;
            counter-increment: step-counter;
            padding-left: 10px;
        }}
        
        .instructions li::before {{
            content: counter(step-counter);
            position: absolute;
            left: -40px;
            top: 0;
            background: #667eea;
            color: white;
            width: 25px;
            height: 25px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 0.9em;
        }}
        
        kbd {{
            background: linear-gradient(145deg, #f8f9fa, #e9ecef);
            border: 1px solid #dee2e6;
            border-radius: 6px;
            padding: 4px 8px;
            font-family: 'Courier New', monospace;
            font-weight: bold;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .tip {{
            background: linear-gradient(135deg, #fff3e0, #ffe0b2);
            border-left: 4px solid #ff9800;
            margin-top: 20px;
            padding: 15px;
            border-radius: 8px;
            font-style: italic;
        }}
        
        /* Image status */
        .status-bar {{
            background: #f8f9fa;
            padding: 20px 30px;
            border-bottom: 1px solid #e9ecef;
        }}
        
        .status-item {{
            display: inline-block;
            margin-right: 25px;
            padding: 8px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: 600;
        }}
        
        .status-success {{
            background: #d4edda;
            color: #155724;
        }}
        
        .status-warning {{
            background: #fff3cd;
            color: #856404;
        }}
        
        /* Graph sections */
        .content {{
            padding: 30px;
        }}
        
        .graph-section {{
            margin: 50px 0;
            text-align: center;
            page-break-inside: avoid;
            background: rgba(255,255,255,0.7);
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.05);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}
        
        .graph-section:hover {{
            transform: translateY(-5px);
            box-shadow: 0 15px 35px rgba(0,0,0,0.1);
        }}
        
        .graph-section h2 {{
            color: #2c3e50;
            font-size: 2em;
            margin-bottom: 30px;
            padding-bottom: 15px;
            border-bottom: 3px solid #667eea;
            display: inline-block;
            font-weight: 700;
        }}
        
        .graph-section img {{
            max-width: 100%;
            height: auto;
            border-radius: 12px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
            transition: transform 0.4s ease;
        }}
        
        .graph-section img:hover {{
            transform: scale(1.05);
        }}
        
        .missing-graph {{
            background: linear-gradient(135deg, #fff3e0, #ffcc80);
            border: 3px dashed #ff9800;
            border-radius: 15px;
            padding: 50px;
            color: #e65100;
            font-weight: 600;
        }}
        
        .missing-graph-icon {{
            font-size: 3em;
            margin-bottom: 15px;
        }}
        
        /* Footer */
        .footer {{
            background: linear-gradient(135deg, #2c3e50, #34495e);
            color: white;
            text-align: center;
            padding: 30px;
            font-size: 0.95em;
        }}
        
        .footer p {{
            margin: 8px 0;
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
                background: white;
            }}
            
            .instructions, .status-bar {{
                display: none;
            }}
            
            .graph-section {{
                page-break-before: always;
                margin-top: 0;
                background: white;
                box-shadow: none;
            }}
            
            .graph-section:first-child {{
                page-break-before: auto;
            }}
            
            .header {{
                page-break-after: always;
                background: #667eea !important;
            }}
            
            .graph-section:hover, .graph-section img:hover {{
                transform: none;
            }}
        }}
        
        /* Responsive */
        @media (max-width: 768px) {{
            .title {{
                font-size: 2.2em;
            }}
            
            .header, .content, .instructions {{
                padding: 20px;
            }}
            
            .status-item {{
                display: block;
                margin: 5px 0;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="title">📊 Rapport des Publications HAL</h1>
            <p class="subtitle">📁 Source : {nom_fichier_csv}.csv</p>
            <p class="subtitle">📅 Généré le {current_date}</p>
        </div>
        
        <div class="status-bar">
            <span class="status-item status-success">✅ {len(existing_images)} graphiques disponibles</span>"""
    
    if missing_images:
        html_content += f'<span class="status-item status-warning">⚠️ {len(missing_images)} graphiques manquants</span>'
    
    html_content += """
        </div>
        
        <div class="instructions">
            <h3>Comment convertir ce rapport en PDF :</h3>
            <ol>
                <li>Appuyez sur <kbd>Ctrl+P</kbd> (ou <kbd>Cmd+P</kbd> sur Mac)</li>
                <li>Dans la fenêtre d'impression, sélectionnez <strong>"Enregistrer au format PDF"</strong></li>
                <li>Ajustez les paramètres : orientation <strong>Portrait</strong>, marges <strong>Normales</strong></li>
                <li>Cliquez sur <strong>"Enregistrer"</strong> et choisissez l'emplacement souhaité</li>
            </ol>
            <div class="tip">
                <strong>Astuce :</strong> Ce rapport a été optimisé pour l'impression PDF. 
                Les instructions et informations techniques seront automatiquement masquées lors de l'impression.
            </div>
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
                    <div class="missing-graph-icon">🚫</div>
                    <p><strong>Graphique non disponible</strong></p>
                    <p>Le fichier <code>{os.path.basename(img_path)}</code> est introuvable.</p>
                    <p>Veuillez générer les graphiques avant de créer le rapport.</p>
                </div>"""
        
        html_content += """
            </div>"""

    # End of HTML
    html_content += """
        </div>
        
        <div class="footer">
            <p><strong>Rapport généré automatiquement</strong> par l'outil d'analyse des publications HAL</p>
            <p>Interface graphique version • Pour plus d'informations, consultez la documentation</p>
        </div>
    </div>
</body>
</html>"""

    # File writing
    with open(output_path, "w", encoding="utf-8") as file:
        file.write(html_content)
        
    # Automatic browser opening (optional)
    if open_browser:
        try:
            webbrowser.open(f"file://{os.path.abspath(output_path)}")
        except Exception as e:
            print(f"⚠️  Impossible d'ouvrir le navigateur : {e}")
    
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
        print(f" Attention : Images manquantes pour le rapport LaTeX :")
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

    Ce document contient une analyse graphique des données extraites, incluant des informations sur les publications, les types de documents, les mots-clés les plus fréquents, les domaines, les auteurs prolifiques, et les tendances des publications par année.
    \vspace{{1cm}}

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
    with open(output_path, "w", encoding="utf-8") as file:
        file.write(content)
    print(f"Rapport LaTeX généré avec succès dans : {output_path}")
    return output_path

def generate_pdf_report(output_path, nom_fichier_csv):
    """
    Compatibility function for graphical interface - redirects to generate_html_report_for_app
    
    Args:
        output_path (str): Parameter kept for compatibility (not used)
        nom_fichier_csv (str): CSV file name
    
    Returns:
        str: Path to generated HTML file
    """
    return generate_html_report_for_app(nom_fichier_csv, open_browser=True)