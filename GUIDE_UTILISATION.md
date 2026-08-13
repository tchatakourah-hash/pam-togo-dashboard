# Guide d'utilisation — DASHBOARD-IA PAM TOGO

Ce guide s'adresse à un chargé de Suivi-Évaluation **débutant en Python**. Il explique comment installer, faire tourner, personnaliser et déployer le dashboard, ainsi que comment faire remonter les données du terrain via KoboToolbox.

---

## 1. Installation

### Prérequis
- Python 3.10 ou plus récent installé sur votre ordinateur ([python.org](https://www.python.org/downloads/))
- Une invite de commande (Terminal sur Mac/Linux, PowerShell ou CMD sur Windows)

### Étapes

```bash
# 1. Se placer dans le dossier du projet
cd pam_togo_dashboard

# 2. (Recommandé) Créer un environnement virtuel pour isoler les librairies
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# 3. Installer toutes les dépendances
pip install -r requirements.txt

# 4. (Si besoin) régénérer le fichier de données de démonstration
python generate_data.py

# 5. Lancer l'application
python app.py
```

Ouvrez ensuite votre navigateur à l'adresse : **http://127.0.0.1:8050**

Pour arrêter le serveur : `Ctrl + C` dans le terminal.

---

## 2. Structure du projet

```
pam_togo_dashboard/
│
├── app.py                     # L'application Dash (le dashboard lui-même)
├── generate_data.py           # Génère des données factices de démonstration
├── generate_kobo_form.py      # Génère le formulaire Kobo pour les agents
├── donnees_pam.xlsx           # Fichier de données (lu par défaut par app.py)
├── kobo_formulaire_pam.xlsx   # Formulaire prêt à importer sur KoboToolbox
├── requirements.txt           # Liste des librairies Python nécessaires
├── GUIDE_UTILISATION.md       # Ce guide
└── assets/
    └── style.css              # Habillage visuel (couleurs, cartes, boutons...)
```

| Fichier | À quoi il sert | À modifier si... |
|---|---|---|
| `app.py` | Toute la logique du dashboard : chargement des données, graphiques, callbacks, IA | Vous ajoutez un indicateur, changez un seuil d'alerte, modifiez le prompt IA |
| `donnees_pam.xlsx` | La source de données par défaut | Vous remplacez les données de démo par vos vraies données (mêmes colonnes) |
| `assets/style.css` | Le style visuel (Dash charge automatiquement tout le dossier `assets/`) | Vous changez les couleurs, polices, effets visuels |
| `kobo_formulaire_pam.xlsx` | Le formulaire de collecte terrain | Vous ajoutez une question au formulaire des agents |

---

## 3. Brancher votre base de données (MySQL / PostgreSQL)

Par défaut, l'app lit `donnees_pam.xlsx`. Pour brancher une vraie base, ouvrez `app.py` et repérez le bloc `### SECTION CONFIG BDD ###` (vers le haut du fichier).

### Étape 1 — Changer la source

```python
CONFIG = {
    "SOURCE_DONNEES": "mysql",   # au lieu de "excel"
    ...
}
```

### Étape 2 — Renseigner les identifiants de connexion

Deux options :
- **Le plus simple et le plus sûr** : définir des variables d'environnement avant de lancer l'app (elles sont déjà lues automatiquement par `CONFIG`) :

```bash
export PAM_MYSQL_HOST="votre-serveur.exemple.com"
export PAM_MYSQL_USER="utilisateur"
export PAM_MYSQL_PASSWORD="mot_de_passe"
export PAM_MYSQL_DB="pam_togo"
python app.py
```

- **Ou directement dans le code** (déconseillé si le code est partagé/versionné avec Git, car le mot de passe serait visible) :

```python
"MYSQL": {
    "host": "votre-serveur.exemple.com",
    "user": "utilisateur",
    "password": "mot_de_passe",
    "database": "pam_togo",
    "port": 3306,
},
```

### Étape 3 — Installer le connecteur

```bash
pip install mysql-connector-python      # pour MySQL
# ou
pip install psycopg2-binary             # pour PostgreSQL
```

### Étape 4 — Adapter la requête SQL si besoin

Dans `app.py`, les fonctions `charger_depuis_mysql()` et `charger_depuis_postgresql()` utilisent par défaut :

```python
requete = "SELECT * FROM distributions"
```

Remplacez `distributions` par le nom réel de votre table. **Important** : les colonnes renvoyées par votre requête doivent porter les mêmes noms que dans `donnees_pam.xlsx` (`region`, `cible`, `atteint`, etc.), sinon le dashboard ne pourra pas les reconnaître — ou alors ajoutez un `AS` dans votre SQL pour les renommer (ex : `SELECT nom_region AS region, ...`).

---

## 4. Ajouter un indicateur (tutoriel pas à pas)

**Exemple concret : ajouter un KPI "Nombre de sites actifs" sur la Vue d'ensemble.**

### Étape 1 — Vérifier que la donnée existe
Assurez-vous que votre fichier Excel/BDD contient bien une colonne permettant de calculer cet indicateur (ici, on peut simplement compter les `id_distribution` uniques par site, ou ajouter une colonne `site_actif`).

### Étape 2 — Calculer la valeur dans `contenu_onglet_vue_ensemble()`

Dans `app.py`, repérez la fonction `contenu_onglet_vue_ensemble()` et ajoutez, avec les autres calculs :

```python
nb_sites_actifs = df["prefecture"].nunique()
```

### Étape 3 — Ajouter la carte KPI

Toujours dans la même fonction, ajoutez une 5ᵉ carte dans la `dbc.Row` des KPI :

```python
carte_kpi("Sites Actifs", nb_sites_actifs, "bi-geo-alt", COULEURS["orange_pam"]),
```

*(La liste des icônes disponibles se trouve sur [icons.getbootstrap.com](https://icons.getbootstrap.com/) — copiez le nom de la classe, ex : `bi-geo-alt`.)*

### Étape 4 — Relancer l'app

```bash
python app.py
```

C'est tout ! Le même principe s'applique pour ajouter un graphique : créez une fonction `creer_xxx(df)` qui renvoie une figure Plotly, puis appelez-la dans la fonction `contenu_onglet_...` correspondante avec `dcc.Graph(figure=creer_xxx(df))`.

---

## 5. Modifier les couleurs / le logo

### Couleurs
Deux endroits à modifier ensemble (pour que les graphiques Plotly ET l'interface restent cohérents) :

1. **Dans `app.py`**, le dictionnaire `COULEURS` en haut du fichier (pilote les graphiques) :
   ```python
   COULEURS = {
       "bleu_pam": "#007DBC",     # → remplacez par votre couleur principale
       "orange_pam": "#F7941E",   # → votre couleur d'accent
       ...
   }
   ```
2. **Dans `assets/style.css`**, le bloc `:root` en haut du fichier (pilote le reste de l'interface : header, cartes, boutons) :
   ```css
   :root {
     --bleu-pam: #007DBC;
     --orange-pam: #F7941E;
     ...
   }
   ```

### Logo
Le header affiche actuellement un badge textuel "PAM" (`logo-badge` dans `app.py`, fonction `entete()`). Pour utiliser une vraie image de logo :

1. Placez votre fichier logo (ex : `logo.png`) dans le dossier `assets/`.
2. Dans `app.py`, fonction `entete()`, remplacez :
   ```python
   html.Div("PAM", className="logo-badge"),
   ```
   par :
   ```python
   html.Img(src="/assets/logo.png", className="logo-image"),
   ```
3. Dans `assets/style.css`, ajoutez :
   ```css
   .logo-image { height: 48px; }
   ```

---

## 6. Modifier le prompt IA

Le prompt envoyé à l'IA se construit dans **deux fonctions** de `app.py` :

- `construire_prompt_ia(df_mois, mois_label)` → construit le **résumé chiffré** (KPI du mois) + la **consigne** donnée à l'IA. C'est ici que vous changez :
  - Les indicateurs inclus dans le résumé
  - Le nombre de constats/recommandations demandés
  - Le ton, le format de sortie attendu, la langue

  Exemple : pour demander 5 recommandations au lieu de 3, modifiez la chaîne `consigne` :
  ```python
  "RECOMMANDATIONS:\n- recommandation 1\n- recommandation 2\n- recommandation 3\n- recommandation 4\n- recommandation 5\n"
  ```

- `appeler_ia_openai(prompt)` → gère l'appel technique à l'API (modèle utilisé, température, longueur max). Vous pouvez par exemple changer `model="gpt-4o-mini"` vers un autre modèle disponible sur votre compte OpenAI.

**Clé API requise** : définissez la variable d'environnement avant de lancer l'app :
```bash
export OPENAI_API_KEY="sk-votre-cle"     # Mac/Linux
setx OPENAI_API_KEY "sk-votre-cle"       # Windows (redémarrer le terminal après)
```
Sans clé, le bouton "Générer Rapport Mensuel IA" affichera un message d'erreur clair au lieu de faire planter l'application.

---

## 7. Déployer gratuitement en ligne

### Option A — Render.com (recommandé, simple)

1. Créez un compte sur [render.com](https://render.com) et connectez votre dépôt GitHub contenant ce projet.
2. Cliquez sur **New > Web Service**, sélectionnez votre dépôt.
3. Configurez :
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `gunicorn app:server`
4. Ajoutez vos variables d'environnement (`OPENAI_API_KEY`, identifiants BDD si utilisés) dans l'onglet **Environment**.
5. Déployez. Render vous donne une URL publique (ex : `https://votre-app.onrender.com`).

> `app:server` fait référence à la ligne `server = app.server` déjà présente dans `app.py` — ne la supprimez pas, elle est nécessaire pour Gunicorn.

### Option B — Hugging Face Spaces

1. Créez un compte sur [huggingface.co](https://huggingface.co), puis **New Space**.
2. Choisissez le SDK **Docker** (ou "Gradio"/"Streamlit" ne conviennent pas à Dash — préférez Docker).
3. Ajoutez un fichier `Dockerfile` minimal à la racine du projet :
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY . .
   RUN pip install -r requirements.txt
   EXPOSE 7860
   CMD ["gunicorn", "app:server", "--bind", "0.0.0.0:7860"]
   ```
4. Poussez votre code (via `git push` ou l'interface web de Hugging Face).
5. Ajoutez vos clés secrètes (`OPENAI_API_KEY`, etc.) dans **Settings > Repository secrets**.

---

## 8. Passer à une vraie carte choroplèthe (optionnel)

Par défaut, la carte du Togo utilise des **bulles positionnées sur les chefs-lieux de région** (pas besoin de fichier externe, fonctionne immédiatement). Si vous obtenez un fichier **GeoJSON** des frontières des 5 régions du Togo :

1. Placez le fichier (ex : `togo_regions.geojson`) à la racine du projet.
2. Dans `app.py`, remplacez l'appel à `creer_carte_togo(df)` par `creer_choropleth_reel(df, "togo_regions.geojson", cle_id="NOM_DE_LA_PROPRIETE_REGION")` dans la fonction `contenu_onglet_vue_ensemble()`.
3. Adaptez `cle_id` au nom exact de la propriété contenant le nom de région dans votre GeoJSON (ouvrez le fichier avec un éditeur de texte pour le vérifier, ex : `"NAME_1"`, `"region"`, etc.).

La fonction `creer_choropleth_reel()` est déjà entièrement écrite dans `app.py`, prête à l'emploi.

---

## 9. Formulaire KoboToolbox pour les agents de terrain

Pour que les agents collectent les données **directement sur le terrain** (smartphone, y compris hors connexion) et alimentent ce même dashboard **sans qu'il faille toucher au code**, un formulaire prêt à l'emploi est fourni : `kobo_formulaire_pam.xlsx`.

### Pourquoi ça marche "sans rien casser"
Chaque question du formulaire Kobo porte **exactement le même nom** qu'une colonne attendue par le dashboard (`region`, `type_aide`, `cible`, `atteint`, `stock_restant_kg`, etc.). Résultat : l'export Kobo peut remplacer `donnees_pam.xlsx` avec un minimum d'ajustements, sans modifier `app.py`.

### Étape 1 — Créer le compte et importer le formulaire
1. Allez sur [kf.kobotoolbox.org](https://kf.kobotoolbox.org) et créez un compte (gratuit).
2. Cliquez sur **New > Upload XLSForm**, puis sélectionnez `kobo_formulaire_pam.xlsx`.
3. Le formulaire apparaît avec toutes les questions déjà configurées : région → préfecture (liste filtrée automatiquement selon la région choisie), type d'aide, cible/atteint, stock, délai, satisfaction, et position GPS.
4. Cliquez sur **Deploy** pour le rendre disponible.

### Étape 2 — Équiper les agents de terrain
1. Les agents installent l'application **KoboCollect** (Android, gratuite sur le Play Store).
2. Dans l'app, ils ajoutent le serveur `kf.kobotoolbox.org` avec les identifiants du compte (ou un compte dédié par agent, recommandé pour la traçabilité).
3. Ils téléchargent le formulaire "PAM Togo - Fiche de suivi des distributions" et peuvent l'utiliser **même sans connexion internet** ; les réponses sont envoyées dès qu'une connexion est disponible.

### Étape 3 — Exporter les données vers le dashboard
1. Sur la plateforme Kobo, allez dans votre projet > **Data > Downloads**.
2. Exportez au format **XLSX**.
3. **Point d'attention** : le champ GPS (`position_gps`) est automatiquement éclaté par Kobo en plusieurs colonnes à l'export (`_position_gps_latitude`, `_position_gps_longitude`, etc.). Renommez ces deux colonnes en `latitude` et `longitude` (par ex. avec un renommage rapide dans Excel, ou en ajoutant 2 lignes dans `generate_data.py`/un petit script de transformation) avant de remplacer `donnees_pam.xlsx`.
4. Remplacez le fichier `donnees_pam.xlsx` du dashboard par cet export (mêmes noms de colonnes = mêmes noms de fichier = **aucune modification de `app.py` nécessaire**).

### Étape 4 (optionnel) — Automatiser l'export
Pour éviter l'export manuel répété, Kobo propose une **API REST** (`https://kf.kobotoolbox.org/api/v2/`) qui permet d'écrire un petit script Python (avec la librairie `requests`) exécuté automatiquement chaque nuit pour récupérer les nouvelles soumissions et mettre à jour `donnees_pam.xlsx`, ou pour aller directement écrire dans votre base MySQL/PostgreSQL (voir section 3). Ce sera l'étape naturelle une fois le dashboard connecté à une vraie base de données.

### Modifier le formulaire (ajouter une question)
Ouvrez `generate_kobo_form.py`, ajoutez une ligne dans la liste `survey` (voir les exemples existants pour le format), relancez `python generate_kobo_form.py`, puis ré-importez le fichier généré sur KoboToolbox (il proposera de remplacer la version existante).

---

## Besoin d'aide ?
Ce projet a été structuré pour rester simple à maintenir : chaque section de `app.py` est commentée en français et découpée par bloc numéroté (0 à 9). En cas de doute, repérez le numéro de bloc concerné par votre besoin dans ce guide et allez directement à la section correspondante du code.
