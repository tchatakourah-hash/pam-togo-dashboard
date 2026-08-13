# ============================================================================
# APP.PY — DASHBOARD-IA PAM TOGO
# ----------------------------------------------------------------------------
# Suivi-Évaluation automatisé des projets de sécurité alimentaire du PAM
# au Togo — TAISS 2026
#
# Auteur  : Généré avec Claude (Anthropic) — à adapter par l'équipe S&E PAM
# Stack   : Dash + Plotly + Pandas + OpenAI API
#
# LANCEMENT :
#       python app.py
# puis ouvrir : http://127.0.0.1:8050
# ============================================================================

import os
from functools import lru_cache
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, dash_table, Input, Output, State, ctx
import dash_bootstrap_components as dbc

# ============================================================================
# 0) CONFIGURATION GÉNÉRALE
# ============================================================================
# Toutes les options "faciles à changer" sont regroupées ici en haut du
# fichier pour qu'un chargé S&E puisse personnaliser l'app sans devoir
# fouiller dans tout le code.

APP_TITLE = "DASHBOARD-IA PAM TOGO"
APP_SOUSTITRE = "Suivi-Évaluation Sécurité Alimentaire — TAISS 2026"

# --- Palette de couleurs officielle PAM (à modifier ici pour rebrander) ----
COULEURS = {
    "bleu_pam": "#007DBC",        # Bleu institutionnel PAM
    "bleu_fonce": "#00507A",      # Bleu foncé (header, texte fort)
    "orange_pam": "#F7941E",      # Orange PAM (accents, CTA)
    "gris_fond": "#F4F6F8",       # Fond général de la page
    "blanc": "#FFFFFF",
    "rouge_alerte": "#E63946",    # Alertes critiques
    "vert_ok": "#2A9D8F",         # Indicateurs positifs
    "gris_texte": "#495057",
}

# --- Seuils utilisés pour les alertes automatiques (Onglet IA & Alertes) ---
SEUIL_JOURS_STOCK_CRITIQUE = 15   # jours d'autonomie de stock restants
SEUIL_DELAI_JOURS_CRITIQUE = 10   # délai (en jours) jugé excessif

# ============================================================================
# ### SECTION CONFIG BDD ###
# ----------------------------------------------------------------------------
# Par défaut, l'application lit le fichier Excel "donnees_pam.xlsx".
# Pour brancher une base de données plus tard (MySQL ou PostgreSQL), il
# suffit de modifier CONFIG["SOURCE_DONNEES"] et de compléter les
# identifiants ci-dessous. Voir le GUIDE_UTILISATION.md, section 3, pour le
# détail complet (y compris les librairies à installer).
# ============================================================================
CONFIG = {
    # "excel" (par défaut) | "mysql" | "postgresql"
    "SOURCE_DONNEES": "excel",

    "FICHIER_EXCEL": "donnees_pam.xlsx",

    # Paramètres de connexion (utilisés uniquement si SOURCE_DONNEES != "excel")
    "MYSQL": {
        "host": os.environ.get("PAM_MYSQL_HOST", "localhost"),
        "user": os.environ.get("PAM_MYSQL_USER", "root"),
        "password": os.environ.get("PAM_MYSQL_PASSWORD", ""),
        "database": os.environ.get("PAM_MYSQL_DB", "pam_togo"),
        "port": int(os.environ.get("PAM_MYSQL_PORT", 3306)),
    },
    "POSTGRESQL": {
        "host": os.environ.get("PAM_PG_HOST", "localhost"),
        "user": os.environ.get("PAM_PG_USER", "postgres"),
        "password": os.environ.get("PAM_PG_PASSWORD", ""),
        "database": os.environ.get("PAM_PG_DB", "pam_togo"),
        "port": int(os.environ.get("PAM_PG_PORT", 5432)),
    },
}


def charger_depuis_mysql():
    """Exemple de connexion MySQL — activée si CONFIG['SOURCE_DONNEES'] == 'mysql'.
    Nécessite : pip install mysql-connector-python
    """
    import mysql.connector  # import local pour ne pas exiger la lib si non utilisée

    conn = mysql.connector.connect(**CONFIG["MYSQL"])
    requete = "SELECT * FROM distributions"  # adapter le nom de table si besoin
    df = pd.read_sql(requete, conn)
    conn.close()
    return df


