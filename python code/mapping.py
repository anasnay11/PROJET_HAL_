# -*- coding: utf-8 -*-
"""
Created on Mon Dec  2 16:34:48 2024


"""

# mapping.py

# Domaine

domain_mapping = {
     "0.shs": "Sciences humaines et sociales",
    "0.sdv": "Sciences du vivant",
    "0.phys": "Physique",
    "0.info": "Informatique",
    "0.spi": "Sciences de l'ingénieur",
    "0.sde": "Sciences de l'environnement",
    "0.chim": "Chimie",
    "0.sdu": "Sciences de l'Univers",
    "0.math": "Mathématiques",
    "0.stat": "Statistiques",
    "1.shs.droit": "Droit",
    "1.shs.hist": "Histoire",
    "1.shs.litt": "Littérature",
    "1.shs.archeo": "Archéologie",
    "1.shs.socio": "Sociologie",
    "1.shs.eco": "Économie",
    "1.shs.geo": "Géographie",
    "1.shs.langue": "Langues",
    "1.shs.gestion": "Gestion",
    "1.shs.edu": "Sciences de l'éducation",
    "1.shs.scipo": "Sciences politiques",
    "1.shs.art": "Arts",
    "1.phys.phys": "Physique générale",
    "1.phys.meca": "Mécanique",
    "1.phys.cond": "Physique de la matière condensée",
    "1.phys.astr": "Astronomie",
    "1.phys.hist": "Histoire de la physique",
    "1.phys.nexp": "Physique nucléaire expérimentale",
    "1.phys.hexp": "Physique des hautes énergies expérimentale",
    "1.math.math-ap": "Mathématiques appliquées",
    "1.math.math-pr": "Mathématiques pures",
    "1.math.math-st": "Statistiques",
    "1.math.math-oc": "Optimisation et contrôle",
    "1.info.info-ai": "Intelligence artificielle",
    "1.info.info-mo": "Modélisation et simulation",
    "1.info.info-ts": "Théorie des systèmes",
    "1.info.info-ni": "Réseaux informatiques",
    "1.spi.signal": "Traitement du signal",
    "1.spi.mat": "Matériaux",
    "1.spi.gproc": "Génie des procédés",
    "1.spi.auto": "Automatique",
    "1.spi.elec": "Électronique",
    "1.spi.opti": "Optique",
    "1.spi.nano": "Nanotechnologies",
    "1.spi.tron": "Microélectronique",
    "1.sde.be": "Biodiversité et écologie",
    "1.sde.es": "Environnement et société",
    "1.sde.ie": "Ingénierie écologique",
    "1.sde.mcg": "Modélisation en géosciences",
    "1.sdu.stu": "Sciences de la Terre",
    "1.sdu.ocean": "Océanographie",
    "1.sdu.astr": "Astrophysique",
    "1.chim.mate": "Matériaux en chimie",
    "1.chim.orga": "Chimie organique",
    "1.chim.cata": "Catalyse",
    "1.chim.theo": "Chimie théorique",
    "1.chim.anal": "Chimie analytique",
    "1.chim.poly": "Polymères",
    "1.sdv.bbm": "Biologie cellulaire et moléculaire",
    "1.sdv.neu": "Neurosciences",
    "1.sdv.spee": "Écologie des populations et des écosystèmes",
    "1.sdv.bc": "Biologie structurale",
    "1.sdv.aen": "Agronomie et environnement",
    "1.sdv.gen": "Génétique",
    "1.sdv.sp": "Santé publique",
    "1.sdv.can": "Cancer",
    "1.sdv.ib": "Biologie intégrative",
    "1.sdv.imm": "Immunologie",
    "1.sdv.bid": "Bioinformatique",
    "1.sdv.mp": "Médecine et santé mentale",
    "1.sdv.sa": "Sciences animales",
    "1.shs.phil": "Philosophie",
    "1.shs.anthro-se": "Anthropologie",
    "1.shs.museo": "Muséologie",
    "1.shs.psy": "Psychologie",
    "1.shs.archi": "Architecture",
    "1.shs.class": "Études classiques",
    "1.shs.musiq": "Musicologie",
    "1.shs.relig": "Religions",
}

def map_domain(domain):
    if isinstance(domain, list):
        return ', '.join([domain_mapping.get(d, "Domaine non défini") for d in domain])
    else:
        return domain_mapping.get(domain, "Domaine non défini")

def list_domains():
    """
    Retourne la liste des domaines disponibles pour le filtrage.
    """
    return domain_mapping

def get_domain_code(domain_name):
    reverse_mapping = {v.lower(): k for k, v in domain_mapping.items()}
    return reverse_mapping.get(domain_name.lower(), None)

# Type de documents avec codes HDR étendus

