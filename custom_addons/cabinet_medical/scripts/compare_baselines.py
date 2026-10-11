#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de comparaison des baselines pour la prédiction du No-Show :
1. Règle simple : lead_days > 14
2. Heuristique métier : _heuristic_risk de models/ml_no_show.py
3. Modèle Machine Learning : RandomForestClassifier (no_show_model.joblib)

Utilise exactement le même jeu de données synthétique et le même découpage
train/test (random_state=42, test_size=0.20, stratify=y) que train_no_show_model.py.
"""

import os
import sys
import importlib.util
import warnings
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
)

# Supprimer les avertissements de version de scikit-learn lors du unpickle
warnings.filterwarnings("ignore", category=UserWarning)

# Chemins relatifs sécurisés
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(MODULE_DIR, "data")
MODELS_DIR = os.path.join(MODULE_DIR, "models")

# 1. Chargement dynamique de train_no_show_model sans dépendance Odoo
train_path = os.path.join(SCRIPT_DIR, "train_no_show_model.py")
spec_train = importlib.util.spec_from_file_location("train_no_show", train_path)
if spec_train is None or spec_train.loader is None:
    raise ImportError(f"Impossible de charger le module depuis {train_path}")
train_mod = importlib.util.module_from_spec(spec_train)
sys.modules["train_no_show"] = train_mod
spec_train.loader.exec_module(train_mod)
generate_synthetic_dataset = train_mod.generate_synthetic_dataset

# 2. Chargement dynamique de ml_no_show sans déclencher models/__init__.py
ml_path = os.path.join(MODELS_DIR, "ml_no_show.py")
spec_ml = importlib.util.spec_from_file_location("ml_no_show", ml_path)
if spec_ml is None or spec_ml.loader is None:
    raise ImportError(f"Impossible de charger le module depuis {ml_path}")
ml_mod = importlib.util.module_from_spec(spec_ml)
sys.modules["ml_no_show"] = ml_mod
spec_ml.loader.exec_module(ml_mod)
_heuristic_risk = ml_mod._heuristic_risk

def run_comparison():
    # Génération du dataset identique (1 500 échantillons, seed=42)
    df = generate_synthetic_dataset(n_samples=1500, random_state=42)
    features = [
        'lead_days', 'day_of_week', 'is_afternoon', 'is_urgence',
        'is_nouveau_patient', 'patient_previous_rdv_count', 'patient_historical_noshow_rate'
    ]
    X = df[features]
    y = df['no_show']

    # Split Train/Test identique (80% train / 20% test, seed=42, stratifié)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    total_test = len(y_test)
    total_positives = int(y_test.sum())
    total_negatives = total_test - total_positives

    print("=========================================================================================")
    print("                  COMPARAISON DES BASELINES - PRÉDICTION DU NO-SHOW                      ")
    print("=========================================================================================")
    print(f"Jeu de test : {total_test} RDV ({total_negatives} Présents [0], {total_positives} Absents [1])")
    print(f"Taux de no-show réel dans le jeu de test : {total_positives / total_test * 100:.2f}%\n")

    # -------------------------------------------------------------------------
    # Baseline (a) : Règle simple (lead_days > 14)
    # -------------------------------------------------------------------------
    y_pred_a = (X_test['lead_days'] > 14).astype(int)
    auc_a = roc_auc_score(y_test, y_pred_a)
    auc_a_cont = roc_auc_score(y_test, X_test['lead_days'])
    acc_a = accuracy_score(y_test, y_pred_a)
    prec_a = precision_score(y_test, y_pred_a, zero_division=0)
    rec_a = recall_score(y_test, y_pred_a, zero_division=0)
    f1_a = f1_score(y_test, y_pred_a, zero_division=0)

    # -------------------------------------------------------------------------
    # Baseline (b) : Heuristique _heuristic_risk (models/ml_no_show.py)
    # -------------------------------------------------------------------------
    scores_b = np.array([
        _heuristic_risk(
            r['lead_days'], r['day_of_week'], r['is_afternoon'],
            r['is_urgence'], r['is_nouveau_patient'],
            r['patient_previous_rdv_count'], r['patient_historical_noshow_rate']
        )
        for _, r in X_test.iterrows()
    ])
    # ROC-AUC évalué sur le score continu (5.0 à 95.0)
    auc_b = roc_auc_score(y_test, scores_b)

    # Seuil décisionnel clinique à 30% (identique au modèle ML)
    th_b_clinique = 30.0
    y_pred_b_30 = (scores_b >= th_b_clinique).astype(int)
    acc_b_30 = accuracy_score(y_test, y_pred_b_30)
    prec_b_30 = precision_score(y_test, y_pred_b_30, zero_division=0)
    rec_b_30 = recall_score(y_test, y_pred_b_30, zero_division=0)
    f1_b_30 = f1_score(y_test, y_pred_b_30, zero_division=0)

    # Seuil 'risque élevé' du module à 45% (> 45%)
    th_b_eleve = 45.0
    y_pred_b_45 = (scores_b > th_b_eleve).astype(int)
    acc_b_45 = accuracy_score(y_test, y_pred_b_45)
    prec_b_45 = precision_score(y_test, y_pred_b_45, zero_division=0)
    rec_b_45 = recall_score(y_test, y_pred_b_45, zero_division=0)
    f1_b_45 = f1_score(y_test, y_pred_b_45, zero_division=0)

    # -------------------------------------------------------------------------
    # Baseline (c) : RandomForestClassifier enregistré (no_show_model.joblib)
    # -------------------------------------------------------------------------
    model_path = os.path.join(DATA_DIR, "no_show_model.joblib")
    rf_model = joblib.load(model_path)
    y_proba_c = rf_model.predict_proba(X_test)[:, 1]

    # Seuil officiel enregistré à 30% (tau = 0.30)
    th_c = 0.30
    y_pred_c = (y_proba_c >= th_c).astype(int)
    auc_c = roc_auc_score(y_test, y_proba_c)
    acc_c = accuracy_score(y_test, y_pred_c)
    prec_c = precision_score(y_test, y_pred_c, zero_division=0)
    rec_c = recall_score(y_test, y_pred_c, zero_division=0)
    f1_c = f1_score(y_test, y_pred_c, zero_division=0)

    # -------------------------------------------------------------------------
    # Affichage du tableau comparatif
    # -------------------------------------------------------------------------
    rows = [
        {
            "Approche / Modèle": "(a) Règle simple (lead_days > 14)",
            "ROC-AUC": f"{auc_a:.4f} (binaire) / {auc_a_cont:.4f} (continu)",
            "Accuracy": f"{acc_a:.4f}",
            "Precision": f"{prec_a:.4f}",
            "Recall": f"{rec_a:.4f}",
            "F1-Score": f"{f1_a:.4f}",
        },
        {
            "Approche / Modèle": "(b) Heuristique _heuristic_risk (seuil clinique 30%)",
            "ROC-AUC": f"{auc_b:.4f}",
            "Accuracy": f"{acc_b_30:.4f}",
            "Precision": f"{prec_b_30:.4f}",
            "Recall": f"{rec_b_30:.4f}",
            "F1-Score": f"{f1_b_30:.4f}",
        },
        {
            "Approche / Modèle": "(b bis) Heuristique _heuristic_risk (seuil élevé > 45%)",
            "ROC-AUC": f"{auc_b:.4f}",
            "Accuracy": f"{acc_b_45:.4f}",
            "Precision": f"{prec_b_45:.4f}",
            "Recall": f"{rec_b_45:.4f}",
            "F1-Score": f"{f1_b_45:.4f}",
        },
        {
            "Approche / Modèle": "(c) Random Forest enregistré (seuil clinique 30%)",
            "ROC-AUC": f"{auc_c:.4f}",
            "Accuracy": f"{acc_c:.4f}",
            "Precision": f"{prec_c:.4f}",
            "Recall": f"{rec_c:.4f}",
            "F1-Score": f"{f1_c:.4f}",
        },
    ]

    df_results = pd.DataFrame(rows)
    print(df_results.to_string(index=False))
    print("\n=========================================================================================")

if __name__ == "__main__":
    run_comparison()
