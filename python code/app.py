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
            if len(types) == 1:
                details_list.append(f"• Type de document : {types[0]}")
            else:
                details_list.append(f"• Types de documents : {', '.join(types)}")
        
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
                
                # # Real-time GUI update
                # progress_percentage = int((i / total_tasks) * 100)
                # root.after(0, lambda p=progress_percentage: 
                #           message_label_analyse.config(text=f"Generating graphs... {p}%") 
                #           if 'message_label_analyse' in globals() else None)
        
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

notebook.add(frame_extraction, text="Extraction")
notebook.add(frame_analyse, text="Analyse")

# Launch application
if __name__ == "__main__":
    root.mainloop()