def charger_depuis_postgresql():
    """Exemple de connexion PostgreSQL — activée si CONFIG['SOURCE_DONNEES'] == 'postgresql'.
    Nécessite : pip install psycopg2-binary
    """
    import psycopg2  # import local

    conn = psycopg2.connect(**CONFIG["POSTGRESQL"])
    requete = "SELECT * FROM distributions"
    df = pd.read_sql(requete, conn)
    conn.close()
    return df


# ============================================================================
# 1) CHARGEMENT DES DONNÉES (mis en cache pour la performance)
# ============================================================================
# @lru_cache évite de relire le fichier Excel (ou la BDD) à chaque clic de
# l'utilisateur : les données ne sont chargées qu'une seule fois en mémoire,
# puis réutilisées pour tous les callbacks. Pour forcer un rechargement
# (ex: après mise à jour du fichier), il suffit de relancer l'application.
@lru_cache(maxsize=1)
def charger_donnees():
    """Charge les données selon la source définie dans CONFIG, les nettoie
    et calcule les colonnes dérivées utiles au dashboard."""

    source = CONFIG["SOURCE_DONNEES"]

    if source == "excel":
        df = pd.read_excel(CONFIG["FICHIER_EXCEL"])
    elif source == "mysql":
        df = charger_depuis_mysql()
    elif source == "postgresql":
        df = charger_depuis_postgresql()
    else:
        raise ValueError(f"SOURCE_DONNEES inconnue : {source}")

    # --- Nettoyage / typage ---
    df["date_distribution"] = pd.to_datetime(df["date_distribution"])
    df["mois"] = df["date_distribution"].dt.to_period("M").astype(str)

    # --- Colonnes calculées ---
    df["taux_couverture"] = (df["atteint"] / df["cible"]).clip(upper=2) * 100
    df["autonomie_jours"] = df["stock_restant_kg"] / df["consommation_jour"].replace(0, pd.NA)

    # --- Détection des alertes (mêmes règles que l'onglet "IA & Alertes") ---
    df["alerte_stock"] = df["autonomie_jours"] < SEUIL_JOURS_STOCK_CRITIQUE
    df["alerte_delai"] = df["delai_jours"] > SEUIL_DELAI_JOURS_CRITIQUE
    df["alerte"] = df["alerte_stock"] | df["alerte_delai"]

    return df


DF_GLOBAL = charger_donnees()

# Listes utilisées pour peupler les filtres (dropdowns)
LISTE_REGIONS = sorted(DF_GLOBAL["region"].unique().tolist())
LISTE_TYPES_AIDE = sorted(DF_GLOBAL["type_aide"].unique().tolist())
LISTE_COLONNES_TABLE = [
    "id_distribution", "region", "prefecture", "date_distribution", "type_aide",
    "cible", "atteint", "stock_restant_kg", "consommation_jour", "delai_jours",
    "satisfaction_moyenne",
]

# ============================================================================
# 2) INITIALISATION DE L'APPLICATION DASH
# ============================================================================
app = Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.FLATLY,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css",
    ],
    title=APP_TITLE,
    suppress_callback_exceptions=True,
)
server = app.server  # nécessaire pour un déploiement (Render, Gunicorn, etc.)


# ============================================================================
# 3) COMPOSANTS RÉUTILISABLES
# ============================================================================

def carte_kpi(titre, valeur, icone, couleur, suffixe=""):
    """Génère une carte KPI stylée (icône + valeur + titre)."""
    return dbc.Col(
        dbc.Card(
            dbc.CardBody(
                [
                    html.Div(
                        html.I(className=f"bi {icone}"),
                        className="kpi-icone",
                        style={"backgroundColor": couleur},
                    ),
                    html.H2(f"{valeur}{suffixe}", className="kpi-valeur"),
                    html.P(titre, className="kpi-titre"),
                ]
            ),
            className="kpi-carte shadow-sm",
        ),
        xs=12, sm=6, lg=3,
    )


