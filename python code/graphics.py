# -*- coding: utf-8 -*-

# graphics.py

import pandas as pd
import plotly.express as px
import os
import threading
from wordcloud import WordCloud
import plotly.graph_objects as go
import numpy as np
from PIL import Image
import networkx as nx
import matplotlib.pyplot as plt
import ast

# Créer un verrou global pour la génération de graphiques
graph_generation_lock = threading.Lock()

# Fonction pour créer les dossier 'png' et 'html'
def create_directories():
    base_path = os.path.dirname(os.path.abspath(__file__))
    directories = ['png', 'html']
    for directory in directories:
        path = os.path.join(base_path, directory)
        if not os.path.exists(path):
            os.makedirs(path)

# Analyse des données
def analyze_data(filename):
    """
    Effectue une analyse complète des données :
    - Mots-clés les plus fréquents
    - Répartition des types de documents
    - Publications par auteur (top 10)
    - Publications par structure de recherche (top 10)
    - Publications par année (distribution complète)
    - Nombre moyen d'auteurs par publication
    - Nombre moyen de mots-clés par publication
    - Nombre de publications total
    """
    df = pd.read_csv(filename)

    # Assurer que les colonnes utilisées existent bien dans le fichier
    required_columns = ['Nom', 'Prenom', 'IdHAL des auteurs de la publication', 'Docid', 'Titre',
                        'Année de Publication', 'Type de Document', 'Mots-clés', 'Laboratoire de Recherche']

    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"La colonne '{col}' est manquante dans le fichier.")

    # Mots-clés les plus fréquents (nettoyage préalable)
    keyword_counts = (
        df['Mots-clés'].dropna()
        .str.replace(r"[^\w\s,]", "", regex=True)  # Suppression des caractères spéciaux
        .str.split(',')
        .explode()
        .str.strip()
        .value_counts()
        .head(10)
    )

    # Répartition des types de documents
    doc_type_counts = df['Type de Document'].value_counts()

    # Publications par auteur (basé sur les combinaisons Nom + Prénom)
    author_counts = df.groupby(['Nom', 'Prenom']).size().sort_values(ascending=False).head(10)

    # Publications par structure de recherche
    structure_counts = df['Laboratoire de Recherche'].dropna().str.strip().value_counts().head(10)

    # Distribution des publications par année
    year_counts = df['Année de Publication'].value_counts().sort_index()

    # Nombre moyen d'auteurs par publication
    avg_authors_per_pub = df['IdHAL des auteurs de la publication'].apply(lambda x: len(eval(x)) if pd.notnull(x) else 0).mean()

    # Nombre moyen de mots-clés par publication
    avg_keywords_per_pub = df['Mots-clés'].apply(lambda x: len(eval(x)) if pd.notnull(x) else 0).mean()

    # Nombre total de publications
    total_publications = len(df)

    # Retourner tous les résultats sous forme de dictionnaire
    return {
        "keywords": keyword_counts,
        "doc_types": doc_type_counts,
        "authors": author_counts,
        "structures": structure_counts,
        "year_counts": year_counts,
        "avg_authors_per_pub": avg_authors_per_pub,
        "avg_keywords_per_pub": avg_keywords_per_pub,
        "total_publications": total_publications
    }

# Visualisation : Histogramme par année
def plot_publications_by_year(filename, output_html="html/pubs_by_year.html", output_png="png/pubs_by_year.png"):
    """
    Affiche un histogramme interactif des publications par année.
    Sauvegarde le graphique en HTML.
    """
    
    with graph_generation_lock:
        
        # Créer les dossiers pour ranger les fichiers html et png
        create_directories()
        
        # Charger les données
        df = pd.read_csv(filename)
        
        # Vérifier la colonne "Année de Publication"
        year_counts = df['Année de Publication'].dropna().value_counts().reset_index()
        year_counts.columns = ['Année', 'Nombre de publications']
        year_counts = year_counts.sort_values(by='Année')  # Trier par année
    
        # Créer le graphique interactif
        fig = px.bar(
            year_counts,
            x='Année',
            y='Nombre de publications',
            title="Nombre de publications par année",
            labels={'Année': 'Année', 'Nombre de publications': 'Nombre de publications'},
            color='Nombre de publications',
            color_continuous_scale='Viridis'
        )
    
        # Sauvegarder le graphique
        fig.write_html(output_html)
        fig.write_image(output_png)


