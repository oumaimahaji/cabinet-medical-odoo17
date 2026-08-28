import os
import json
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)
import joblib

def generate_synthetic_dataset(n_samples=1500, random_state=42):
    """
    Génère un jeu de données simulé réaliste de 1 500 rendez-vous médicaux
    en s'appuyant sur la littérature clinique sur l'absentéisme (No-Show).
    """
    np.random.seed(random_state)
    
    # 1. Variables explicatives
    lead_days = np.clip(np.random.exponential(scale=10.0, size=n_samples) + np.random.uniform(0, 3, size=n_samples), 0, 60).round().astype(int)
    day_of_week = np.random.choice([0, 1, 2, 3, 4, 5], size=n_samples, p=[0.22, 0.18, 0.18, 0.18, 0.16, 0.08])
    is_afternoon = np.random.binomial(1, 0.45, size=n_samples)
    is_urgence = np.random.binomial(1, 0.08, size=n_samples)
    is_nouveau_patient = np.random.binomial(1, 0.25, size=n_samples)
    
    patient_previous_rdv_count = np.where(
        is_nouveau_patient == 1,
        0,
        np.random.poisson(lam=4.0, size=n_samples) + 1
    )
    
    patient_historical_noshow_rate = np.zeros(n_samples)
    for i in range(n_samples):
        if is_nouveau_patient[i] == 0:
            category = np.random.choice([0, 1, 2], p=[0.70, 0.20, 0.10])
            if category == 0:
                patient_historical_noshow_rate[i] = 0.0
            elif category == 1:
                patient_historical_noshow_rate[i] = np.random.uniform(0.10, 0.30)
            else:
                patient_historical_noshow_rate[i] = np.random.uniform(0.40, 0.80)
    
    # 2. Modélisation de la probabilité réelle de No-Show
    logit = (
        -1.85
        + 0.045 * lead_days
        + 0.40 * (day_of_week == 0).astype(int)
        + 0.35 * (day_of_week == 4).astype(int)
        + 0.15 * is_afternoon
        + 0.50 * is_nouveau_patient
        + 2.80 * patient_historical_noshow_rate
        - 0.12 * np.log1p(patient_previous_rdv_count)
        - 2.50 * is_urgence
        + np.random.normal(0, 0.35, size=n_samples)
    )
    
    prob_no_show = 1.0 / (1.0 + np.exp(-logit))
    prob_no_show = np.where(is_urgence == 1, np.minimum(prob_no_show, 0.03), prob_no_show)
    no_show = np.random.binomial(1, prob_no_show)
    
    df = pd.DataFrame({
        'lead_days': lead_days,
        'day_of_week': day_of_week,
        'is_afternoon': is_afternoon,
        'is_urgence': is_urgence,
        'is_nouveau_patient': is_nouveau_patient,
        'patient_previous_rdv_count': patient_previous_rdv_count,
        'patient_historical_noshow_rate': np.round(patient_historical_noshow_rate, 3),
        'no_show': no_show
    })
    
    return df

def train_and_evaluate_model(output_dir="custom_addons/cabinet_medical/data"):
    """
    Entraîne le RandomForestClassifier (distribution de probabilité naturelle sans distortion artificielle),
    évalue les métriques officielles avec le seuil décisionnel clinique à 30% (orienté rappel),
    et sérialise le modèle dans no_show_model.joblib.
    """
    os.makedirs(output_dir, exist_ok=True)
    df = generate_synthetic_dataset(n_samples=1500, random_state=42)
    
    features = [
        'lead_days',
        'day_of_week',
        'is_afternoon',
        'is_urgence',
        'is_nouveau_patient',
        'patient_previous_rdv_count',
        'patient_historical_noshow_rate'
    ]
    
    X = df[features]
    y = df['no_show']
    
    # Split 80% train / 20% test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    
    # Modèle Random Forest calibré sur la prévalence réelle
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=6,
        min_samples_split=5,
        min_samples_leaf=3,
        random_state=42
    )
    model.fit(X_train, y_train)
    
    # Probabilités continues prédites
    y_proba = model.predict_proba(X_test)[:, 1]
    
    # Seuil décisionnel clinique à 30% (optimisé pour la sensibilité/rappel des no-shows en médecine)
    threshold = 0.30
    y_pred = (y_proba >= threshold).astype(int)
    
    # Métriques
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    roc_auc = roc_auc_score(y_test, y_proba)
    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel()
    
    # Validation croisée 5-Fold sur l'AUC
    cv_scores = cross_val_score(model, X, y, cv=5, scoring='roc_auc')
    
    # Feature Importances
    importances = model.feature_importances_
    feat_importance_list = sorted(
        zip(features, importances), key=lambda x: x[1], reverse=True
    )
    
    results = {
        'model_name': 'RandomForestClassifier (Natural Calibrated Probabilities)',
        'dataset_size': len(df),
        'train_size': len(X_train),
        'test_size': len(X_test),
        'base_noshow_rate_percent': round(float(df['no_show'].mean() * 100), 2),
        'decision_threshold': threshold,
        'risk_thresholds': {
            'faible': '< 25%',
            'moyen': '25% - 45%',
            'eleve': '> 45%'
        },
        'metrics': {
            'accuracy': round(float(acc), 4),
            'precision': round(float(prec), 4),
            'recall': round(float(rec), 4),
            'f1_score': round(float(f1), 4),
            'roc_auc': round(float(roc_auc), 4),
            'cv_roc_auc_5fold_mean': round(float(cv_scores.mean()), 4),
            'cv_roc_auc_5fold_std': round(float(cv_scores.std()), 4)
        },
        'confusion_matrix': {
            'true_negatives_venu_predit_venu': int(tn),
            'false_positives_venu_predit_absent': int(fp),
            'false_negatives_absent_predit_venu': int(fn),
            'true_positives_absent_predit_absent': int(tp)
        },
        'feature_importances': [
            {'feature': f, 'importance_percent': round(float(imp * 100), 2)}
            for f, imp in feat_importance_list
        ]
    }
    
    # Sauvegarde du modèle .joblib
    model_path = os.path.join(output_dir, "no_show_model.joblib")
    joblib.dump(model, model_path)
    
    # Sauvegarde des métriques en JSON
    metrics_path = os.path.join(output_dir, "no_show_metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
        
    print("=== ENTRAINEMENT ML NO-SHOW TERMINE AVEC SUCCES ===")
    print(f"Modèle sauvegardé dans : {model_path}")
    print(f"Métriques JSON dans : {metrics_path}")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return results

if __name__ == "__main__":
    train_and_evaluate_model()