def carte_alerte(ligne):
    """Génère une carte pour une alerte individuelle (onglet IA & Alertes)."""
    raisons = []
    if ligne["alerte_stock"]:
        autonomie = ligne["autonomie_jours"]
        autonomie_txt = "N/A" if pd.isna(autonomie) else f"{autonomie:.1f} j"
        raisons.append(f"Stock critique ({autonomie_txt} d'autonomie)")
    if ligne["alerte_delai"]:
        raisons.append(f"Délai excessif ({int(ligne['delai_jours'])} jours)")

    return dbc.ListGroupItem(
        [
            html.Div(
                [
                    html.Span(ligne["id_distribution"], className="fw-bold me-2"),
                    dbc.Badge(ligne["region"], color="light", text_color="dark", className="me-1"),
                    dbc.Badge(ligne["type_aide"], color="light", text_color="dark"),
                ]
            ),
            html.Div(
                f"{ligne['prefecture']} — {ligne['date_distribution'].strftime('%d/%m/%Y')}",
                className="text-muted small",
            ),
            html.Div(" • ".join(raisons), className="alerte-raison"),
        ],
        className="alerte-item",
    )


# ============================================================================
# 4) GRAPHIQUES — ONGLET "VUE D'ENSEMBLE"
# ============================================================================

def creer_carte_togo(df):
    """Carte du Togo par région (vue synthétique).

    ⚠️ Note technique : une VRAIE carte choroplèthe (régions colorées comme
    des polygones) nécessite un fichier GeoJSON des frontières régionales du
    Togo. Pour rester 100% fonctionnel "prêt à l'emploi" sans dépendance
    externe, cette version utilise une carte à bulles (scatter_mapbox)
    positionnée sur les chefs-lieux de région : la couleur = taux de
    couverture, la taille = volume de bénéficiaires atteints.

    Si vous obtenez un fichier GeoJSON des régions du Togo, voir la fonction
    `creer_choropleth_reel()` juste en dessous, prête à l'emploi, et le
    GUIDE_UTILISATION.md section "Passer à une vraie carte choroplèthe".
    """
    agg = df.groupby("region").agg(
        cible=("cible", "sum"),
        atteint=("atteint", "sum"),
        latitude=("latitude", "mean"),
        longitude=("longitude", "mean"),
        nb_distributions=("id_distribution", "count"),
    ).reset_index()
    agg["taux_couverture"] = (agg["atteint"] / agg["cible"] * 100).round(1)

    fig = px.scatter_map(
        agg,
        lat="latitude",
        lon="longitude",
        size="nb_distributions",
        color="taux_couverture",
        color_continuous_scale=["#E63946", "#F7941E", "#2A9D8F"],
        range_color=[50, 110],
        hover_name="region",
        hover_data={
            "latitude": False, "longitude": False,
            "atteint": True, "cible": True, "taux_couverture": True,
            "nb_distributions": True,
        },
        size_max=45,
        zoom=6.1,
        map_style="carto-positron",
        title=None,
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        coloraxis_colorbar=dict(title="Taux couv. %"),
        map_center={"lat": 8.6, "lon": 1.0},
        height=400,
    )
    return fig


def creer_choropleth_reel(df, chemin_geojson, cle_id="NAME_1"):
    """Version "vraie carte choroplèthe" à activer une fois un GeoJSON des
    régions du Togo disponible. Non utilisée par défaut.

    Exemple d'utilisation dans le callback de la carte :
        fig = creer_choropleth_reel(df, "togo_regions.geojson")
    """
    import json
    with open(chemin_geojson, encoding="utf-8") as f:
        geojson_togo = json.load(f)

    agg = df.groupby("region").agg(
        cible=("cible", "sum"), atteint=("atteint", "sum")
    ).reset_index()
    agg["taux_couverture"] = (agg["atteint"] / agg["cible"] * 100).round(1)

    fig = px.choropleth_map(
        agg,
        geojson=geojson_togo,
        locations="region",
        featureidkey=f"properties.{cle_id}",
        color="taux_couverture",
        color_continuous_scale=["#E63946", "#F7941E", "#2A9D8F"],
        map_style="carto-positron",
        zoom=6.1,
        center={"lat": 8.6, "lon": 1.0},
        opacity=0.75,
    )
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=400)
    return fig


