import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel, Listbox, MULTIPLE, ttk
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import os
import webbrowser
from hal_data import get_hal_data
from mapping import list_domains, list_types
from utils import generate_filename
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
from report_generator_app import generate_pdf_report, generate_latex_report
import threading

# Variables globales pour conserver le chemin du fichier CSV chargé
current_csv_file = None
dashboard_file = None

# Variable globale pour gérer l'arrêt de l'extraction
stop_extraction = False
btn_stop_extraction = None

# Variables globales pour gérer l'affichage de la progression de l'extraction
message_label = None
progress_bar = None

# Fonction pour charger un fichier CSV
def charger_csv():
    fichier_csv = filedialog.askopenfilename(
        title="Sélectionner un fichier CSV",
        filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")]
    )
    if fichier_csv:
        try:
            global scientists_df, fichier_charge
            scientists_df = pd.read_csv(fichier_csv)
            fichier_charge = True
            messagebox.showinfo("Succès", f"Fichier chargé : {fichier_csv}")
            afficher_boutons_options()
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger le fichier CSV : {e}")

# Fonction pour afficher les boutons après le chargement
def afficher_boutons_options():
    btn_extraire.pack(pady=5)
    btn_filtrer.pack(pady=5)

# Fonction pour extraire toutes les données
def extraire_toutes_les_donnees():
    extraction_data(None, None, None)

# Fenêtre pour appliquer des filtres
def appliquer_filtres():
    filtre_window = Toplevel(root)
    filtre_window.title("Filtres d'extraction")
    filtre_window.geometry("400x500")

    periode_var = tk.StringVar()
    types_selectionnes = []
    domaines_selectionnes = []

    def choisir_types():
        types_window = Toplevel(filtre_window)
        types_window.title("Choisir les types de documents")
        listbox = Listbox(types_window, selectmode=MULTIPLE)
        for t in list_types().values():
            listbox.insert(tk.END, t)
        listbox.pack(padx=10, pady=10)

        def valider_types():
            nonlocal types_selectionnes
            types_selectionnes = [listbox.get(i) for i in listbox.curselection()]
            types_window.destroy()

        tk.Button(types_window, text="Valider", command=valider_types).pack()

    def choisir_domaines():
        domaines_window = Toplevel(filtre_window)
        domaines_window.title("Choisir les domaines")
        listbox = Listbox(domaines_window, selectmode=MULTIPLE)
        for d in list_domains().values():
            listbox.insert(tk.END, d)
        listbox.pack(padx=10, pady=10)

        def valider_domaines():
            nonlocal domaines_selectionnes
            domaines_selectionnes = [listbox.get(i) for i in listbox.curselection()]
            domaines_window.destroy()

        tk.Button(domaines_window, text="Valider", command=valider_domaines).pack()

    tk.Label(filtre_window, text="Période (ex: 2019-2023)").pack(pady=5)
    periode_entry = tk.Entry(filtre_window, textvariable=periode_var)
    periode_entry.pack(pady=5)

    tk.Button(filtre_window, text="Filtrer par types", command=choisir_types).pack(pady=5)
    tk.Button(filtre_window, text="Filtrer par domaines", command=choisir_domaines).pack(pady=5)
    
    def valider_filtres():
        init_extraction_widgets()
        message_label.config(text="Extraction en cours... : 0%")
        progress_bar.pack(pady=5)
        progress_bar["value"] = 0
        root.update_idletasks()  # Forcer l'affichage immédiat des widgets
    
        # Lancer l'extraction avec filtres
        extraction_data(periode_var.get(), types_selectionnes, domaines_selectionnes)
        filtre_window.destroy()
        
    tk.Button(filtre_window, text="Lancer l'extraction", command=valider_filtres).pack(pady=10) 


# Fonction d'initialisation des éléments graphiques
def init_extraction_widgets():
    global message_label, progress_bar, btn_stop_extraction
    if message_label is None:
        message_label = tk.Label(frame_extraction, text="Extraction en cours... : 0%", font=("Helvetica", 12))
        message_label.pack(pady=5)

    if progress_bar is None:
        progress_bar = ttk.Progressbar(frame_extraction, orient="horizontal", length=500, mode="determinate")
        progress_bar.pack(pady=5)
    else:
        progress_bar.pack(pady=5)

    # Ajout du bouton d'arrêt si inexistant
    if btn_stop_extraction is None:
        btn_stop_extraction = tk.Button(frame_extraction, text="Stopper l'extraction", font=("Helvetica", 12), command=stop_extraction_task)
        btn_stop_extraction.pack(pady=5)

