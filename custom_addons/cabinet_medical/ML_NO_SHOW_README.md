# Module IA : Prédiction du Risque de Rendez-Vous Manqué (No-Show)

## 📌 1. Contexte et Démarche d'Ingénierie

### État de la Base de Données Réelle au Lancement du Projet
Lors de l'audit initial de la base de données du cabinet médical (`cabinet_medical`) :
* **Nombre total de rendez-vous enregistrés :** 60 rendez-vous.
* **Nombre de rendez-vous avec statut d'absence qualifié (`state = 'absent'`) :** **0 rendez-vous**.
* **Rendez-vous passés restés non clôturés :** 40 rendez-vous en attente de qualification.

> [!WARNING]
> **Limite Méthodologique Reconnue :** En l'absence de classe positive (0 absence réelle en base locale), il était impossible d'entraîner un modèle supervisé sur les données de production actuelles sans biaiser gravement l'apprentissage.

### Deux Phases de Modélisation Complémentaires
1. **Phase 1 (PoC Initial) :** Modèle synthétique supervisé (1 500 RDV simulés selon les règles de la littérature clinique) servant de socle architectural initial (`no_show_model.joblib`).
2. **Phase 2 (Modèle Réel Public Kaggle) :** Entraînement et déploiement du modèle canonique `no_show_model_public.joblib` sur **110 521 rendez-vous réels** issus du jeu public Kaggle (*Medical Appointment No Shows* de Joni Hoppen / Aquarela Analytics, sous licence **CC BY-NC-SA 4.0**).

---

## 🔬 2. Caractéristiques (Features) et Règle Métier

### Modèle intégré au module : `no_show_model_public.joblib` (5 variables)

| Variable | Type | Rôle / Règle Métier |
| :--- | :--- | :--- |
| `lead_days` | Numérique (jours) | **Délai entre la prise de RDV et le RDV.** Plus le délai est long (> 15j), plus le risque de no-show augmente fortement (83.18% d'importance). |
| `patient_historical_noshow_rate` | Continu (0.0 à 1.0) | **Taux d'absence antérieur du patient.** Antécédent fort de récidive d'absence (12.29% d'importance). Calculé chronologiquement sans fuite de données (*data leakage*). |
| `patient_previous_rdv_count` | Entier | **Nombre de RDV passés (Fidélité).** Un patient assidu avec antécédents vierges est hautement protecteur (3.10% d'importance). |
| `day_of_week` | Catégoriel (0 à 6) | **Jour de la semaine.** Fluctuation du risque selon le créneau hebdomadaire (1.01% d'importance). |
| `is_nouveau_patient` | Binaire (0/1) | **Nouveau patient.** Absence d'historique thérapeutique préalable (0.42% d'importance). |

### 🛡️ Traitement Spécifique de l'Urgence et du Créneau Horaire
* **Règle métier d'urgence médicale (`is_urgence`) :** Traitée en amont du modèle statistique. Si `is_urgence = 1`, le risque est immédiatement verrouillé à **2.5% (Niveau Faible)** avec facteur explicatif dédié (*"Consultation d'urgence (présence quasi certaine)"*). Cette règle métier garantit qu'une urgence médicale n'est jamais faussement signalée à haut risque.
* **Variable `is_afternoon` :** Absente du jeu Kaggle (les heures y étant tronquées à 00:00:00Z) ; elle est préservée dans l'API Odoo pour rétrocompatibilité avec l'ancien modèle et l'heuristique de repli.

---

## 🌲 3. Choix de l'Algorithme et Calibrage : `RandomForestClassifier`

Le modèle intégré au module (`data/no_show_model_public.joblib`) est une **Forêt Aléatoire (`RandomForestClassifier`)** calibrée sur la distribution naturelle de prévalence (taux d'absence réel de 20.19%) :
* Hyperparamètres : `n_estimators=100`, `max_depth=6`, `min_samples_leaf=3`, `min_samples_split=5`, `random_state=42`.
* Seuil d'alerte décisionnel : $\tau = 30\%$ (optimisé pour capter un maximum d'absences réelles tout en limitant les faux positifs).

### Paliers de Risque Harmonisés dans l'Interface :
* 🟢 **Faible (< 25%)** : Patient régulier / court délai / urgence. Taux d'absence réel observé : **10.68%**.
* 🟡 **Moyen (25% à 45%)** : Délai standard ou récidive modérée. Taux d'absence réel observé : **30.54%** (concentre 64.82% des absents). Rappel SMS automatisé recommandé.
* 🔴 **Élevé (> 45%)** : Délai lourd (> 30j) avec récidive forte (ex: 80% absence -> 50.8%). Taux d'absence réel observé : **56.55%**. Appel de confirmation recommandé.

---

## 📊 4. Métriques Officielles du Modèle Public (Jeu de Test : 22 105 RDV)

Entraînement officiel généré par [train_no_show_public.py](scripts/train_no_show_public.py) (`scikit-learn 1.7.2`, `random_state=42`) :

### 📈 Performances Globales Réelles

| Métrique | Modèle Public Kaggle (22 105 test) | Ancien Modèle PoC (300 test) |
| :--- | :---: | :---: |
| **ROC-AUC (Discrimination globale)** | **0.7214** | 0.6840 |
| **Validation Croisée (5-Fold ROC-AUC)** | **0.7080 ± 0.0126** | 0.6680 ± 0.0222 |
| **Accuracy (Exactitude globale)** | **75.95 %** | 68.67 % |
| **Precision (Seuil 30%)** | **37.48 %** | 44.34 % |
| **Recall (Rappel des absents, seuil 30%)** | **28.64 %** | 57.32 % |
| **F1-Score (Seuil 30%)** | **0.3247** | 0.5000 |

### ⚠️ Analyse de la Précision et Règle Métier des Coûts Asymétriques

> [!IMPORTANT]
> **Règle métier sur l'asymétrie des coûts :**
> * **Coût d'un Faux Négatif (Absence manquée) :** ÉLEVÉ. Créneau médical perdu et patient malade privé de soins.
> * **Coût d'un Faux Positif (Fausse alerte d'absence) :** QUASI NUL. L'action déclenchée est un simple SMS de rappel automatisé perçu comme une attention de service.
> * **Règle métier retenue :** Privilégier la sensibilité et la stratification prédictive du risque plutôt qu'une précision stricte.

---

## 🔄 5. Architecture de Résilience (Double Repli / Fallback)

Le système implémente une chaîne de tolérance aux pannes à trois niveaux dans [models/ml_no_show.py](models/ml_no_show.py) :

1. **Niveau 1 (Actif) :** `data/no_show_model_public.joblib` (5 variables issues des 110 521 RDV Kaggle).
2. **Niveau 2 (Repli PoC) :** `data/no_show_model.joblib` (7 variables synthétiques initiales).
3. **Niveau 3 (Repli Heuristique) :** Fonction `_heuristic_risk()` sans aucune dépendance binaire externe.
