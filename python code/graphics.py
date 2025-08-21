# -*- coding: utf-8 -*-

# graphics.py

import pandas as pd
import plotly.express as px
import os
import threading
import plotly.graph_objects as go

# Create global lock for graph generation
graph_generation_lock = threading.Lock()

def create_directories():
    """Create 'png' and 'html' directories"""
    base_path = os.path.dirname(os.path.abspath(__file__))
    directories = ['png', 'html']
    for directory in directories:
        path = os.path.join(base_path, directory)
        if not os.path.exists(path):
            os.makedirs(path)

def analyze_data(filename):
    """
    Performs complete data analysis including:
    - Most frequent keywords
    - Document type distribution
    - Publications per author (top 10)
    - Publications per research structure (top 10)  
    - Publications per year (complete distribution)
    - Average number of authors per publication
    - Average number of keywords per publication
    - Total number of publications
    
    Args:
        filename (str): Path to CSV file to analyze
        
    Returns:
        dict: Dictionary containing all analysis results
    """
    df = pd.read_csv(filename)

    # Ensure that required columns exist in the file
    required_columns = ['Nom', 'Prenom', 'IdHAL des auteurs de la publication', 'Docid', 'Titre',
                        'Année de Publication', 'Type de Document', 'Mots-clés', 'Laboratoire de Recherche']

    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Column '{col}' is missing from the file.")

    # Most frequent keywords (with preprocessing)
    keyword_counts = (
        df['Mots-clés'].dropna()
        .str.replace(r"[^\w\s,]", "", regex=True)  # Remove special characters
        .str.split(',')
        .explode()
        .str.strip()
        .value_counts()
        .head(10)
    )

    # Document type distribution
    doc_type_counts = df['Type de Document'].value_counts()

    # Publications per author (based on Name + First name combinations)
    author_counts = df.groupby(['Nom', 'Prenom']).size().sort_values(ascending=False).head(10)

    # Publications per research structure
    structure_counts = df['Laboratoire de Recherche'].dropna().str.strip().value_counts().head(10)

    # Publication distribution per year
    year_counts = df['Année de Publication'].value_counts().sort_index()

    # Average number of authors per publication
    avg_authors_per_pub = df['IdHAL des auteurs de la publication'].apply(lambda x: len(eval(x)) if pd.notnull(x) else 0).mean()

    # Average number of keywords per publication
    avg_keywords_per_pub = df['Mots-clés'].apply(lambda x: len(eval(x)) if pd.notnull(x) else 0).mean()

    # Total number of publications
    total_publications = len(df)

    # Return all results as dictionary
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

def plot_publications_by_year(filename, output_html="html/pubs_by_year.html", output_png="png/pubs_by_year.png"):
    """
    Display an interactive histogram of publications by year.
    Save the graph in HTML format.
    """
    
    with graph_generation_lock:
        
        # Create directories to store html and png files
        create_directories()
        
        # Load data
        df = pd.read_csv(filename)
        
        # Check "Publication Year" column
        year_counts = df['Année de Publication'].dropna().value_counts().reset_index()
        year_counts.columns = ['Année', 'Nombre de publications']
        year_counts = year_counts.sort_values(by='Année')  # Sort by year
    
        # Create interactive graph
        fig = px.bar(
            year_counts,
            x='Année',
            y='Nombre de publications',
            title="Nombre de publications par année",
            labels={'Année': 'Année', 'Nombre de publications': 'Nombre de publications'},
            color='Nombre de publications',
            color_continuous_scale='Viridis'
        )
    
        # Save graph
        fig.write_html(output_html)
        fig.write_image(output_png)


def plot_document_types(filename, output_html="html/type_distribution.html", output_png="png/type_distribution.png"):
    """
    Display an interactive pie chart of document types.
    """
    with graph_generation_lock:
    
        # Create directories to store html and png files
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


