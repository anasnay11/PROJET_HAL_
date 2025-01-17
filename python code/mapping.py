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

# Type de documents

type_mapping = {
    "ART": "Article de journal",
    "COMM": "Communication dans une conférence",
    "POSTER": "Affiche",
    "COUV": "Chapitre d'ouvrage",
    "OUV": "Ouvrage",
    "THESE": "Thèse",
    "HDR": "Habilitation à diriger des recherches",
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
    return type_mapping.get(doc_type, "Type non défini")

def list_types():
    """
    Retourne la liste des types de documents disponibles pour le filtrage.
    """
    return type_mapping

def get_type_code(type_name):
    reverse_mapping = {v.lower(): k for k, v in type_mapping.items()}
    return reverse_mapping.get(type_name.lower(), None)