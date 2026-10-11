#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script d'analyse des seuils décisionnels et de calibration du risque No-Show
sur le jeu de données public Kaggle ("Medical Appointment No Shows").

Règles respectées :
- Aucun fichier existant n'est modifié.
- Mêmes étapes de nettoyage (incohérences de dates et âges négatifs).
- Même calcul chronologique sans fuite de données (data leakage).
- Mêmes variables explicatives.
- Même split initial train/test (80/20, stratifié, random_state=42).
"""

import os
import sys
import glob
import warnings
import numpy as np
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score

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


def locate_public_model():
    candidates = [
        os.path.join(DATA_DIR, "no_show_model_public.joblib"),
        os.path.join(SCRIPT_DIR, "no_show_model_public.joblib"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    raise FileNotFoundError("Impossible de trouver no_show_model_public.joblib. Exécutez d'abord train_no_show_public.py.")


def prepare_dataset():
    csv_path = locate_kaggle_csv()
    df_raw = pd.read_csv(csv_path)

    # Nettoyage identique à train_no_show_public.py
    sched_dates = pd.to_datetime(df_raw["ScheduledDay"]).dt.date
    app_dates = pd.to_datetime(df_raw["AppointmentDay"]).dt.date

    mask_invalid = (df_raw["Age"] < 0) | (app_dates < sched_dates)
    df = df_raw[~mask_invalid].copy()

    df["sched_dt"] = pd.to_datetime(df["ScheduledDay"])
    df["app_dt"] = pd.to_datetime(df["AppointmentDay"])

    # Tri chronologique strict sans fuite de données
    df = df.sort_values(by=["app_dt", "sched_dt", "AppointmentID"]).reset_index(drop=True)

    df["lead_days"] = (df["app_dt"].dt.date - df["sched_dt"].dt.date).apply(lambda d: d.days)
    df["day_of_week"] = df["app_dt"].dt.dayofweek
    df["no_show_target"] = (df["No-show"] == "Yes").astype(int)

    df["patient_previous_rdv_count"] = df.groupby("PatientId").cumcount()
    prev_absences = df.groupby("PatientId")["no_show_target"].cumsum() - df["no_show_target"]
    df["patient_historical_noshow_rate"] = np.where(
        df["patient_previous_rdv_count"] > 0,
        prev_absences / df["patient_previous_rdv_count"],
        0.0
    )
    df["is_nouveau_patient"] = np.where(df["patient_previous_rdv_count"] == 0, 1, 0)

    features = [
        "lead_days",
        "day_of_week",
        "is_nouveau_patient",
        "patient_previous_rdv_count",
        "patient_historical_noshow_rate"
    ]
    return df[features], df["no_show_target"]


def main():
    print("=" * 95)
    print("  ANALYSE DES SEUILS DÉCISIONNELS & CALIBRATION DU RISQUE (DATASET PUBLIC KAGGLE)")
    print("=" * 95)

    X, y = prepare_dataset()

    # Split initial 80% Train / 20% Test (identique à train_no_show_public.py)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    print(f"\n[INIT] Découpage initial 80/20 :")
    print(f"  - Train : {len(X_train):,} RDV ({y_train.sum():,} absences, {y_train.mean()*100:.2f}%)")
    print(f"  - Test  : {len(X_test):,} RDV ({y_test.sum():,} absences, {y_test.mean()*100:.2f}%)")

    # -------------------------------------------------------------------------
    # 1. Découpage du train en train/validation (80/20) & Optimisation de seuils
    # -------------------------------------------------------------------------
    print("\n" + "-" * 95)
    print("1. SOUS-DÉCOUPAGE DU TRAIN EN TRAIN / VALIDATION (80/20) & BALAYAGE DES SEUILS")
    print("-" * 95)

    X_subtrain, X_val, y_subtrain, y_val = train_test_split(
        X_train, y_train, test_size=0.20, random_state=42, stratify=y_train
    )

    print(f"  - Sous-Train (64% du total) : {len(X_subtrain):,} RDV")
    print(f"  - Validation (16% du total) : {len(X_val):,} RDV ({y_val.sum():,} absences, {y_val.mean()*100:.2f}%)")

    # Entraînement Random Forest sur le sous-train
    rf_sub = RandomForestClassifier(
        n_estimators=100,
        max_depth=6,
        min_samples_split=5,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1
    )
    rf_sub.fit(X_subtrain, y_subtrain)

    val_proba = rf_sub.predict_proba(X_val)[:, 1]
    val_auc = roc_auc_score(y_val, val_proba)
    print(f"  - ROC-AUC sur Validation : {val_auc:.4f}")

    seuils = [0.15, 0.20, 0.25, 0.30, 0.35, 0.40]
    rows_seuils = []

    for th in seuils:
        y_pred = (val_proba >= th).astype(int)
        nb_signales = int(y_pred.sum())
        pct_signales = (nb_signales / len(X_val)) * 100
        prec = precision_score(y_val, y_pred, zero_division=0)
        rec = recall_score(y_val, y_pred, zero_division=0)
        f1 = f1_score(y_val, y_pred, zero_division=0)
        vrais_positifs = int((y_pred & y_val).sum())

        rows_seuils.append({
            "Seuil": f"{th:.2f} ({int(th*100)}%)",
            "RDV Signalés": f"{nb_signales:,} ({pct_signales:5.1f}%)",
            "Absents Capturés (TP)": f"{vrais_positifs:,} / {y_val.sum():,}",
            "Precision": f"{prec:.4f} ({prec*100:5.2f}%)",
            "Recall (Sensibilité)": f"{rec:.4f} ({rec*100:5.2f}%)",
            "F1-Score": f"{f1:.4f}",
        })

    df_seuils = pd.DataFrame(rows_seuils)
    print("\nPerformances sur l'ensemble de validation selon le seuil :")
    print(df_seuils.to_string(index=False))

    # -------------------------------------------------------------------------
    # 2. Distribution des probabilités prédites
    # -------------------------------------------------------------------------
    print("\n" + "-" * 95)
    print("2. DISTRIBUTION DES PROBABILITÉS PRÉDITES (VALIDATION)")
    print("-" * 95)

    p_min = float(np.min(val_proba))
    p_q25 = float(np.percentile(val_proba, 25))
    p_med = float(np.median(val_proba))
    p_mean = float(np.mean(val_proba))
    p_q75 = float(np.percentile(val_proba, 75))
    p_max = float(np.max(val_proba))
    p_std = float(np.std(val_proba))

    print(f"  - Minimum       : {p_min:.4f} ({p_min*100:.2f}%)")
    print(f"  - 1er quartile  : {p_q25:.4f} ({p_q25*100:.2f}%)")
    print(f"  - Médiane (50%) : {p_med:.4f} ({p_med*100:.2f}%)")
    print(f"  - Moyenne       : {p_mean:.4f} ({p_mean*100:.2f}%)")
    print(f"  - 3e quartile   : {p_q75:.4f} ({p_q75*100:.2f}%)")
    print(f"  - Maximum       : {p_max:.4f} ({p_max*100:.2f}%)")
    print(f"  - Écart-type    : {p_std:.4f}")

    # -------------------------------------------------------------------------
    # 3. Évaluation sur le test avec no_show_model_public.joblib (groupes cliniques)
    # -------------------------------------------------------------------------
    print("\n" + "-" * 95)
    print("3. ÉVALUATION SUR LE TEST AVEC LE MODÈLE OFFICIEL (no_show_model_public.joblib)")
    print("   Tranches de risque de ml_no_show.py : Faible (<25%), Moyen [25%-45%], Élevé (>45%)")
    print("-" * 95)

    model_path = locate_public_model()
    print(f"  - Modèle chargé depuis : {model_path}")
    rf_public = joblib.load(model_path)

    test_proba = rf_public.predict_proba(X_test)[:, 1]

    mask_faible = test_proba < 0.25
    mask_moyen = (test_proba >= 0.25) & (test_proba <= 0.45)
    mask_eleve = test_proba > 0.45

    groupes = [
        ("Faible (< 25%)", mask_faible),
        ("Moyen (25% - 45%)", mask_moyen),
        ("Élevé (> 45%)", mask_eleve),
    ]

    total_test = len(X_test)
    total_absents_test = int(y_test.sum())
    rows_groupes = []

    for label, mask in groupes:
        nb_rdv = int(mask.sum())
        part_rdv = (nb_rdv / total_test) * 100
        abs_reels = int(y_test[mask].sum())
        taux_absence_reel = (abs_reels / nb_rdv * 100) if nb_rdv > 0 else 0.0
        part_absents_captures = (abs_reels / total_absents_test * 100) if total_absents_test > 0 else 0.0

        rows_groupes.append({
            "Niveau de Risque": label,
            "Nombre RDV": f"{nb_rdv:,}",
            "Part des RDV (%)": f"{part_rdv:6.2f}%",
            "Absents Réels": f"{abs_reels:,}",
            "Taux d'Absence Réel": f"{taux_absence_reel:6.2f}%",
            "Part des Absents Capturés": f"{part_absents_captures:6.2f}%"
        })

    df_groupes = pd.DataFrame(rows_groupes)
    print("\nRépartition et taux d'absence réels observés sur le jeu de test :")
    print(df_groupes.to_string(index=False))

    print("\n" + "=" * 95)


if __name__ == "__main__":
    main()
