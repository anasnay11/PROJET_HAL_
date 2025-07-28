# -*- coding: utf-8 -*-

# app.py

import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel, Listbox, MULTIPLE, ttk
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import os
import webbrowser
import json
from hal_data import get_hal_data
from mapping import list_domains, list_types
from utils import generate_filename
from config import get_threshold_from_level, get_level_from_threshold, list_sensitivity_levels, DEFAULT_THRESHOLD
from dashboard_generator import create_dashboard
from report_generator_app import generate_pdf_report, generate_latex_report
from clustering_model import load_and_analyze_csv
import threading
import time
from graphics import (
    plot_publications_by_year,
    plot_document_types,
    plot_keywords,
    plot_top_domains,
    plot_publications_by_author,
    plot_structures_stacked,
    plot_publications_trends,
    plot_employer_distribution,
    plot_theses_hdr_by_year,
    plot_theses_keywords_wordcloud,
)

# Global variables to store the loaded CSV file path
current_csv_file = None
dashboard_file = None

# Global variables for data
scientists_df = None
fichier_charge = False

# Global variable to manage extraction stop
stop_extraction = False
btn_stop_extraction = None

# Global variables to manage extraction progress display
message_label_extraction = None  
progress_bar = None

# Global variables for configuration
current_threshold = DEFAULT_THRESHOLD
settings_file = "app_settings.json"

# Global variables for clustering
analysis_results = None

def load_settings():
    """Load saved settings from JSON file"""
    global current_threshold
    current_threshold = DEFAULT_THRESHOLD

def open_settings():
    """
    Opens the configuration window for sensitivity settings
    
    Creates a detailed GUI for adjusting name matching sensitivity with
    predefined levels and custom options
    """
    global current_threshold
    
    settings_window = Toplevel(root)
    settings_window.title("Configuration - Sensibilité de correspondance")
    settings_window.geometry("600x650")  # Larger window
    settings_window.resizable(False, False)
    
    # Center the window
    settings_window.transient(root)
    settings_window.grab_set()
    
    # Title
    title_label = tk.Label(settings_window, text="Configuration de la sensibilité", 
                          font=("Helvetica", 16, "bold"))
    title_label.pack(pady=10)
    
    # Description
    desc_label = tk.Label(settings_window, 
                         text="Ajustez la sensibilité de la correspondance des noms d'auteurs.\n"
                              "Une sensibilité plus stricte trouvera moins de correspondances mais plus précises.\n"
                              "Une sensibilité plus permissive trouvera plus de correspondances mais potentiellement moins précises.",
                         wraplength=550, justify="left", font=("Helvetica", 10))
    desc_label.pack(pady=(0, 20), padx=20)
    
    # Main frame with scrollbar if needed
    main_frame = tk.Frame(settings_window)
    main_frame.pack(fill="both", expand=True, padx=20, pady=10)
    
    # Variable for choice
    sensitivity_var = tk.StringVar()
    custom_threshold_var = tk.IntVar()
    custom_threshold_var.set(current_threshold)
    
    # Determine current level
    current_level = get_level_from_threshold(current_threshold)
    if current_level == "personnalisé":
        sensitivity_var.set("personnalisé")
    else:
        sensitivity_var.set(current_level)
    
    # Label for predefined levels
    levels_label = tk.Label(main_frame, text="Niveaux prédéfinis :", 
                           font=("Helvetica", 12, "bold"))
    levels_label.pack(anchor="w", pady=(0, 10))
    
    # Frame for radiobuttons
    radio_frame = tk.Frame(main_frame)
    radio_frame.pack(fill="x", pady=(0, 15))
    
    # Create radiobuttons for each level
    levels = list_sensitivity_levels()
    for level, description in levels.items():
        rb = tk.Radiobutton(radio_frame, text=f"{level.title()} - {description}", 
                           variable=sensitivity_var, value=level,
                           wraplength=500, justify="left", font=("Helvetica", 10))
        rb.pack(anchor="w", pady=3)
    
    # Separator
    separator = ttk.Separator(main_frame, orient="horizontal")
    separator.pack(fill="x", pady=15)
        
    # Frame for current information
    info_frame = tk.Frame(main_frame)
    info_frame.pack(fill="x", pady=(0, 20))
    
    # Current information label
    current_info = tk.Label(info_frame, 
                           text=f"Configuration actuelle : {get_level_from_threshold(current_threshold).title()} (distance = {current_threshold})",
                           font=("Helvetica", 9, "italic"), 
                           bg="#f0f0f0", relief="ridge", bd=1)
    current_info.pack(fill="x", pady=5, padx=5)
    
    # Frame for bottom buttons
    button_frame = tk.Frame(settings_window)
    button_frame.pack(side="bottom", fill="x", padx=20, pady=20)
    
    def apply_settings():
        global current_threshold
        
        selected_level = sensitivity_var.get()
        
        if selected_level == "personnalisé":
            new_threshold = custom_threshold_var.get()
        else:
            new_threshold = get_threshold_from_level(selected_level)
        
        # Validation
        if new_threshold < 0 or new_threshold > 10:
            messagebox.showerror("Erreur", "La valeur du seuil doit être entre 0 et 10.")
            return
        
        current_threshold = new_threshold
        
        # Update information label in configuration window
        level_name = get_level_from_threshold(current_threshold)
        current_info.config(text=f"Configuration actuelle : {level_name.title()} (distance = {current_threshold})")
        
        # Update label in main interface
        update_config_display()
        
        messagebox.showinfo("Configuration", 
                           f"Sensibilité mise à jour :\n"
                           f"Niveau : {level_name.title()}\n"
                           f"Distance : {current_threshold}\n\n"
                           f"Cette configuration sera utilisée pour les prochaines extractions.")
        
        settings_window.destroy()
    
    def reset_settings():
        global current_threshold
        current_threshold = DEFAULT_THRESHOLD
        
        # Update label in main interface
        update_config_display()
        
        messagebox.showinfo("Configuration", 
                           f"Configuration réinitialisée au niveau par défaut :\n"
                           f"Niveau : Modéré\n"
                           f"Distance : {DEFAULT_THRESHOLD}")
        settings_window.destroy()
    
    # Buttons with better layout
    btn_frame = tk.Frame(button_frame)
    btn_frame.pack(pady=10)
    
    tk.Button(btn_frame, text="Annuler", command=settings_window.destroy,
              font=("Helvetica", 11), width=12).pack(side="left", padx=5)
    
    tk.Button(btn_frame, text="Réinitialiser", command=reset_settings,
              font=("Helvetica", 11), width=12).pack(side="left", padx=5)
    
    tk.Button(btn_frame, text="Valider", command=apply_settings,
              font=("Helvetica", 11, "bold"), bg="#4CAF50", fg="white", width=12).pack(side="left", padx=5)

def charger_csv():
    """Load a CSV file through file dialog"""
    fichier_csv = filedialog.askopenfilename(
        title="Sélectionner un fichier CSV",
        filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")]
    )
    if fichier_csv:
        try:
            global scientists_df, fichier_charge
            scientists_df = pd.read_csv(fichier_csv, encoding='utf-8-sig')
            fichier_charge = True
            messagebox.showinfo("Succès", f"Fichier chargé : {fichier_csv}")
            afficher_boutons_options()
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger le fichier CSV : {e}")

