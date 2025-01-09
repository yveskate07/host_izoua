import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

# Charger un jeu de données intégré (par exemple, tips)
data = sns.load_dataset('tips')

# Calculer la moyenne des pourboires pour chaque jour
mean_tips = data.groupby('day')['tip'].mean().reset_index()

# Mapper les valeurs des pourboires sur une palette de couleurs (chaud -> froid)
norm = plt.Normalize(mean_tips['tip'].min(), mean_tips['tip'].max())
colors = plt.cm.coolwarm(norm(mean_tips['tip']))

# Créer un barplot avec des couleurs personnalisées
sns.barplot(x='day', y='tip', data=mean_tips, ci=None, palette=colors)

# Ajouter des titres et des étiquettes
plt.title("Pourboires moyens par jour avec couleurs chaud-froid")
plt.xlabel("Jour")
plt.ylabel("Pourboire moyen")

# Afficher le graphique
#plt.show()

print(f"data: {data.to_string()}")


print(f"means: {mean_tips}")