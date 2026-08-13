# ============================================================================
# GENERATE_DATA.PY — Générateur de données factices pour DASHBOARD-IA PAM TOGO
# ----------------------------------------------------------------------------
# Ce script crée un fichier Excel "donnees_pam.xlsx" avec 300 lignes de
# données simulées mais réalistes de distributions d'aide alimentaire du PAM
# dans les 5 régions du Togo.
#
# À exécuter UNE SEULE FOIS (ou à chaque fois que vous voulez régénérer un
# jeu de données de démonstration) :
#       python generate_data.py
# ============================================================================

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# On fixe la graine aléatoire pour que les données générées soient toujours
# les mêmes d'une exécution à l'autre (pratique pour les démonstrations).
np.random.seed(42)

# ----------------------------------------------------------------------------
# 1) RÉFÉRENTIEL GÉOGRAPHIQUE DU TOGO
# ----------------------------------------------------------------------------
# Pour chaque région, on définit :
#   - une liste de préfectures réelles
#   - les coordonnées GPS (latitude, longitude) du chef-lieu régional
#     (utilisées comme centre pour générer des points dispersés autour)
REGIONS = {
    "Maritime": {
        "prefectures": ["Golfe", "Avé", "Vo", "Yoto", "Zio", "Lacs", "Bas-Mono"],
        "chef_lieu": "Lomé",
        "lat": 6.1319,
        "lon": 1.2228,
    },
    "Plateaux": {
        "prefectures": ["Ogou", "Wawa", "Amou", "Kloto", "Danyi", "Akébou", "Anié", "Haho"],
        "chef_lieu": "Atakpamé",
        "lat": 7.5299,
        "lon": 1.1147,
    },
    "Centrale": {
        "prefectures": ["Tchamba", "Tchaoudjo", "Sotouboua", "Blitta"],
        "chef_lieu": "Sokodé",
        "lat": 8.9833,
        "lon": 1.1333,
    },
    "Kara": {
        "prefectures": ["Kozah", "Bassar", "Assoli", "Bimah", "Dankpen", "Doufelgou", "Kéran"],
        "chef_lieu": "Kara",
        "lat": 9.5511,
        "lon": 1.1861,
    },
    "Savanes": {
        "prefectures": ["Tône", "Cinkassé", "Kpendjal", "Oti", "Tandjouaré", "Oti-Sud"],
        "chef_lieu": "Dapaong",
        "lat": 10.8631,
        "lon": 0.2064,
    },
}

TYPES_AIDE = ["Vivres", "Cash Transfert", "Nutrition", "Cantines Scolaires", "Résilience"]

N_LIGNES = 300

# ----------------------------------------------------------------------------
# 2) GÉNÉRATION DES DATES DE DISTRIBUTION
# ----------------------------------------------------------------------------
# On génère des dates réparties sur 18 mois (janvier 2024 à juin 2025) afin
# de pouvoir tracer une courbe d'évolution temporelle crédible.
date_debut = datetime(2024, 1, 1)
date_fin = datetime(2025, 6, 30)
jours_ecart = (date_fin - date_debut).days

lignes = []
liste_regions = list(REGIONS.keys())

for i in range(1, N_LIGNES + 1):
    region = np.random.choice(liste_regions)
    infos_region = REGIONS[region]
    prefecture = np.random.choice(infos_region["prefectures"])

    # Date aléatoire dans la plage définie
    date_dist = date_debut + timedelta(days=int(np.random.randint(0, jours_ecart)))

    type_aide = np.random.choice(TYPES_AIDE)

    # Cible = nombre de bénéficiaires visés pour cette distribution
    cible = int(np.random.randint(500, 5000))
    # Atteint = nombre réellement touché (parfois en dessous, parfois au-dessus de la cible)
    taux_realisation = np.random.normal(loc=0.88, scale=0.15)
    taux_realisation = max(0.4, min(1.15, taux_realisation))  # on borne entre 40% et 115%
    atteint = int(cible * taux_realisation)

    # Stock restant et consommation journalière (servent au calcul des alertes)
    stock_restant_kg = float(np.random.uniform(200, 15000))
    consommation_jour = float(np.random.uniform(50, 800))

    # Délai de distribution en jours (retard entre planification et exécution réelle)
    delai_jours = int(np.random.exponential(scale=5))  # la plupart < 10, quelques valeurs élevées
    delai_jours = min(delai_jours, 30)

    # Satisfaction moyenne des bénéficiaires (enquête post-distribution), sur 5
    satisfaction_moyenne = round(float(np.clip(np.random.normal(3.9, 0.6), 1.0, 5.0)), 1)

    # Coordonnées GPS : on disperse légèrement autour du chef-lieu régional
    # pour simuler des points de distribution répartis sur le territoire
    latitude = round(infos_region["lat"] + np.random.uniform(-0.35, 0.35), 5)
    longitude = round(infos_region["lon"] + np.random.uniform(-0.35, 0.35), 5)

    lignes.append({
        "id_distribution": f"PAM-TG-{i:04d}",
        "region": region,
        "prefecture": prefecture,
        "date_distribution": date_dist.strftime("%Y-%m-%d"),
        "type_aide": type_aide,
        "cible": cible,
        "atteint": atteint,
        "stock_restant_kg": round(stock_restant_kg, 1),
        "consommation_jour": round(consommation_jour, 1),
        "delai_jours": delai_jours,
        "satisfaction_moyenne": satisfaction_moyenne,
        "latitude": latitude,
        "longitude": longitude,
    })

# ----------------------------------------------------------------------------
# 3) CONSTRUCTION DU DATAFRAME ET EXPORT EXCEL
# ----------------------------------------------------------------------------
df = pd.DataFrame(lignes)

# On trie par date pour que le fichier soit plus lisible à l'ouverture
df = df.sort_values("date_distribution").reset_index(drop=True)

chemin_sortie = "donnees_pam.xlsx"
df.to_excel(chemin_sortie, index=False, sheet_name="distributions")

print(f"✅ Fichier généré avec succès : {chemin_sortie}")
print(f"   → {len(df)} lignes, {len(df.columns)} colonnes")
print(f"   → Régions couvertes : {', '.join(liste_regions)}")
print(f"   → Période : {df['date_distribution'].min()} → {df['date_distribution'].max()}")
