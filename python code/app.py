# -*- coding: utf-8 -*-

# app.py


import tkinter as tk
import json
import os
from tkinter import filedialog, messagebox, Toplevel, Listbox, MULTIPLE, ttk
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import webbrowser
from hal_data import get_hal_data, extract_author_id_with_candidates
from mapping import list_domains, list_types
from utils import generate_filename
from config import get_threshold_from_level, get_level_from_threshold, list_sensitivity_levels, DEFAULT_THRESHOLD
from dashboard_generator import create_dashboard
from report_generator_app import generate_pdf_report, generate_latex_report
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
    plot_temporal_evolution_by_team,
)
from detection_doublons_homonymes import DuplicateHomonymDetector
from integration import detection_doublons_homonymes

# Global variables to store the loaded CSV file path
current_csv_file = None
dashboard_file = None

# Global variables for data
scientists_df = None
fichier_charge = False

# Global variables to manage extraction progress display
message_label_extraction = None  
progress_bar = None

# Id verification
last_generated_csv = None  
btn_verifier_id = None

# Global variables for configuration
current_threshold = DEFAULT_THRESHOLD
settings_file = "app_settings.json"

# Global variables for detection
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
    
    # Buttons
    btn_frame = tk.Frame(button_frame)
    btn_frame.pack(pady=10)
    
    tk.Button(btn_frame, text="Annuler", command=settings_window.destroy,
              font=("Helvetica", 11), width=12).pack(side="left", padx=5)
    
    tk.Button(btn_frame, text="Réinitialiser", command=reset_settings,
              font=("Helvetica", 11), width=12).pack(side="left", padx=5)
    
    tk.Button(btn_frame, text="Valider", command=apply_settings,
              font=("Helvetica", 11, "bold"), bg="#4CAF50", fg="white", width=12).pack(side="left", padx=5)

def charger_csv_identifiants():
    """Load CSV file for identifier extraction"""
    fichier_csv = filedialog.askopenfilename(
        title="Sélectionner un fichier CSV pour extraction d'identifiants",
        filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")]
    )
    if fichier_csv:
        try:
            global scientists_df, fichier_charge
            scientists_df = pd.read_csv(fichier_csv, encoding='utf-8-sig')
            fichier_charge = True
            
            # Store filename for later use
            root.current_csv_filename = os.path.basename(fichier_csv)
            
            messagebox.showinfo("Succès", f"Fichier chargé : {fichier_csv}\n"
                              f"Nombre de scientifiques : {len(scientists_df)}")
            btn_extraire_id.config(state="normal")
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger le fichier CSV : {e}")

def charger_csv_publications():
    """Load CSV file with IdHAL for publication extraction - accepts files with at least 'title' column"""
    fichier_csv = filedialog.askopenfilename(
        title="Select CSV file with IdHAL",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )
    if fichier_csv:
        try:
            global scientists_df, fichier_charge
            scientists_df = pd.read_csv(fichier_csv, encoding='utf-8-sig')
            
            # Check if 'title' column exists (minimum requirement)
            has_title = 'title' in scientists_df.columns
            
            if not has_title:
                messagebox.showerror("Error", 
                    "The file must contain at least the 'title' column.\n\n"
                    "The 'title' column should contain the full name of each author.")
                return
            
            # Check if 'nom' and 'prenom' columns exist
            has_nom_prenom = 'nom' in scientists_df.columns and 'prenom' in scientists_df.columns
            
            # If 'nom' and 'prenom' don't exist, create them by parsing 'title'
            if not has_nom_prenom:
                def parse_title(title_str):
                    """
                    Parse a title string to extract first name and last name.
                    
                    Convention: 
                    - First name: starts with uppercase, rest in lowercase (may be compound with hyphens)
                    - Last name: completely in uppercase
                                        
                    Args:
                        title_str: Full name string
                        
                    Returns:
                        tuple: (prenom, nom)
                    """
                    if not title_str or not isinstance(title_str, str):
                        return ('', '')
                    
                    title_str = title_str.strip()
                    if not title_str:
                        return ('', '')
                    
                    # Split the title into words
                    words = title_str.split()
                    
                    if len(words) == 0:
                        return ('', '')
                    elif len(words) == 1:
                        # Only one word: consider it as last name if all uppercase, otherwise as first name
                        if words[0].isupper():
                            return ('', words[0])
                        else:
                            return (words[0], '')
                    
                    # Find the boundary between first name and last name
                    # Last name parts are fully uppercase
                    prenom_parts = []
                    nom_parts = []
                    
                    for word in words:
                        # Check if the word is fully uppercase (excluding hyphens and apostrophes)
                        word_letters = ''.join(c for c in word if c.isalpha())
                        
                        if word_letters and word_letters.isupper():
                            # This word is part of the last name
                            nom_parts.append(word)
                        else:
                            # This word is part of the first name
                            # Only add to prenom if we haven't started collecting nom yet
                            if not nom_parts:
                                prenom_parts.append(word)
                            else:
                                nom_parts.append(word)
                    
                    prenom = ' '.join(prenom_parts)
                    nom = ' '.join(nom_parts)
                    
                    return (prenom, nom)
                
                # Apply parsing to all rows
                scientists_df[['prenom', 'nom']] = scientists_df['title'].apply(
                    lambda x: pd.Series(parse_title(x))
                )
                
                # Count how many were successfully parsed
                parsed_count = scientists_df[
                    (scientists_df['nom'] != '') & (scientists_df['prenom'] != '')
                ].shape[0]
                
                messagebox.showinfo("Information",
                    f"Columns 'nom' and 'prenom' created from 'title' column.\n\n"
                    f"Successfully parsed: {parsed_count}/{len(scientists_df)} authors\n\n"
                    f"Parsing rule:\n"
                    f"  • First name: Mixed case\n"
                    f"  • Last name: UPPERCASE")
            
            # Check if IdHAL column exists
            has_idhal = 'IdHAL' in scientists_df.columns
            
            if not has_idhal:
                messagebox.showwarning("Warning", 
                    "The file does not contain an 'IdHAL' column.\n"
                    "Extraction will use full names only (less precise).")
            
            fichier_charge = True
            root.current_csv_filename = os.path.basename(fichier_csv)
            
            # Display info about available columns
            info_msg = f"File loaded: {fichier_csv}\n"
            info_msg += f"Number of scientists: {len(scientists_df)}\n\n"
            info_msg += "Detected columns:\n"
            info_msg += "  • title: ✓\n"
            info_msg += f"  • nom + prenom: {'✓' if has_nom_prenom else '✓ (auto-generated from title)'}\n"
            info_msg += f"  • IdHAL: {'✓' if has_idhal else '✗'}"
            
            messagebox.showinfo("Success", info_msg)
            btn_extraire.config(state="normal")
            btn_filtrer.config(state="normal")
            
        except Exception as e:
            messagebox.showerror("Error", f"Unable to load CSV file: {e}")
      
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

def extraire_identifiants():
    """Extract HAL identifiers with summary"""
    afficher_recapitulatif_extraction_id()

