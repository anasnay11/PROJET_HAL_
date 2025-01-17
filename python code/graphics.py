# -*- coding: utf-8 -*-
"""
Created on Tue Dec  3 16:36:58 2024


"""

import pandas as pd
import plotly.express as px
import os
import threading

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