def afficher_boutons_options():
    """Show option buttons after loading"""
    btn_extraire.pack(pady=5)
    btn_filtrer.pack(pady=5)

def afficher_recapitulatif_extraction(periode=None, types=None, domaines=None):
    """
    Display a summary of the extraction chosen by the user
    
    Args:
        periode (str, optional): Time period filter
        types (list, optional): Document types filter
        domaines (list, optional): Domains filter
        
    Shows a confirmation dialog with extraction parameters before starting
    """
    
    # Build summary message
    if not periode and not types and not domaines:
        message = "Vous avez choisi d'extraire toutes les données"
        details = "Aucun filtre appliqué - extraction complète"
    else:
        message = "Vous avez choisi d'extraire les données avec les filtres suivants :"
        details_list = []
        
        if periode:
            details_list.append(f"• Période : {periode}")
        
        if types:
            # Vérifier si THESE ou HDR sont sélectionnés pour informer l'utilisateur
            these_hdr_info = ""
            if any(t.lower() in ["thèse", "habilitation à diriger des recherches"] for t in types):
                these_hdr_info = " (inclut automatiquement thèses et HDR)"
            
            if len(types) == 1:
                details_list.append(f"• Type de document : {types[0]}{these_hdr_info}")
            else:
                details_list.append(f"• Types de documents : {', '.join(types)}{these_hdr_info}")
        
        if domaines:
            if len(domaines) == 1:
                details_list.append(f"• Domaine : {domaines[0]}")
            else:
                details_list.append(f"• Domaines : {', '.join(domaines)}")
        
        details = "\n".join(details_list)
    
    # Confirmation window
    recap_window = tk.Toplevel(root)
    recap_window.title("Récapitulatif de l'extraction")
    recap_window.geometry("500x350")
    recap_window.resizable(False, False)
    
    # Center window
    recap_window.transient(root)
    recap_window.grab_set()
    
    # Title
    title_label = tk.Label(recap_window, text="Récapitulatif de l'extraction", 
                          font=("Helvetica", 16, "bold"))
    title_label.pack(pady=15)
    
    # Main message
    message_label = tk.Label(recap_window, text=message, 
                            font=("Helvetica", 12), wraplength=450)
    message_label.pack(pady=10)
    
    # Details in a frame
    details_frame = tk.Frame(recap_window, relief="ridge", bd=2, bg="#f8f8f8")
    details_frame.pack(pady=15, padx=20, fill="x")
    
    details_label = tk.Label(details_frame, text=details, 
                            font=("Helvetica", 10), justify="left", bg="#f8f8f8")
    details_label.pack(pady=10, padx=10)
    
    # Information about number of scientists
    nb_scientifiques = len(scientists_df)
    info_label = tk.Label(recap_window, 
                         text=f"Nombre de scientifiques à traiter : {nb_scientifiques}",
                         font=("Helvetica", 10, "italic"), fg="gray")
    info_label.pack(pady=5)
    
    # Configuration information
    level_name = get_level_from_threshold(current_threshold)
    config_label = tk.Label(recap_window, 
                           text=f"Sensibilité de correspondance : {level_name.title()} (distance = {current_threshold})",
                           font=("Helvetica", 9, "italic"), fg="gray")
    config_label.pack(pady=2)
    
    # Frame for buttons
    button_frame = tk.Frame(recap_window)
    button_frame.pack(side="bottom", pady=20)
    
    def confirmer_extraction():
        recap_window.destroy()
        # Start extraction
        init_extraction_widgets()
        message_label_extraction.config(text="Extraction en cours... : 0%")
        progress_bar.pack(pady=5)
        progress_bar["value"] = 0
        root.update_idletasks()
        
        # Start extraction with parameters
        extraction_data(periode, types, domaines)
    
    def annuler_extraction():
        recap_window.destroy()
    
    # Buttons
    tk.Button(button_frame, text="Annuler", command=annuler_extraction,
              font=("Helvetica", 11), width=12).pack(side="left", padx=10)
    
    tk.Button(button_frame, text="Confirmer et lancer", command=confirmer_extraction,
              font=("Helvetica", 11, "bold"), bg="#4CAF50", fg="white", width=18).pack(side="left", padx=10)

def extraire_toutes_les_donnees():
    """Extract all data with summary"""
    afficher_recapitulatif_extraction()

