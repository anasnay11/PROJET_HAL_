# -*- coding: utf-8 -*-

# integration.py


import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel, ttk
import pandas as pd
import os
import threading
from detection_doublons_homonymes import DuplicateHomonymDetector

def detection_doublons_homonymes():
    """
    Main function for duplicate and homonym detection
    """
    # Create main window
    detection_window = Toplevel()
    detection_window.title("Détection Doublons & Homonymes")
    detection_window.geometry("800x700")
    detection_window.resizable(True, True)
    
    # Title
    title_label = tk.Label(detection_window, text="Détection Doublons & Homonymes", 
                          font=("Helvetica", 18, "bold"))
    title_label.pack(pady=15)
    
    # Method description
    description_text = """
ALGORITHME AUTHIDPERSON_I

Cette méthode améliore considérablement la précision de détection :

1. Groupement par (nom, prénom) des publications
2. Requête API HAL 
3. Analyse précise basée sur les identifiants HAL uniques
4. Détection des collaborations vs thèses principales
    """
    
    info_frame = tk.Frame(detection_window, relief="ridge", bd=2, bg="#f0f0f0")
    info_frame.pack(fill="x", padx=20, pady=10)
    
    info_label = tk.Label(info_frame, text=description_text, 
                         font=("Helvetica", 10), justify="left", bg="#f0f0f0")
    info_label.pack(pady=10, padx=15)
    
    # Separator
    ttk.Separator(detection_window, orient="horizontal").pack(fill="x", padx=20, pady=10)
    
    # Frame for main buttons
    main_buttons_frame = tk.Frame(detection_window)
    main_buttons_frame.pack(pady=20)
    
    # Global variables for this window
    analysis_results = None
    
    def analyser_fichier():
        """Launches analysis of a CSV file"""
        
        # Select main file to analyze
        analysis_file = filedialog.askopenfilename(
            title="Sélectionner un fichier CSV à analyser",
            filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")],
            initialdir="extraction"
        )
        
        if not analysis_file:
            return
        
        # Optional: select laboratory file
        use_lab_file = messagebox.askyesno(
            "Fichier laboratoire",
            "Souhaitez-vous utiliser un fichier de laboratoires\n"
            "pour améliorer la détection des homonymes ?\n\n"
            "Ce fichier doit contenir les colonnes 'nom', 'prenom', 'unite_de_recherche'"
        )
        
        laboratory_file = None
        if use_lab_file:
            laboratory_file = filedialog.askopenfilename(
                title="Sélectionner le fichier des laboratoires (optionnel)",
                filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")]
            )
        
        # Create analysis window
        analysis_window = Toplevel(detection_window)
        analysis_window.title("Analyse en cours...")
        analysis_window.geometry("900x800")
        analysis_window.transient(detection_window)
        analysis_window.grab_set()
        
        # Variables for thread management
        analysis_thread = None
        detector_instance = None
        
        # Title
        tk.Label(analysis_window, text="Analyse des Doublons & Homonymes", 
                font=("Helvetica", 16, "bold")).pack(pady=10)
        
        # File information
        file_info = f"Fichier analysé: {os.path.basename(analysis_file)}"
        if laboratory_file:
            file_info += f"\nFichier laboratoire: {os.path.basename(laboratory_file)}"
        
        tk.Label(analysis_window, text=file_info, 
                font=("Helvetica", 10, "italic")).pack(pady=5)
        
        # Notebook to organize results
        results_notebook = ttk.Notebook(analysis_window)
        results_notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Tabs
        summary_frame = ttk.Frame(results_notebook)
        results_notebook.add(summary_frame, text="Résumé")
        
        duplicates_frame = ttk.Frame(results_notebook)
        results_notebook.add(duplicates_frame, text="Doublons")
        
        homonyms_frame = ttk.Frame(results_notebook)
        results_notebook.add(homonyms_frame, text="Homonymes")
        
        multithesis_frame = ttk.Frame(results_notebook)
        results_notebook.add(multithesis_frame, text="Multi-thèses")
        
        collaborators_frame = ttk.Frame(results_notebook)
        results_notebook.add(collaborators_frame, text="Collaborations")
        
        issues_frame = ttk.Frame(results_notebook)
        results_notebook.add(issues_frame, text="Problèmes")
        
        # Progress bar and status
        progress_var = tk.StringVar()
        progress_var.set("Initialisation de l'analyse...")
        progress_label = tk.Label(analysis_window, textvariable=progress_var, 
                                 font=("Helvetica", 10))
        progress_label.pack(pady=5)
        
        progress_bar = ttk.Progressbar(analysis_window, mode='indeterminate')
        progress_bar.pack(pady=5, fill="x", padx=20)
        
        # Action buttons
        action_frame = tk.Frame(analysis_window)
        action_frame.pack(side="bottom", pady=10)
        
        def fermer_analyse():
            """Closes window and stops analysis - improved version"""
            nonlocal analysis_thread, detector_instance
            
            print("Fermeture de l'analyse demandée par l'utilisateur...")
            
            # Stop detector if it exists
            if detector_instance:
                detector_instance.set_stop_flag(True)
                print("Signal d'arrêt envoyé au détecteur")
            
            # Stop progress bar
            try:
                progress_bar.stop()
            except:
                pass
            
            # Wait for thread to finish (with timeout)
            if analysis_thread and analysis_thread.is_alive():
                print("Attente de l'arrêt du thread...")
                analysis_thread.join(timeout=2.0)  # Wait maximum 2 seconds
            
            # Close window
            analysis_window.destroy()
        
        # Window close button handling - improved
        analysis_window.protocol("WM_DELETE_WINDOW", fermer_analyse)
        
        def lancer_analyse():
            """Launches analysis in separate thread - improved version"""
            nonlocal analysis_thread, detector_instance
            
            def analysis_thread_func():
                nonlocal analysis_results, detector_instance
                
                try:
                    
                    # Start progress bar
                    progress_bar.start()
                    progress_var.set("Analyse en cours... Interrogation de l'API HAL")
                    
                    # Create detector and launch analysis
                    detector_instance = DuplicateHomonymDetector()
                    
                    analysis_results = detector_instance.analyze_csv_file(analysis_file, laboratory_file)
                    
                    # Check if analysis was interrupted
                    if detector_instance.stop_requested:
                        print("Analyse interrompue - affichage des résultats partiels")
                        progress_var.set("Analyse interrompue par l'utilisateur")
                        return
                                        
                    # Display results in tabs
                    display_summary(summary_frame, analysis_results)
                    display_duplicates(duplicates_frame, analysis_results)
                    display_homonyms(homonyms_frame, analysis_results)
                    display_multithesis(multithesis_frame, analysis_results)
                    display_collaborators(collaborators_frame, analysis_results)
                    display_issues(issues_frame, analysis_results)
                
                    # Enable action buttons
                    btn_traiter.config(state="normal")
                    btn_exporter.config(state="normal")
                    btn_recommandations.config(state="normal")
                
                    progress_var.set("Analyse terminée avec succès!")
                
                except Exception as e:
                    print(f"DEBUG: Erreur dans le thread: {str(e)}")
                    if not (detector_instance and detector_instance.stop_requested):
                        # Show error only if not voluntary stop
                        error_text = tk.Text(summary_frame, font=("Courier", 10), wrap="word")
                        error_text.pack(fill="both", expand=True, padx=5, pady=5)
                        error_text.insert(tk.END, f"ERREUR lors de l'analyse:\n{str(e)}")
                        error_text.config(state="disabled")
                    
                        progress_var.set("Erreur lors de l'analyse")
                
                finally:
                    try:
                        if not (detector_instance and detector_instance.stop_requested):
                            progress_bar.stop()
                    except:
                        pass
                    print("Thread d'analyse terminé")
            
            # Launch in separate thread
            analysis_thread = threading.Thread(target=analysis_thread_func, daemon=True)
            analysis_thread.start()
        
        def traiter_donnees():
            """Interface for problematic data processing"""
            if not analysis_results:
                messagebox.showerror("Erreur", "Aucune analyse disponible.")
                return
            
            traitement_window = create_treatment_interface(analysis_window, analysis_results, analysis_file)
        
        def exporter_resultats():
            """Results export interface"""
            if not analysis_results:
                messagebox.showerror("Erreur", "Aucune analyse disponible.")
                return
            
            export_results_interface(analysis_results, analysis_file)
        
        def afficher_recommandations():
            """Displays recommendations based on analysis"""
            if not analysis_results:
                messagebox.showerror("Erreur", "Aucune analyse disponible.")
                return
            
            show_recommendations(analysis_results)
        
        # Action buttons
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
        
        btn_recommandations = tk.Button(action_frame, text="Recommandations", 
                                       command=afficher_recommandations, font=("Helvetica", 11),
                                       bg="#9C27B0", fg="white", width=15, state="disabled")
        btn_recommandations.pack(side="left", padx=5)
        
        btn_fermer = tk.Button(action_frame, text="Fermer", 
                              command=fermer_analyse, font=("Helvetica", 11),
                              width=10)
        btn_fermer.pack(side="right", padx=5)
        
        # Automatically launch analysis
        lancer_analyse()
    
    # Main analysis button
    btn_analyser = tk.Button(main_buttons_frame, text="Analyser un fichier CSV", 
                            command=analyser_fichier, font=("Helvetica", 14, "bold"),
                            bg="#4CAF50", fg="white", width=30, height=2)
    btn_analyser.pack(pady=10)
    
    # Additional information
    complementary_info = """
CONSEIL D'UTILISATION :

1. Préparez votre fichier CSV d'extraction (format standard de l'application)
2. Optionnel : Préparez un fichier des laboratoires pour améliorer la précision
3. Lancez l'analyse - patience requise car interrogation API HAL
4. Examinez les résultats dans les différents onglets
5. Utilisez les fonctions de traitement pour nettoyer automatiquement
6. Exportez les résultats pour documentation

IMPORTANT : Cette méthode interroge l'API HAL pour chaque publication,
le temps d'analyse dépend du nombre de publications à traiter.
    """
    
    info_label2 = tk.Label(detection_window, text=complementary_info, 
                          font=("Helvetica", 9), justify="left",
                          relief="flat", bg="#f8f8f8")
    info_label2.pack(pady=10, padx=20, fill="x")
    
    # Close button
    btn_fermer = tk.Button(detection_window, text="Fermer", 
                          command=detection_window.destroy, font=("Helvetica", 11),
                          width=15)
    btn_fermer.pack(side="bottom", pady=10)


