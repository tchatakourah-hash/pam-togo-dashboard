# ============================================================================
# GENERATE_KOBO_FORM.PY — Génère le formulaire XLSForm pour KoboToolbox
# ----------------------------------------------------------------------------
# Ce script crée "kobo_formulaire_pam.xlsx" : un formulaire au format
# XLSForm, prêt à être importé TEL QUEL dans KoboToolbox (kf.kobotoolbox.org
# ou humanitarianresponse.info) pour que les agents de terrain collectent
# les données sur smartphone/tablette (via l'app KoboCollect, y compris
# hors-ligne).
#
# Les noms de questions (colonne "name") sont VOLONTAIREMENT identiques aux
# colonnes attendues par le dashboard (app.py / donnees_pam.xlsx), afin que
# l'export Kobo puisse être branché sans modifier le code du dashboard.
# Voir GUIDE_UTILISATION.md, section "Formulaire Kobo pour les agents".
#
# Exécution :
#       python generate_kobo_form.py
# ============================================================================

import pandas as pd

# ----------------------------------------------------------------------------
# 1) FEUILLE "survey" — les questions du formulaire, dans l'ordre d'affichage
# ----------------------------------------------------------------------------
survey = [
    # type, name, label, hint, required, appearance, constraint, constraint_message, calculation
    {"type": "start", "name": "start", "label": ""},
    {"type": "end", "name": "end", "label": ""},

    {"type": "note", "name": "note_intro", "label": "Enquêteur PAM — Fiche de suivi d'une distribution"},

    {"type": "text", "name": "id_distribution", "label": "Identifiant de la distribution",
     "hint": "Ex : PAM-TG-0301. Laisser un format cohérent avec le registre du bureau.",
     "required": "yes"},

    {"type": "date", "name": "date_distribution", "label": "Date de la distribution",
     "required": "yes"},

    {"type": "select_one region_choices", "name": "region", "label": "Région",
     "required": "yes"},

    {"type": "select_one prefecture_choices", "name": "prefecture", "label": "Préfecture",
     "required": "yes", "appearance": "search",
     "choice_filter": "region=${region}"},

    {"type": "select_one type_aide_choices", "name": "type_aide", "label": "Type d'aide distribuée",
     "required": "yes"},

    {"type": "integer", "name": "cible", "label": "Nombre de bénéficiaires ciblés",
     "hint": "Nombre prévu selon le plan de distribution.", "required": "yes",
     "constraint": ". >= 0", "constraint_message": "La valeur doit être positive."},

    {"type": "integer", "name": "atteint", "label": "Nombre de bénéficiaires réellement atteints",
     "hint": "Nombre de personnes effectivement servies aujourd'hui.", "required": "yes",
     "constraint": ". >= 0", "constraint_message": "La valeur doit être positive."},

    {"type": "decimal", "name": "stock_restant_kg", "label": "Stock restant après distribution (en kg)",
     "required": "yes", "constraint": ". >= 0",
     "constraint_message": "La valeur doit être positive."},

    {"type": "decimal", "name": "consommation_jour", "label": "Consommation journalière moyenne (en kg/jour)",
     "hint": "Utilisée pour calculer l'autonomie de stock restante.",
     "required": "yes", "constraint": ". > 0",
     "constraint_message": "La valeur doit être supérieure à zéro."},

    {"type": "integer", "name": "delai_jours", "label": "Délai entre planification et distribution réelle (en jours)",
     "required": "yes", "constraint": ". >= 0",
     "constraint_message": "La valeur doit être positive."},

    {"type": "decimal", "name": "satisfaction_moyenne",
     "label": "Satisfaction moyenne des bénéficiaires (enquête rapide, note sur 5)",
     "hint": "Moyenne des notes recueillies auprès d'un échantillon de bénéficiaires (1 = très insatisfait, 5 = très satisfait).",
     "required": "yes", "constraint": ". >= 1 and . <= 5",
     "constraint_message": "La note doit être comprise entre 1 et 5."},

    {"type": "geopoint", "name": "position_gps", "label": "Position GPS du site de distribution",
     "hint": "Activez le GPS et attendez une bonne précision avant de valider.",
     "required": "yes"},

    {"type": "note", "name": "note_fin",
     "label": "Merci ! Vérifiez les informations avant d'envoyer le formulaire."},
]

