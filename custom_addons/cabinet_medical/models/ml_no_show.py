import os
import logging

_logger = logging.getLogger(__name__)

_MODEL_CACHE = None

def get_model_path():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "data", "no_show_model.joblib")

def load_ml_model():
    global _MODEL_CACHE
    if _MODEL_CACHE is not None:
        return _MODEL_CACHE
    
    model_path = get_model_path()
    if os.path.exists(model_path):
        try:
            import joblib
            _MODEL_CACHE = joblib.load(model_path)
            _logger.info("Modèle ML No-Show chargé avec succès depuis %s", model_path)
            return _MODEL_CACHE
        except Exception as e:
            _logger.warning("Impossible de charger le modèle ML No-Show (%s), passage au fallback heuristique.", e)
            return None
    return None

def predict_no_show_risk(lead_days=0, day_of_week=0, is_afternoon=0, is_urgence=0,
                        is_nouveau_patient=0, patient_previous_rdv_count=0,
                        patient_historical_noshow_rate=0.0):
    """
    Calcule le risque de No-Show d'un rendez-vous.
    Retourne :
      - risk_score : float (0.0 à 100.0)
      - risk_level : str ('faible', 'moyen', 'eleve')
      - top_factors : list of str
    """
    # 1. Cas d'urgence médicale : risque minimal garanti (< 3%)
    if is_urgence:
        return 2.5, 'faible', ["Consultation d'urgence (présence quasi certaine)"]
    
    model = load_ml_model()
    top_factors = []
    
    if model is not None:
        try:
            import numpy as np
            import pandas as pd
            
            features = [
                'lead_days',
                'day_of_week',
                'is_afternoon',
                'is_urgence',
                'is_nouveau_patient',
                'patient_previous_rdv_count',
                'patient_historical_noshow_rate'
            ]
            
            X_df = pd.DataFrame([{
                'lead_days': max(0, int(lead_days)),
                'day_of_week': int(day_of_week),
                'is_afternoon': int(bool(is_afternoon)),
                'is_urgence': int(bool(is_urgence)),
                'is_nouveau_patient': int(bool(is_nouveau_patient)),
                'patient_previous_rdv_count': max(0, int(patient_previous_rdv_count)),
                'patient_historical_noshow_rate': float(np.clip(patient_historical_noshow_rate, 0.0, 1.0))
            }])[features]
            
            proba = model.predict_proba(X_df)[0][1]
            risk_score = round(float(proba * 100.0), 1)
        except Exception as e:
            _logger.warning("Erreur inférence ML No-Show: %s. Utilisation de la formule heuristique.", e)
            risk_score = _heuristic_risk(
                lead_days, day_of_week, is_afternoon, is_urgence,
                is_nouveau_patient, patient_previous_rdv_count, patient_historical_noshow_rate
            )
    else:
        risk_score = _heuristic_risk(
            lead_days, day_of_week, is_afternoon, is_urgence,
            is_nouveau_patient, patient_previous_rdv_count, patient_historical_noshow_rate
        )
    
    # Explications cliniques pour l'interface
    if lead_days > 15:
        top_factors.append(f"Délai de prise de RDV long ({lead_days} jours)")
    elif lead_days <= 1:
        top_factors.append("Prise de RDV récente (court délai)")
        
    if patient_historical_noshow_rate > 0.25:
        top_factors.append(f"Antécédents d'absence ({int(patient_historical_noshow_rate*100)}% de no-show)")
    elif patient_previous_rdv_count >= 3 and patient_historical_noshow_rate == 0.0:
        top_factors.append("Patient assidu et régulier")
        
    if is_nouveau_patient:
        top_factors.append("Nouveau patient (pas d'historique)")
        
    if day_of_week in (0, 4):
        top_factors.append("Créneau en début/fin de semaine")

    if not top_factors:
        top_factors.append("Profil de rendez-vous standard")

    # Classification en 3 niveaux
    if risk_score < 25.0:
        risk_level = 'faible'
    elif risk_score <= 45.0:
        risk_level = 'moyen'
    else:
        risk_level = 'eleve'
        
    return risk_score, risk_level, top_factors

def _heuristic_risk(lead_days, day_of_week, is_afternoon, is_urgence,
                    is_nouveau_patient, patient_previous_rdv_count,
                    patient_historical_noshow_rate):
    """Fallback heuristique équivalent en l'absence du modèle .joblib"""
    if is_urgence:
        return 2.5
    
    score = 12.0
    score += min(35.0, lead_days * 1.5)
    if is_nouveau_patient:
        score += 10.0
    if patient_historical_noshow_rate > 0:
        score += min(40.0, patient_historical_noshow_rate * 60.0)
    if day_of_week in (0, 4):
        score += 5.0
    if is_afternoon:
        score += 3.0
    if patient_previous_rdv_count > 2 and patient_historical_noshow_rate == 0:
        score = max(5.0, score - 8.0)
        
    return round(min(95.0, max(5.0, score)), 1)