# Fonction pour créer un dossier 'extraction' où ranger les fichiers csv resultants
def create_extraction_folder():
    # Obtient le chemin du dossier où le script Python est exécuté
    current_directory = os.path.dirname(os.path.abspath(__file__))
    extraction_directory = os.path.join(current_directory, 'extraction')

    # Vérifie si le dossier 'extraction' existe, sinon le crée
    if not os.path.exists(extraction_directory):
        os.makedirs(extraction_directory)

    return extraction_directory

# Fonction pour extraire les données
def extraction_data(periode, types, domaines):
    global stop_extraction, message_label, progress_bar

    init_extraction_widgets()  

    # Mise à jour immédiate pour afficher le message et la barre de progression
    message_label.config(text="Extraction en cours... : 0%")
    progress_bar.pack(pady=5)
    progress_bar["value"] = 0
    root.update_idletasks()  # Forcer la mise à jour de l'interface graphique

    # Désactivation des boutons pendant l'extraction
    btn_extraire.config(state="disabled")
    btn_filtrer.config(state="disabled")
    btn_charger.config(state="disabled")

    stop_extraction = False  # Réinitialisation de la variable d'arrêt

    def extraction_task():
        global stop_extraction
        all_results = pd.DataFrame()
        total_rows = len(scientists_df)
        progress_bar["maximum"] = total_rows

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(get_hal_data, row['nom'], row['prenom'], period=periode, domain_filter=domaines, type_filter=types): index 
                for index, row in scientists_df.iterrows()
            }
            for future in as_completed(futures):
                if stop_extraction:
                    break
                result = future.result()
                all_results = pd.concat([all_results, result], ignore_index=True)
                
                # Mise à jour de la barre de progression et du message
                completed = futures[future] + 1
                progress_percentage = (completed / total_rows) * 100
                root.after(0, lambda: progress_bar.step(1))
                root.after(0, lambda: message_label.config(text=f"Extraction en cours... : {progress_percentage:.2f}%"))

        # Fin de l'extraction et sauvegarde des résultats
        if not stop_extraction:
            extraction_directory = create_extraction_folder()
            filename = generate_filename(periode, "_".join(domaines) if domaines else None, "_".join(types) if types else None)
            output_path = os.path.join(extraction_directory, filename)
            all_results.to_csv(output_path, index=False)
            root.after(0, lambda: message_label.config(text="Extraction terminée."))
            root.after(0, lambda: messagebox.showinfo("Extraction terminée", f"Les résultats ont été sauvegardés dans : {output_path}"))

        # Réactivation des boutons après l'extraction
        root.after(0, lambda: btn_extraire.config(state="normal"))
        root.after(0, lambda: btn_filtrer.config(state="normal"))
        root.after(0, lambda: btn_charger.config(state="normal"))
        root.after(0, progress_bar.pack_forget)
        root.after(0, message_label.pack_forget)
        root.after(0, btn_stop_extraction.pack_forget)

    # Démarrer l'extraction dans un thread séparé
    thread = threading.Thread(target=extraction_task)
    thread.start()

# Variable globale pour gérer l'arrêt de l'extraction
stop_extraction = False

# Fonction pour stopper l'extraction
def stop_extraction_task():
    global stop_extraction
    stop_extraction = True
    message_label.config(text="Arrêt de l'extraction en cours...")
    progress_bar.stop()
    messagebox.showinfo("Interruption", "L'extraction a été interrompue par l'utilisateur.")

# Fonctions pour charger un fichier CSV et générer un graphique
def generate_graphs_thread():
    try:
        plot_publications_by_year(current_csv_file, output_html="html/pubs_by_year.html", output_png="png/pubs_by_year.png")
        plot_document_types(current_csv_file, output_html="html/type_distribution.html", output_png="png/type_distribution.png")
        plot_keywords(current_csv_file, output_html="html/keywords_distribution.html", output_png="png/keywords_distribution.png")
        plot_top_domains(current_csv_file, output_html="html/domain_distribution.html", output_png="png/domain_distribution.png")
        plot_publications_by_author(current_csv_file, output_html="html/top_authors.html", output_png="png/top_authors.png")
        plot_structures_stacked(current_csv_file, output_html="html/structures_stacked.html", output_png="png/structures_stacked.png")
        plot_publications_trends(current_csv_file, output_html="html/publication_trends.html", output_png="png/publication_trends.png")

        global dashboard_file
        dashboard_file = create_dashboard()
        messagebox.showinfo("Succès", "Graphiques générés avec succès.")
        btn_afficher_graphiques.pack(pady=5)
        btn_generer_rapport.pack(pady=5)
    except Exception as e:
        messagebox.showerror("Erreur", f"Erreur lors de la génération des graphiques : {e}")