# Visualisation : Types de documents
def plot_document_types(filename, output_html="html/type_distribution.html", output_png="png/type_distribution.png"):
    """
    Affiche un graphique circulaire interactif des types de documents.
    """
    with graph_generation_lock:
    
        # Créer les dossiers pour ranger les fichiers html et png
        create_directories()
        
        df = pd.read_csv(filename)
        doc_type_counts = df['Type de Document'].dropna().value_counts().reset_index()
        doc_type_counts.columns = ['Type de document', 'Nombre']
    
        fig = px.pie(
            doc_type_counts,
            names='Type de document',
            values='Nombre',
            title="Répartition des types de documents",
            hole=0.3
        )
        fig.write_html(output_html)
        fig.write_image(output_png)


# Visualisation : Mots-clés
def plot_keywords(filename, output_html="html/keywords_distribution.html", output_png="png/keywords_distribution.png"):
    """
    Affiche un barplot horizontal interactif des mots-clés les plus fréquents.
    """
    
    with graph_generation_lock:
        
        # Créer les dossiers pour ranger les fichiers html et png
        create_directories()
        
        df = pd.read_csv(filename)
        keyword_counts = (
            df['Mots-clés']
            .dropna()
            .str.split(',')
            .explode()
            .str.strip()
            .replace('[]', pd.NA)  # Exclure les mots-clés vides
            .dropna()
            .value_counts()
            .head(10)
            .reset_index()
        )
        keyword_counts.columns = ['Mots-clés', 'Nombre de publications']
    
        fig = px.bar(
            keyword_counts,
            x='Nombre de publications',
            y='Mots-clés',
            orientation='h',
            title="Top 10 des mots-clés les plus fréquents",
            color='Nombre de publications',
            color_continuous_scale='Blues'
        )
        fig.write_html(output_html)
        fig.write_image(output_png)


# Visualisation : Domaines
def plot_top_domains(filename, output_html="html/domain_distribution.html", output_png="png/domain_distribution.png"):
    """
    Affiche un histogramme interactif des domaines les plus fréquents.
    """
    
    with graph_generation_lock:
        
        # Créer les dossiers pour ranger les fichiers html et png
        create_directories()
        
        df = pd.read_csv(filename)
        domain_counts = (
            df['Domaine']
            .dropna()
            .str.split(',')
            .explode()
            .str.strip()
            .replace('Domaine non défini', pd.NA)  # Exclure les domaines non définis
            .dropna()
            .value_counts()
            .head(10)
            .reset_index()
        )
        domain_counts.columns = ['Domaine', 'Nombre de publications']
    
        fig = px.bar(
            domain_counts,
            x='Domaine',
            y='Nombre de publications',
            title="Top 10 des domaines les plus fréquents",
            color='Nombre de publications',
            color_continuous_scale='Blues'
        )
        fig.write_html(output_html)
        fig.write_image(output_png)


# Visualisation : Auteurs prolifiques
def plot_publications_by_author(filename, output_html="html/top_authors.html", output_png="png/top_authors.png"):
    """
    Affiche un histogramme interactif des auteurs les plus prolifiques.
    """
    
    with graph_generation_lock:
        
        # Créer les dossiers pour ranger les fichiers html et png
        create_directories()
        
        df = pd.read_csv(filename)
        author_counts = df['Nom'].dropna().value_counts().head(10).reset_index()
        author_counts.columns = ['Auteur', 'Nombre de publications']
    
        fig = px.bar(
            author_counts,
            x='Auteur',
            y='Nombre de publications',
            title="Top 10 des auteurs les plus prolifiques",
            color='Nombre de publications',
            color_continuous_scale='Teal'
        )
        fig.write_html(output_html)
        fig.write_image(output_png)


# Visualisation : Structures prolifiques
def plot_structures_stacked(filename, output_html="html/structures_stacked.html", output_png="png/structures_stacked.png"):
    """
    Affiche un graphique en barres empilées des publications par structure et par année.
    """
    
    with graph_generation_lock:
        
        # Créer les dossiers pour ranger les fichiers html et png
        create_directories()
        
        df = pd.read_csv(filename)
        
        # Exclure les valeurs 'Non disponible'
        df = df[df['Laboratoire de Recherche'] != 'Non disponible']
        
        grouped = df.groupby(['Laboratoire de Recherche', 'Année de Publication']).size().reset_index(name='Nombre de publications')
    
        top_structures = grouped['Laboratoire de Recherche'].value_counts().head(10).index
        grouped_top = grouped[grouped['Laboratoire de Recherche'].isin(top_structures)]
    
        fig = px.bar(
            grouped_top,
            x='Laboratoire de Recherche',
            y='Nombre de publications',
            color='Année de Publication',
            title="Publications par structure et par année (Top 10 structures)",
            barmode='stack'
        )
        fig.write_html(output_html)
        fig.write_image(output_png)

    