def creer_barre_atteint_vs_cible(df):
    """Barres groupées : Atteint vs Cible par type d'aide."""
    agg = df.groupby("type_aide").agg(
        Cible=("cible", "sum"), Atteint=("atteint", "sum")
    ).reset_index()
    agg = agg.melt(id_vars="type_aide", value_vars=["Cible", "Atteint"],
                    var_name="Indicateur", value_name="Valeur")

    fig = px.bar(
        agg, x="type_aide", y="Valeur", color="Indicateur",
        barmode="group",
        color_discrete_map={"Cible": "#B9C4CC", "Atteint": COULEURS["bleu_pam"]},
        text_auto=".2s",
    )
    fig.update_layout(
        legend_title_text="",
        xaxis_title="", yaxis_title="Bénéficiaires",
        plot_bgcolor="white", height=380,
        margin=dict(l=10, r=10, t=20, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def creer_donut_repartition(df):
    """Bonus 'hyper cool' : répartition des bénéficiaires atteints par type d'aide."""
    agg = df.groupby("type_aide")["atteint"].sum().reset_index()
    fig = px.pie(
        agg, names="type_aide", values="atteint", hole=0.55,
        color_discrete_sequence=[COULEURS["bleu_pam"], COULEURS["orange_pam"],
                                  COULEURS["vert_ok"], "#7B8FA1", "#B9C4CC"],
    )
    fig.update_traces(textposition="inside", textinfo="percent")
    fig.update_layout(
        showlegend=True, height=380,
        margin=dict(l=10, r=10, t=20, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=-0.15),
        annotations=[dict(text="Répartition", x=0.5, y=0.5, font_size=13, showarrow=False)],
    )
    return fig


# ============================================================================
# 5) GRAPHIQUES — ONGLET "ANALYSE DÉTAILLÉE"
# ============================================================================

def creer_courbe_evolution(df):
    """Évolution mensuelle des distributions (Atteint vs Cible) dans le temps."""
    agg = df.groupby("mois").agg(Cible=("cible", "sum"), Atteint=("atteint", "sum")).reset_index()
    agg = agg.sort_values("mois")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=agg["mois"], y=agg["Cible"], name="Cible", mode="lines",
        line=dict(color="#B9C4CC", dash="dash", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=agg["mois"], y=agg["Atteint"], name="Atteint", mode="lines+markers",
        line=dict(color=COULEURS["bleu_pam"], width=3),
        fill="tozeroy", fillcolor="rgba(0,125,188,0.08)",
    ))
    fig.update_layout(
        plot_bgcolor="white", height=380,
        xaxis_title="Mois", yaxis_title="Bénéficiaires",
        margin=dict(l=10, r=10, t=20, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )
    return fig


# ============================================================================
# 6) MODULE IA — GÉNÉRATION DU RAPPORT MENSUEL (OpenAI API)
# ============================================================================
# Le prompt envoyé à l'IA se trouve dans la fonction `construire_prompt_ia()`
# ci-dessous — c'est ici qu'il faut le modifier si vous voulez changer le
# style ou le contenu du rapport généré (voir GUIDE_UTILISATION.md, section 6).

def construire_prompt_ia(df_mois, mois_label):
    """Construit le prompt (résumé chiffré + consigne) envoyé à l'IA."""
    n = len(df_mois)
    cible_totale = int(df_mois["cible"].sum())
    atteint_total = int(df_mois["atteint"].sum())
    taux = round(atteint_total / cible_totale * 100, 1) if cible_totale else 0
    delai_moyen = round(df_mois["delai_jours"].mean(), 1)
    satisfaction = round(df_mois["satisfaction_moyenne"].mean(), 2)
    nb_alertes = int(df_mois["alerte"].sum())
    par_region = df_mois.groupby("region")["atteint"].sum().sort_values(ascending=False).to_dict()
    par_type = df_mois.groupby("type_aide")["atteint"].sum().sort_values(ascending=False).to_dict()

    resume = f"""
Résumé chiffré des opérations PAM Togo pour {mois_label} :
- Nombre de distributions : {n}
- Bénéficiaires ciblés : {cible_totale}
- Bénéficiaires atteints : {atteint_total}
- Taux de couverture global : {taux}%
- Délai moyen de distribution : {delai_moyen} jours
- Satisfaction moyenne des bénéficiaires : {satisfaction}/5
- Nombre d'alertes actives (stock critique ou délai excessif) : {nb_alertes}
- Répartition des bénéficiaires atteints par région : {par_region}
- Répartition des bénéficiaires atteints par type d'aide : {par_type}
""".strip()

    consigne = (
        "Tu es un expert en Suivi-Évaluation du Programme Alimentaire Mondial (PAM) au Togo. "
        "À partir du résumé chiffré ci-dessus, rédige un rapport court et opérationnel en français, "
        "structuré STRICTEMENT ainsi :\n"
        "CONSTATS:\n- constat 1\n- constat 2\n- constat 3\n"
        "RECOMMANDATIONS:\n- recommandation 1\n- recommandation 2\n- recommandation 3\n"
        "Sois concret, chiffré quand c'est pertinent, et adapté à un contexte humanitaire au Togo. "
        "N'ajoute aucun texte en dehors de cette structure."
    )

    return f"{resume}\n\n{consigne}"


def appeler_ia_openai(prompt):
    """Appelle l'API OpenAI (SDK >= 1.0) et renvoie le texte généré.

    Nécessite la variable d'environnement OPENAI_API_KEY définie, par ex. :
        export OPENAI_API_KEY="sk-..."          (Mac/Linux)
        setx OPENAI_API_KEY "sk-..."            (Windows)
    """
    from openai import OpenAI  # import local : évite un crash au démarrage si la lib/clé manque

    cle_api = os.environ.get("OPENAI_API_KEY")
    if not cle_api:
        raise RuntimeError(
            "Aucune clé OPENAI_API_KEY trouvée. Définissez-la comme variable "
            "d'environnement avant de lancer l'application (voir GUIDE_UTILISATION.md)."
        )

    client = OpenAI(api_key=cle_api)
    reponse = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Tu réponds toujours en français, de façon claire et structurée."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        max_tokens=600,
    )
    return reponse.choices[0].message.content


def parser_reponse_ia(texte):
    """Transforme la réponse texte de l'IA en deux listes : constats / recommandations."""
    constats, recommandations = [], []
    section_courante = None
    for ligne in texte.splitlines():
        ligne_nettoyee = ligne.strip()
        if not ligne_nettoyee:
            continue
        if ligne_nettoyee.upper().startswith("CONSTATS"):
            section_courante = "constats"
            continue
        if ligne_nettoyee.upper().startswith("RECOMMANDATIONS"):
            section_courante = "recommandations"
            continue
        if ligne_nettoyee.startswith("-") or ligne_nettoyee.startswith("•"):
            contenu = ligne_nettoyee.lstrip("-•").strip()
            if section_courante == "constats":
                constats.append(contenu)
            elif section_courante == "recommandations":
                recommandations.append(contenu)
    return constats, recommandations


# ============================================================================
# 7) MISE EN PAGE (LAYOUT)
# ============================================================================

def entete():
    """Bandeau d'en-tête avec logo, titre et badge d'alertes en direct."""
    nb_alertes_total = int(DF_GLOBAL["alerte"].sum())
    return html.Div(
        dbc.Container(
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            [
                                html.Div("PAM", className="logo-badge"),
                                html.Div(
                                    [
                                        html.H1(APP_TITLE, className="entete-titre"),
                                        html.P(APP_SOUSTITRE, className="entete-soustitre"),
                                    ]
                                ),
                            ],
                            className="entete-gauche",
                        ),
                        width="auto",
                    ),
                    dbc.Col(
                        html.Div(
                            [
                                dbc.Badge(
                                    [html.I(className="bi bi-exclamation-triangle-fill me-1"),
                                     f"{nb_alertes_total} alertes actives"],
                                    color="danger" if nb_alertes_total else "success",
                                    className="badge-alertes",
                                    id="badge-alertes-header",
                                ),
                                html.Div("TAISS 2026", className="badge-taiss"),
                            ],
                            className="entete-droite",
                        ),
                        width="auto",
                        className="ms-auto d-flex align-items-center gap-2",
                    ),
                ],
                align="center",
                className="w-100",
            ),
            fluid=True,
        ),
        className="entete-app",
    )