type_mapping = {
    "ART": "Article de journal",
    "COMM": "Communication dans une conférence",
    "POSTER": "Affiche",
    "COUV": "Chapitre d'ouvrage",
    "OUV": "Ouvrage",
    "THESE": "Thèse",
    "THESE_DOCTORANT": "Thèse (Doctorant)",
    "THESE_HDR": "Thèse (HDR)",  
    "REPORT": "Rapport",
    "UNDEFINED": "Non défini",
    "SYNTHESE": "Synthèse",
    "REPORT_FPROJ": "Rapport de projet final",
    "REPORT_GLICE": "Rapport général de licence",
    "ETABTHESE": "Thèse d'établissement",
    "REPACT": "Rapport d'activité",
    "MEMLIC": "Mémoire de licence",
    "REPORT_RFOINT": "Rapport de recherche internationale",
    "REPORT_COOR": "Rapport de coordination",
    "SOFTWARE": "Logiciel",
    "PRESCONF": "Présentation en conférence",
    "OTHER": "Autre"
}

# Fonctions de mapping pour les types de documents et les domaines
def map_doc_type(doc_type):
    """
    🔧 ENHANCED: Map document type with debug for unknown types
    """
    if not doc_type:
        return "Type non défini"
    
    mapped = type_mapping.get(doc_type, None)
    if mapped is None:
        return f"Type non défini (Code: {doc_type})"
    
    return mapped

def list_types():
    """
    Retourne la liste des types de documents disponibles pour le filtrage.
    """
    return type_mapping

def get_type_code(type_name):
    reverse_mapping = {v.lower(): k for k, v in type_mapping.items()}
    return reverse_mapping.get(type_name.lower(), None)

def get_linked_types(type_codes):
    """
    🔧 ENHANCED: Gère les nouveaux types de thèses avec granularité et codes HDR étendus
    
    Args:
        type_codes (list): Liste des codes de types sélectionnés
    
    Returns:
        list: Liste des codes HAL à utiliser dans la requête
    """
    if not type_codes:
        return type_codes
    
    # Créer une copie pour éviter de modifier la liste originale
    hal_codes = []
    
    # 🔧 ALL POSSIBLE HDR CODES
    hdr_codes = ["HDR", "HABDIR", "HABIL", "HABILITATION", "HDR_SOUTENANCE", "HDR_DEFENSE", "MEMHDR"]
    
    for type_code in type_codes:
        if type_code == "THESE":
            # "Thèse" (ancien comportement) → THESE + tous les codes HDR
            if "THESE" not in hal_codes:
                hal_codes.append("THESE")
            for hdr_code in hdr_codes:
                if hdr_code not in hal_codes:
                    hal_codes.append(hdr_code)
                
        elif type_code == "THESE_DOCTORANT":
            # "Thèse (Doctorant)" → seulement THESE
            if "THESE" not in hal_codes:
                hal_codes.append("THESE")
                
        elif type_code == "HDR":
            if "THESE" not in hal_codes:
                hal_codes.append("THESE")
            for hdr_code in hdr_codes:
                if hdr_code not in hal_codes:
                    hal_codes.append(hdr_code)
                
        elif type_code == "THESE_HDR":
            # "Thèse (HDR)" → seulement tous les codes HDR
            for hdr_code in hdr_codes:
                if hdr_code not in hal_codes:
                    hal_codes.append(hdr_code)
                
        else:
            # Autres types : comportement normal
            hal_codes.append(type_code)
    
    return hal_codes

def get_hal_filter_for_post_processing(type_filter):
    """
    🔧 ENHANCED: Retourne les types HAL à accepter lors du post-filtrage avec codes HDR étendus
    
    Args:
        type_filter (list): Liste des types sélectionnés par l'utilisateur
    
    Returns:
        set: Ensemble des types HAL à accepter dans les résultats
    """
    if not type_filter:
        return None
    
    accepted_hal_types = set()
    
    # 🔧 ALL POSSIBLE HDR CODES
    hdr_codes = ["HDR", "HABDIR", "HABIL", "HABILITATION", "HDR_SOUTENANCE", "HDR_DEFENSE", "MEMHDR"]
    
    for type_name in type_filter:
        type_code = get_type_code(type_name)
        
        if type_code == "THESE":
            # "Thèse" → accepter THESE et tous les codes HDR
            accepted_hal_types.add("THESE")
            for hdr_code in hdr_codes:
                accepted_hal_types.add(hdr_code)
            
        elif type_code == "THESE_DOCTORANT":
            # "Thèse (Doctorant)" → accepter seulement THESE
            accepted_hal_types.add("THESE")
            
        elif type_code == "HDR":
            # "Habilitation à diriger des recherches" → accepter THESE et tous les codes HDR
            accepted_hal_types.add("THESE")
            for hdr_code in hdr_codes:
                accepted_hal_types.add(hdr_code)
            
        elif type_code == "THESE_HDR":
            # "Thèse (HDR)" → accepter seulement tous les codes HDR
            for hdr_code in hdr_codes:
                accepted_hal_types.add(hdr_code)
            
        else:
            # Autres types
            if type_code:
                accepted_hal_types.add(type_code)
    
    return accepted_hal_types