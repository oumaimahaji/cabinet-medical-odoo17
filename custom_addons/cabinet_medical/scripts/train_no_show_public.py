#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script d'entraînement et d'évaluation du modèle No-Show sur le jeu de données public
Kaggle ("Medical Appointment No Shows").

Règles respectées :
- Aucune modification de no_show_model.joblib, ml_no_show.py ni aucun fichier existant.
- Sauvegarde sous no_show_model_public.joblib.
- Calcul chronologique strict de l'historique patient sans fuite de données (data leakage).
- Exclusion explicite de SMS_received et Scholarship.
"""

import os
import sys
import glob
import warnings
import numpy as np
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)

warnings.filterwarnings("ignore", category=UserWarning)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(MODULE_DIR, "data")


def locate_kaggle_csv():
    candidates = [
        os.path.join(SCRIPT_DIR, "KaggleV2-May.csv"),
        os.path.join(SCRIPT_DIR, "KaggleV2-May-2016.csv"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    matches = glob.glob(os.path.join(SCRIPT_DIR, "*Kaggle*.csv"))
    if matches:
        return matches[0]
    raise FileNotFoundError("Impossible de trouver le fichier CSV Kaggle dans scripts/")


def main():
    print("=" * 90)
    print("  ENTRAÎNEMENT & ANALYSE SUR JEU DE DONNÉES PUBLIC KAGGLE (MEDICAL APPOINTMENTS)")
    print("=" * 90)

    # -------------------------------------------------------------------------
    # 1. Lecture du CSV et inspection
    # -------------------------------------------------------------------------
    csv_path = locate_kaggle_csv()
    print(f"\n[1] LECTURE DU DATASET : {os.path.basename(csv_path)}")
    df_raw = pd.read_csv(csv_path)

    total_rows_raw = len(df_raw)
    raw_cols = df_raw.columns.tolist()
    print(f"  - Nombre de lignes brut : {total_rows_raw:,}")
    print(f"  - Colonnes réelles ({len(raw_cols)}) : {raw_cols}")

    target_counts = df_raw["No-show"].value_counts(dropna=False)
    noshow_yes = int(target_counts.get("Yes", 0))
    noshow_no = int(target_counts.get("No", 0))
    raw_noshow_rate = (noshow_yes / total_rows_raw) * 100

    print("  - Distribution de la colonne cible 'No-show' :")
    print(f"      'No'  (Patient venu / présent) : {noshow_no:,} ({noshow_no/total_rows_raw*100:.2f}%)")
    print(f"      'Yes' (Patient absent / No-show) : {noshow_yes:,} ({raw_noshow_rate:.2f}%)")
    print("  - Sens validé : 'No-show' = 'Yes' correspond à un patient ABSENT (classe positive = 1).")

    # Vérification de l'heure dans AppointmentDay
    app_day_series = df_raw["AppointmentDay"].astype(str)
    unique_times = app_day_series.str.extract(r'T(.*)$')[0].value_counts()
    print("  - Vérification de l'heure dans AppointmentDay :")
    for time_val, count in unique_times.items():
        print(f"      Composante heure '{time_val}' : {count:,} lignes ({count/total_rows_raw*100:.1f}%)")
    if len(unique_times) == 1 and unique_times.index[0] in ["00:00:00Z", "00:00:00"]:
        print("    -> Constat : AppointmentDay ne contient AUCUNE heure (tronqué à minuit 00:00:00Z).")

    # -------------------------------------------------------------------------
    # 2. Nettoyage : suppression des incohérences
    # -------------------------------------------------------------------------
    print("\n[2] NETTOYAGE DES LIGNES INCOHÉRENTES")
    sched_dates = pd.to_datetime(df_raw["ScheduledDay"]).dt.normalize()
    app_dates = pd.to_datetime(df_raw["AppointmentDay"]).dt.normalize()

    mask_negative_age = df_raw["Age"] < 0
    mask_date_incoherent = app_dates < sched_dates
    mask_invalid = mask_negative_age | mask_date_incoherent

    nb_neg_age = int(mask_negative_age.sum())
    nb_date_incoh = int(mask_date_incoherent.sum())
    nb_total_dropped = int(mask_invalid.sum())

    print(f"  - Lignes avec âge négatif (Age < 0) : {nb_neg_age}")
    print(f"  - Lignes avec date de RDV antérieure à la date de prise (AppointmentDate < ScheduledDate) : {nb_date_incoh}")
    print(f"  - Total lignes supprimées : {nb_total_dropped}")

    df = df_raw[~mask_invalid].copy()
    print(f"  - Lignes conservées après nettoyage : {len(df):,}")

    # -------------------------------------------------------------------------
    # 3. Calcul des variables & Historique sans fuite de données
    # -------------------------------------------------------------------------
    print("\n[3] CALCUL DES VARIABLES & HISTORIQUE PATIENT SANS FUITE DE DONNÉES")
    df["sched_dt"] = pd.to_datetime(df["ScheduledDay"])
    df["app_dt"] = pd.to_datetime(df["AppointmentDay"])

    # Tri chronologique rigoureux : d'abord la date du RDV, puis le moment de prise de RDV, puis ID
    df = df.sort_values(by=["app_dt", "sched_dt", "AppointmentID"]).reset_index(drop=True)

    # Variables de base
    # lead_days = différence stricte entre les DATES (jours calendaires entiers)
    # Calcul vectorisé via NumPy datetime64[D] pour tronquer au jour calendaire sans ambiguïté de type statique
    df["lead_days"] = (
        np.asarray(df["app_dt"], dtype="datetime64[D]") - np.asarray(df["sched_dt"], dtype="datetime64[D]")
    ).astype(int)
    df["day_of_week"] = getattr(df["app_dt"].dt, "dayofweek")  # 0=Lundi, ..., 6=Dimanche
    df["no_show_target"] = (df["No-show"] == "Yes").astype(int)

    # Calcul chronologique de l'historique patient SANS fuite de données :
    # cumcount() donne 0 pour le premier rendez-vous, 1 pour le second, etc.
    df["patient_previous_rdv_count"] = df.groupby("PatientId").cumcount()

    # Cumsum des absences excluant le rendez-vous en cours
    prev_absences = df.groupby("PatientId")["no_show_target"].cumsum() - df["no_show_target"]
    df["patient_historical_noshow_rate"] = np.where(
        df["patient_previous_rdv_count"] > 0,
        prev_absences / df["patient_previous_rdv_count"],
        0.0
    )
    df["is_nouveau_patient"] = np.where(df["patient_previous_rdv_count"] == 0, 1, 0)

    print(f"  - lead_days : min={df['lead_days'].min()}, median={df['lead_days'].median():.0f}, max={df['lead_days'].max()}, mean={df['lead_days'].mean():.2f}")
    print(f"  - Distribution day_of_week (Lundi=0 -> Samedi=5) :\n{df['day_of_week'].value_counts().sort_index().to_dict()}")
    print(f"  - Patients uniques : {df['PatientId'].nunique():,}")
    print(f"  - Nouveaux patients (1er RDV du dataset) : {(df['is_nouveau_patient'] == 1).sum():,} ({(df['is_nouveau_patient'] == 1).mean()*100:.1f}%)")
    print(f"  - RDV avec historique antérieur : {(df['is_nouveau_patient'] == 0).sum():,} ({(df['is_nouveau_patient'] == 0).mean()*100:.1f}%)")
    print(f"  - Taux de no-show moyen historique pour les patients récurrents : {df[df['is_nouveau_patient'] == 0]['patient_historical_noshow_rate'].mean()*100:.2f}%")

    # -------------------------------------------------------------------------
    # 4. Inventaire des variables du modèle actuel vs calculables
    # -------------------------------------------------------------------------
    print("\n[4] ANALYSE COMPARATIVE DES VARIABLES DU MODÈLE ACTUEL")
    print("  Variables du modèle actuel (models/ml_no_show.py / train_no_show_model.py) :")
    print("    1. lead_days                       -> CALCULABLE (AppointmentDay - ScheduledDay)")
    print("    2. day_of_week                     -> CALCULABLE (AppointmentDay.weekday)")
    print("    3. is_afternoon                    -> NON CALCULABLE (AppointmentDay n'a pas d'heure dans Kaggle)")
    print("    4. is_urgence                      -> NON CALCULABLE (aucune notion d'urgence/motif dans Kaggle)")
    print("    5. is_nouveau_patient              -> CALCULABLE (patient_previous_rdv_count == 0)")
    print("    6. patient_previous_rdv_count      -> CALCULABLE (historique chronologique par PatientId)")
    print("    7. patient_historical_noshow_rate  -> CALCULABLE (taux d'absence passé sans fuite)")
    print("  -> Les variables 'is_afternoon' et 'is_urgence' NE PEUVENT PAS être calculées avec ce jeu de données.")
    print("     Elles ne sont donc PAS injectées arbitrairement.")

    # -------------------------------------------------------------------------
    # 5. Exclusion des variables tierces
    # -------------------------------------------------------------------------
    print("\n[5] EXCLUSION DES VARIABLES TIERCES")
    print("  - SMS_received et Scholarship sont EXCLUES des variables explicatives.")
    
    features = [
        "lead_days",
        "day_of_week",
        "is_nouveau_patient",
        "patient_previous_rdv_count",
        "patient_historical_noshow_rate"
    ]
    print(f"  - Variables explicatives retenues ({len(features)}) : {features}")

    X = df[features]
    y = df["no_show_target"]

    # -------------------------------------------------------------------------
    # 6. Découpage Train/Test 80/20 stratifié
    # -------------------------------------------------------------------------
    print("\n[6] DÉCOUPAGE TRAIN / TEST (80% / 20%, stratifié, random_state=42)")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    print(f"  - Train set : {len(X_train):,} RDV ({y_train.sum():,} absences, {y_train.mean()*100:.2f}%)")
    print(f"  - Test set  : {len(X_test):,} RDV ({y_test.sum():,} absences, {y_test.mean()*100:.2f}%)")

    # -------------------------------------------------------------------------
    # 7. Entraînement RandomForest (mêmes hyperparamètres)
    # -------------------------------------------------------------------------
    print("\n[7] ENTRAÎNEMENT DU RANDOM FOREST CLASSIFIER")
    print("  Hyperparamètres : n_estimators=100, max_depth=6, min_samples_split=5, min_samples_leaf=3, random_state=42")
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=6,
        min_samples_split=5,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1
    )
    rf_model.fit(X_train, y_train)

    # -------------------------------------------------------------------------
    # 8. Évaluation sur le test & Validation croisée
    # -------------------------------------------------------------------------
    print("\n[8] ÉVALUATION DU MODÈLE RANDOM FOREST")
    threshold = 0.30
    rf_proba = rf_model.predict_proba(X_test)[:, 1]
    rf_pred_30 = (rf_proba >= threshold).astype(int)

    rf_roc_auc = roc_auc_score(y_test, rf_proba)
    rf_acc = accuracy_score(y_test, rf_pred_30)
    rf_prec = precision_score(y_test, rf_pred_30, zero_division=0)
    rf_rec = recall_score(y_test, rf_pred_30, zero_division=0)
    rf_f1 = f1_score(y_test, rf_pred_30, zero_division=0)

    print(f"  - Seuil clinique décisionnel : {threshold*100:.0f}%")
    print(f"  - ROC-AUC  : {rf_roc_auc:.4f}")
    print(f"  - Accuracy : {rf_acc:.4f} ({rf_acc*100:.2f}%)")
    print(f"  - Precision: {rf_prec:.4f} ({rf_prec*100:.2f}%)")
    print(f"  - Recall   : {rf_rec:.4f} ({rf_rec*100:.2f}%)")
    print(f"  - F1-Score : {rf_f1:.4f}")

    print("\n  - Validation croisée 5-Fold ROC-AUC (sur l'ensemble des données) :")
    cv_scores = cross_val_score(rf_model, X, y, cv=5, scoring="roc_auc", n_jobs=-1)
    print(f"      Scores des 5 plis : {[round(float(s), 4) for s in cv_scores]}")
    print(f"      Moyenne CV ROC-AUC: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

    # -------------------------------------------------------------------------
    # 9. Comparaison avec les baselines (Règle simple & Régression Logistique)
    # -------------------------------------------------------------------------
    print("\n[9] COMPARAISON DES MODÈLES SUR LE MÊME JEU DE TEST")

    # (a) Règle simple : lead_days > 14
    rule_pred = (X_test["lead_days"] > 14).astype(int)
    rule_auc_bin = roc_auc_score(y_test, rule_pred)
    rule_auc_cont = roc_auc_score(y_test, X_test["lead_days"])
    rule_acc = accuracy_score(y_test, rule_pred)
    rule_prec = precision_score(y_test, rule_pred, zero_division=0)
    rule_rec = recall_score(y_test, rule_pred, zero_division=0)
    rule_f1 = f1_score(y_test, rule_pred, zero_division=0)

    # (b) Régression Logistique (avec standardisation préalable)
    lr_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(random_state=42, max_iter=1000))
    ])
    lr_pipeline.fit(X_train, y_train)
    lr_proba = lr_pipeline.predict_proba(X_test)[:, 1]
    lr_pred_30 = (lr_proba >= threshold).astype(int)

    lr_auc = roc_auc_score(y_test, lr_proba)
    lr_acc = accuracy_score(y_test, lr_pred_30)
    lr_prec = precision_score(y_test, lr_pred_30, zero_division=0)
    lr_rec = recall_score(y_test, lr_pred_30, zero_division=0)
    lr_f1 = f1_score(y_test, lr_pred_30, zero_division=0)

    comparison_rows = [
        {
            "Approche": "1. Règle simple (lead_days > 14)",
            "ROC-AUC": f"{rule_auc_bin:.4f} (bin) / {rule_auc_cont:.4f} (cont)",
            "Accuracy": f"{rule_acc:.4f}",
            "Precision": f"{rule_prec:.4f}",
            "Recall": f"{rule_rec:.4f}",
            "F1-Score": f"{rule_f1:.4f}",
        },
        {
            "Approche": "2. Régression Logistique (seuil 30%)",
            "ROC-AUC": f"{lr_auc:.4f}",
            "Accuracy": f"{lr_acc:.4f}",
            "Precision": f"{lr_prec:.4f}",
            "Recall": f"{lr_rec:.4f}",
            "F1-Score": f"{lr_f1:.4f}",
        },
        {
            "Approche": "3. Random Forest Public (seuil 30%)",
            "ROC-AUC": f"{rf_roc_auc:.4f}",
            "Accuracy": f"{rf_acc:.4f}",
            "Precision": f"{rf_prec:.4f}",
            "Recall": f"{rf_rec:.4f}",
            "F1-Score": f"{rf_f1:.4f}",
        },
    ]

    df_comp = pd.DataFrame(comparison_rows)
    print(df_comp.to_string(index=False))

    # -------------------------------------------------------------------------
    # 10. Importance des variables
    # -------------------------------------------------------------------------
    print("\n[10] IMPORTANCE DES VARIABLES (RANDOM FOREST)")
    importances = rf_model.feature_importances_
    sorted_importances = sorted(zip(features, importances), key=lambda x: x[1], reverse=True)
    for feat, imp in sorted_importances:
        print(f"  - {feat:32s} : {imp*100:6.2f}%")

    # -------------------------------------------------------------------------
    # Sauvegarde du modèle sous no_show_model_public.joblib et métriques JSON
    # -------------------------------------------------------------------------
    os.makedirs(DATA_DIR, exist_ok=True)
    out_path_data = os.path.join(DATA_DIR, "no_show_model_public.joblib")
    joblib.dump(rf_model, out_path_data)

    cm = confusion_matrix(y_test, rf_pred_30)
    tn, fp, fn, tp = cm.ravel()

    metrics_public = {
        "dataset": {
            "name": "Medical Appointment No Shows",
            "source_file": os.path.basename(csv_path),
            "author": "Joni Hoppen (Aquarela Analytics)",
            "license": "CC BY-NC-SA 4.0",
            "license_source": "Kaggle Dataset (Medical Appointment No Shows - Joni Hoppen / Aquarela Advanced Analytics)",
            "publication_year": 2016,
            "training_date": "2026-10-11",
            "total_rows_raw": total_rows_raw,
            "total_rows_cleaned": len(df),
            "cleaned_rows_dropped": nb_total_dropped,
            "unique_patients": int(df["PatientId"].nunique()),
            "natural_noshow_rate_percent": round(float(df["no_show_target"].mean() * 100), 2)
        },
        "model": {
            "model_name": "RandomForestClassifier",
            "hyperparameters": {
                "n_estimators": 100,
                "max_depth": 6,
                "min_samples_split": 5,
                "min_samples_leaf": 3,
                "random_state": 42
            },
            "features": features,
            "features_count": len(features),
            "train_size": len(X_train),
            "test_size": len(X_test),
            "decision_threshold": threshold,
            "risk_thresholds": {
                "faible": "< 25%",
                "moyen": "25% - 45%",
                "eleve": "> 45%"
            }
        },
        "test_metrics": {
            "accuracy": round(float(rf_acc), 4),
            "precision": round(float(rf_prec), 4),
            "recall": round(float(rf_rec), 4),
            "f1_score": round(float(rf_f1), 4),
            "roc_auc": round(float(rf_roc_auc), 4),
            "cv_roc_auc_5fold_mean": round(float(cv_scores.mean()), 4),
            "cv_roc_auc_5fold_std": round(float(cv_scores.std()), 4)
        },
        "confusion_matrix": {
            "true_negatives_venu_predit_venu": int(tn),
            "false_positives_venu_predit_absent": int(fp),
            "false_negatives_absent_predit_venu": int(fn),
            "true_positives_absent_predit_absent": int(tp)
        },
        "feature_importances": [
            {"feature": f, "importance_percent": round(float(imp * 100), 2)}
            for f, imp in sorted_importances
        ]
    }

    metrics_path = os.path.join(DATA_DIR, "no_show_metrics_public.json")
    import json
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_public, f, indent=4, ensure_ascii=False)

    print("\n" + "=" * 90)
    print("  SAUVEGARDE DU NOUVEAU MODÈLE & DES MÉTRIQUES RÉALISÉE AVEC SUCCÈS")
    print(f"  - Modèle : {out_path_data}")
    print(f"  - Métriques JSON : {metrics_path}")
    print("  - Fichier original intact : data/no_show_model.joblib (NON MODIFIÉ)")
    print("=" * 90)


if __name__ == "__main__":
    main()