def contenu_onglet_vue_ensemble():
    df = DF_GLOBAL
    taux_couv = round(df["atteint"].sum() / df["cible"].sum() * 100, 1)
    delai_moyen = round(df["delai_jours"].mean(), 1)
    stock_total = df["stock_restant_kg"].sum()
    stock_total_txt = f"{stock_total / 1000:.1f}k" if stock_total >= 1000 else f"{stock_total:.0f}"
    satisfaction = round(df["satisfaction_moyenne"].mean(), 1)

    return html.Div(
        [
            dbc.Row(
                [
                    carte_kpi("Taux de Couverture", taux_couv, "bi-bullseye", COULEURS["bleu_pam"], "%"),
                    carte_kpi("Délai Moyen", delai_moyen, "bi-clock-history", COULEURS["orange_pam"], " j"),
                    carte_kpi("Stock Total", stock_total_txt, "bi-box-seam", COULEURS["vert_ok"], " kg"),
                    carte_kpi("Satisfaction", satisfaction, "bi-emoji-smile", COULEURS["bleu_fonce"], "/5"),
                ],
                className="g-3 mb-4",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.H5([html.I(className="bi bi-geo-alt-fill me-2"),
                                              "Carte du Togo — Taux de couverture par région"],
                                             className="carte-titre"),
                                    dcc.Graph(figure=creer_carte_togo(df), config={"displayModeBar": False}),
                                ]
                            ),
                            className="shadow-sm h-100",
                        ),
                        lg=7, className="mb-3",
                    ),
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.H5([html.I(className="bi bi-pie-chart-fill me-2"),
                                              "Répartition par type d'aide"],
                                             className="carte-titre"),
                                    dcc.Graph(figure=creer_donut_repartition(df), config={"displayModeBar": False}),
                                ]
                            ),
                            className="shadow-sm h-100",
                        ),
                        lg=5, className="mb-3",
                    ),
                ],
                className="g-3",
            ),
            dbc.Row(
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H5([html.I(className="bi bi-bar-chart-line-fill me-2"),
                                          "Atteint vs Cible par type d'aide"],
                                         className="carte-titre"),
                                dcc.Graph(figure=creer_barre_atteint_vs_cible(df), config={"displayModeBar": False}),
                            ]
                        ),
                        className="shadow-sm",
                    ),
                    width=12,
                ),
                className="g-3 mt-1",
            ),
        ]
    )