# Tendance des publications
def plot_publications_trends(filename, output_html="html/publication_trends.html", output_png="png/publication_trends.png"):
    """
    Affiche un graphique linéaire interactif des tendances des publications par année.
    """
    
    with graph_generation_lock:
        
        # Créer les dossiers pour ranger les fichiers html et png
        create_directories()
        
        df = pd.read_csv(filename)
        year_counts = df['Année de Publication'].dropna().value_counts().sort_index().reset_index()
        year_counts.columns = ['Année', 'Nombre de publications']
    
        fig = px.line(
            year_counts,
            x='Année',
            y='Nombre de publications',
            title="Tendances des publications par année",
            markers=True
        )
        fig.write_html(output_html)
        fig.write_image(output_png)
        
# Répartition par employeur
def plot_employer_distribution(filename, output_html="html/employer_distribution.html", output_png="png/employer_distribution.png"):
    """
    Affiche un graphique en barres empilées des publications par employeurs (laboratoires).
    """
    
    with graph_generation_lock:
    
        df = pd.read_csv(filename)
        
        # Nettoyer les noms d’employeurs
        employer_counts = (
            df['Laboratoire de Recherche']
            .dropna()
            [df['Laboratoire de Recherche'] != "Non disponible"]
            .str.replace(r"Laboratoire des sciences et techniques.*", "Lab-STICC", regex=True)
            .str.replace(r"Inria.*", "Inria", regex=True)
            .value_counts()
            .head(15)
        )
    
        # Reformater pour plotly
        df_plot = employer_counts.reset_index()
        df_plot.columns = ["Employeur", "Nombre de publications"]
    
        fig = px.bar(
        df_plot,
        x='Employeur',
        y='Nombre de publications',
        title="Répartition des publications par employeur (Top 15)"
        )
    
        fig.write_html(output_html)
        fig.write_image(output_png)

# Thèses et HDR par année
def plot_theses_hdr_by_year(filename, output_html="html/theses_hdr_by_year.html", output_png="png/theses_hdr_by_year.png"):
    """
    Affiche un graphique en barres des thèses et HDR soutenues par année.
    """
    
    with graph_generation_lock:
        
        # Créer les dossiers pour ranger les fichiers html et png
        create_directories()
        
        df = pd.read_csv(filename)

        # Filtrer les thèses et HDR (non sensible à la casse, ignore les valeurs manquantes)
        theses_hdr = df[df['Type de Document'].str.contains("Thèse|HDR", case=False, na=False)]
        
        # Compter par année
        year_counts = theses_hdr['Année de Publication'].dropna().value_counts().sort_index().reset_index()
        year_counts.columns = ['Année', 'Nombre de thèses et HDR']

        fig = px.bar(
            year_counts,
            x='Année',
            y='Nombre de thèses et HDR',
            title="Thèses et HDR soutenues par année"
        )
        fig.update_layout(xaxis_tickangle=-45)

        fig.write_html(output_html)
        fig.write_image(output_png)

