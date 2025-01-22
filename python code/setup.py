from setuptools import setup, find_packages

setup(
    name="hal-publication",  # Nom projet
    version="1.0.0",
    description="Outil pour analyser les publications scientifiques avec la base HAL",
    authors="chancella Litoko, Anas Nay",
    author_email="litoko.13chancella@gmail.com , anasnay7@gmail.com",
    packages=find_packages(),  # Trouver tous les packages Python dans le projet
    include_package_data=True,  # Inclure tous les fichiers de données 
    install_requires=[
        "fpdf",        
        "pandas",      
        "tqdm",        
        "plotly",      
        "requests",    
        "unidecode",
        "kaleido" ,
        "tkinter" ,
        "matplotlib" 
    ],
    entry_points={
        "console_scripts": [
            "hal-publication=main:main",  # Ajouter une commande CLI pour exécuter votre projet
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",  # Version minimale de Python requise
)