def plot_keywords(filename, output_html="html/keywords_distribution.html", output_png="png/keywords_distribution.png"):
    """
    Display an interactive horizontal bar plot of most frequent keywords.
    """
    
    with graph_generation_lock:
        
        # Create directories to store html and png files
        create_directories()
        
        df = pd.read_csv(filename)
        keyword_counts = (
            df['Mots-clés']
            .dropna()
            .str.split(',')
            .explode()
            .str.strip()
            .replace('[]', pd.NA)  # Exclude empty keywords
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


def plot_top_domains(filename, output_html="html/domain_distribution.html", output_png="png/domain_distribution.png"):
    """
    Display an interactive histogram of most frequent domains.
    """
    
    with graph_generation_lock:
        
        # Create directories to store html and png files
        create_directories()
        
        df = pd.read_csv(filename)
        domain_counts = (
            df['Domaine']
            .dropna()
            .str.split(',')
            .explode()
            .str.strip()
            .replace('Domaine non défini', pd.NA)  # Exclude undefined domains
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


def plot_publications_by_author(filename, output_html="html/top_authors.html", output_png="png/top_authors.png"):
    """
    Display an interactive histogram of most prolific authors.
    """
    
    with graph_generation_lock:
        
        # Create directories to store html and png files
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


def plot_structures_stacked(filename, output_html="html/structures_stacked.html", output_png="png/structures_stacked.png"):
    """
    Display a stacked bar chart of publications by structure and year.
    """
    
    with graph_generation_lock:
        
        # Create directories to store html and png files
        create_directories()
        
        df = pd.read_csv(filename)
        
        # Exclude 'Not available' values
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

    
def plot_publications_trends(filename, output_html="html/publication_trends.html", output_png="png/publication_trends.png"):
    """
    Display an interactive line chart of publication trends by year.
    """
    
    with graph_generation_lock:
        
        # Create directories to store html and png files
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
        
def plot_employer_distribution(filename, output_html="html/employer_distribution.html", output_png="png/employer_distribution.png"):
    """
    Display a stacked bar chart of publications by employers (laboratories).
    """
    
    with graph_generation_lock:
    
        df = pd.read_csv(filename)
        
        # Clean employer names
        employer_counts = (
            df['Laboratoire de Recherche']
            .dropna()
            [df['Laboratoire de Recherche'] != "Non disponible"]
            .str.replace(r"Laboratoire des sciences et techniques.*", "Lab-STICC", regex=True)
            .str.replace(r"Inria.*", "Inria", regex=True)
            .value_counts()
            .head(15)
        )
    
        # Reformat for plotly
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

def plot_theses_hdr_by_year(filename, output_html="html/theses_hdr_by_year.html", output_png="png/theses_hdr_by_year.png"):
    """
    Display a bar chart of theses and HDR defended by year.
    """
    
    with graph_generation_lock:
        
        # Create directories to store html and png files
        create_directories()
        
        df = pd.read_csv(filename)

        # Filter theses and HDR (case insensitive, ignore missing values)
        theses_hdr = df[df['Type de Document'].str.contains("Thèse|HDR", case=False, na=False)]
        
        # Count by year
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

def plot_theses_keywords_wordcloud(filename, 
                                 output_html="html/theses_keywords_wordcloud.html",
                                 output_png="png/theses_keywords_wordcloud.png",
                                 max_words=15):
    """
    Generate a centered vertical list of top 15 thesis/HDR keywords
    with visual hierarchy by color and size.
    
    Args:
        filename (str): Path to CSV file
        output_html (str): HTML output path
        output_png (str): PNG output path
        max_words (int): Maximum number of words to display
    """
    
    with graph_generation_lock:
        create_directories()
        
        # Load and prepare data
        df = pd.read_csv(filename)
        theses_hdr = df[df['Type de Document'].str.contains("Thèse|HDR", case=False, na=False)]
        
        # Thorough cleaning
        keywords = (
            theses_hdr['Mots-clés']
            .dropna()
            .str.replace(r"[\[\]'\"\\]", "", regex=True)
            .str.split(',')
            .explode()
            .str.strip()
            .str.lower()
        )
        
        # Filter irrelevant words
        stopwords = {
            'de', 'la', 'le', 'et', 'les', 'des', 'en', 'du', 'à', 'au', 'aux',
            'pour', 'dans', 'sur', 'avec', 'est', 'son', 'ses', 'une', 'un',
            'par', 'ce', 'cette', 'ces', 'ou', 'où', 'qui', 'que', 'dont'
        }
        keywords = keywords[~keywords.isin(stopwords) & (keywords.str.len() > 3)]
        
        # Select top words
        word_counts = keywords.value_counts()
        top_words = word_counts.head(max_words)
        
        if len(top_words) == 0:
            # Create empty graph if no keywords
            fig = go.Figure()
            fig.add_annotation(
                text="Aucun mot-clé trouvé dans les thèses/HDR",
                x=0.5, y=0.5,
                xref="paper", yref="paper",
                showarrow=False,
                font=dict(size=20, color='gray')
            )
            fig.update_layout(
                title="Mots-clés des thèses et HDR",
                xaxis=dict(visible=False),
                yaxis=dict(visible=False)
            )
        else:
            # Create centered list visualization
            fig = go.Figure()
            
            # Size and spacing parameters
            max_font_size = 28
            min_font_size = 14
            line_spacing = 40  # Spacing between lines
            
            # Calculate proportional font sizes
            max_freq = top_words.max()
            min_freq = top_words.min()
            
            for i, (word, freq) in enumerate(top_words.items()):
                # Y position (from top to bottom)
                y_position = (len(top_words) - i - 1) * line_spacing
                
                # Size proportional to frequency
                if max_freq == min_freq:
                    font_size = max_font_size
                else:
                    font_size = min_font_size + (freq - min_freq) / (max_freq - min_freq) * (max_font_size - min_font_size)
                
                # Color by rank
                if i < 3:  # Top 1-3
                    color = '#E53E3E'  # Red
                    weight = 'bold'
                elif i < 6:  # Top 4-6
                    color = '#DD6B20'  # Orange
                    weight = 'bold'
                elif i < 10:  # Top 7-10
                    color = '#38A169'  # Green
                    weight = 'normal'
                else:  # Top 11+
                    color = '#805AD5'  # Purple
                    weight = 'normal'
                
                # Add word to graph (centered on x=0)
                fig.add_trace(go.Scatter(
                    x=[0],
                    y=[y_position],
                    text=[word.capitalize()],
                    mode="text",
                    textfont=dict(
                        size=font_size,
                        color=color,
                        family="Arial Black" if weight == 'bold' else "Arial"
                    ),
                    hovertemplate=f"<b>#{i+1} - {word.capitalize()}</b><br>" +
                                f"Fréquence: {freq}<br>" +
                                f"Pourcentage: {freq/word_counts.sum()*100:.1f}%<extra></extra>",
                    showlegend=False,
                    name=word
                ))
            
            # Calculate display limits
            total_height = len(top_words) * line_spacing
            y_range = [-line_spacing, total_height]
            x_range = [-300, 300]  # Fixed centered width
            
            # Layout
            fig.update_layout(
                title={
                    'text': f"Top {len(top_words)} des mots-clés des thèses et HDR<br><sub style='font-size:14px'>Classement par fréquence d'apparition</sub>",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 24, 'color': '#2c3e50', 'family': 'Arial Black'}
                },
                xaxis=dict(
                    visible=False, 
                    range=x_range
                ),
                yaxis=dict(
                    visible=False, 
                    range=y_range
                ),
                plot_bgcolor='#f8fafc',
                paper_bgcolor='white',
                margin=dict(l=50, r=50, t=120, b=80),
                height=max(600, total_height + 200),
                width=800,
                annotations=[
                    # Instructions at bottom
                    dict(
                        text="Survolez les mots pour voir les détails • Taille proportionnelle à la fréquence",
                        x=0.5, y=-0.08,
                        xref="paper", yref="paper",
                        showarrow=False,
                        font=dict(size=12, color='#64748b')
                    ),
                    # Color legend at top right
                    dict(
                        text="<b>Code couleur :</b><br>" +
                             "Top 1-3 (Rouge)<br>" +
                             "Top 4-6 (Orange)<br>" +
                             "Top 7-10 (Vert)<br>" +
                             "Top 11+ (Violet)",
                        x=0.98, y=0.85,
                        xref="paper", yref="paper",
                        showarrow=False,
                        align="right",
                        bgcolor="rgba(255,255,255,0.95)",
                        bordercolor="#e2e8f0",
                        borderwidth=1,
                        font=dict(size=11, color='#374151')
                    )
                ]
            )
        
        # Save files
        fig.write_html(output_html)
        fig.write_image(output_png)
        
def plot_temporal_evolution_by_team(filename, output_html="html/temporal_evolution_teams.html", output_png="png/temporal_evolution_teams.png"):
    """
    Display an interactive line chart of publication evolution by research team over time.
    """
    
    with graph_generation_lock:
        
        # Create directories to store html and png files
        create_directories()
        
        df = pd.read_csv(filename)
        
        # Filter out unavailable laboratories
        df_filtered = df[df['Laboratoire de Recherche'] != 'Non disponible'].copy()
        
        # Clean laboratory names for better display
        df_filtered['Laboratoire de Recherche'] = (
            df_filtered['Laboratoire de Recherche']
            .str.replace(r"Laboratoire des sciences et techniques.*", "Lab-STICC", regex=True)
            .str.replace(r"Inria.*", "Inria", regex=True)
            .str.slice(0, 50)  # Limit length for better display
        )
        
        # Group by laboratory and year
        grouped = df_filtered.groupby(['Laboratoire de Recherche', 'Année de Publication']).size().reset_index(name='Nombre de publications')
        
        # Keep only top 10 most productive laboratories for readability
        top_labs = df_filtered['Laboratoire de Recherche'].value_counts().head(10).index
        grouped_top = grouped[grouped['Laboratoire de Recherche'].isin(top_labs)]
        
        # Create interactive line chart
        fig = px.line(
            grouped_top,
            x='Année de Publication',
            y='Nombre de publications',
            color='Laboratoire de Recherche',
            title="Évolution temporelle des publications par équipe de recherche",
            labels={'Année de Publication': 'Année', 'Nombre de publications': 'Nombre de publications'},
            markers=True
        )
        
        # Customize layout
        fig.update_layout(
            xaxis_title="Année",
            yaxis_title="Nombre de publications",
            legend_title="Laboratoire de Recherche",
            hovermode='x unified'
        )
        
        # Save files
        fig.write_html(output_html)
        fig.write_image(output_png)