def afficher_recapitulatif_extraction_id():
    """
    Display a summary for identifier extraction
    """
    # Build summary message
    message = "Vous avez choisi d'extraire les identifiants HAL"
    details = "Extraction des identifiants HAL pour tous les scientifiques du fichier"
    
    # Confirmation window
    recap_window = tk.Toplevel(root)
    recap_window.title("Récapitulatif de l'extraction des identifiants")
    recap_window.geometry("500x300")
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
    
    def confirmer_extraction_id():
        recap_window.destroy()
        # Start identifier extraction
        init_extraction_widgets()
        message_label_extraction.config(text="Extraction des identifiants en cours... : 0%")
        progress_bar.pack(pady=5)
        progress_bar["value"] = 0
        root.update_idletasks()
        
        # Start extraction
        extraction_identifiants()
    
    def annuler_extraction():
        recap_window.destroy()
    
    # Buttons
    tk.Button(button_frame, text="Annuler", command=annuler_extraction,
              font=("Helvetica", 11), width=12).pack(side="left", padx=10)
    
    tk.Button(button_frame, text="Confirmer et lancer", command=confirmer_extraction_id,
              font=("Helvetica", 11, "bold"), bg="#4CAF50", fg="white", width=18).pack(side="left", padx=10)

def extraction_identifiants():
    """
    Extract identifiers in CSV format.
    """
    global message_label_extraction, progress_bar, last_generated_csv

    init_extraction_widgets()  
    message_label_extraction.config(text="Extracting identifiers... 0/0")
    progress_bar.pack(pady=5)
    progress_bar["value"] = 0
    root.update_idletasks()

    # Disable buttons during extraction
    btn_extraire.config(state="disabled")
    btn_filtrer.config(state="disabled")
    btn_extraire_id.config(state="disabled")
    btn_charger_identifiants.config(state="disabled")
    if btn_verifier_id:
        btn_verifier_id.config(state="disabled")

    def extraction_task():
        global last_generated_csv
        
        # Create result DataFrame
        result_df = scientists_df.copy()
        
        # Initialize columns
        result_df['IdHAL'] = ''
        result_df['Candidats'] = ''
        result_df['Details'] = ''
        result_df['ID_Atypique'] = ''
        
        total_rows = len(scientists_df)
        progress_bar["maximum"] = total_rows
        completed_count = 0
        parasite_count = 0

        with ThreadPoolExecutor(max_workers=100) as executor:
            future_to_index = {
                executor.submit(extract_author_id_with_candidates, 
                              row.get('title', ''), 
                              row.get('nom', ''), 
                              row.get('prenom', ''),
                              threshold=current_threshold): index 
                for index, row in scientists_df.iterrows()
            }
            
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    id_result = future.result()
                    
                    # Check if id_result is a dict
                    if isinstance(id_result, dict):
                        # Extract dictionary values
                        result_df.at[index, 'IdHAL'] = id_result.get('IdHAL', ' ')
                        result_df.at[index, 'Candidats'] = id_result.get('Candidats', '')
                        result_df.at[index, 'Details'] = id_result.get('Details', '{}')
                        result_df.at[index, 'ID_Atypique'] = id_result.get('ID_Atypique', 'NON')
                    else:
                        # If it's a string, process it
                        result_df.at[index, 'IdHAL'] = str(id_result) if id_result != "Id non disponible" else ' '
                        result_df.at[index, 'Candidats'] = ''
                        result_df.at[index, 'Details'] = '{}'
                        result_df.at[index, 'ID_Atypique'] = 'NON'
                    
                    # Count atypical IDs
                    if result_df.at[index, 'ID_Atypique'] == 'OUI':
                        parasite_count += 1
                    
                except Exception as e:
                    result_df.at[index, 'IdHAL'] = " "
                    result_df.at[index, 'Candidats'] = ""
                    result_df.at[index, 'Details'] = "{}"
                    result_df.at[index, 'ID_Atypique'] = "NON"
                    print(f"Error for index {index}: {str(e)}")
                
                completed_count += 1
                root.after(0, lambda: progress_bar.step(1))
                root.after(0, lambda c=completed_count, t=total_rows: 
                          message_label_extraction.config(text=f"Extracting identifiers... {c}/{t}"))

        # Save results
        extraction_directory = create_extraction_folder()
        
        if hasattr(root, 'current_csv_filename'):
            base_filename = os.path.splitext(root.current_csv_filename)[0]
        else:
            base_filename = "extraction"
        
        filename = f"{base_filename}_hal_id.csv"
        output_path = os.path.join(extraction_directory, filename)
        last_generated_csv = output_path
        
        result_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        root.after(0, lambda: message_label_extraction.config(text="Identifier extraction complete."))
        
        # Customized message
        if parasite_count > 0:
            message = (f"CSV file: {output_path}\n\n"
                      f"WARNING: {parasite_count} atypical identifier(s) detected\n"
                      f"(IDs not resembling the name/surname)\n\n"
                      f"It is STRONGLY RECOMMENDED to verify these identifiers\n"
                      f"before launching the publication extraction.\n\n"
                      f"Use the button '3. Verify extracted identifiers'")
        else:
            message = (f"CSV file: {output_path}\n\n"
                      f"No atypical identifiers detected.\n"
                      f"You can proceed with publication extraction.")
        
        root.after(0, lambda: messagebox.showinfo("Extraction Complete", message))

        # Re-enable buttons
        root.after(0, lambda: btn_extraire.config(state="normal"))
        root.after(0, lambda: btn_filtrer.config(state="normal"))
        root.after(0, lambda: btn_extraire_id.config(state="normal"))
        root.after(0, lambda: btn_charger_identifiants.config(state="normal"))
        
        # Enable verification button
        if btn_verifier_id:
            root.after(0, lambda: btn_verifier_id.config(state="normal"))
        
        root.after(0, progress_bar.pack_forget)
        root.after(0, message_label_extraction.pack_forget)

    # Launch extraction in separate thread
    thread = threading.Thread(target=extraction_task)
    thread.start()

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
    global message_label_extraction, progress_bar
    if message_label_extraction is None:
        message_label_extraction = tk.Label(frame_extraction, text="Extraction en cours... : 0%", font=("Helvetica", 12))
        message_label_extraction.pack(pady=5)

    if progress_bar is None:
        progress_bar = ttk.Progressbar(frame_extraction, orient="horizontal", length=500, mode="determinate")
        progress_bar.pack(pady=5)
    else:
        progress_bar.pack(pady=5)
        
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
    Main data extraction function using IdHAL (primary) or fullname (fallback)
    Extracts publications based on HAL identifiers from CSV file
    
    Args:
        periode (str): Time period filter
        types (list): Document types filter  
        domaines (list): Domains filter
        
    Runs extraction in separate thread with progress tracking
    """
    global message_label_extraction, progress_bar

    init_extraction_widgets()  

    # Immediate update to show message and progress bar
    message_label_extraction.config(text="Extraction en cours... 0/0")
    progress_bar.pack(pady=5)
    progress_bar["value"] = 0
    root.update_idletasks()

    # Disable buttons during extraction
    btn_extraire.config(state="disabled")
    btn_filtrer.config(state="disabled")
    btn_charger_publications.config(state="disabled")

    def extraction_task():
        all_results = pd.DataFrame()
        total_rows = len(scientists_df)
        progress_bar["maximum"] = total_rows
        
        completed_count = 0

        with ThreadPoolExecutor(max_workers=100) as executor:
            # Create all futures at once before the executor context closes
            future_to_index = {}
            
            for index, row in scientists_df.iterrows():
                # Get author information from CSV
                nom = row.get('nom', '')
                prenom = row.get('prenom', '')
                title = row.get('title', '')
                author_id = row.get('IdHAL', '')
                
                # Submit task with author_id parameter
                future = executor.submit(
                    get_hal_data, 
                    nom=nom,
                    prenom=prenom, 
                    title=title if title else None,
                    author_id=author_id if author_id and author_id.strip() and author_id != " " else None,
                    period=periode, 
                    domain_filter=domaines, 
                    type_filter=types,
                    threshold=current_threshold
                )
                future_to_index[future] = index
            
            # Process completed futures
            for future in as_completed(future_to_index):
                result = future.result()
                all_results = pd.concat([all_results, result], ignore_index=True)
                
                # Progress bar 
                completed_count += 1
                root.after(0, lambda: progress_bar.step(1))
                root.after(0, lambda c=completed_count, t=total_rows: 
                          message_label_extraction.config(text=f"Extraction en cours... {c}/{t}"))

        # End extraction and save results
        extraction_directory = create_extraction_folder()
        filename = generate_filename(periode, "_".join(domaines) if domaines else None, 
                                   "_".join(types) if types else None)
        output_path = os.path.join(extraction_directory, filename)
        all_results.to_csv(output_path, index=False, encoding='utf-8-sig')
        root.after(0, lambda: message_label_extraction.config(text="Extraction terminée."))
        root.after(0, lambda: messagebox.showinfo("Extraction terminée", 
            f"Les résultats ont été sauvegardés dans : {output_path}"))

        # Re-enable buttons after extraction
        root.after(0, lambda: btn_extraire.config(state="normal"))
        root.after(0, lambda: btn_filtrer.config(state="normal"))
        root.after(0, lambda: btn_charger_publications.config(state="normal"))
        root.after(0, progress_bar.pack_forget)
        root.after(0, message_label_extraction.pack_forget)

    # Start extraction in separate thread
    thread = threading.Thread(target=extraction_task)
    thread.start()
    
def verifier_identifiants():
    """
    Ouvre un FRAME de vérification dans l'application principale.
    """
    global last_generated_csv
    
    if not last_generated_csv or not os.path.exists(last_generated_csv):
        response = messagebox.askyesno(
            "Fichier non trouvé",
            "Aucun fichier d'extraction récent trouvé.\n\n"
            "Voulez-vous sélectionner un fichier CSV manuellement ?"
        )
        if response:
            csv_file = filedialog.askopenfilename(
                title="Sélectionner le fichier CSV avec IdHAL",
                filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")]
            )
            if csv_file:
                last_generated_csv = csv_file
            else:
                return
        else:
            return
    
    # Créer le frame de vérification dans l'onglet actuel
    create_verification_frame(last_generated_csv)

def create_verification_frame(csv_file):
    """
    Create an integrated verification frame for identifier validation.
    Accepts CSV files with either (nom+prenom) OR (title) columns.
    
    The verification process:
    - Displays problematic cases (parasite IDs or multiple candidates)
    - Allows manual selection of alternative identifiers
    - Saves the COMPLETE file (all authors, not just verified ones)
    
    Args:
        csv_file (str): Path to the CSV file containing extracted identifiers
    """
    # Create a tab for verification
    frame_verification = ttk.Frame(notebook)
    notebook.add(frame_verification, text="✓ Verification IdHAL")
    notebook.select(frame_verification)
    
    # Create scrollable canvas
    canvas = tk.Canvas(frame_verification, highlightthickness=0)
    scrollbar_y = ttk.Scrollbar(frame_verification, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar_y.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar_y.pack(side="right", fill="y")

    # Load the CSV file
    try:
        df = pd.read_csv(csv_file, encoding='utf-8-sig')
        
        # Check for required columns (accept title OR nom+prenom)
        has_title = 'title' in df.columns
        has_nom_prenom = 'nom' in df.columns and 'prenom' in df.columns
        
        if not has_title and not has_nom_prenom:
            messagebox.showerror("Error", 
                "The file must contain either:\n"
                "  • Column 'title'\n"
                "  • OR columns 'nom' + 'prenom'")
            notebook.forget(frame_verification)
            return
        
        # Check for IdHAL column
        if 'IdHAL' not in df.columns:
            messagebox.showerror("Error", "Missing 'IdHAL' column in CSV file")
            notebook.forget(frame_verification)
            return
        
    except Exception as e:
        messagebox.showerror("Error", f"Unable to load file:\n{str(e)}")
        notebook.forget(frame_verification)
        return
    
    # Identify problematic rows
    problematic_rows = identify_problematic_rows(df)
    
    # If no problems detected, still offer manual verification option
    if not problematic_rows:
        response = messagebox.askyesno("No Problems Detected",
            f"All {len(df)} extracted identifiers appear correct.\n\n"
            "Would you still like to verify them manually?")
        
        if not response:
            notebook.forget(frame_verification)
            return
        else:
            # Display all authors with an IdHAL
            problematic_rows = [
                i for i, row in df.iterrows() 
                if str(row.get('IdHAL', '') or '').strip() not in ['', ' ', 'NONE', 'nan']
            ]
            
            if not problematic_rows:
                messagebox.showinfo("Information", "No identifiers found in the file.")
                notebook.forget(frame_verification)
                return
    
    # Control variables
    current_index = [0]
    modified_rows = set()
        
    # ===== HEADER =====
    top_frame = tk.Frame(scrollable_frame, bg="#2c3e50", padx=10, pady=10)
    top_frame.pack(fill="x", side="top")
    
    title_label = tk.Label(top_frame, 
        text="HAL Identifier Verification",
        font=("Helvetica", 16, "bold"),
        bg="#2c3e50", fg="white")
    title_label.pack()
    
    stats_label = tk.Label(top_frame,
        text=f"Total: {len(df)} | To verify: {len(problematic_rows)} | Modified: 0",
        font=("Helvetica", 10),
        bg="#2c3e50", fg="#ecf0f1")
    stats_label.pack(pady=(10, 0))
    
    # ===== PROGRESS =====
    progress_frame = tk.Frame(scrollable_frame, padx=10, pady=5)
    progress_frame.pack(fill="x")
    
    progress_label = tk.Label(progress_frame,
        text=f"Author 1 of {len(problematic_rows)}",
        font=("Helvetica", 11, "bold"))
    progress_label.pack()
    
    progress_bar_verif = ttk.Progressbar(progress_frame, 
        mode='determinate', length=600)
    progress_bar_verif["maximum"] = len(problematic_rows)
    progress_bar_verif["value"] = 1
    progress_bar_verif.pack(pady=5)
    
    ttk.Separator(scrollable_frame, orient="horizontal").pack(fill="x", pady=5)
    
    # ===== MAIN CONTENT =====
    main_frame = tk.Frame(scrollable_frame, padx=20, pady=10)
    main_frame.pack(fill="both", expand=True)
    
    # Author info frame
    author_frame = tk.LabelFrame(main_frame, text="Author Information",
        font=("Helvetica", 12, "bold"), padx=10, pady=10)
    author_frame.pack(fill="x", pady=(0, 10))
    
    author_info_frame = tk.Frame(author_frame)
    author_info_frame.pack(fill="x")
    
    # Display identity (title OR nom+prenom)
    tk.Label(author_info_frame, text="Identity:", 
        font=("Helvetica", 10, "bold"), width=15, anchor="w").grid(row=0, column=0, sticky="w", pady=2)
    identite_label = tk.Label(author_info_frame, text="", 
        font=("Helvetica", 10), anchor="w")
    identite_label.grid(row=0, column=1, sticky="w", pady=2)
    
    tk.Label(author_info_frame, text="Atypical ID:", 
        font=("Helvetica", 10, "bold"), width=15, anchor="w").grid(row=1, column=0, sticky="w", pady=2)
    atypique_label = tk.Label(author_info_frame, text="", 
        font=("Helvetica", 10), anchor="w")
    atypique_label.grid(row=1, column=1, sticky="w", pady=2)
    
    # Current ID frame
    id_frame = tk.LabelFrame(main_frame, text="Current Identifier",
        font=("Helvetica", 12, "bold"), padx=10, pady=10)
    id_frame.pack(fill="x", pady=(0, 10))
    
    current_id_frame = tk.Frame(id_frame)
    current_id_frame.pack(fill="x")
    
    tk.Label(current_id_frame, text="IdHAL:", 
        font=("Helvetica", 10, "bold"), width=15, anchor="w").pack(side="left")
    current_id_label = tk.Label(current_id_frame, text="", 
        font=("Helvetica", 11, "bold"), fg="#2980b9", anchor="w")
    current_id_label.pack(side="left", padx=(10, 0))
    
    def open_hal_profile():
        """Open the HAL profile page for the current identifier in a web browser"""
        df_index = problematic_rows[current_index[0]]
        row = df.iloc[df_index]
        id_hal = str(row.get('IdHAL', '') or '').strip()
        if id_hal and id_hal not in ['nan', 'NAN', ' ', '']:
            import webbrowser
            url = f"https://hal.science/search/index/?q=authIdHal_s:{id_hal}"
            webbrowser.open(url)
    
    btn_open_hal = tk.Button(current_id_frame, text="View on HAL",
        command=open_hal_profile, bg="#3498db", fg="white", 
        font=("Helvetica", 9))
    btn_open_hal.pack(side="left", padx=10)
    
    # Candidates frame
    candidates_frame = tk.LabelFrame(main_frame, text="Alternative Candidates",
        font=("Helvetica", 12, "bold"), padx=10, pady=10)
    candidates_frame.pack(fill="both", expand=True, pady=(0, 10))
    
    tk.Label(candidates_frame, 
        text="Double-click on an identifier to select it:",
        font=("Helvetica", 9, "italic"), fg="gray").pack(anchor="w", pady=(0, 5))
    
    list_frame = tk.Frame(candidates_frame)
    list_frame.pack(fill="both", expand=True)
    
    scrollbar = tk.Scrollbar(list_frame)
    scrollbar.pack(side="right", fill="y")
    
    candidates_listbox = tk.Listbox(list_frame, 
        height=10, 
        font=("Courier", 10),
        selectmode=tk.SINGLE,
        yscrollcommand=scrollbar.set)
    candidates_listbox.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=candidates_listbox.yview)
    
    # Details frame
    details_frame = tk.LabelFrame(main_frame, text="Technical Details",
        font=("Helvetica", 10, "bold"), padx=10, pady=5)
    details_frame.pack(fill="x", pady=(0, 10))
    
    details_text_frame = tk.Frame(details_frame)
    details_text_frame.pack(fill="x")
    
    details_scrollbar = tk.Scrollbar(details_text_frame)
    details_scrollbar.pack(side="right", fill="y")
    
    details_text = tk.Text(details_text_frame, 
        height=4, 
        font=("Courier", 8),
        wrap="word",
        yscrollcommand=details_scrollbar.set,
        bg="#f8f9fa")
    details_text.pack(side="left", fill="both", expand=True)
    details_scrollbar.config(command=details_text.yview)
    
    # ===== FUNCTIONS =====
    def display_current_author():
        """Display information for the current author being verified"""
        if current_index[0] >= len(problematic_rows):
            messagebox.showinfo("Complete", "All authors have been verified!")
            save_and_quit()
            return
        
        df_index = problematic_rows[current_index[0]]
        row = df.iloc[df_index]
        
        # Display identity (title OR nom+prenom)
        if 'title' in df.columns and str(row.get('title', '') or '').strip():
            identite_val = str(row.get('title', '') or '')
        elif 'nom' in df.columns and 'prenom' in df.columns:
            nom_val = str(row.get('nom', '') or 'N/A')
            prenom_val = str(row.get('prenom', '') or 'N/A')
            identite_val = f"{prenom_val} {nom_val}"
        else:
            identite_val = "N/A"
        
        identite_label.config(text=identite_val)
        
        # Display atypical status
        id_atypique = str(row.get('ID_Atypique', 'NON') or 'NON').upper()
        if id_atypique == 'OUI':
            atypique_label.config(text="YES - ID does not resemble name", 
                                 fg="#e74c3c", font=("Helvetica", 10, "bold"))
        else:
            atypique_label.config(text="NO", fg="#27ae60")
        
        # Display current ID
        id_hal = str(row.get('IdHAL', '') or '').strip()
        if id_hal and id_hal not in ['nan', 'NAN', ' ', '']:
            current_id_label.config(text=id_hal)
            btn_open_hal.config(state="normal")
        else:
            current_id_label.config(text="(No identifier)")
            btn_open_hal.config(state="disabled")
        
        # Display candidates
        candidates_listbox.delete(0, tk.END)
        candidats_str = str(row.get('Candidats', '') or '').strip()
        
        # Add current ID as first option
        if id_hal and id_hal not in ['nan', 'NAN', ' ', '']:
            candidates_listbox.insert(tk.END, f"[CURRENT] {id_hal}")
            candidates_listbox.itemconfig(0, bg="#d4edda")
        
        # Add alternative candidates
        if candidats_str and candidats_str not in ['nan', 'NAN', '']:
            candidats_list = [c.strip() for c in candidats_str.split(',')]
            for i, candidat in enumerate(candidats_list, start=1):
                if candidat and candidat != id_hal:
                    candidates_listbox.insert(tk.END, f"[ALT-{i}] {candidat}")
        
        if candidates_listbox.size() <= 1:
            candidates_listbox.insert(tk.END, "(No alternative candidates)")
            candidates_listbox.itemconfig(candidates_listbox.size()-1, fg="gray")
        
        # Display details
        details_text.delete('1.0', tk.END)
        details_str = str(row.get('Details', '') or '')
        if details_str and details_str not in ['nan', 'NAN', '{}']:
            try:
                details_dict = json.loads(details_str)
                formatted_json = json.dumps(details_dict, indent=2, ensure_ascii=False)
                details_text.insert('1.0', formatted_json)
            except:
                details_text.insert('1.0', details_str)
        else:
            details_text.insert('1.0', "(No details available)")
        
        # Update progress
        progress_label.config(text=f"Author {current_index[0] + 1} of {len(problematic_rows)}")
        progress_bar_verif["value"] = current_index[0] + 1
        stats_label.config(text=f"Total: {len(df)} | To verify: {len(problematic_rows)} | Modified: {len(modified_rows)}")
    
    def previous_author():
        """Navigate to the previous author in the verification list"""
        if current_index[0] > 0:
            current_index[0] -= 1
            display_current_author()
    
    def next_author():
        """Navigate to the next author or finish verification"""
        if current_index[0] < len(problematic_rows) - 1:
            current_index[0] += 1
            display_current_author()
        else:
            response = messagebox.askyesno("Verification Complete",
                "You have verified all authors.\n\nDo you want to save the modifications?")
            if response:
                save_and_quit()
    
    def apply_selection():
        """Apply the selected alternative identifier to the current author"""
        selection = candidates_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an identifier from the list.")
            return
        
        selected_text = candidates_listbox.get(selection[0])
        if "(No alternative candidates)" in selected_text:
            return
        
        # Extract ID from selection text
        parts = selected_text.split('] ')
        if len(parts) == 2:
            new_id = parts[1].strip()
            df_index = problematic_rows[current_index[0]]
            old_id = str(df.iloc[df_index].get('IdHAL', '') or '').strip()
            if new_id != old_id:
                df.at[df_index, 'IdHAL'] = new_id
                df.at[df_index, 'ID_Atypique'] = 'NON'
                modified_rows.add(df_index)
                messagebox.showinfo("Modification Applied", 
                                   f"Identifier modified:\nOld: {old_id if old_id else '(empty)'}\nNew: {new_id}")
            next_author()
    
    def save_and_quit():
        """
        Save the complete verified file (ALL authors, not just modified ones).
        Includes all 200 authors with any modifications applied.
        """
        if not modified_rows:
            response = messagebox.askyesno("No Modifications", 
                                           "No modifications were made.\n\nDo you still want to close?")
            if response:
                notebook.forget(frame_verification)
            return
    
        base_name = os.path.splitext(os.path.basename(csv_file))[0]
        directory = os.path.dirname(csv_file)
        new_filename = f"{base_name}_verified.csv"
        output_path = os.path.join(directory, new_filename)
    
        try:
            # Save the complete verified CSV (all rows)
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
        
            messagebox.showinfo("Save Successful",
                                f"Verified file saved:\n{output_path}\n\n"
                                f"Statistics:\n"
                                f"  • Total authors: {len(df)}\n"
                                f"  • Authors verified: {len(problematic_rows)}\n"
                                f"  • Identifiers modified: {len(modified_rows)}")
        
            global last_generated_csv
            last_generated_csv = output_path
            notebook.forget(frame_verification)
        
        except Exception as e:
            messagebox.showerror("Save Error", 
                                 f"Unable to save file:\n{str(e)}")
    
    # Double-click binding
    candidates_listbox.bind('<Double-Button-1>', lambda e: apply_selection())
    
    # ===== BOTTOM BUTTONS =====
    button_frame = tk.Frame(frame_verification, padx=20, pady=10, bg="#f4f6f7")
    button_frame.pack(fill="x", side="bottom")

    left_buttons = tk.Frame(button_frame, bg="#f4f6f7")
    left_buttons.pack(side="left")

    tk.Button(left_buttons, text="Previous", command=previous_author,
        font=("Helvetica", 10), width=12).pack(side="left", padx=5)
    
    tk.Button(left_buttons, text="Validate and Next", command=next_author,
        font=("Helvetica", 10), bg="#27ae60", fg="white", width=18).pack(side="left", padx=5)
    
    right_buttons = tk.Frame(button_frame, bg="#f4f6f7")
    right_buttons.pack(side="right")
    
    tk.Button(right_buttons, text="Apply Selection", command=apply_selection,
        font=("Helvetica", 10, "bold"), bg="#e67e22", fg="white", width=20).pack(side="left", padx=5)
    
    def delete_current_id():
        """Remove the current identifier for this author"""
        df_index = problematic_rows[current_index[0]]
        old_id = str(df.iloc[df_index].get('IdHAL', '') or '').strip()
        
        if not old_id or old_id == ' ':
            messagebox.showinfo("Information", "No identifier to delete.")
            return
        
        response = messagebox.askyesno("Confirm Deletion",
            f"Are you sure you want to delete this identifier?\n\n"
            f"Current ID: {old_id}\n\n"
            f"This will leave the author without an identifier.")
        
        if response:
            df.at[df_index, 'IdHAL'] = ' '
            df.at[df_index, 'ID_Atypique'] = 'NON'
            modified_rows.add(df_index)
            messagebox.showinfo("Deletion Complete", 
                               f"Identifier deleted: {old_id}\n\n"
                               f"The author will have no identifier.")
            next_author()
    
    tk.Button(right_buttons, text="Delete Current ID", command=delete_current_id,
        font=("Helvetica", 10), bg="#c0392b", fg="white", width=20).pack(side="left", padx=5)
    
    tk.Button(right_buttons, text="Save and Close", command=save_and_quit,
        font=("Helvetica", 10, "bold"), bg="#2ecc71", fg="white", width=20).pack(side="left", padx=5)
    
    # Display first author
    display_current_author()

    
def identify_problematic_rows(df):
    """
    Identify rows requiring verification based on atypical ID detection and alternative candidates.
    
    A row is considered problematic if:
    - The ID is marked as atypical (does not resemble the author's name)
    - Alternative candidates exist (non-empty 'Candidats' column)
    
    Args:
        df (pd.DataFrame): DataFrame containing extracted identifiers
        
    Returns:
        list: List of row indices that need verification
    """
    problematic_rows = []
    
    for idx, row in df.iterrows():
        # Safely retrieve values and handle NaN/None cases
        id_hal = str(row.get('IdHAL', '') or '').strip()
        candidats = str(row.get('Candidats', '') or '').strip()
        id_atypique = str(row.get('ID_Atypique', 'NON') or 'NON').upper()
        
        # IGNORE cases without any identifier
        if not id_hal or id_hal.upper() in ['NONE', 'NAN', ' ', '']:
            continue
        
        # CRITERION 1: Atypical ID (MAXIMUM PRIORITY)
        if id_atypique == 'OUI':
            problematic_rows.append(idx)
            continue
        
        # CRITERION 2: Presence of alternative candidates
        if candidats and candidats not in ['nan', 'NAN', '']:
            problematic_rows.append(idx)
            continue
    
    return problematic_rows

def detection_doublons_homonymes():
    """
    Wrapper function that calls the duplicate and homonym detection process.
    
    Purpose: Delegates the detection logic to the integration module
    """
    from integration import detection_doublons_homonymes as nouvelle_detection
    nouvelle_detection()
    
def create_detection_tab():
    """
    Creates the duplicate and homonym detection tab in the GUI.
    
    Purpose: Sets up the complete UI for the detection functionality including
             buttons, labels, and information panels
    """
    
    # Create the frame for the detection tab
    global frame_detection
    frame_detection = ttk.Frame(notebook)
    frame_detection.pack(fill="both", expand=True)
    
    # Main title
    label_detection = tk.Label(
        frame_detection,
        text="Détection Doublons & Homonymes\n",
        font=("Helvetica", 16)
    )
    label_detection.pack(pady=20)
    
    # Visual separator
    ttk.Separator(frame_detection, orient="horizontal").pack(fill="x", padx=20, pady=10)
    
    # Main action button
    btn_detection = tk.Button(
        frame_detection, 
        text="Lancer la Détection", 
        font=("Helvetica", 14, "bold"),
        command=detection_doublons_homonymes,
        bg="#4CAF50", 
        fg="white",
        width=35,
        height=2
    )
    btn_detection.pack(pady=20)
    
    # Method information panel
    info_text = """
MÉTHODE Basée sur :
• Groupement par (nom, prénom) des publications multiples
• Requête API HAL
• Distinction précise basée sur les identifiants HAL uniques
• Détection des collaborations vs thèses principales
    """
    
    # Information display with styling
    info_label = tk.Label(frame_detection, text=info_text, 
                         font=("Helvetica", 10), justify="left",
                         relief="ridge", bd=1, bg="#e8f5e8")
    info_label.pack(pady=10, padx=20, fill="x")
    
    # Technical instructions panel
    tech_text = """
INSTRUCTIONS D'UTILISATION :
1. Préparez votre fichier CSV d'extraction (format standard de l'application)
2. Optionnel: fichier laboratoire pour améliorer précision homonymes
3. Lancez l'analyse 
4. Examinez résultats dans les onglets spécialisés
5. Utilisez traitement automatique pour nettoyer les données
6. Exportez résultats pour documentation et archivage
    """
    
    # Technical instructions display
    tech_label = tk.Label(frame_detection, text=tech_text, 
                         font=("Helvetica", 9), justify="left",
                         fg="gray")
    tech_label.pack(pady=10, padx=20, fill="x")

def generate_graphs_thread():
    """Graph generation with parallelization and progress bar"""
    
    # Create progress window
    progress_window = Toplevel(root)
    progress_window.title("Génération en cours")
    progress_window.geometry("500x150")
    progress_window.resizable(False, False)
    progress_window.transient(root)
    
    tk.Label(progress_window, text="Génération des graphiques en cours...", 
             font=("Helvetica", 12, "bold")).pack(pady=20)
    
    progress_bar_graphs = ttk.Progressbar(progress_window, orient="horizontal", 
                                         length=450, mode="determinate")
    progress_bar_graphs.pack(pady=10)
    
    progress_label_graphs = tk.Label(progress_window, text="Préparation...", 
                                     font=("Helvetica", 10))
    progress_label_graphs.pack(pady=10)
    
    def run_generation():
        try:
            start_time = time.time()
            print("Starting graph generation...")
            
            # Get absolute paths
            base_path = os.path.dirname(os.path.abspath(__file__))
            html_dir = os.path.join(base_path, 'html')
            png_dir = os.path.join(base_path, 'png')
            
            # Create directories
            os.makedirs(html_dir, exist_ok=True)
            os.makedirs(png_dir, exist_ok=True)
            
            # Load CSV
            progress_label_graphs.config(text="Chargement des données...")
            progress_window.update()
            
            global shared_dataframe
            shared_dataframe = pd.read_csv(current_csv_file)
            
            # Graph functions
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
                (plot_theses_keywords_wordcloud, "theses_keywords_wordcloud"),
                (plot_temporal_evolution_by_team, "temporal_evolution_teams")
            ]
            
            progress_bar_graphs["maximum"] = len(graph_functions)
            
            def execute_graph_function_optimized(func, filename_base):
                try:
                    html_path = os.path.join(html_dir, f"{filename_base}.html")
                    png_path = os.path.join(png_dir, f"{filename_base}.png")
                    
                    func(current_csv_file, output_html=html_path, output_png=png_path)
                    
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
            
            max_workers = min(12, (os.cpu_count() or 1) + 4)
            success_count = 0
            total_tasks = len(graph_functions)
            completed = 0
                    
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(execute_graph_function_optimized, func, filename_base): (func.__name__, filename_base)
                    for func, filename_base in graph_functions
                }
                
                for future in as_completed(futures):
                    result = future.result()
                    func_name, filename = futures[future]
                    
                    if "SUCCESS:" in result:
                        success_count += 1
                    
                    completed += 1
                    progress_bar_graphs["value"] = completed
                    progress_label_graphs.config(text=f"Graphique {completed}/{total_tasks} généré...")
                    progress_window.update()
            
            # Dashboard generation
            progress_label_graphs.config(text="Génération du tableau de bord...")
            progress_window.update()
            
            global dashboard_file
            dashboard_file = create_dashboard()
            
            elapsed_time = time.time() - start_time
            
            # Clean up
            if 'shared_dataframe' in globals():
                del shared_dataframe
            
            # Close progress window
            progress_window.destroy()
            
            # Success message
            success_message = (f"Graphiques générés avec succès !\n\n"
                              f"Succès : {success_count}/{total_tasks} graphiques créés\n"
                              f"Temps d'exécution : {elapsed_time:.2f} secondes\n"
                              f"Threads utilisés : {max_workers}\n"
                              f"Fichiers sauvegardés dans :\n"
                              f"   • {html_dir}\n"
                              f"   • {png_dir}")
            
            messagebox.showinfo("Succès", success_message)
            
            # Display buttons
            btn_afficher_graphiques.pack(pady=5)
            btn_generer_rapport.pack(pady=5)
            
        except Exception as e:
            progress_window.destroy()
            error_msg = f"Erreur lors de la génération :\n{str(e)}"
            messagebox.showerror("Erreur", error_msg)
            
            if 'shared_dataframe' in globals():
                del shared_dataframe
    
    # Launch in thread
    threading.Thread(target=run_generation).start()
    
# ============================================================================
# KEYWORD ANALYSIS FUNCTIONS
# ============================================================================

def analyser_mots_cles():
    """
    Analyze keywords from a publications CSV file.
    Generate keyword frequency analysis with associated document IDs.
    """
    # Load publications file
    fichier_csv = filedialog.askopenfilename(
        title="Sélectionner le fichier de publications CSV",
        filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")]
    )
    
    if not fichier_csv:
        return
    
    try:
        # Load the publications DataFrame
        publications_df = pd.read_csv(fichier_csv, encoding='utf-8-sig')
        
        # Check required columns (noms exacts)
        if 'Mots-clés' not in publications_df.columns:
            messagebox.showerror("Erreur - Colonne manquante", 
                "Le fichier doit contenir la colonne 'Mots-clés'.\n\n"
                "Colonnes trouvées dans le fichier :\n" + 
                ", ".join(publications_df.columns.tolist()))
            return
        
        if 'Docid' not in publications_df.columns:
            messagebox.showerror("Erreur - Colonne manquante", 
                "Le fichier doit contenir la colonne 'Docid'.\n\n"
                "Colonnes trouvées dans le fichier :\n" + 
                ", ".join(publications_df.columns.tolist()))
            return
        
        # Check if there are any keywords
        non_empty_keywords = publications_df['Mots-clés'].notna().sum()
        if non_empty_keywords == 0:
            messagebox.showwarning("Attention",
                "La colonne 'Mots-clés' ne contient aucune donnée.\n\n"
                "Impossible de réaliser l'analyse.")
            return
        
        # Open options window
        create_keyword_analysis_options_window(publications_df, fichier_csv)
        
    except Exception as e:
        messagebox.showerror("Erreur", f"Impossible de charger le fichier:\n{str(e)}")
        
def create_keyword_analysis_options_window(publications_df, source_file):
    """Create options window for keyword analysis configuration"""
    options_window = Toplevel(root)
    options_window.title("Options d'analyse des mots-clés")
    options_window.geometry("600x650")  # Augmenté de 600 à 650
    options_window.resizable(False, False)
    
    options_window.transient(root)
    options_window.grab_set()
    
    # Title
    title_label = tk.Label(options_window, text="Configuration de l'analyse", 
                          font=("Helvetica", 16, "bold"))
    title_label.pack(pady=15)
    
    # Info frame
    info_frame = tk.Frame(options_window, relief="ridge", bd=2, bg="#e8f5e8")
    info_frame.pack(pady=10, padx=20, fill="x")
    
    info_text = f"Fichier chargé : {os.path.basename(source_file)}\n"
    info_text += f"Nombre de publications : {len(publications_df)}"
    
    tk.Label(info_frame, text=info_text, bg="#e8f5e8", 
             font=("Helvetica", 10), justify="left").pack(pady=10, padx=10)
    
    # Options frame
    options_frame = tk.Frame(options_window)
    options_frame.pack(pady=15, padx=20, fill="both", expand=True)
    
    # Minimum occurrences threshold
    threshold_frame = tk.LabelFrame(options_frame, text="Seuil d'occurrences", 
                                   font=("Helvetica", 11, "bold"), padx=10, pady=10)
    threshold_frame.pack(fill="x", pady=(0, 15))
    
    tk.Label(threshold_frame, text="Afficher uniquement les mots-clés avec au moins :", 
             font=("Helvetica", 10)).pack(anchor="w")
    
    threshold_var = tk.IntVar(value=1)
    threshold_spinbox = tk.Spinbox(threshold_frame, from_=1, to=100, 
                                   textvariable=threshold_var, width=10,
                                   font=("Helvetica", 10))
    threshold_spinbox.pack(anchor="w", pady=5)
    tk.Label(threshold_frame, text="occurrence(s)", 
             font=("Helvetica", 9), fg="gray").pack(anchor="w")
    
    # Normalization options
    norm_frame = tk.LabelFrame(options_frame, text="Normalisation", 
                              font=("Helvetica", 11, "bold"), padx=10, pady=10)
    norm_frame.pack(fill="x", pady=(0, 15))
    
    normalize_var = tk.BooleanVar(value=True)
    
    # Checkbox
    tk.Checkbutton(norm_frame, text="Normaliser la casse des mots-clés", 
                  variable=normalize_var, font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(5, 10))
    
    # Explication
    explication_text = (
        "Si coché : Les variations de majuscules/minuscules seront fusionnées.\n"
        "   Exemple : 'Machine Learning', 'machine learning', 'MACHINE LEARNING'\n"
        "   → tous comptés comme 'machine learning' (total cumulé)\n\n"
        "Si décoché : Chaque variation sera comptée séparément.\n"
        "   Exemple : 'Machine Learning' (3 occurrences)\n"
        "                  'machine learning' (5 occurrences)\n"
        "   → 2 entrées distinctes dans le résultat"
    )
    
    explication_label = tk.Label(norm_frame, text=explication_text, 
                                font=("Helvetica", 9), justify="left",
                                fg="#555555", wraplength=520, bg="#f9f9f9",
                                relief="flat", padx=10, pady=10)
    explication_label.pack(anchor="w", fill="x", pady=5)
    
    # SPACER
    spacer = tk.Frame(options_window, height=30)  
    spacer.pack(fill="both", expand=True)
    
    # Buttons frame
    button_frame = tk.Frame(options_window, bg="#d0d0d0", height=100)  
    button_frame.pack(side="bottom", fill="x")
    button_frame.pack_propagate(False)
    
    def lancer_analyse():
        min_occurrences = threshold_var.get()
        normalize = normalize_var.get()
        
        options_window.destroy()
        
        threading.Thread(target=perform_keyword_analysis, 
                        args=(publications_df, source_file, min_occurrences, 
                              normalize)).start()
    
    # Centrer les boutons
    button_container = tk.Frame(button_frame, bg="#d0d0d0")
    button_container.place(relx=0.5, rely=0.5, anchor="center")
    
    tk.Button(button_container, text="Annuler", 
              command=options_window.destroy,
              font=("Helvetica", 13), width=15, height=2,
              bg="#95a5a6", fg="white").pack(side="left", padx=15)
    
    tk.Button(button_container, text="Lancer l'analyse", 
              command=lancer_analyse,
              font=("Helvetica", 13, "bold"), bg="#27ae60", fg="white", 
              width=22, height=2).pack(side="left", padx=15)
    
def perform_keyword_analysis(publications_df, source_file, min_occurrences, normalize):
    """Perform keyword analysis and generate output files with progress bar"""
    
    # Create progress window
    progress_window = Toplevel(root)
    progress_window.title("Analyse en cours")
    progress_window.geometry("500x150")
    progress_window.resizable(False, False)
    progress_window.transient(root)
    progress_window.grab_set()
    
    tk.Label(progress_window, text="Analyse des mots-clés en cours...", 
             font=("Helvetica", 12, "bold")).pack(pady=20)
    
    progress_bar = ttk.Progressbar(progress_window, orient="horizontal", 
                                   length=450, mode="determinate")
    progress_bar.pack(pady=10)
    progress_bar["maximum"] = len(publications_df)
    
    progress_label = tk.Label(progress_window, text="0 / 0 publications analysées", 
                             font=("Helvetica", 10))
    progress_label.pack(pady=10)
    
    def run_analysis():
        try:
            keyword_data = {}
            
            for idx, row in publications_df.iterrows():
                # Get data from row
                keywords = row.get('Mots-clés', '')
                docid = row.get('Docid', '')
                labo = row.get('Laboratoire de Recherche', '')
                
                # Convert to string
                if pd.isna(docid) or docid == '':
                    docid_str = ''
                else:
                    docid_str = str(docid)
                
                # Convert labo to string and filter "Non disponible"
                if pd.isna(labo) or labo == '' or str(labo).lower() in ['non disponible', 'nan']:
                    labo_str = ''
                else:
                    labo_str = str(labo)
                
                # Skip if no keywords
                if not keywords or pd.isna(keywords):
                    # Update progress
                    progress_bar["value"] = idx + 1
                    progress_label.config(text=f"{idx + 1} / {len(publications_df)} publications analysées")
                    progress_window.update()
                    continue
                
                # Handle different keyword formats
                if isinstance(keywords, str):
                    # Filter empty keywords and '[]'
                    keyword_list = [k.strip() for k in keywords.replace(';', ',').split(',') 
                                   if k.strip() and k.strip() != '[]']
                elif isinstance(keywords, list):
                    keyword_list = [k for k in keywords if k and k != '[]']
                else:
                    progress_bar["value"] = idx + 1
                    progress_label.config(text=f"{idx + 1} / {len(publications_df)} publications analysées")
                    progress_window.update()
                    continue
                
                # Process each keyword
                for keyword in keyword_list:
                    if not keyword or keyword == '[]':
                        continue
                    
                    # Normalize if requested
                    if normalize:
                        keyword = keyword.lower()
                    
                    # Initialize keyword entry
                    if keyword not in keyword_data:
                        keyword_data[keyword] = {
                            'count': 0,
                            'docids': set(),
                            'labos': set()
                        }
                    
                    # Update data
                    keyword_data[keyword]['count'] += 1
                    if docid_str:
                        keyword_data[keyword]['docids'].add(docid_str)
                    if labo_str:  # Only add if not empty (already filtered above)
                        keyword_data[keyword]['labos'].add(labo_str)
                
                # Update progress bar
                progress_bar["value"] = idx + 1
                progress_label.config(text=f"{idx + 1} / {len(publications_df)} publications analysées")
                progress_window.update()
            
            # Close progress window
            progress_window.destroy()
            
            # Filter by minimum occurrences
            filtered_keywords = {k: v for k, v in keyword_data.items() 
                               if v['count'] >= min_occurrences}
            
            # Check if any keywords found
            if not filtered_keywords:
                messagebox.showwarning("Aucun résultat",
                    f"Aucun mot-clé trouvé avec au moins {min_occurrences} occurrence(s).\n\n"
                    f"Suggestions :\n"
                    f"  • Diminuez le seuil d'occurrences\n"
                    f"  • Vérifiez que la colonne 'Mots-clés' contient des données")
                return
            
            # Generate output file
            extraction_directory = create_extraction_folder()
            base_name = os.path.splitext(os.path.basename(source_file))[0]
            
            global_output_path = os.path.join(extraction_directory, 
                                             f"{base_name}_keywords_analysis.csv")
            
            global_data = []
            for keyword, data in sorted(filtered_keywords.items(), 
                                       key=lambda x: x[1]['count'], reverse=True):
                # Sort docids
                docids_list = sorted(data['docids'], key=lambda x: int(x) if x.isdigit() else x)
                docids_str = ','.join(docids_list)
                
                # Sort and join unique laboratories (empty if no valid labs)
                labos_list = sorted(data['labos'])
                labos_str = ', '.join(labos_list) if labos_list else ''
                
                global_data.append({
                    'Mot-clé': keyword,
                    'Occurrences': data['count'],
                    'Laboratoires': labos_str,
                    'Docids': docids_str
                })
            
            global_df = pd.DataFrame(global_data)
            global_df.to_csv(global_output_path, index=False, encoding='utf-8-sig')
            
            # Success message
            success_msg = "Analyse terminée avec succès !\n\n"
            success_msg += "Statistiques :\n"
            success_msg += f"  • Nombre de mots-clés uniques : {len(filtered_keywords)}\n"
            success_msg += f"  • Seuil minimal : {min_occurrences} occurrence(s)\n"
            success_msg += f"  • Normalisation : {'✓ Activée' if normalize else '✗ Désactivée'}\n"
            success_msg += f"  • Publications analysées : {len(publications_df)}\n\n"
            success_msg += f"Fichier généré :\n{global_output_path}"
            
            messagebox.showinfo("Analyse terminée", success_msg)
            
        except Exception as e:
            progress_window.destroy()
            import traceback
            error_detail = traceback.format_exc()
            messagebox.showerror("Erreur", 
                f"Erreur lors de l'analyse :\n{str(e)}\n\n"
                f"Détails techniques :\n{error_detail}")
    
    # Launch analysis in thread
    threading.Thread(target=run_analysis).start()
    
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
            messagebox.showinfo("Rapport PDF", "Le rapport PDF a été généré avec succès.")
        elif format_choisi == "LaTeX":
             generate_latex_report(nom_fichier_csv)
             messagebox.showinfo("Rapport LaTeX", "Le rapport LaTeX a été généré avec succès.")
        else:
            messagebox.showerror("Erreur", "Veuillez choisir un format valide.")
        rapport_window.destroy()

    # Validation button
    btn_valider = tk.Button(rapport_window, text="Valider", command=valider_choix)
    btn_valider.pack(pady=10)

# Main interface
root = tk.Tk()
root.title("Outil d'Extraction et Analyse - API HAL - Version Améliorée")
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

# Main title
label_accueil = tk.Label(
    frame_extraction,
    text="Bienvenue sur la section Extraction !",
    font=("Helvetica", 18, "bold")
)
label_accueil.pack(pady=15)

def update_config_label():
    """Generate current configuration label text"""
    level_name = get_level_from_threshold(current_threshold)
    return f"Configuration actuelle : {level_name.title()} (distance = {current_threshold})"

# Configuration information label
config_info_label = tk.Label(frame_extraction, text=update_config_label(), 
                            font=("Helvetica", 9, "italic"), fg="gray")
config_info_label.pack(pady=(0, 20))

# Main separator
ttk.Separator(frame_extraction, orient="horizontal").pack(fill="x", padx=20, pady=10)

# ===== SECTION 1: IDENTIFIER EXTRACTION =====
frame_identifiants = tk.LabelFrame(
    frame_extraction, 
    text="Étape 1 : Extraction des Identifiants HAL",
    font=("Helvetica", 13, "bold"),
    padx=20,
    pady=15
)
frame_identifiants.pack(fill="x", padx=30, pady=15)

label_info_id = tk.Label(
    frame_identifiants,
    text="Chargez un fichier CSV contenant les colonnes 'nom' et 'prenom'\n"
         "pour extraire les identifiants HAL des auteurs.",
    font=("Helvetica", 10),
    justify="left"
)
label_info_id.pack(pady=(0, 10))

btn_charger_identifiants = tk.Button(
    frame_identifiants, 
    text="1. Charger fichier CSV (nom/prenom)", 
    font=("Helvetica", 11),
    command=charger_csv_identifiants,
    bg="#2196F3",
    fg="white",
    width=35
)
btn_charger_identifiants.pack(pady=5)

btn_extraire_id = tk.Button(
    frame_identifiants, 
    text="2. Extraire les identifiants HAL", 
    font=("Helvetica", 11, "bold"),
    command=extraire_identifiants,
    bg="#4CAF50",
    fg="white",
    width=35,
    state="disabled"
)
btn_extraire_id.pack(pady=5)

btn_verifier_id = tk.Button(
    frame_identifiants, 
    text="3. Vérifier les identifiants extraits", 
    font=("Helvetica", 11),
    command=verifier_identifiants,
    bg="#9b59b6",
    fg="white",
    width=35,
    state="disabled"  
)
btn_verifier_id.pack(pady=5)

# Separator between sections
ttk.Separator(frame_extraction, orient="horizontal").pack(fill="x", padx=20, pady=20)

# ===== SECTION 2: PUBLICATION EXTRACTION =====
frame_publications = tk.LabelFrame(
    frame_extraction, 
    text="Étape 2 : Extraction des Publications",
    font=("Helvetica", 13, "bold"),
    padx=20,
    pady=15
)
frame_publications.pack(fill="x", padx=30, pady=15)

label_info_pub = tk.Label(
    frame_publications,
    text="Chargez un fichier CSV contenant la colonne 'IdHAL' (recommandé)\n"
         "et/ou 'title' pour extraire les publications des auteurs.\n"
         "Les identifiants HAL sont utilisés en priorité pour une recherche optimale.",
    font=("Helvetica", 10),
    justify="left"
)
label_info_pub.pack(pady=(0, 10))

btn_charger_publications = tk.Button(
    frame_publications, 
    text="1. Charger fichier CSV (avec IdHAL)", 
    font=("Helvetica", 11),
    command=charger_csv_publications,
    bg="#2196F3",
    fg="white",
    width=35
)
btn_charger_publications.pack(pady=5)

btn_extraire = tk.Button(
    frame_publications, 
    text="2a. Extraire toutes les données", 
    font=("Helvetica", 11),
    command=extraire_toutes_les_donnees,
    bg="#4CAF50",
    fg="white",
    width=35,
    state="disabled"
)
btn_extraire.pack(pady=5)

btn_filtrer = tk.Button(
    frame_publications, 
    text="2b. Appliquer des filtres d'extraction", 
    font=("Helvetica", 11),
    command=appliquer_filtres,
    bg="#FF9800",
    fg="white",
    width=35,
    state="disabled"
)
btn_filtrer.pack(pady=5)

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

# ===== ANALYSE DES MOTS-CLÉS =====

# Separator entre les deux sections
ttk.Separator(frame_analyse, orient="horizontal").pack(fill="x", padx=20, pady=20)

# Section Analyse des mots-clés
label_keywords = tk.Label(
    frame_analyse,
    text="Analyse des Mots-clés",
    font=("Helvetica", 14, "bold")
)
label_keywords.pack(pady=10)

label_keywords_desc = tk.Label(
    frame_analyse,
    text="Analysez la fréquence des mots-clés dans vos publications extraites.\n"
         "Génère un fichier CSV avec les mots-clés, leur nombre d'occurrences et les documents associés.",
    font=("Helvetica", 10),
    justify="center"
)
label_keywords_desc.pack(pady=5)

btn_analyser_keywords = tk.Button(
    frame_analyse, 
    text="Charger un fichier et analyser les mots-clés", 
    font=("Helvetica", 12),
    command=analyser_mots_cles,
    bg="#9b59b6",
    fg="white"
)
btn_analyser_keywords.pack(pady=10)

# Create detection tab first
create_detection_tab()

# Add tabs in the correct order: Extraction, Analysis, then Detection
notebook.add(frame_extraction, text="Extraction")
notebook.add(frame_analyse, text="Analyse")
notebook.add(frame_detection, text="Détection Doublons & Homonymes")

# Launch application
if __name__ == "__main__":
    root.mainloop()