def appliquer_filtres():
    """
    Open the filter application window
    
    Creates a GUI for selecting extraction filters including period,
    document types, and scientific domains
    """
    filtre_window = Toplevel(root)
    filtre_window.title("Filtres d'extraction")
    filtre_window.geometry("400x550")
    filtre_window.resizable(False, False)

    periode_var = tk.StringVar()
    types_selectionnes = []
    domaines_selectionnes = []

    def choisir_types():
        types_window = Toplevel(filtre_window)
        types_window.title("Choisir les types de documents")
        types_window.geometry("400x450")
        
        # Frame with scrollbar if needed
        main_frame = tk.Frame(types_window)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        tk.Label(main_frame, text="Sélectionnez les types de documents :", 
                font=("Helvetica", 12, "bold")).pack(pady=(0, 10))
        
        # Frame for listbox with scrollbar
        listbox_frame = tk.Frame(main_frame)
        listbox_frame.pack(fill="both", expand=True)
        
        scrollbar = tk.Scrollbar(listbox_frame)
        scrollbar.pack(side="right", fill="y")
        
        listbox = Listbox(listbox_frame, selectmode=MULTIPLE, height=15, yscrollcommand=scrollbar.set)
        for t in list_types().values():
            listbox.insert(tk.END, t)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        def valider_types():
            nonlocal types_selectionnes
            types_selectionnes = [listbox.get(i) for i in listbox.curselection()]
            # Update display in filter window
            if types_selectionnes:
                types_label.config(text=f"Types sélectionnés : {len(types_selectionnes)} type(s)")
            else:
                types_label.config(text="Aucun type sélectionné")
            types_window.destroy()

        tk.Button(main_frame, text="Valider la sélection", command=valider_types,
                 font=("Helvetica", 11), bg="#2196F3", fg="white").pack(pady=10)

    def choisir_domaines():
        domaines_window = Toplevel(filtre_window)
        domaines_window.title("Choisir les domaines")
        domaines_window.geometry("400x450")
        
        # Frame with scrollbar if needed
        main_frame = tk.Frame(domaines_window)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        tk.Label(main_frame, text="Sélectionnez les domaines :", 
                font=("Helvetica", 12, "bold")).pack(pady=(0, 10))
        
        # Frame for listbox with scrollbar
        listbox_frame = tk.Frame(main_frame)
        listbox_frame.pack(fill="both", expand=True)
        
        scrollbar = tk.Scrollbar(listbox_frame)
        scrollbar.pack(side="right", fill="y")
        
        listbox = Listbox(listbox_frame, selectmode=MULTIPLE, height=15, yscrollcommand=scrollbar.set)
        for d in list_domains().values():
            listbox.insert(tk.END, d)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        def valider_domaines():
            nonlocal domaines_selectionnes
            domaines_selectionnes = [listbox.get(i) for i in listbox.curselection()]
            # Update display in filter window
            if domaines_selectionnes:
                domaines_label.config(text=f"Domaines sélectionnés : {len(domaines_selectionnes)} domaine(s)")
            else:
                domaines_label.config(text="Aucun domaine sélectionné")
            domaines_window.destroy()

        tk.Button(main_frame, text="Valider la sélection", command=valider_domaines,
                 font=("Helvetica", 11), bg="#2196F3", fg="white").pack(pady=10)

    # Filter interface
    tk.Label(filtre_window, text="Configuration des filtres d'extraction", 
             font=("Helvetica", 14, "bold")).pack(pady=15)
    
    # Separator
    ttk.Separator(filtre_window, orient="horizontal").pack(fill="x", padx=20, pady=10)
    
    # Period
    periode_frame = tk.Frame(filtre_window)
    periode_frame.pack(pady=10)
    
    tk.Label(periode_frame, text="Période (format : YYYY-YYYY)", 
             font=("Helvetica", 11, "bold")).pack()
    tk.Label(periode_frame, text="Exemple : 2019-2023", 
             font=("Helvetica", 9), fg="gray").pack()
    periode_entry = tk.Entry(periode_frame, textvariable=periode_var, width=20, font=("Helvetica", 11))
    periode_entry.pack(pady=5)

    # Types
    types_frame = tk.Frame(filtre_window)
    types_frame.pack(pady=15)
    
    tk.Button(types_frame, text="Sélectionner les types de documents", 
              command=choisir_types, width=35, font=("Helvetica", 10),
              bg="#2196F3", fg="white").pack()
    types_label = tk.Label(types_frame, text="Aucun type sélectionné", 
                          font=("Helvetica", 9), fg="gray")
    types_label.pack(pady=(5, 0))

    # Domains
    domaines_frame = tk.Frame(filtre_window)
    domaines_frame.pack(pady=15)
    
    tk.Button(domaines_frame, text="Sélectionner les domaines", 
              command=choisir_domaines, width=35, font=("Helvetica", 10),
              bg="#2196F3", fg="white").pack()
    domaines_label = tk.Label(domaines_frame, text="Aucun domaine sélectionné", 
                             font=("Helvetica", 9), fg="gray")
    domaines_label.pack(pady=(5, 0))
    
    # Separator
    ttk.Separator(filtre_window, orient="horizontal").pack(fill="x", padx=20, pady=20)
    
    def valider_filtres():
        # Get values
        periode = periode_var.get().strip() if periode_var.get().strip() else None
        
        # Close filter window
        filtre_window.destroy()
        
        # Show summary with selected filters
        afficher_recapitulatif_extraction(periode, types_selectionnes, domaines_selectionnes)
        
    # Validation button
    tk.Button(filtre_window, text="Continuer vers le récapitulatif", 
              command=valider_filtres, font=("Helvetica", 12, "bold"),
              bg="#4CAF50", fg="white", width=25).pack(pady=15)

def init_extraction_widgets():
    """Initialize graphical elements for extraction"""
    global message_label_extraction, progress_bar, btn_stop_extraction
    if message_label_extraction is None:
        message_label_extraction = tk.Label(frame_extraction, text="Extraction en cours... : 0%", font=("Helvetica", 12))
        message_label_extraction.pack(pady=5)

    if progress_bar is None:
        progress_bar = ttk.Progressbar(frame_extraction, orient="horizontal", length=500, mode="determinate")
        progress_bar.pack(pady=5)
    else:
        progress_bar.pack(pady=5)

    # Add stop button if not existing
    if btn_stop_extraction is None:
        btn_stop_extraction = tk.Button(
            frame_extraction, 
            text="Arrêter l'extraction", 
            font=("Helvetica", 11, "bold"),
            bg="#f44336",  # Red
            fg="white",
            activebackground="#d32f2f",
            command=stop_extraction_task,
            relief="raised",
            bd=2
        )
        btn_stop_extraction.pack(pady=8)

def create_extraction_folder():
    """Create extraction folder to store resulting CSV files"""
    # Get the path of the directory where the Python script is executed
    current_directory = os.path.dirname(os.path.abspath(__file__))
    extraction_directory = os.path.join(current_directory, 'extraction')

    # Check if extraction folder exists, otherwise create it
    if not os.path.exists(extraction_directory):
        os.makedirs(extraction_directory)

    return extraction_directory

def extraction_data(periode, types, domaines):
    """
    Main data extraction function with parallel processing
    
    Args:
        periode (str): Time period filter
        types (list): Document types filter  
        domaines (list): Domains filter
        
    Runs extraction in separate thread with progress tracking and stop capability
    """
    global stop_extraction, message_label_extraction, progress_bar

    init_extraction_widgets()  

    # Immediate update to show message and progress bar
    message_label_extraction.config(text="Extraction en cours... : 0%")
    progress_bar.pack(pady=5)
    progress_bar["value"] = 0
    root.update_idletasks()  # Force GUI update

    # Disable buttons during extraction
    btn_extraire.config(state="disabled")
    btn_filtrer.config(state="disabled")
    btn_charger.config(state="disabled")

    stop_extraction = False  # Reset stop variable

    def extraction_task():
        global stop_extraction
        all_results = pd.DataFrame()
        total_rows = len(scientists_df)
        progress_bar["maximum"] = total_rows

        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = {
                executor.submit(get_hal_data, row['nom'], row['prenom'], 
                              period=periode, domain_filter=domaines, type_filter=types,
                              threshold=current_threshold): index 
                for index, row in scientists_df.iterrows()
            }
            for future in as_completed(futures):
                if stop_extraction:
                    break
                result = future.result()
                all_results = pd.concat([all_results, result], ignore_index=True)
                
                # Update progress bar and message
                completed = futures[future] + 1
                progress_percentage = int((completed / total_rows) * 100)
                root.after(0, lambda: progress_bar.step(1))
                root.after(0, lambda: message_label_extraction.config(text=f"Extraction en cours... : {progress_percentage}%"))

        # End extraction and save results
        if not stop_extraction:
            extraction_directory = create_extraction_folder()
            filename = generate_filename(periode, "_".join(domaines) if domaines else None, "_".join(types) if types else None)
            output_path = os.path.join(extraction_directory, filename)
            all_results.to_csv(output_path, index=False)
            root.after(0, lambda: message_label_extraction.config(text="Extraction terminée."))
            root.after(0, lambda: messagebox.showinfo("Extraction terminée", f"Les résultats ont été sauvegardés dans : {output_path}"))

        # Re-enable buttons after extraction
        root.after(0, lambda: btn_extraire.config(state="normal"))
        root.after(0, lambda: btn_filtrer.config(state="normal"))
        root.after(0, lambda: btn_charger.config(state="normal"))
        root.after(0, progress_bar.pack_forget)
        root.after(0, message_label_extraction.pack_forget)
        root.after(0, btn_stop_extraction.pack_forget)

    # Start extraction in separate thread
    thread = threading.Thread(target=extraction_task)
    thread.start()