def display_summary(frame, results):
    """
    Displays analysis summary
    
    Args:
        frame: Tkinter frame to display in
        results (dict): Analysis results
    """
    summary_text = tk.Text(frame, font=("Courier", 10), wrap="word")
    summary_text.pack(fill="both", expand=True, padx=5, pady=5)
    
    summary = results['summary']
    content = f"""
RÉSUMÉ DE L'ANALYSE
{'='*50}

Publications analysées: {summary['total_publications']}
Auteurs avec publications multiples: {summary['authors_with_multiple_pubs']}

DÉTECTIONS :
├─ Doublons: {summary['duplicate_publications']}
├─ Homonymes: {summary['homonym_publications']}  
├─ Multi-thèses: {summary['multi_thesis_publications']}
├─ Collaborations: {len(results['collaborator_cases'])}
└─ Problèmes techniques: {len(results['no_authid_cases'])}

FONCTIONNALITÉS :
• Utilisation des identifiants HAL officiels (authIdPerson_i)
• Analyse de la similarité des titres (seuil: 0.8)
• Vérification de l'écart temporel (seuil: 2 ans)
• Détection des collaborations vs thèses principales

{'='*50}
Analyse terminée avec succès!
    """
    
    summary_text.insert(tk.END, content)
    summary_text.config(state="disabled")


