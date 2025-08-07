# -*- coding: utf-8 -*-

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
    Return the list of available domains for filtering.
    """
    return domain_mapping

def get_domain_code(domain_name):
    reverse_mapping = {v.lower(): k for k, v in domain_mapping.items()}
    return reverse_mapping.get(domain_name.lower(), None)

# Types of documents with HDR codes

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

# Mapping function for documents types and domains
def map_doc_type(doc_type):
    """
    Map document type with debug for unknown types
    """
    if not doc_type:
        return "Type non défini"
    
    mapped = type_mapping.get(doc_type, None)
    if mapped is None:
        return f"Type non défini (Code: {doc_type})"
    
    return mapped

def list_types():
    """
    Return the list of available type documents for filtering.
    """
    return type_mapping

def get_type_code(type_name):
    reverse_mapping = {v.lower(): k for k, v in type_mapping.items()}
    return reverse_mapping.get(type_name.lower(), None)

def get_linked_types(type_codes):
    """    
    Args:
        type_codes (list): List of the selectionned types codes
    
    Returns:
        list: List of the HAL codes tu use during the request
    """
    if not type_codes:
        return type_codes
    
    # Create a copy to avoid modificating the orifinal list
    hal_codes = []
    
    # ALL POSSIBLE HDR CODES
    hdr_codes = ["HDR", "HABDIR", "HABIL", "HABILITATION", "HDR_SOUTENANCE", "HDR_DEFENSE", "MEMHDR"]
    
    for type_code in type_codes:
        if type_code == "THESE":
            # "Thèse" → THESE + all HDR codes
            if "THESE" not in hal_codes:
                hal_codes.append("THESE")
            for hdr_code in hdr_codes:
                if hdr_code not in hal_codes:
                    hal_codes.append(hdr_code)
                
        elif type_code == "THESE_DOCTORANT":
            # "Thèse (Doctorant)" → THESE only
            if "THESE" not in hal_codes:
                hal_codes.append("THESE")
                
        elif type_code == "HDR":
            if "THESE" not in hal_codes:
                hal_codes.append("THESE")
            for hdr_code in hdr_codes:
                if hdr_code not in hal_codes:
                    hal_codes.append(hdr_code)
                
        elif type_code == "THESE_HDR":
            # "Thèse (HDR)" → only all HDR codes
            for hdr_code in hdr_codes:
                if hdr_code not in hal_codes:
                    hal_codes.append(hdr_code)
                
        else:
            # Other types : normal behaviour
            hal_codes.append(type_code)
    
    return hal_codes

def get_hal_filter_for_post_processing(type_filter):
    """
    Return list of HAL types to accept during post-filtering
    
    Args:
        type_filter (list): List of types selectionned by the user
    
    Returns:
        set: All HAL types to accept in the results
    """
    if not type_filter:
        return None
    
    accepted_hal_types = set()
    
    # ALL POSSIBLE HDR CODES
    hdr_codes = ["HDR", "HABDIR", "HABIL", "HABILITATION", "HDR_SOUTENANCE", "HDR_DEFENSE", "MEMHDR"]
    
    for type_name in type_filter:
        type_code = get_type_code(type_name)
        
        if type_code == "THESE":
            # "Thèse" → accept THESE and all HDR codes
            accepted_hal_types.add("THESE")
            for hdr_code in hdr_codes:
                accepted_hal_types.add(hdr_code)
            
        elif type_code == "THESE_DOCTORANT":
            # "Thèse (Doctorant)" → accept THESE only
            accepted_hal_types.add("THESE")
            
        elif type_code == "HDR":
            # "Habilitation à diriger des recherches" → accept THESE and all HDR codes
            accepted_hal_types.add("THESE")
            for hdr_code in hdr_codes:
                accepted_hal_types.add(hdr_code)
            
        elif type_code == "THESE_HDR":
            # "Thèse (HDR)" → accept only all HDR codes
            for hdr_code in hdr_codes:
                accepted_hal_types.add(hdr_code)
            
        else:
            # Other types
            if type_code:
                accepted_hal_types.add(type_code)
    
    return accepted_hal_types