def stop_extraction_task():
    """Stop extraction with confirmation"""
    global stop_extraction
    
    # Ask for confirmation before stopping
    result = messagebox.askyesno(
        "Confirmer l'arrêt", 
        "Êtes-vous sûr de vouloir arrêter l'extraction en cours ?\n\n"
        "Les données déjà extraites seront perdues et vous devrez "
        "relancer l'extraction depuis le début.",
        icon='warning'
    )
    
    if result:
        stop_extraction = True
        message_label_extraction.config(text="Arrêt de l'extraction en cours...")
        progress_bar.stop()
        
        # Show detailed information message
        messagebox.showinfo(
            "Extraction interrompue", 
            "L'extraction a été interrompue par l'utilisateur.\n\n"
            "Aucun fichier n'a été sauvegardé. Pour récupérer des données, "
            "vous devrez relancer une nouvelle extraction."
        )

def check_model_status():
    """
    Vérifie le statut du modèle de clustering
    
    Returns:
        tuple: (model_exists, model_info)
    """
    model_path = 'clustering_model.pkl'
    
    if not os.path.exists(model_path):
        return False, "Aucun modèle trouvé"
    
    try:
        # Charger temporairement le modèle pour obtenir les infos
        from clustering_model import DuplicateHomonymClusteringModel
        temp_model = DuplicateHomonymClusteringModel()
        temp_model.load_model(model_path)
        
        model_info = {
            'total_publications': temp_model.training_stats['total_publications'],
            'duplicate_clusters': temp_model.training_stats['duplicate_clusters'],
            'homonym_clusters': temp_model.training_stats['homonym_clusters']
        }
        
        return True, model_info
        
    except Exception as e:
        return False, f"Erreur lors du chargement: {str(e)}"