def generer_graphiques():
    global current_csv_file
    current_csv_file = filedialog.askopenfilename(
        title="Sélectionner le fichier extrait",
        filetypes=[("CSV files", "*.csv")]
    )
    if current_csv_file:
        threading.Thread(target=generate_graphs_thread).start()

# Fonction pour afficher les graphiques
def afficher_graphiques():
    if dashboard_file:
        webbrowser.open('file://' + os.path.realpath(dashboard_file))
    else:
        messagebox.showerror("Erreur", "Aucun graphique n'a été généré.")

# Fonction pour générer les rapports 
def generer_rapport():
    rapport_window = Toplevel(root)
    rapport_window.title("Générer un rapport")
    rapport_window.geometry("300x150")

    choix_format = tk.StringVar(value="")  # Variable définie dans le même scope
    tk.Label(rapport_window, text="Choisissez le format du rapport :", font=("Helvetica", 12)).pack(pady=10)
    tk.Radiobutton(rapport_window, text="PDF", variable=choix_format, value="PDF", font=("Helvetica", 10)).pack()
    tk.Radiobutton(rapport_window, text="LaTeX", variable=choix_format, value="LaTeX", font=("Helvetica", 10)).pack()

    def valider_choix():
        format_choisi = choix_format.get()
        nom_fichier_csv = os.path.basename(current_csv_file).replace(".csv", "")

        # Générer le rapport selon le choix
        if format_choisi == "PDF":
            fichier_pdf = f"{nom_fichier_csv}.pdf"
            generate_pdf_report(nom_fichier_csv)
            messagebox.showinfo("Rapport PDF", f"Le rapport PDF '{fichier_pdf}' a été généré avec succès.")
        elif format_choisi == "LaTeX":
            fichier_latex = f"{nom_fichier_csv}.tex"
            generate_latex_report(nom_fichier_csv)
            messagebox.showinfo("Rapport LaTeX", f"Le rapport LaTeX '{fichier_latex}' a été généré avec succès.")
        else:
            messagebox.showwarning("Choix invalide", "Veuillez choisir un format.")
        
        # Fermer la fenêtre après validation
        rapport_window.destroy()

    # Bouton de validation
    btn_valider = tk.Button(rapport_window, text="Valider", command=valider_choix)
    btn_valider.pack(pady=10)

# Interface principale
root = tk.Tk()
root.title("Outil d'Extraction et Analyse - API HAL")
root.geometry("700x600")

# Onglets avec Notebook
notebook = ttk.Notebook(root)
notebook.pack(expand=1, fill="both")

# Frame Extraction
frame_extraction = ttk.Frame(notebook)
frame_extraction.pack(fill="both", expand=True)

label_accueil = tk.Label(
    frame_extraction,
    text="Bienvenue sur la section Extraction ! \nVous pouvez charger un fichier d'entrée et extraire à partir de celui-ci.",
    font=("Helvetica", 16)
)
label_accueil.pack(pady=10)

btn_charger = tk.Button(frame_extraction, text="Charger un fichier CSV", font=("Helvetica", 12), command=charger_csv)
btn_charger.pack(pady=5)

btn_extraire = tk.Button(frame_extraction, text="Extraire toutes les données", font=("Helvetica", 12), command=extraire_toutes_les_donnees)
btn_filtrer = tk.Button(frame_extraction, text="Appliquer des filtres d'extraction", font=("Helvetica", 12), command=appliquer_filtres)

# Barre de progression (initialement cachée)
progress_bar = ttk.Progressbar(frame_extraction, orient="horizontal", length=500, mode="determinate")
progress_bar.pack(pady=10)
progress_bar.pack_forget()

# Frame Analyse
frame_analyse = ttk.Frame(notebook)
frame_analyse.pack(fill="both", expand=True)

label_analyse = tk.Label(
    frame_analyse,
    text="Bienvenue sur la section Analyse Graphique ! \nVous pouvez charger un fichier de données et générer des graphiques à partir de celui-ci.",
    font=("Helvetica", 16)
)
label_analyse.pack(pady=10)

btn_generer_graphiques = tk.Button(frame_analyse, text="Charger un fichier et générer des graphiques", font=("Helvetica", 12), command=generer_graphiques)
btn_generer_graphiques.pack(pady=5)

btn_afficher_graphiques = tk.Button(frame_analyse, text="Afficher les graphiques", font=("Helvetica", 12), command=afficher_graphiques)
btn_generer_rapport = tk.Button(frame_analyse, text="Générer un rapport", font=("Helvetica", 12), command=generer_rapport)

btn_afficher_graphiques.pack_forget()
btn_generer_rapport.pack_forget()

notebook.add(frame_extraction, text="Extraction")
notebook.add(frame_analyse, text="Analyse")

# Lancer l'application
root.mainloop()