def display_duplicates(frame, results):
    """
    Displays detected duplicates
    
    Args:
        frame: Tkinter frame to display in
        results (dict): Analysis results
    """
    if not results['duplicate_cases']:
        tk.Label(frame, text="Aucun doublon détecté", 
                font=("Helvetica", 14, "bold"), fg="green").pack(pady=50)
        return
    
    # Create treeview to display duplicates
    columns = ('Auteur', 'Similarité', 'Titre 1', 'Titre 2', 'Années', 'Type')
    tree = ttk.Treeview(frame, columns=columns, show='headings', height=15)
    
    # Configure columns
    tree.heading('Auteur', text='Auteur')
    tree.heading('Similarité', text='Score')
    tree.heading('Titre 1', text='Titre 1')
    tree.heading('Titre 2', text='Titre 2')
    tree.heading('Années', text='Années')
    tree.heading('Type', text='Type')
    
    tree.column('Auteur', width=150)
    tree.column('Similarité', width=80)
    tree.column('Titre 1', width=200)
    tree.column('Titre 2', width=200)
    tree.column('Années', width=100)
    tree.column('Type', width=150)
    
    # Add scrollbar
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    
    # Insert data
    for case in results['duplicate_cases']:
        tree.insert('', 'end', values=(
            case['author'],
            f"{case['similarity_score']:.3f}",
            case['publication1']['title'][:40] + "..." if len(case['publication1']['title']) > 40 else case['publication1']['title'],
            case['publication2']['title'][:40] + "..." if len(case['publication2']['title']) > 40 else case['publication2']['title'],
            f"{case['publication1']['year']} / {case['publication2']['year']}",
            case['type']
        ))
    
    # Pack widgets
    tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
    scrollbar.pack(side="right", fill="y")


def display_homonyms(frame, results):
    """
    Displays detected homonyms
    
    Args:
        frame: Tkinter frame to display in
        results (dict): Analysis results
    """
    if not results['homonym_cases']:
        tk.Label(frame, text="Aucun homonyme détecté", 
                font=("Helvetica", 14, "bold"), fg="green").pack(pady=50)
        return
    
    # Create treeview to display homonyms
    columns = ('Auteur', 'Titre 1', 'Titre 2', 'Années', 'Domaines', 'Laboratoires')
    tree = ttk.Treeview(frame, columns=columns, show='headings', height=15)
    
    # Configure columns
    for col in columns:
        tree.heading(col, text=col)
    
    tree.column('Auteur', width=150)
    tree.column('Titre 1', width=200)
    tree.column('Titre 2', width=200)
    tree.column('Années', width=100)
    tree.column('Domaines', width=150)
    tree.column('Laboratoires', width=150)
    
    # Scrollbar
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    
    # Insert data
    for case in results['homonym_cases']:
        tree.insert('', 'end', values=(
            case['author'],
            case['publication1']['title'][:40] + "..." if len(case['publication1']['title']) > 40 else case['publication1']['title'],
            case['publication2']['title'][:40] + "..." if len(case['publication2']['title']) > 40 else case['publication2']['title'],
            f"{case['publication1']['year']} / {case['publication2']['year']}",
            f"{case['publication1']['domain']} / {case['publication2']['domain']}",
            f"{case['publication1']['lab']} / {case['publication2']['lab']}"
        ))
    
    tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
    scrollbar.pack(side="right", fill="y")


