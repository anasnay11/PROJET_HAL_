# SOFTWARE PROJECT :  "Extracting publication data and statistics from HAL database" 

## CONTEXT:

 In France, researchers are expected to upload their publications to a database known as HAL. This database
 contains recent publications from the French scienti c community. It is useful to leverage this database to
 generate statistics on the various topics scientists are working on, as well as the venues (conferences, journals)
 where they publish their results.
 In this project, we aim to design a tool for analyzing the publication habits of scientists working in a given
 domain, using the HAL database.
 More specically, we will focus on Working Groups (GDR) and research laboratories of the INS2I institute
 of CNRS. Our goal is to understand the publishing habits of researchers who are members of GDRs or research
 laboratories within INS2I. The task is to extend an existing Python codebase so that it can perform the following
 tasks.
 Given a list of scientists (including their names, professional email addresses, and employers) working in a
 speci c GDR or research laboratory, and a list of research topics pursued in that GDR or laboratory, the task
 is to extract the following information from the HAL database:
 Extract the publications of all scientists on the list for a given period.
 Extract the unique HAL IDs of the scientists.
 For each scientist, extract the topics they have published on and the venues (conferences, journals, etc.).
 Visualize statistics (histograms, distribution curves, pie charts, etc.) on the various topics the scientists
 have published on.
 Visualize the time evolution of the number of publications in di erent venues and on di erent topics.
 Automatically generate reports on publications according to various criteria.

## OBJECTIF:

L’objectif principal de ce projet est de developper un outil interactif et intuitif permettant l’extraction, l’analyse et la visualisation de donnees scientifiques issues de l’API HAL. 
HAL est une plateforme d’archivage ouverte qui centralise des publications scientifiques provenant de differentes institutions et chercheurs.
Cet outil vise a faciliter l’exploration et l’exploitation des donnees de recherche en offrant des fonctionnalites cles, telles que :

 **• Extraction de donnees :** Recuperer automatiquement les publications scientifiques selon des criteres definis (periodes, domaines, types de documents...).
 
 **• Visualisation graphique :** Generer des graphiques interactifs (histogrammes, graphiques en barres, tendances temporelles...) pour representer visuellement les
 statistiques issues des donnees extraites.
 
 **• Rapports automatises :** Produire des rapports complets au format PDF ou LaTeX integrant les graphiques generes pour une presentation claire et professionnelle.
 