def detection_doublons_homonymes():
    """
    Ouvre la fenêtre principale de détection des doublons et homonymes
    Version mise à jour sans possibilité d'entraînement
    """
    global analysis_results
    
    # Créer la fenêtre principale
    detection_window = Toplevel(root)
    detection_window.title("Détection Doublons & Homonymes")
    detection_window.geometry("700x600")
    detection_window.resizable(True, True)
    
    # Titre
    title_label = tk.Label(detection_window, text="Détection Doublons & Homonymes", 
                          font=("Helvetica", 18, "bold"))
    title_label.pack(pady=15)
    
    # Séparateur
    ttk.Separator(detection_window, orient="horizontal").pack(fill="x", padx=20, pady=10)
    
    # Frame pour les informations sur le modèle
    model_info_frame = tk.Frame(detection_window, relief="ridge", bd=2, bg="#f0f0f0")
    model_info_frame.pack(fill="x", padx=20, pady=10)
    
    # Vérifier si le modèle existe
    model_exists, model_info = check_model_status()
    
    if model_exists and isinstance(model_info, dict):
        model_info_text = f"Modèle entraîné disponible\n"
        model_info_text += f"Entraîné sur {model_info['total_publications']} publications\n"
        model_info_text += f"{model_info['duplicate_clusters']} clusters de doublons détectés\n"
        model_info_text += f"{model_info['homonym_clusters']} clusters d'homonymes détectés"
        model_status = "PRÊT"
    elif model_exists:
        model_info_text = f"Erreur avec le modèle: {model_info}"
        model_status = "ERREUR"
    else:
        model_info_text = "Aucun modèle entraîné trouvé\n"
        model_info_text += "Vous devez d'abord entraîner un modèle.\n"
        model_info_text += "Utilisez le script: python train_model.py"
        model_status = "NON_ENTRAINÉ"
                               
    model_info_label = tk.Label(model_info_frame, text=model_info_text, 
                               font=("Helvetica", 11), justify="left", bg="#f0f0f0")
    model_info_label.pack(pady=10, padx=15)
    
    # Frame pour les boutons principaux
    main_buttons_frame = tk.Frame(detection_window)
    main_buttons_frame.pack(pady=20)
    
    def analyser_fichier():
        """Lance l'analyse d'un fichier CSV"""
        
        # Sélectionner le fichier à analyser
        analysis_file = filedialog.askopenfilename(
            title="Sélectionner un fichier CSV à analyser",
            filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")],
            initialdir="extraction"
        )
        
        if not analysis_file:
            return
        
        # Créer la fenêtre d'analyse
        analysis_window = Toplevel(detection_window)
        analysis_window.title("Analyse des Doublons & Homonymes")
        analysis_window.geometry("800x700")
        analysis_window.transient(detection_window)
        analysis_window.grab_set()
        
        # Titre
        tk.Label(analysis_window, text="Analyse des Doublons & Homonymes", 
                font=("Helvetica", 16, "bold")).pack(pady=10)
        
        # Informations sur le fichier
        tk.Label(analysis_window, text=f"Fichier analysé: {os.path.basename(analysis_file)}", 
                font=("Helvetica", 10, "italic")).pack(pady=5)
        
        # Notebook pour organiser les résultats
        results_notebook = ttk.Notebook(analysis_window)
        results_notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Onglet Résumé
        summary_frame = ttk.Frame(results_notebook)
        results_notebook.add(summary_frame, text="Résumé")
        
        # Onglet Doublons
        duplicates_frame = ttk.Frame(results_notebook)
        results_notebook.add(duplicates_frame, text="Doublons")
        
        # Onglet Homonymes
        homonyms_frame = ttk.Frame(results_notebook)
        results_notebook.add(homonyms_frame, text="Homonymes")
        
        # Barre de progression
        progress_var = tk.StringVar()
        progress_var.set("Préparation de l'analyse...")
        progress_label = tk.Label(analysis_window, textvariable=progress_var, 
                                 font=("Helvetica", 10))
        progress_label.pack(pady=5)
        
        progress_bar = ttk.Progressbar(analysis_window, mode='indeterminate')
        progress_bar.pack(pady=5, fill="x", padx=20)
        
        # Boutons d'action
        action_frame = tk.Frame(analysis_window)
        action_frame.pack(side="bottom", pady=10)
        
        def lancer_analyse():
            """Lance l'analyse dans un thread séparé"""
            def analysis_thread():
                global analysis_results
                
                try:
                    # Démarrer la barre de progression
                    progress_bar.start()
                    progress_var.set("Analyse en cours...")
                    
                    # Lancer l'analyse
                    analysis_results = load_and_analyze_csv(analysis_file, 'clustering_model.pkl')
                    
                    # Afficher les résultats dans l'onglet Résumé
                    summary_text = tk.Text(summary_frame, font=("Courier", 10), wrap="word")
                    summary_text.pack(fill="both", expand=True, padx=5, pady=5)
                    
                    summary = analysis_results['summary']
                    summary_content = f"""
RÉSUMÉ DE L'ANALYSE
{'='*50}

Publications analysées: {summary['total_publications']}
Auteurs uniques: {summary['unique_authors']}
Paires de doublons détectées: {summary['duplicate_pairs']}
Paires d'homonymes détectées: {summary['homonym_pairs']}

{'='*50}
Analyse terminée avec succès!
                    """
                    
                    summary_text.insert(tk.END, summary_content)
                    summary_text.config(state="disabled")
                    
                    # Afficher les doublons
                    if analysis_results['duplicate_cases']:
                        dup_tree = ttk.Treeview(duplicates_frame, 
                                              columns=('Auteur', 'Score', 'Titre1', 'Titre2', 'Années'), 
                                              show='headings')
                        dup_tree.heading('Auteur', text='Auteur')
                        dup_tree.heading('Score', text='Score')
                        dup_tree.heading('Titre1', text='Titre 1')
                        dup_tree.heading('Titre2', text='Titre 2')
                        dup_tree.heading('Années', text='Années')
                        
                        for case in analysis_results['duplicate_cases']:
                            dup_tree.insert('', 'end', values=(
                                case['author'],
                                f"{case['similarity_score']:.3f}",
                                case['title1'][:50] + "..." if len(case['title1']) > 50 else case['title1'],
                                case['title2'][:50] + "..." if len(case['title2']) > 50 else case['title2'],
                                f"{case['year1']} / {case['year2']}"
                            ))
                        
                        dup_tree.pack(fill="both", expand=True, padx=5, pady=5)
                    else:
                        tk.Label(duplicates_frame, text="Aucun doublon détecté", 
                                font=("Helvetica", 12)).pack(pady=50)
                    
                    # Afficher les homonymes
                    if analysis_results['homonym_cases']:
                        hom_tree = ttk.Treeview(homonyms_frame, 
                                              columns=('Auteur', 'Écart', 'Titre1', 'Titre2', 'Score'), 
                                              show='headings')
                        hom_tree.heading('Auteur', text='Auteur')
                        hom_tree.heading('Écart', text='Écart (ans)')
                        hom_tree.heading('Titre1', text='Titre 1')
                        hom_tree.heading('Titre2', text='Titre 2')
                        hom_tree.heading('Score', text='Score')
                        
                        for case in analysis_results['homonym_cases']:
                            hom_tree.insert('', 'end', values=(
                                case['author'],
                                f"{case['year_gap']}",
                                case['title1'][:50] + "..." if len(case['title1']) > 50 else case['title1'],
                                case['title2'][:50] + "..." if len(case['title2']) > 50 else case['title2'],
                                f"{case['similarity_score']:.3f}"
                            ))
                        
                        hom_tree.pack(fill="both", expand=True, padx=5, pady=5)
                    else:
                        tk.Label(homonyms_frame, text="Aucun homonyme détecté", 
                                font=("Helvetica", 12)).pack(pady=50)
                    
                    # Activer les boutons d'action
                    btn_traiter.config(state="normal")
                    btn_exporter.config(state="normal")
                    
                    progress_var.set("Analyse terminée avec succès!")
                    
                except Exception as e:
                    # Afficher l'erreur
                    error_text = tk.Text(summary_frame, font=("Courier", 10), wrap="word")
                    error_text.pack(fill="both", expand=True, padx=5, pady=5)
                    error_text.insert(tk.END, f"ERREUR lors de l'analyse:\n{str(e)}")
                    error_text.config(state="disabled")
                    
                    progress_var.set("Erreur lors de l'analyse")
                    
                finally:
                    progress_bar.stop()
            
            # Lancer dans un thread séparé
            thread = threading.Thread(target=analysis_thread)
            thread.start()
        
        def traiter_donnees():
            """Traite les données problématiques"""
            if not analysis_results:
                messagebox.showerror("Erreur", "Aucune analyse disponible.")
                return
            
            # Créer une fenêtre de traitement
            treatment_window = Toplevel(analysis_window)
            treatment_window.title("Traitement des Données")
            treatment_window.geometry("600x450")
            treatment_window.transient(analysis_window)
            treatment_window.grab_set()
            
            # Titre
            tk.Label(treatment_window, text="Traitement des Données Problématiques", 
                    font=("Helvetica", 14, "bold")).pack(pady=10)
            
            # Options de traitement
            treatment_frame = tk.Frame(treatment_window)
            treatment_frame.pack(fill="both", expand=True, padx=20, pady=10)
            
            # Variables pour les options
            remove_duplicates = tk.BooleanVar(value=True)
            flag_homonyms = tk.BooleanVar(value=True)
            
            # Checkboxes
            tk.Label(treatment_frame, text="Choisissez les actions à effectuer:", 
                    font=("Helvetica", 12, "bold")).pack(anchor="w", pady=(0, 10))
            
            tk.Checkbutton(treatment_frame, text="Supprimer les doublons détectés", 
                          variable=remove_duplicates, font=("Helvetica", 11)).pack(anchor="w", pady=2)
            
            tk.Checkbutton(treatment_frame, text="Marquer les homonymes (ajouter une colonne)", 
                          variable=flag_homonyms, font=("Helvetica", 11)).pack(anchor="w", pady=2)
            
            # Statistiques
            stats_frame = tk.Frame(treatment_frame, relief="ridge", bd=2, bg="#f8f8f8")
            stats_frame.pack(fill="x", pady=20)
            
            summary = analysis_results['summary']
            stats_text = f"""
Impact du traitement:
   • Doublons à supprimer: {summary['duplicate_pairs']} paires
   • Homonymes à marquer: {summary['homonym_pairs']} paires
            """
            
            tk.Label(stats_frame, text=stats_text, font=("Helvetica", 10), 
                    justify="left", bg="#f8f8f8").pack(pady=10, padx=10)
            
            # Boutons
            button_frame = tk.Frame(treatment_window)
            button_frame.pack(side="bottom", pady=10)
            
            def appliquer_traitement():
                """Applique le traitement sélectionné"""
                try:
                    # Charger les données originales
                    original_df = pd.read_csv(analysis_file)
                    processed_df = original_df.copy()
                    
                    # Supprimer les doublons
                    if remove_duplicates.get():
                        indices_to_remove = set()
                        for case in analysis_results['duplicate_cases']:
                            # Garder le premier, supprimer le second
                            indices_to_remove.add(case['index2'])
                        
                        processed_df = processed_df.drop(indices_to_remove).reset_index(drop=True)
                    
                    # Marquer les homonymes
                    if flag_homonyms.get():
                        processed_df['Homonyme_Potentiel'] = False
                        for case in analysis_results['homonym_cases']:
                            if case['index1'] < len(processed_df):
                                processed_df.loc[case['index1'], 'Homonyme_Potentiel'] = True
                            if case['index2'] < len(processed_df):
                                processed_df.loc[case['index2'], 'Homonyme_Potentiel'] = True
                    
                    # Sauvegarder le fichier traité
                    base_name = os.path.splitext(os.path.basename(analysis_file))[0]
                    processed_filename = f"{base_name}_traite.csv"
                    processed_path = os.path.join('extraction', processed_filename)
                    
                    processed_df.to_csv(processed_path, index=False)
                    
                    # Message de succès
                    messagebox.showinfo(
                        "Traitement terminé",
                        f"Données traitées avec succès!\n\n"
                        f"Fichier original: {len(original_df)} publications\n"
                        f"Fichier traité: {len(processed_df)} publications\n"
                        f"Publications supprimées: {len(original_df) - len(processed_df)}\n\n"
                        f"Sauvegardé dans: {processed_path}"
                    )
                    
                    treatment_window.destroy()
                    
                except Exception as e:
                    messagebox.showerror("Erreur", f"Erreur lors du traitement: {str(e)}")
            
            tk.Button(button_frame, text="Annuler", 
                     command=treatment_window.destroy, font=("Helvetica", 11),
                     width=12).pack(side="left", padx=5)
            
            tk.Button(button_frame, text="Appliquer le traitement", 
                     command=appliquer_traitement, font=("Helvetica", 11, "bold"),
                     bg="#4CAF50", fg="white", width=20).pack(side="right", padx=5)
        
        def exporter_resultats():
            """Exporte les résultats de l'analyse"""
            if not analysis_results:
                messagebox.showerror("Erreur", "Aucune analyse disponible.")
                return
            
            # Choisir le dossier d'exportation
            export_dir = filedialog.askdirectory(
                title="Choisir le dossier d'exportation",
                initialdir="extraction"
            )
            
            if export_dir:
                try:
                    exported_files = []
                    
                    # Exporter les doublons
                    if analysis_results['duplicate_cases']:
                        dup_df = pd.DataFrame(analysis_results['duplicate_cases'])
                        dup_path = os.path.join(export_dir, 'doublons_detectes.csv')
                        dup_df.to_csv(dup_path, index=False)
                        exported_files.append('doublons_detectes.csv')
                    
                    # Exporter les homonymes
                    if analysis_results['homonym_cases']:
                        hom_df = pd.DataFrame(analysis_results['homonym_cases'])
                        hom_path = os.path.join(export_dir, 'homonymes_detectes.csv')
                        hom_df.to_csv(hom_path, index=False)
                        exported_files.append('homonymes_detectes.csv')
                    
                    # Exporter le résumé
                    summary_path = os.path.join(export_dir, 'resume_analyse.txt')
                    with open(summary_path, 'w', encoding='utf-8') as f:
                        summary = analysis_results['summary']
                        f.write("RÉSUMÉ DE L'ANALYSE\n")
                        f.write("="*50 + "\n\n")
                        f.write(f"Publications analysées: {summary['total_publications']}\n")
                        f.write(f"Auteurs uniques: {summary['unique_authors']}\n")
                        f.write(f"Paires de doublons: {summary['duplicate_pairs']}\n")
                        f.write(f"Paires d'homonymes: {summary['homonym_pairs']}\n")
                    
                    exported_files.append('resume_analyse.txt')
                    
                    # Message de succès
                    files_list = '\n'.join([f"   • {f}" for f in exported_files])
                    messagebox.showinfo(
                        "Exportation terminée",
                        f"Résultats exportés avec succès:\n\n{files_list}\n\nDans le dossier:\n{export_dir}"
                    )
                    
                except Exception as e:
                    messagebox.showerror("Erreur", f"Erreur lors de l'exportation: {str(e)}")
        
        # Boutons d'action
        btn_analyser = tk.Button(action_frame, text="Lancer l'analyse", 
                                command=lancer_analyse, font=("Helvetica", 11, "bold"),
                                bg="#4CAF50", fg="white", width=15)
        btn_analyser.pack(side="left", padx=5)
        
        btn_traiter = tk.Button(action_frame, text="Traiter les données", 
                               command=traiter_donnees, font=("Helvetica", 11),
                               bg="#FF9800", fg="white", width=18, state="disabled")
        btn_traiter.pack(side="left", padx=5)
        
        btn_exporter = tk.Button(action_frame, text="Exporter résultats", 
                                command=exporter_resultats, font=("Helvetica", 11),
                                bg="#2196F3", fg="white", width=15, state="disabled")
        btn_exporter.pack(side="left", padx=5)
        
        btn_fermer = tk.Button(action_frame, text="Fermer", 
                              command=analysis_window.destroy, font=("Helvetica", 11),
                              width=10)
        btn_fermer.pack(side="right", padx=5)
        
        # Lancer automatiquement l'analyse
        lancer_analyse()
    
    def ouvrir_script_entrainement():
        """Ouvre une fenêtre d'information pour l'entraînement"""
        info_window = Toplevel(detection_window)
        info_window.title("Entraînement du Modèle")
        info_window.geometry("500x400")
        info_window.transient(detection_window)
        info_window.grab_set()
        
        # Titre
        tk.Label(info_window, text="Entraînement du Modèle", 
                font=("Helvetica", 16, "bold")).pack(pady=15)
        
        # Instructions
        instructions_text = """
Pour créer ou mettre à jour le modèle de clustering, 
vous devez utiliser le script d'entraînement dédié.

ÉTAPES À SUIVRE :

1. Fermez cette interface graphique

2. Ouvrez un terminal/invite de commandes

3. Naviguez vers le dossier du projet

4. Exécutez la commande :
   python train_model.py

5. Suivez les instructions pour :
   • Sélectionner un fichier CSV d'entraînement
   • Confirmer les paramètres
   • Attendre la fin de l'entraînement

6. Une fois terminé, relancez cette interface :
   python app.py

Le modèle sera alors disponible pour l'analyse.

RECOMMANDATIONS :

• Utilisez un fichier CSV avec des cas variés
• Minimum 500-1000 publications
• Données de qualité avec auteurs divers
        """
        
        text_widget = tk.Text(info_window, font=("Helvetica", 10), wrap="word",
                             relief="flat", bg="#f8f8f8", padx=10, pady=10)
        text_widget.pack(fill="both", expand=True, padx=15, pady=10)
        text_widget.insert("1.0", instructions_text)
        text_widget.config(state="disabled")
        
        # Bouton fermer
        tk.Button(info_window, text="Compris", command=info_window.destroy,
                 font=("Helvetica", 11, "bold"), bg="#4CAF50", fg="white",
                 width=15).pack(pady=15)
    
    # Affichage des boutons selon le statut du modèle
    if model_status == "PRÊT":
        btn_analyser = tk.Button(main_buttons_frame, text="Charger un fichier CSV et Analyser", 
                                command=analyser_fichier, font=("Helvetica", 14, "bold"),
                                bg="#4CAF50", fg="white", width=30, height=2)
        btn_analyser.pack(pady=10)
        
        btn_info_modele = tk.Button(main_buttons_frame, text="Comment ré-entraîner le modèle ?", 
                                   command=ouvrir_script_entrainement, font=("Helvetica", 11),
                                   bg="#FF9800", fg="white", width=25)
        btn_info_modele.pack(pady=5)
        
    else:
        btn_info_entrainement = tk.Button(main_buttons_frame, text="Comment entraîner le modèle ?", 
                                         command=ouvrir_script_entrainement, font=("Helvetica", 14, "bold"),
                                         bg="#2196F3", fg="white", width=30, height=2)
        btn_info_entrainement.pack(pady=10)
        
        btn_analyser_disabled = tk.Button(main_buttons_frame, text="Analyser un fichier CSV", 
                                         command=lambda: messagebox.showwarning("Modèle requis", 
                                                                                "Veuillez d'abord entraîner un modèle avec train_model.py"), 
                                         font=("Helvetica", 11),
                                         bg="#9E9E9E", fg="white", width=25, state="disabled")
        btn_analyser_disabled.pack(pady=5)
    
    # Bouton fermer
    btn_fermer = tk.Button(detection_window, text="Fermer", 
                          command=detection_window.destroy, font=("Helvetica", 11),
                          width=15)
    btn_fermer.pack(side="bottom", pady=10)