def display_multithesis(frame, results):
    """
    Displays multi-thesis cases
    
    Args:
        frame: Tkinter frame to display in
        results (dict): Analysis results
    """
    if not results['multi_thesis_cases']:
        tk.Label(frame, text="Aucun cas de multi-thèse détecté", 
                font=("Helvetica", 14, "bold"), fg="green").pack(pady=50)
        return
    
    # Explanatory information
    info_text = """
CAS DE MULTI-THÈSES DÉTECTÉS

Ces cas correspondent à des auteurs ayant apparemment plusieurs thèses.
Cela peut arriver dans des situations rares comme :
• Changement de spécialisation
• Thèse abandonnée puis reprise
• Erreur dans les métadonnées HAL

Vérifiez manuellement ces cas pour confirmer s'il s'agit vraiment de thèses
distinctes du même auteur ou d'autres problèmes de données.
    """
    
    info_label = tk.Label(frame, text=info_text, font=("Helvetica", 10),
                         justify="left", bg="#fff3cd", relief="ridge", bd=1)
    info_label.pack(fill="x", padx=10, pady=5)
    
    # Treeview for multi-thesis
    columns = ('Auteur', 'Titre 1', 'Titre 2', 'Écart (ans)', 'Similarité', 'Domaines')
    tree = ttk.Treeview(frame, columns=columns, show='headings', height=10)
    
    for col in columns:
        tree.heading(col, text=col)
    
    tree.column('Auteur', width=150)
    tree.column('Titre 1', width=200)
    tree.column('Titre 2', width=200)
    tree.column('Écart (ans)', width=100)
    tree.column('Similarité', width=100)
    tree.column('Domaines', width=150)
    
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    
    for case in results['multi_thesis_cases']:
        tree.insert('', 'end', values=(
            case['author'],
            case['publication1']['title'][:40] + "..." if len(case['publication1']['title']) > 40 else case['publication1']['title'],
            case['publication2']['title'][:40] + "..." if len(case['publication2']['title']) > 40 else case['publication2']['title'],
            case['year_gap'],
            f"{case['similarity_score']:.3f}",
            f"{case['publication1']['domain']} / {case['publication2']['domain']}"
        ))
    
    tree.pack(fill="both", expand=True, padx=5, pady=5)
    scrollbar.pack(side="right", fill="y")


def display_collaborators(frame, results):
    """
    Displays detected collaboration cases
    
    Args:
        frame: Tkinter frame to display in
        results (dict): Analysis results
    """
    if not results['collaborator_cases']:
        tk.Label(frame, text="Aucune collaboration détectée", 
                font=("Helvetica", 14), fg="blue").pack(pady=50)
        return
    
    # Explanatory information
    info_text = """
COLLABORATIONS DÉTECTÉES

Ces cas correspondent probablement à des auteurs qui apparaissent dans
plusieurs thèses : leur propre thèse + collaboration sur d'autres thèses.

Actions recommandées :
• Conserver la thèse principale (généralement la plus ancienne)
• Supprimer les collaborations si elles ne vous intéressent pas
• Ou les marquer comme "collaboration" pour distinction
    """
    
    info_label = tk.Label(frame, text=info_text, font=("Helvetica", 10),
                         justify="left", bg="#d1ecf1", relief="ridge", bd=1)
    info_label.pack(fill="x", padx=10, pady=5)
    
    # Simple display of collaborations
    for i, case in enumerate(results['collaborator_cases'], 1):
        case_frame = tk.Frame(frame, relief="ridge", bd=1, bg="#f8f9fa")
        case_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(case_frame, text=f"{i}. {case['author']}", 
                font=("Helvetica", 11, "bold"), bg="#f8f9fa").pack(anchor="w", padx=5, pady=2)
        
        main_thesis = case['main_thesis']['row_data']
        collaboration = case['collaboration']['row_data']
        
        tk.Label(case_frame, 
                text=f"   Thèse principale ({main_thesis['Année de Publication']}): {main_thesis['Titre'][:80]}...", 
                font=("Helvetica", 9), bg="#f8f9fa").pack(anchor="w", padx=5)
        
        tk.Label(case_frame, 
                text=f"   Collaboration ({collaboration['Année de Publication']}): {collaboration['Titre'][:80]}...", 
                font=("Helvetica", 9), bg="#f8f9fa", fg="gray").pack(anchor="w", padx=5, pady=(0,2))