def contenu_onglet_analyse():
    return html.Div(
        [
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H5([html.I(className="bi bi-funnel-fill me-2"), "Filtres"], className="carte-titre"),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        html.Label("Région", className="filtre-label"),
                                        dcc.Dropdown(
                                            id="filtre-region",
                                            options=[{"label": r, "value": r} for r in LISTE_REGIONS],
                                            multi=True, placeholder="Toutes les régions",
                                        ),
                                    ],
                                    md=4,
                                ),
                                dbc.Col(
                                    [
                                        html.Label("Type d'aide", className="filtre-label"),
                                        dcc.Dropdown(
                                            id="filtre-type-aide",
                                            options=[{"label": t, "value": t} for t in LISTE_TYPES_AIDE],
                                            multi=True, placeholder="Tous les types",
                                        ),
                                    ],
                                    md=4,
                                ),
                                dbc.Col(
                                    [
                                        html.Label("Période", className="filtre-label"),
                                        dcc.DatePickerRange(
                                            id="filtre-dates",
                                            min_date_allowed=DF_GLOBAL["date_distribution"].min(),
                                            max_date_allowed=DF_GLOBAL["date_distribution"].max(),
                                            display_format="DD/MM/YYYY",
                                            className="w-100",
                                        ),
                                    ],
                                    md=4,
                                ),
                            ],
                            className="g-3",
                        ),
                    ]
                ),
                className="shadow-sm mb-3",
            ),
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H5([html.I(className="bi bi-graph-up me-2"),
                                  "Évolution des distributions dans le temps"],
                                 className="carte-titre"),
                        dcc.Graph(id="graphique-evolution", config={"displayModeBar": False}),
                    ]
                ),
                className="shadow-sm mb-3",
            ),
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H5([html.I(className="bi bi-table me-2"), "Détail des distributions"],
                                 className="carte-titre"),
                        dash_table.DataTable(
                            id="tableau-distributions",
                            columns=[{"name": c.replace("_", " ").capitalize(), "id": c} for c in LISTE_COLONNES_TABLE],
                            page_size=12,
                            sort_action="native",
                            filter_action="native",
                            style_table={"overflowX": "auto"},
                            style_header={
                                "backgroundColor": COULEURS["bleu_pam"], "color": "white",
                                "fontWeight": "bold", "textAlign": "left",
                            },
                            style_cell={"padding": "8px", "fontFamily": "Poppins, sans-serif", "fontSize": "13px"},
                            style_data_conditional=[
                                {"if": {"row_index": "odd"}, "backgroundColor": COULEURS["gris_fond"]},
                            ],
                        ),
                    ]
                ),
                className="shadow-sm",
            ),
        ]
    )