def create_detection_tab():
    """Crée l'onglet de détection des doublons et homonymes"""
    
    # Créer le frame pour l'onglet détection
    global frame_detection
    frame_detection = ttk.Frame(notebook)
    frame_detection.pack(fill="both", expand=True)
    
    # Titre
    label_detection = tk.Label(
        frame_detection,
        text="Détection Doublons & Homonymes\n"
             "Modèle de clustering intelligent pour identifier les problèmes dans vos extractions",
        font=("Helvetica", 16)
    )
    label_detection.pack(pady=20)
    
    # Séparateur
    ttk.Separator(frame_detection, orient="horizontal").pack(fill="x", padx=20, pady=10)
    
    # Informations sur le modèle
    info_text = """
MODÈLE DE CLUSTERING INTELLIGENT :

• Détection automatique des doublons (publications identiques référencées plusieurs fois)
• Identification des homonymes (même nom, personnes différentes)
• Algorithmes de machine learning (DBSCAN, Hierarchical Clustering)
• Analyse sur vos données spécifiques

FONCTIONNALITÉS :

• Analyse automatique de fichiers CSV
• Interface détaillée avec onglets (Résumé, Doublons, Homonymes)
• Traitement automatique des données problématiques
• Exportation des résultats d'analyse

WORKFLOW RECOMMANDÉ :

1. Entraîner le modèle avec train_model.py (une seule fois)
2. Analyser vos fichiers CSV avec le modèle entraîné
3. Consulter les résultats détaillés par catégorie
4. Traiter automatiquement les données problématiques
5. Exporter les résultats ou utiliser les fichiers nettoyés

ENTRAÎNEMENT DU MODÈLE :

Pour créer ou mettre à jour le modèle, utilisez :
python train_model.py

Ce script séparé vous permet de choisir vos données d'entraînement
et de créer un modèle optimisé pour vos besoins.
    """
    
    info_label = tk.Label(frame_detection, text=info_text, 
                         font=("Helvetica", 11), justify="left",
                         relief="ridge", bd=1, bg="#f8f8f8")
    info_label.pack(pady=10, padx=20, fill="x")
    
    # Bouton principal
    btn_detection = tk.Button(
        frame_detection, 
        text="Ouvrir la Détection Doublons & Homonymes", 
        font=("Helvetica", 14, "bold"),
        command=detection_doublons_homonymes,
        bg="#9C27B0", 
        fg="white",
        width=35,
        height=2
    )
    btn_detection.pack(pady=20)
    
    # Informations techniques
    tech_text = """
INFORMATIONS TECHNIQUES :

• Utilise scikit-learn pour le machine learning
• TF-IDF pour l'analyse des titres
• Normalisation et réduction de dimensionnalité (PCA)
• Matrice de similarité personnalisée pour les auteurs
• Modèle persistant et réutilisable (clustering_model.pkl)

CONSEILS :

• Entraînez le modèle sur un fichier CSV avec des cas variés
• Plus le fichier d'entraînement est grand, meilleur est le modèle
• Le modèle s'améliore avec des données de qualité
• Testez sur différents types de publications (articles, thèses, etc.)
    """
    
    tech_label = tk.Label(frame_detection, text=tech_text, 
                         font=("Helvetica", 10), justify="left",
                         fg="gray")
    tech_label.pack(pady=10, padx=20, fill="x")