def display_issues(frame, results):
    """
    Displays detected technical issues
    
    Args:
        frame: Tkinter frame to display in
        results (dict): Analysis results
    """
    if not results['no_authid_cases']:
        tk.Label(frame, text="Aucun problème technique détecté", 
                font=("Helvetica", 14, "bold"), fg="green").pack(pady=50)
        return
    
    # Explanatory information
    info_text = """
PROBLÈMES TECHNIQUES

Ces cas nécessitent une attention particulière car l'analyse automatique
n'a pas pu les traiter complètement :

• Publications sans authIdPerson_i dans HAL
• Cas ambigus nécessitant une vérification manuelle
• Problèmes de métadonnées dans HAL

Examinez ces cas manuellement pour décider de la marche à suivre.
    """
    
    info_label = tk.Label(frame, text=info_text, font=("Helvetica", 10),
                         justify="left", bg="#f8d7da", relief="ridge", bd=1)
    info_label.pack(fill="x", padx=10, pady=5)
    
    # Display issues
    text_widget = tk.Text(frame, font=("Courier", 9), wrap="word", height=20)
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text_widget.yview)
    text_widget.configure(yscrollcommand=scrollbar.set)
    
    for i, case in enumerate(results['no_authid_cases'], 1):
        text_widget.insert(tk.END, f"{i}. {case['author']} - {case['type']}\n")
        if 'publication_without_authid' in case:
            pub = case['publication_without_authid']['row_data']
            text_widget.insert(tk.END, f"   Publication: {pub['Titre'][:80]}...\n")
            text_widget.insert(tk.END, f"   Année: {pub['Année de Publication']}\n\n")
    
    text_widget.pack(side="left", fill="both", expand=True, padx=5, pady=5)
    scrollbar.pack(side="right", fill="y")
    text_widget.config(state="disabled")