df_survey = pd.DataFrame(survey)
# On garantit la présence de toutes les colonnes XLSForm usuelles, même vides
colonnes_survey = ["type", "name", "label", "hint", "required", "appearance",
                    "constraint", "constraint_message", "choice_filter", "calculation"]
for col in colonnes_survey:
    if col not in df_survey.columns:
        df_survey[col] = ""
df_survey = df_survey[colonnes_survey]

# ----------------------------------------------------------------------------
# 2) FEUILLE "choices" — les options des questions à choix (select_one)
# ----------------------------------------------------------------------------
choices = []

# --- Régions ---
for nom in ["Maritime", "Plateaux", "Centrale", "Kara", "Savanes"]:
    choices.append({"list_name": "region_choices", "name": nom, "label": nom})

# --- Préfectures (avec colonne 'region' pour le filtrage en cascade) ---
prefectures_par_region = {
    "Maritime": ["Golfe", "Avé", "Vo", "Yoto", "Zio", "Lacs", "Bas-Mono"],
    "Plateaux": ["Ogou", "Wawa", "Amou", "Kloto", "Danyi", "Akébou", "Anié", "Haho"],
    "Centrale": ["Tchamba", "Tchaoudjo", "Sotouboua", "Blitta"],
    "Kara": ["Kozah", "Bassar", "Assoli", "Bimah", "Dankpen", "Doufelgou", "Kéran"],
    "Savanes": ["Tône", "Cinkassé", "Kpendjal", "Oti", "Tandjouaré", "Oti-Sud"],
}
for region, prefectures in prefectures_par_region.items():
    for prefecture in prefectures:
        choices.append({
            "list_name": "prefecture_choices",
            "name": prefecture.lower().replace(" ", "_").replace("-", "_"),
            "label": prefecture,
            "region": region,
        })

# --- Types d'aide ---
for nom in ["Vivres", "Cash Transfert", "Nutrition", "Cantines Scolaires", "Résilience"]:
    choices.append({
        "list_name": "type_aide_choices",
        "name": nom.lower().replace(" ", "_"),
        "label": nom,
    })

df_choices = pd.DataFrame(choices)
for col in ["list_name", "name", "label", "region"]:
    if col not in df_choices.columns:
        df_choices[col] = ""
df_choices = df_choices[["list_name", "name", "label", "region"]]

# ----------------------------------------------------------------------------
# 3) FEUILLE "settings" — métadonnées du formulaire
# ----------------------------------------------------------------------------
df_settings = pd.DataFrame([{
    "form_title": "PAM Togo - Fiche de suivi des distributions",
    "form_id": "pam_togo_suivi_distributions",
    "version": "2026010100",
    "default_language": "français (fr)",
}])

# ----------------------------------------------------------------------------
# 4) EXPORT DANS UN SEUL FICHIER EXCEL (3 feuilles, format XLSForm standard)
# ----------------------------------------------------------------------------
chemin_sortie = "kobo_formulaire_pam.xlsx"
with pd.ExcelWriter(chemin_sortie, engine="openpyxl") as writer:
    df_survey.to_excel(writer, sheet_name="survey", index=False)
    df_choices.to_excel(writer, sheet_name="choices", index=False)
    df_settings.to_excel(writer, sheet_name="settings", index=False)

print(f"✅ Formulaire XLSForm généré : {chemin_sortie}")
print("   → À importer directement sur kf.kobotoolbox.org (bouton 'New' > 'Upload XLSForm')")