def generate_graphs_thread():
    """
    Graph generation with parallelization and single CSV reading
    
    Generates all visualization graphs using ThreadPoolExecutor for improved performance
    """
    
    try:
        start_time = time.time()
        print("Starting graph generation...")
        
        # Get absolute paths for directories
        base_path = os.path.dirname(os.path.abspath(__file__))
        html_dir = os.path.join(base_path, 'html')
        png_dir = os.path.join(base_path, 'png')
        
        # Create directories explicitly
        os.makedirs(html_dir, exist_ok=True)
        os.makedirs(png_dir, exist_ok=True)
        print(f"Directories created: {html_dir} and {png_dir}")
        
        # Pre-load CSV data once instead of reading it 10 times
        print("Loading CSV data...")
        global shared_dataframe
        shared_dataframe = pd.read_csv(current_csv_file)
        
        # Prepare graph tasks with separated HTML and PNG generation
        graph_functions = [
            (plot_publications_by_year, "pubs_by_year"),
            (plot_document_types, "type_distribution"),
            (plot_keywords, "keywords_distribution"),
            (plot_top_domains, "domain_distribution"),
            (plot_publications_by_author, "top_authors"),
            (plot_structures_stacked, "structures_stacked"),
            (plot_publications_trends, "publication_trends"),
            (plot_employer_distribution, "employer_distribution"),
            (plot_theses_hdr_by_year, "theses_hdr_by_year"),
            (plot_theses_keywords_wordcloud, "theses_keywords_wordcloud")
        ]
        
        # Wrapper function using pre-loaded data
        def execute_graph_function_optimized(func, filename_base):
            """Execute a graph generation function with pre-loaded data"""
            try:
                html_path = os.path.join(html_dir, f"{filename_base}.html")
                png_path = os.path.join(png_dir, f"{filename_base}.png")
                
                # Use current_csv_file but the data is already loaded in memory by pandas
                func(current_csv_file, output_html=html_path, output_png=png_path)
                
                # Quick file existence check
                if os.path.exists(html_path) and os.path.exists(png_path):
                    return f"SUCCESS: {func.__name__}"
                else:
                    missing = []
                    if not os.path.exists(html_path):
                        missing.append("HTML")
                    if not os.path.exists(png_path):
                        missing.append("PNG")
                    return f"WARNING: {func.__name__} - missing files ({', '.join(missing)})"
                    
            except Exception as e:
                return f"ERROR: {func.__name__} failed - {str(e)}"
        
        # Thread pool size for better parallelization
        max_workers = min(12, (os.cpu_count() or 1) + 4)  
        
        success_count = 0
        total_tasks = len(graph_functions)
                
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(execute_graph_function_optimized, func, filename_base): func.__name__
                for func, filename_base in graph_functions
            }
            
            # Wait for completion of all tasks
            for i, future in enumerate(as_completed(futures), 1):
                result = future.result()
                
                # Count successes (no print here)
                if "SUCCESS:" in result:
                    success_count += 1
                elif "ERROR:" in result or "WARNING:" in result:
                    # Only print if there's an error or warning
                    print(f"[{i}/{total_tasks}] {result}")
        
        # Batch file verification instead of individual checks
        all_files_exist = True
        expected_files = []
        for func, filename_base in graph_functions:
            expected_files.extend([
                os.path.join(html_dir, f"{filename_base}.html"),
                os.path.join(png_dir, f"{filename_base}.png")
            ])
        
        missing_files = [f for f in expected_files if not os.path.exists(f)]
        
        if missing_files:
            error_msg = f"Missing files after generation:\n" + "\n".join([os.path.basename(f) for f in missing_files])
            print(error_msg)
            raise Exception(error_msg)
        
        # Print success message for graph generation
        print("Graph generation completed successfully")
            
        # Dashboard generation
        print("Generating dashboard...")
        global dashboard_file
        dashboard_file = create_dashboard()
        
        elapsed_time = time.time() - start_time
        print("Generation completed successfully")
        
        # Clean up global variable
        if 'shared_dataframe' in globals():
            del shared_dataframe
        
        # Success message with performance info
        success_message = (f"Graphs generated successfully!\n\n"
                          f"Success: {success_count}/{total_tasks} graphs created\n"
                          f"Execution time: {elapsed_time:.2f} seconds\n"
                          f"Threads used: {max_workers}\n"
                          f"Files saved in:\n"
                          f"   • {html_dir}\n"
                          f"   • {png_dir}")
        
        messagebox.showinfo("Success", success_message)
        
        # Display buttons
        btn_afficher_graphiques.pack(pady=5)
        btn_generer_rapport.pack(pady=5)
        
    except Exception as e:
        error_msg = f"Error during graph generation:\n{str(e)}"
        print(f"ERROR: {error_msg}")
        messagebox.showerror("Error", error_msg)
        
        # Clean up global variable in case of error
        if 'shared_dataframe' in globals():
            del shared_dataframe
        
        # Diagnostic in case of error
        print("\nDIAGNOSTIC:")
        print(f"   • CSV file: {current_csv_file}")
        print(f"   • HTML directory exists: {os.path.exists(html_dir) if 'html_dir' in locals() else 'Not defined'}")
        print(f"   • PNG directory exists: {os.path.exists(png_dir) if 'png_dir' in locals() else 'Not defined'}")