def create_treatment_interface(parent_window, results, analysis_file):
    """
    Creates data treatment interface
    
    Args:
        parent_window: Parent window
        results (dict): Analysis results
        analysis_file (str): Path to analyzed file
        
    Returns:
        Toplevel: Treatment window
    """
    treatment_window = Toplevel(parent_window)
    treatment_window.title("Traitement Automatique des Données")
    treatment_window.geometry("700x600")
    treatment_window.transient(parent_window)
    treatment_window.grab_set()
    
    # Title
    tk.Label(treatment_window, text="Traitement Automatique des Données", 
            font=("Helvetica", 16, "bold")).pack(pady=10)
    
    # Statistics
    stats_frame = tk.Frame(treatment_window, relief="ridge", bd=2, bg="#f8f8f8")
    stats_frame.pack(fill="x", padx=20, pady=10)
    
    stats_text = f"""
IMPACT DU TRAITEMENT AUTOMATIQUE :

• Doublons à traiter: {len(results['duplicate_cases'])} cas
• Homonymes détectés: {len(results['homonym_cases'])} cas  
• Collaborations à examiner: {len(results['collaborator_cases'])} cas
• Multi-thèses (rares): {len(results['multi_thesis_cases'])} cas
• Problèmes techniques: {len(results['no_authid_cases'])} cas

ACTIONS DISPONIBLES :
    """
    
    tk.Label(stats_frame, text=stats_text, font=("Helvetica", 10), 
            justify="left", bg="#f8f8f8").pack(pady=10, padx=10)
    
    # Treatment options
    options_frame = tk.Frame(treatment_window)
    options_frame.pack(fill="x", padx=20, pady=10)
    
    # Variables for options
    remove_duplicates = tk.BooleanVar(value=True)
    flag_homonyms = tk.BooleanVar(value=True)
    remove_collaborations = tk.BooleanVar(value=False)
    flag_multithesis = tk.BooleanVar(value=True)
    
    tk.Label(options_frame, text="Sélectionnez les actions à effectuer:", 
            font=("Helvetica", 12, "bold")).pack(anchor="w", pady=(0, 10))
    
    tk.Checkbutton(options_frame, text="Supprimer automatiquement les doublons", 
                  variable=remove_duplicates, font=("Helvetica", 11)).pack(anchor="w", pady=2)
    
    tk.Checkbutton(options_frame, text="Marquer les homonymes (colonne 'Homonyme_Potentiel')", 
                  variable=flag_homonyms, font=("Helvetica", 11)).pack(anchor="w", pady=2)
    
    tk.Checkbutton(options_frame, text="Supprimer les collaborations (garder thèse principale)", 
                  variable=remove_collaborations, font=("Helvetica", 11)).pack(anchor="w", pady=2)
    
    tk.Checkbutton(options_frame, text="Marquer les multi-thèses (colonne 'Multi_These')", 
                  variable=flag_multithesis, font=("Helvetica", 11)).pack(anchor="w", pady=2)
    
    # Buttons
    button_frame = tk.Frame(treatment_window)
    button_frame.pack(side="bottom", pady=20)
    
    def appliquer_traitement():
        """Applies selected treatment"""
        try:
            # Load original data
            original_df = pd.read_csv(analysis_file)
            processed_df = original_df.copy()
            
            actions_performed = []
            indices_to_remove = set()
            
            # Treat duplicates
            if remove_duplicates.get() and results['duplicate_cases']:
                for case in results['duplicate_cases']:
                    # Keep publication1, remove publication2
                    indices_to_remove.add(case['publication2']['index'])
                
                actions_performed.append(f"Supprimé {len(set(case['publication2']['index'] for case in results['duplicate_cases']))} doublons")
            
            # Treat collaborations
            if remove_collaborations.get() and results['collaborator_cases']:
                for case in results['collaborator_cases']:
                    # Remove collaboration, keep main thesis
                    collab_index = case['collaboration']['row_data'].name
                    if collab_index in processed_df.index:
                        indices_to_remove.add(collab_index)
                
                actions_performed.append(f"Supprimé {len(results['collaborator_cases'])} collaborations")
            
            # Remove marked indices
            if indices_to_remove:
                processed_df = processed_df.drop(indices_to_remove).reset_index(drop=True)
                
            homonym_count = 0
            multithesis_count = 0

            # Count homonyms 
            if flag_homonyms.get() and results['homonym_cases']:
                for case in results['homonym_cases']:
                    # Count publications marked as potential homonyms
                    for pub_key in ['publication1', 'publication2']:
                        pub_index = case[pub_key]['index']
                        if pub_index in processed_df.index and pub_index not in indices_to_remove:
                            homonym_count += 1
    
                actions_performed.append(f"Identifié {homonym_count} publications comme homonymes potentiels (non marquées dans le fichier)")

            # Count multi-thesis 
            if flag_multithesis.get() and results['multi_thesis_cases']:
                for case in results['multi_thesis_cases']:
                    for pub_key in ['publication1', 'publication2']:
                        pub_index = case[pub_key]['index']
                        if pub_index in processed_df.index and pub_index not in indices_to_remove:
                            multithesis_count += 1
    
                actions_performed.append(f"Identifié {multithesis_count} publications comme multi-thèses (non marquées dans le fichier)")
            
            # Save processed file
            base_name = os.path.splitext(os.path.basename(analysis_file))[0]
            processed_filename = f"{base_name}_nettoye.csv"
            extraction_dir = 'extraction'
            if not os.path.exists(extraction_dir):
                os.makedirs(extraction_dir)
                
            processed_path = os.path.join(extraction_dir, processed_filename)
            processed_df.to_csv(processed_path, index=False)

            # Success message
            success_msg = f"TRAITEMENT TERMINÉ AVEC SUCCÈS\n\n"
            success_msg += f"Publications originales: {len(original_df)}\n"
            success_msg += f"Publications après traitement: {len(processed_df)}\n"
            success_msg += f"Publications supprimées: {len(original_df) - len(processed_df)}\n\n"
            
            if actions_performed:
                success_msg += "Actions effectuées:\n"
                for action in actions_performed:
                    success_msg += f"   • {action}\n"
            
            success_msg += f"\nFichier sauvegardé: {processed_path}"
            
            messagebox.showinfo("Traitement terminé", success_msg)
            treatment_window.destroy()
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du traitement: {str(e)}")
    
    tk.Button(button_frame, text="Annuler", 
             command=treatment_window.destroy, font=("Helvetica", 11),
             width=12).pack(side="left", padx=5)
    
    tk.Button(button_frame, text="Appliquer le traitement", 
             command=appliquer_traitement, font=("Helvetica", 11, "bold"),
             bg="#4CAF50", fg="white", width=20).pack(side="right", padx=5)
    
    return treatment_window