# Nuage de mots-clés des thèses/HDR
def plot_theses_keywords_wordcloud(filename, 
                                 output_html="html/theses_keywords_wordcloud.html",
                                 output_png="png/theses_keywords_wordcloud.png",
                                 max_words=50):
    """
    Génère un nuage de mots-clés lisible avec :
    - Algorithme de placement intelligent pour éviter les chevauchements
    - Couleurs harmonieuses et contrastées
    - Tailles de police optimisées
    - Légende interactive
    """
    
    with graph_generation_lock:
        create_directories()
        
        # Charger et préparer les données
        df = pd.read_csv(filename)
        theses_hdr = df[df['Type de Document'].str.contains("Thèse|HDR", case=False, na=False)]
        
        # Nettoyage approfondi
        keywords = (
            theses_hdr['Mots-clés']
            .dropna()
            .str.replace(r"[\[\]'\"\\]", "", regex=True)
            .str.split(',')
            .explode()
            .str.strip()
            .str.lower()
        )
        
        # Filtrage des mots non pertinents
        stopwords = {
            'de', 'la', 'le', 'et', 'les', 'des', 'en', 'du', 'à', 'au', 'aux',
            'pour', 'dans', 'sur', 'avec', 'est', 'son', 'ses', 'une', 'un',
            'par', 'ce', 'cette', 'ces', 'ou', 'où', 'qui', 'que', 'dont'
        }
        keywords = keywords[~keywords.isin(stopwords) & (keywords.str.len() > 3)]
        
        # Sélection des top mots
        word_counts = keywords.value_counts()
        top_words = word_counts.head(max_words)
        
        # Version PNG avec WordCloud
        wc = WordCloud(
            width=1800,
            height=1000,
            background_color='white',
            colormap='viridis',  
            max_words=max_words,
            collocations=False,
            min_font_size=12,
            max_font_size=150,
            random_state=42,
            prefer_horizontal=0.9,  
            relative_scaling=0.5    
        ).generate_from_frequencies(top_words.to_dict())
        
        wc.to_file(output_png)
        
        # Version HTML avec affichage ligne par ligne selon la fréquence
        fig = go.Figure()
        
        # Paramètres d'espacement selon le nombre de mots
        if max_words <= 25:
            row_height = 40
            font_size_base = 16
            font_size_range = 20
        elif max_words <= 50:
            row_height = 30
            font_size_base = 12
            font_size_range = 15
        else:
            row_height = 25
            font_size_base = 10
            font_size_range = 12
        
        positions = []
        
        # Placement ligne par ligne 
        for i, (word, freq) in enumerate(top_words.items()):
            # Chaque mot sur sa propre ligne, centré horizontalement
            x = 0  
            y = (len(top_words) - i - 1) * row_height  
            
            # Léger décalage aléatoire pour éviter l'alignement parfait
            x += np.random.uniform(-15, 15)
            
            positions.append((x, y))
        
        # Palette de couleurs harmonieuse
        colors = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
            '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5'
        ]
        
        # Ajouter les mots avec numérotation et dégradé de couleurs
        for i, ((word, freq), (x, y)) in enumerate(zip(top_words.items(), positions)):
            # Taille proportionnelle à la fréquence mais dans une plage restreinte
            font_size = font_size_base + (freq / top_words.max()) * font_size_range
            
            # Dégradé de couleur du rouge (top) au bleu (bottom)
            if i < 5:
                color = '#d32f2f'  
                weight = 'bold'
            elif i < 15:
                color = '#f57c00'  
                weight = 'bold'
            elif i < 30:
                color = '#388e3c'  
                weight = 'normal'
            else:
                color = '#1976d2'  
                weight = 'normal'
            
            # Opacité décroissante
            opacity = max(0.7, 1 - (i / len(top_words)) * 0.3)
            
            fig.add_trace(go.Scatter(
                x=[x],
                y=[y],
                text=[f"#{i+1} {word.capitalize()}"],
                mode="text",
                textfont=dict(
                    size=font_size,
                    color=color,
                    family="Arial",
                    weight=weight
                ),
                opacity=opacity,
                hovertemplate=f"<b>#{i+1} - {word.capitalize()}</b><br>" +
                            f"Fréquence: {freq}<br>" +
                            f"Pourcentage: {freq/word_counts.sum()*100:.1f}%<extra></extra>",
                showlegend=False,
                name=word
            ))
        
        # Dimensions adaptées pour l'affichage vertical
        total_height = len(top_words) * row_height + 100
        if max_words <= 25:
            width = 800
        elif max_words <= 50:
            width = 1000
        else:
            width = 1200
        
        # Calcul des limites pour centrer l'affichage
        y_min = -50
        y_max = (len(top_words) - 1) * row_height + 50
        
        # Mise en page pour affichage vertical
        fig.update_layout(
            title={
                'text': f"Top {max_words} des mots-clés<br><sub>Classement des thèses et HDR</sub>",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 18 if max_words > 50 else 22, 'color': '#2c3e50'}
            },
            xaxis=dict(
                visible=False, 
                range=[-200, 200]
            ),
            yaxis=dict(
                visible=False, 
                range=[y_min, y_max]
            ),
            plot_bgcolor='#fafafa',
            paper_bgcolor='white',
            margin=dict(l=20, r=20, t=80, b=20),
            height=min(total_height, 2000),  
            width=width,
            annotations=[
                dict(
                    text="Affichage par rang de classement • Survolez pour plus de détails",
                    x=0.5, y=-0.02,
                    xref="paper", yref="paper",
                    showarrow=False,
                    font=dict(size=10 if max_words > 50 else 12, color='#7f8c8d')
                )
            ]
        )
        
        # Ajouter une légende des couleurs
        fig.add_annotation(
            text="<b>Code couleur:</b><br>" +
                 "Top 1-5 (Rouge)<br>" +
                 "Top 6-15 (Orange)<br>" +
                 "Top 16-30 (Vert)<br>" +
                 "Top 31+ (Bleu)",
            x=0.02, y=0.98,
            xref="paper", yref="paper",
            showarrow=False,
            align="left",
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#bdc3c7",
            borderwidth=1,
            font=dict(size=9 if max_words > 50 else 10, color='#2c3e50')
        )
        
        fig.write_html(output_html)

