import os

import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'izouapp', 'images','img_gen_from_charts')# chemin où seront stocké les fichiers img

def generate_barplots(file_name, ylab, legend, title=None, xlab=None, data = None, cat=None):
    # Création des datasets
    """data = {
        "Catégorie": ["A", "B", "C", "D"],
        "Dataset_1": [10, 15, 7, 20],
        "Dataset_2": [12, 13, 9, 18]
    }"""

    # Transformation des données en format long pour Seaborn
    df = pd.DataFrame(data)
    df_melted = pd.melt(df, id_vars="Catégorie", var_name="Dataset", value_name="Valeur")

    # Configuration de Seaborn
    sns.set_theme(style="whitegrid")

    # Création du barplot groupé
    plt.figure(figsize=(8, 5))
    barplot = sns.barplot(
        x="Catégorie", y="Valeur", hue="Dataset", data=df_melted, palette="viridis"
    )

    # Annotation des valeurs sur les barres
    for p in barplot.patches:
        barplot.annotate(
            format(p.get_height(), '.1f'),  # Formatage de la valeur
            (p.get_x() + p.get_width() / 2., p.get_height()),  # Position (x, y)
            ha='center', va='center', fontsize=13, color='black', xytext=(0, 5),  # Décalage en y
            textcoords='offset points'
        )

    # Ajout de titres et labels
    #plt.title(title, fontsize=16)
    if xlab:
        plt.xlabel(xlab, fontsize=15)
    else:
        plt.xlabel('', fontsize=15)
    plt.ylabel(ylab, fontsize=15)
    plt.legend(title=legend, fontsize=13)

    # Sauvegarde du graphique
    plt.savefig(os.path.join(img_path,file_name), dpi=300, bbox_inches="tight")

    #return os.path.join(img_path,file_name)
    return file_name


def generate_polarArea(file_name, categories, values, title=None):

    if not values:
        return None

    # Calcul des angles pour chaque catégorie
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()

    # Fermeture du graphique (ajout du premier point à la fin)
    values += values[:1]
    angles += angles[:1]

    # Création de la figure
    #fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={'polar': True})
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={'projection': 'polar'})

    # Tracé du graphique
    #ax.fill(angles, values, color='skyblue', alpha=0.4)  # Remplissage
    #ax.plot(angles, values, color='blue', linewidth=2)  # Contour
    ax.fill(angles, values, color='lightblue', alpha=0.6, edgecolor='blue', linewidth=2)
    ax.plot(angles, values, color='blue', linewidth=2)

    # Ajouter les labels des catégories
    ax.set_yticks(range(0, max(values), 5))  # Ajuste les ticks sur l'axe radial
    #ax.set_xticks(angles[:-1])
    #ax.set_xticklabels(categories)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=15, fontweight='bold')

    # Ajout des annotations des valeurs
    for angle, value in zip(angles[:-1], values[:-1]):
        ax.text(
            angle, value + 2, f"{value:.1f}",  # Texte avec valeur
            ha='center', va='center', fontsize=10, color='black',
            bbox=dict(facecolor='white', edgecolor='none', boxstyle='round,pad=0.3')
        )

    # Titre
    #plt.title(title, fontsize=16, pad=20)

    # Sauvegarde
    plt.savefig(os.path.join(img_path,file_name), dpi=300, bbox_inches="tight")

    #return os.path.join(img_path,file_name)
    return file_name