def export_results_interface(results, analysis_file):
    """
    Results export interface
    
    Args:
        results (dict): Analysis results
        analysis_file (str): Path to analyzed file
    """
    export_dir = filedialog.askdirectory(
        title="Choisir le dossier d'exportation",
        initialdir="extraction"
    )
    
    if not export_dir:
        return
    
    try:
        base_name = os.path.splitext(os.path.basename(analysis_file))[0]
        exported_files = []
        
        # Export duplicates
        if results['duplicate_cases']:
            dup_df = pd.DataFrame([
                {
                    'Auteur': case['author'],
                    'Type': case['type'],
                    'Titre_1': case['publication1']['title'],
                    'Titre_2': case['publication2']['title'],
                    'Annee_1': case['publication1']['year'],
                    'Annee_2': case['publication2']['year'],
                    'Similarite': case['similarity_score'],
                    'Ecart_ans': case['year_gap'],
                    'Docid_1': case['publication1']['docid'],
                    'Docid_2': case['publication2']['docid']
                }
                for case in results['duplicate_cases']
            ])
            dup_path = os.path.join(export_dir, f'{base_name}_doublons_detecte.csv')
            dup_df.to_csv(dup_path, index=False)
            exported_files.append(dup_path)
        
        # Export homonyms
        if results['homonym_cases']:
            hom_df = pd.DataFrame([
                {
                    'Auteur': case['author'],
                    'Type': case['type'],
                    'Titre_1': case['publication1']['title'],
                    'Titre_2': case['publication2']['title'],
                    'Annee_1': case['publication1']['year'],
                    'Annee_2': case['publication2']['year'],
                    'Domaine_1': case['publication1']['domain'],
                    'Domaine_2': case['publication2']['domain'],
                    'Laboratoire_1': case['publication1']['lab'],
                    'Laboratoire_2': case['publication2']['lab'],
                    'AuthIds_1': str(case['publication1']['authids']) if 'authids' in case['publication1'] else '',
                    'AuthIds_2': str(case['publication2']['authids']) if 'authids' in case['publication2'] else ''
                }
                for case in results['homonym_cases']
            ])
            hom_path = os.path.join(export_dir, f'{base_name}_homonymes_detecte.csv')
            hom_df.to_csv(hom_path, index=False)
            exported_files.append(hom_path)
        
        # Export multi-thesis
        if results['multi_thesis_cases']:
            multi_df = pd.DataFrame([
                {
                    'Auteur': case['author'],
                    'Type': case['type'],
                    'Titre_1': case['publication1']['title'],
                    'Titre_2': case['publication2']['title'],
                    'Annee_1': case['publication1']['year'],
                    'Annee_2': case['publication2']['year'],
                    'Ecart_ans': case['year_gap'],
                    'Similarite': case['similarity_score'],
                    'Domaine_1': case['publication1']['domain'],
                    'Domaine_2': case['publication2']['domain']
                }
                for case in results['multi_thesis_cases']
            ])
            multi_path = os.path.join(export_dir, f'{base_name}_multi_theses.csv')
            multi_df.to_csv(multi_path, index=False)
            exported_files.append(multi_path)
        
        # Export collaborations
        if results['collaborator_cases']:
            collab_df = pd.DataFrame([
                {
                    'Auteur': case['author'],
                    'Type': case['type'],
                    'These_principale_annee': case['main_thesis']['row_data']['Année de Publication'],
                    'These_principale_titre': case['main_thesis']['row_data']['Titre'],
                    'Collaboration_annee': case['collaboration']['row_data']['Année de Publication'],
                    'Collaboration_titre': case['collaboration']['row_data']['Titre']
                }
                for case in results['collaborator_cases']
            ])
            collab_path = os.path.join(export_dir, f'{base_name}_collaborations.csv')
            collab_df.to_csv(collab_path, index=False)
            exported_files.append(collab_path)
        
        # Export detailed summary
        summary_path = os.path.join(export_dir, f'{base_name}_resume_detecte.txt')
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("RÉSUMÉ DE L'ANALYSE \n")
            f.write("="*60 + "\n\n")
            f.write(f"Fichier analysé: {os.path.basename(analysis_file)}\n")
            f.write(f"Date d'analyse: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            summary = results['summary']
            f.write("STATISTIQUES GLOBALES:\n")
            f.write(f"Publications totales: {summary['total_publications']}\n")
            f.write(f"Auteurs avec publications multiples: {summary['authors_with_multiple_pubs']}\n\n")
            
            f.write("DÉTECTIONS:\n")
            f.write(f"Doublons: {summary['duplicate_publications']}\n")
            f.write(f"Homonymes: {summary['homonym_publications']}\n")
            f.write(f"Multi-thèses: {summary['multi_thesis_publications']}\n")
            f.write(f"Collaborations: {len(results['collaborator_cases'])}\n")
            f.write(f"Problèmes techniques: {len(results['no_authid_cases'])}\n\n")
            
            f.write("MÉTHODE UTILISÉE:\n")
            f.write("• Algorithme basé sur authIdPerson_i de HAL\n")
            f.write("• Seuil de similarité des titres: 0.8\n")
            f.write("• Seuil d'écart temporel: 2 ans\n")
            f.write("• Détection automatique des collaborations\n")
            f.write("• Gestion robuste des cas sans authIdPerson_i\n")
        
        exported_files.append(summary_path)
        
        # Success message
        files_list = '\n'.join([f"   • {os.path.basename(f)}" for f in exported_files])
        messagebox.showinfo(
            "Exportation terminée",
            f"Résultats exportés avec succès:\n\n{files_list}\n\nDans le dossier:\n{export_dir}"
        )
        
    except Exception as e:
        messagebox.showerror("Erreur", f"Erreur lors de l'exportation: {str(e)}")


def show_recommendations(results):
    """
    Displays recommendations based on analysis
    
    Args:
        results (dict): Analysis results
    """
    rec_window = Toplevel()
    rec_window.title("Recommandations")
    rec_window.geometry("700x600")
    
    tk.Label(rec_window, text="Recommandations d'Actions", 
            font=("Helvetica", 16, "bold")).pack(pady=10)
    
    # Analyze results to generate recommendations
    recommendations = []
    
    if results['duplicate_cases']:
        recommendations.append({
            'priority': 'HIGH',
            'title': f'Traiter {len(results["duplicate_cases"])} doublons détectés',
            'description': 'Action recommandée: Suppression automatique des doublons (conserver la première occurrence)',
            'action': 'Utiliser le traitement automatique avec suppression des doublons activée'
        })
    
    if results['homonym_cases']:
        recommendations.append({
            'priority': 'MEDIUM',
            'title': f'Examiner {len(results["homonym_cases"])} cas d\'homonymes',
            'description': 'Utilisez les informations de laboratoire pour identifier le bon auteur',
            'action': 'Marquer comme homonymes et examiner manuellement pour validation'
        })
    
    if results['collaborator_cases']:
        recommendations.append({
            'priority': 'MEDIUM',
            'title': f'Décider du sort des {len(results["collaborator_cases"])} collaborations',
            'description': 'Ces publications représentent probablement des collaborations plutôt que des thèses principales',
            'action': 'Considérer la suppression si seules les thèses principales vous intéressent'
        })
    
    if results['multi_thesis_cases']:
        recommendations.append({
            'priority': 'LOW',
            'title': f'Vérifier {len(results["multi_thesis_cases"])} cas de multi-thèses',
            'description': 'Cas rares nécessitant une vérification manuelle',
            'action': 'Examiner individuellement pour confirmer la validité'
        })
    
    if results['no_authid_cases']:
        recommendations.append({
            'priority': 'LOW',
            'title': f'Résoudre {len(results["no_authid_cases"])} problèmes techniques',
            'description': 'Publications sans authIdPerson_i ou cas ambigus',
            'action': 'Examen manuel requis - métadonnées HAL incomplètes'
        })
    
    # General recommendations
    if not any([results['duplicate_cases'], results['homonym_cases'], results['collaborator_cases']]):
        recommendations.append({
            'priority': 'INFO',
            'title': 'Données de bonne qualité détectées',
            'description': 'Peu ou pas de problèmes détectés dans votre jeu de données',
            'action': 'Aucune action spécifique requise'
        })
    
    # Display recommendations
    canvas = tk.Canvas(rec_window)
    scrollbar = ttk.Scrollbar(rec_window, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    # Colors by priority
    priority_colors = {
        'HIGH': '#ffebee',
        'MEDIUM': '#fff3e0', 
        'LOW': '#e8f5e8',
        'INFO': '#e3f2fd'
    }
    
    for i, rec in enumerate(recommendations, 1):
        rec_frame = tk.Frame(scrollable_frame, relief="ridge", bd=2, 
                            bg=priority_colors.get(rec['priority'], '#f5f5f5'))
        rec_frame.pack(fill="x", padx=10, pady=5)
        
        # Header with priority
        header_frame = tk.Frame(rec_frame, bg=priority_colors.get(rec['priority'], '#f5f5f5'))
        header_frame.pack(fill="x", padx=5, pady=2)
        
        tk.Label(header_frame, text=f"{i}. {rec['title']}", 
                font=("Helvetica", 11, "bold"),
                bg=priority_colors.get(rec['priority'], '#f5f5f5')).pack(anchor="w")
        
        tk.Label(header_frame, text=f"Priorité: {rec['priority']}", 
                font=("Helvetica", 9),
                bg=priority_colors.get(rec['priority'], '#f5f5f5'),
                fg="gray").pack(anchor="e")
        
        # Description
        tk.Label(rec_frame, text=rec['description'], 
                font=("Helvetica", 10), wraplength=600,
                bg=priority_colors.get(rec['priority'], '#f5f5f5'),
                justify="left").pack(anchor="w", padx=5, pady=2)
        
        # Recommended action
        tk.Label(rec_frame, text=f"Action: {rec['action']}", 
                font=("Helvetica", 10, "italic"),
                bg=priority_colors.get(rec['priority'], '#f5f5f5'),
                fg="navy").pack(anchor="w", padx=5, pady=2)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # Close button
    tk.Button(rec_window, text="Fermer", command=rec_window.destroy,
             font=("Helvetica", 11), width=15).pack(side="bottom", pady=10)


def remplacer_ancienne_detection():
    """Function to launch detection in app.py"""
    return detection_doublons_homonymes