# -*- coding: utf-8 -*-

# dashboard_generator.py

def create_dashboard():
    html_content = """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <title>Dashboard de Publications</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            iframe { width: 100%; height: 500px; border: none; margin-bottom: 20px; }
            h1 { text-align: center; color: #333; }
        </style>
    </head>
    <body>
        <h1>Dashboard de Visualisation des Publications</h1>
        <iframe src="pubs_by_year.html"></iframe>
        <iframe src="type_distribution.html"></iframe>
        <iframe src="keywords_distribution.html"></iframe>
        <iframe src="domain_distribution.html"></iframe>
        <iframe src="top_authors.html"></iframe>
        <iframe src="structures_stacked.html"></iframe>
        <iframe src="publication_trends.html"></iframe>
        <iframe src="employer_distribution.html"></iframe>
        <iframe src="theses_hdr_by_year.html"></iframe>
        <iframe src="theses_keywords_wordcloud.html"></iframe>
    </body>
    </html>
    """
    dashboard_path = "html/dashboard.html"
    with open(dashboard_path, "w", encoding="utf-8") as file:
        file.write(html_content)
    return dashboard_path