def contenu_onglet_ia_alertes():
    df = DF_GLOBAL
    df_alertes = df[df["alerte"]].sort_values("date_distribution", ascending=False)

    liste_alertes = (
        dbc.ListGroup([carte_alerte(row) for _, row in df_alertes.iterrows()], flush=True)
        if len(df_alertes) > 0
        else dbc.Alert("Aucune alerte active sur l'ensemble des données. 🎉", color="success")
    )

    mois_disponibles = sorted(df["mois"].unique().tolist(), reverse=True)

    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.H5(
                                        [html.I(className="bi bi-exclamation-triangle-fill me-2 text-danger"),
                                         f"Alertes rouges automatiques ({len(df_alertes)})"],
                                        className="carte-titre",
                                    ),
                                    html.P(
                                        f"Déclenchées si autonomie de stock < {SEUIL_JOURS_STOCK_CRITIQUE} jours "
                                        f"OU délai de distribution > {SEUIL_DELAI_JOURS_CRITIQUE} jours.",
                                        className="text-muted small",
                                    ),
                                    html.Div(liste_alertes, style={"maxHeight": "520px", "overflowY": "auto"}),
                                ]
                            ),
                            className="shadow-sm h-100",
                        ),
                        lg=6, className="mb-3",
                    ),
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.H5([html.I(className="bi bi-robot me-2"), "Rapport Mensuel IA"],
                                             className="carte-titre"),
                                    html.P(
                                        "Génère automatiquement 3 constats et 3 recommandations à partir "
                                        "des données du mois sélectionné, via l'API OpenAI.",
                                        className="text-muted small",
                                    ),
                                    dcc.Dropdown(
                                        id="selecteur-mois-ia",
                                        options=[{"label": m, "value": m} for m in mois_disponibles],
                                        value=mois_disponibles[0] if mois_disponibles else None,
                                        clearable=False,
                                        className="mb-3",
                                    ),
                                    dbc.Button(
                                        [html.I(className="bi bi-stars me-2"), "Générer Rapport Mensuel IA"],
                                        id="bouton-generer-rapport-ia",
                                        color="warning", className="w-100 mb-3 bouton-ia",
                                        n_clicks=0,
                                    ),
                                    dcc.Loading(
                                        html.Div(id="zone-resultat-ia"),
                                        type="dot", color=COULEURS["orange_pam"],
                                    ),
                                ]
                            ),
                            className="shadow-sm h-100",
                        ),
                        lg=6, className="mb-3",
                    ),
                ],
                className="g-3",
            ),
        ]
    )