def generer_graphiques():
    """Generate graphs from selected CSV file"""
    global current_csv_file
    current_csv_file = filedialog.askopenfilename(
        title="Sélectionner le fichier extrait",
        filetypes=[("CSV files", "*.csv")]
    )
    if current_csv_file:
        threading.Thread(target=generate_graphs_thread).start()

def afficher_graphiques():
    """Display generated graphs in browser"""
    if dashboard_file:
        webbrowser.open('file://' + os.path.realpath(dashboard_file))
    else:
        messagebox.showerror("Erreur", "Aucun graphique n'a été généré.")

def generer_rapport():
    """Generate report in PDF or LaTeX format"""
    rapport_window = Toplevel(root)
    rapport_window.title("Générer un rapport")
    rapport_window.geometry("300x150")

    choix_format = tk.StringVar(value="")  # Variable defined in same scope
    tk.Label(rapport_window, text="Choisissez le format du rapport :", font=("Helvetica", 12)).pack(pady=10)
    tk.Radiobutton(rapport_window, text="PDF", variable=choix_format, value="PDF", font=("Helvetica", 10)).pack()
    tk.Radiobutton(rapport_window, text="LaTeX", variable=choix_format, value="LaTeX", font=("Helvetica", 10)).pack()

    def valider_choix():
        format_choisi = choix_format.get()
        nom_fichier_csv = os.path.basename(current_csv_file).replace(".csv", "")
    
        if format_choisi == "PDF":
            generate_pdf_report("", nom_fichier_csv)
            messagebox.showinfo("Rapport PDF", f"Le rapport PDF a été généré avec succès.")
        elif format_choisi == "LaTeX":
             generate_latex_report(nom_fichier_csv)
             messagebox.showinfo("Rapport LaTeX", f"Le rapport LaTeX a été généré avec succès.")
        else:
            messagebox.showerror("Erreur", "Veuillez choisir un format valide.")
        rapport_window.destroy()

    # Validation button
    btn_valider = tk.Button(rapport_window, text="Valider", command=valider_choix)
    btn_valider.pack(pady=10)

# Main interface
root = tk.Tk()
root.title("Outil d'Extraction et Analyse - API HAL")
root.geometry("700x600")

# Load settings at startup
load_settings()

# Menu bar
menubar = tk.Menu(root)
root.config(menu=menubar)

# Configuration menu
config_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="Configuration", menu=config_menu)
config_menu.add_command(label="Sensibilité de correspondance...", command=open_settings)
config_menu.add_separator()

def update_config_display():
    """Update configuration label after modification"""
    config_info_label.config(text=update_config_label())

def show_current_config():
    """Display information about current configuration"""
    level_name = get_level_from_threshold(current_threshold)
    messagebox.showinfo("Configuration actuelle", 
                       f"Sensibilité de correspondance :\n"
                       f"Niveau : {level_name.title()}\n"
                       f"Distance Levenshtein : {current_threshold}\n\n"
                       f"Cette configuration est utilisée pour toutes les extractions.")

config_menu.add_command(label="Afficher la configuration actuelle", command=show_current_config)

# Tabs with Notebook
notebook = ttk.Notebook(root)
notebook.pack(expand=1, fill="both")

# Extraction Frame
frame_extraction = ttk.Frame(notebook)
frame_extraction.pack(fill="both", expand=True)

label_accueil = tk.Label(
    frame_extraction,
    text="Bienvenue sur la section Extraction ! \nVous pouvez charger un fichier d'entrée et extraire à partir de celui-ci.",
    font=("Helvetica", 16)
)
label_accueil.pack(pady=10)

def update_config_label():
    """Generate current configuration label text"""
    level_name = get_level_from_threshold(current_threshold)
    return f"Configuration actuelle : {level_name.title()} (distance = {current_threshold})"

# Configuration information label
config_info_label = tk.Label(frame_extraction, text=update_config_label(), 
                            font=("Helvetica", 9, "italic"), fg="gray")
config_info_label.pack(pady=(0, 10))

btn_charger = tk.Button(frame_extraction, text="Charger un fichier CSV", font=("Helvetica", 12), command=charger_csv)
btn_charger.pack(pady=5)

btn_extraire = tk.Button(frame_extraction, text="Extraire toutes les données", font=("Helvetica", 12), command=extraire_toutes_les_donnees)
btn_filtrer = tk.Button(frame_extraction, text="Appliquer des filtres d'extraction", font=("Helvetica", 12), command=appliquer_filtres)

# Analysis Frame
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

# Create detection tab first (but don't add it to notebook yet)
create_detection_tab()

# Add tabs in the correct order: Extraction, Analysis, then Detection
notebook.add(frame_extraction, text="Extraction")
notebook.add(frame_analyse, text="Analyse")
notebook.add(frame_detection, text="Détection Doublons & Homonymes")

# Launch application
if __name__ == "__main__":
    root.mainloop()