app.layout = html.Div(
    [
        entete(),
        dbc.Container(
            [
                dbc.Tabs(
                    [
                        dbc.Tab(
                            contenu_onglet_vue_ensemble(),
                            label="Vue d'ensemble",
                            tab_id="tab-vue-ensemble",
                            label_style={"fontWeight": "600"},
                        ),
                        dbc.Tab(
                            contenu_onglet_analyse(),
                            label="Analyse Détaillée",
                            tab_id="tab-analyse",
                            label_style={"fontWeight": "600"},
                        ),
                        dbc.Tab(
                            contenu_onglet_ia_alertes(),
                            label="IA & Alertes",
                            tab_id="tab-ia-alertes",
                            label_style={"fontWeight": "600"},
                        ),
                    ],
                    id="onglets-principaux",
                    active_tab="tab-vue-ensemble",
                    className="mt-4",
                ),
            ],
            fluid=True,
            className="pb-5",
        ),
        html.Footer(
            f"DASHBOARD-IA PAM TOGO — TAISS 2026 · Données mises à jour le "
            f"{datetime.now().strftime('%d/%m/%Y')}",
            className="pied-de-page",
        ),
    ],
    className="page-app",
)


# ============================================================================
# 8) CALLBACKS
# ============================================================================

def _filtrer(df, regions, types_aide, date_debut, date_fin):
    """Applique les filtres communs (région / type d'aide / période)."""
    d = df.copy()
    if regions:
        d = d[d["region"].isin(regions)]
    if types_aide:
        d = d[d["type_aide"].isin(types_aide)]
    if date_debut:
        d = d[d["date_distribution"] >= pd.to_datetime(date_debut)]
    if date_fin:
        d = d[d["date_distribution"] <= pd.to_datetime(date_fin)]
    return d


@app.callback(
    Output("tableau-distributions", "data"),
    Output("graphique-evolution", "figure"),
    Input("filtre-region", "value"),
    Input("filtre-type-aide", "value"),
    Input("filtre-dates", "start_date"),
    Input("filtre-dates", "end_date"),
)
def maj_analyse_detaillee(regions, types_aide, date_debut, date_fin):
    """Met à jour le tableau et la courbe d'évolution selon les filtres choisis."""
    df_filtre = _filtrer(DF_GLOBAL, regions, types_aide, date_debut, date_fin)

    df_table = df_filtre.copy()
    df_table["date_distribution"] = df_table["date_distribution"].dt.strftime("%d/%m/%Y")
    donnees_table = df_table[LISTE_COLONNES_TABLE].to_dict("records")

    figure_evolution = creer_courbe_evolution(df_filtre) if len(df_filtre) else go.Figure()

    return donnees_table, figure_evolution


@app.callback(
    Output("zone-resultat-ia", "children"),
    Input("bouton-generer-rapport-ia", "n_clicks"),
    State("selecteur-mois-ia", "value"),
    prevent_initial_call=True,
)
def generer_rapport_ia(n_clicks, mois_choisi):
    """Callback déclenché par le bouton 'Générer Rapport Mensuel IA'."""
    if not mois_choisi:
        return dbc.Alert("Veuillez sélectionner un mois.", color="warning")

    df_mois = DF_GLOBAL[DF_GLOBAL["mois"] == mois_choisi]
    if df_mois.empty:
        return dbc.Alert("Aucune donnée disponible pour ce mois.", color="warning")

    prompt = construire_prompt_ia(df_mois, mois_choisi)

    try:
        texte_ia = appeler_ia_openai(prompt)
    except Exception as erreur:
        # On affiche un message clair plutôt qu'un crash de l'application.
        return dbc.Alert(
            [
                html.Strong("Impossible de générer le rapport IA. "),
                html.Span(str(erreur)),
            ],
            color="danger",
        )

    constats, recommandations = parser_reponse_ia(texte_ia)

    return html.Div(
        [
            html.H6([html.I(className="bi bi-search me-2"), "Constats"], className="ia-section-titre"),
            html.Ul([html.Li(c) for c in constats]) if constats else html.P(texte_ia, className="small"),
            html.H6([html.I(className="bi bi-lightbulb me-2"), "Recommandations"],
                     className="ia-section-titre mt-3") if recommandations else None,
            html.Ul([html.Li(r) for r in recommandations]) if recommandations else None,
        ],
        className="ia-resultat",
    )


# ============================================================================
# 9) LANCEMENT DE L'APPLICATION
# ============================================================================
if __name__ == "__main__":
    # debug=True affiche les erreurs détaillées en développement.
    # Mettre debug=False avant un déploiement en production.
    app.run(debug=True, host="0.0.0.0", port=8050)
