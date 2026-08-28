# Module IA : Prédiction du Risque de Rendez-Vous Manqué (No-Show)

## 📌 1. Contexte et Démarche d'Ingénierie (PoC Assumé)

### État de la Base de Données Réelle au Lancement du Projet
Lors de l'audit initial de la base de données du cabinet médical (`cabinet_medical`) :
* **Nombre total de rendez-vous enregistrés :** 60 rendez-vous.
* **Nombre de rendez-vous avec statut d'absence qualifié (`state = 'absent'`) :** **0 rendez-vous**.
* **Rendez-vous passés restés non clôturés :** 40 rendez-vous en attente de qualification.

> [!WARNING]
> **Limite Méthodologique Reconnue :** En l'absence de classe positive (0 absence réelle en base), il est mathématiquement impossible d'entraîner un modèle supervisé sur les données de production actuelles sans biaiser gravement l'apprentissage.

### Choix de Conception : Démonstration de Faisabilité (PoC) Transparente
Pour concevoir un pipeline Machine Learning complet et fonctionnel prêt pour la production future, nous avons développé :
1. Un **générateur de données simulées réaliste (1 500 rendez-vous)** s'appuyant sur les règles et corrélations prouvées par la littérature clinique internationale en médecine générale.
2. Un entraînement supervisé rigoureux avec validation croisée et séparation Train/Test stricte (80% / 20%).
3. Une **intégration temps réel dans l'interface Odoo** calculant le score de risque pour chaque rendez-vous à venir.

---

## 🔬 2. Caractéristiques (Features) et Logique Clinique Modélisée

Le modèle analyse 7 variables pour chaque rendez-vous :

| Variable | Type | Rôle Clinique / Hypothèse Métier |
| :--- | :--- | :--- |
| `lead_days` | Numérique (jours) | **Délai entre la prise de RDV et le RDV.** Plus le délai est long (> 15j), plus le taux d'oubli ou de désistement augmente. |
| `patient_historical_noshow_rate` | Continu (0.0 à 1.0) | **Taux d'absence antérieur du patient.** Antécédent fort de récidive d'absence. |
| `patient_previous_rdv_count` | Entier | **Nombre de RDV passés (Fidélité).** Un patient régulier est plus assidu qu'un patient ponctuel. |
| `is_urgence` | Binaire (0/1) | **Rendez-vous d'urgence.** Taux de no-show quasi nul (< 3%). Facteur hautement protecteur. |
| `day_of_week` | Catégoriel (0 à 5) | **Jour de la semaine.** Sur-risque documenté le lundi (reprise) et le vendredi (départ week-end). |
| `is_afternoon` | Binaire (0/1) | **Créneau horaire.** Créneaux d'après-midi légèrement plus sujets aux imprévus. |
| `is_nouveau_patient` | Binaire (0/1) | **Nouveau patient.** Absence de lien thérapeutique préalable = sur-risque modéré (~15%). |

---

## 🌲 3. Choix de l'Algorithme et Calibrage : `RandomForestClassifier`

Le modèle déployé en production (`no_show_model.joblib`) est une **Forêt Aléatoire (`RandomForestClassifier`)** calibrée sur la distribution naturelle de prévalence (sans distorsion de poids artificielle) :
* Hyperparamètres : `n_estimators=100`, `max_depth=6`, `min_samples_leaf=3`, `min_samples_split=5`, `random_state=42`.
* Seuil d'alerte décisionnel clinique : $\tau = 30\%$ (optimisé pour capter un maximum d'absences réelles).

### Paliers de Risque Harmonisés dans l'Interface :
* 🟢 **Faible (< 25%)** : Patient régulier / court délai / urgence (ex: 2.5% à 18%).
* 🟡 **Moyen (25% à 45%)** : Délai standard (5-15j) sans antécédents. Rappel SMS automatisé recommandé.
* 🔴 **Élevé (> 45%)** : Long délai (> 20j), patient récidiviste d'absence ou nouveau patient à délai éloigné. Appel de confirmation recommandé.

---

## 📊 4. Métriques Officielles du Modèle Déployé (Jeu de Test : 300 RDV)

Entraînement officiel généré par [train_no_show_model.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/scripts/train_no_show_model.py) (`scikit-learn 1.6.1`, `random_state=42`) :

### 📈 Performances Globales

| Métrique | Valeur Exacte | Signification Clinique pour la Soutenance |
| :--- | :---: | :--- |
| **Accuracy (Exactitude globale)** | **68.67 %** | Taux global de bonnes prédictions sur le jeu de test. |
| **ROC-AUC (Aire sous la courbe)** | **0.6840** | Bonne capacité de discrimination globale (baseline aléatoire = 0.50). |
| **Validation Croisée (5-Fold ROC-AUC)** | **0.6680 ± 0.0222** | Stabilité confirmée (écart-type très faible de 2.2%). |
| **Recall (Rappel des absents)** | **57.32 %** | **Près de 6 absences réelles sur 10 sont interceptées en amont (47/82).** |
| **Precision (Précision des alertes)** | **44.34 %** | Proportion d'alertes positives correspondant à une absence réelle (47/106). |
| **F1-Score** | **0.5000** | Équilibre harmonique précision / rappel sur données asymétriques. |

---

### ⚠️ Analyse Critique de la Précision (44,34%) et Justification du Compromis Métier

> [!IMPORTANT]
> **Pourquoi une précision de 44,34% est un compromis délibéré et assumé :**
> * **Réalité des chiffres :** Sur 106 alertes générées par le modèle, **47 sont de vraies absences** et **59 sont de fausses alertes** (le patient se présente finalement).
> * **Asymétrie des coûts en santé :**
>   1. **Coût d'un Faux Négatif (Absence manquée) :** ÉLEVÉ. Un créneau médical de 30 minutes est perdu, le temps du praticien est gaspillé et un autre patient malade est privé de soins.
>   2. **Coût d'un Faux Positif (Fausse alerte d'absence) :** QUASI NUL. L'action déclenchée est simplement un SMS de rappel automatisé ou un appel cordial de la secrétaire 48h avant (*"Bonjour, nous vous confirmons votre rendez-vous de jeudi..."*). Pour le patient ponctuel, cela est perçu comme une attention de service et non comme un préjudice.
> * **Conclusion :** Dans ce cas d'usage clinique, **maximiser le Rappel (Recall)** au détriment d'une précision parfaite est la stratégie la plus rentable et la plus protectrice pour le cabinet.

---

### 🧩 Matrice de Confusion Officielle (300 RDV de Test)

```text
                             ┌────────────────────────┬────────────────────────┐
                             │   Prédit : PRÉSENT     │   Prédit : ABSENT      │
┌────────────────────────────┼────────────────────────┼────────────────────────┤
│ Réel : PRÉSENT (218 RDV)   │   159 (Vrais Négatifs) │    59 (Faux Positifs)  │
├────────────────────────────┼────────────────────────┼────────────────────────┤
│ Réel : ABSENT  (82 RDV)    │    35 (Faux Négatifs)  │    47 (Vrais Positifs) │
└────────────────────────────┴────────────────────────┴────────────────────────┘
```

* **Vrais Négatifs (TN = 159) :** 159 patients ponctuels correctement identifiés sans alerte superflue.
* **Vrais Positifs (TP = 47) :** 47 no-shows réels interceptés avec succès par le modèle.

---

### 🏆 Importance des Variables (Feature Importances Réelles)

Classement validé par l'analyse de réduction d'impureté de Gini :

```text
1. lead_days (Délai de réservation)          ████████████████████ 30.55 %
2. patient_historical_noshow_rate            ████████████████     24.43 %
3. patient_previous_rdv_count (Fidélité)     █████████            13.45 %
4. is_urgence (Caractère d'urgence)          █████████            13.38 %
5. day_of_week (Jour de la semaine)          ███████              11.42 %
6. is_afternoon (Créneau horaire)            ██                   3.41 %
7. is_nouveau_patient                        ██                   3.37 %
```

---

## 🔄 5. Protocole de Bascule vers les Données Réelles

Pour assurer la transition continue vers un modèle 100% ré-entraîné sur les données réelles du cabinet :

1. **Seuil d'Activation :** **300 à 500 rendez-vous réels qualifiés** (avec au moins 40 à 60 absences réelles constatées).
2. **Mécanisme de Clôture Quotidien :** Le filtre et le bandeau d'alerte `⚠️ RDV passés à clôturer` permettent à la secrétaire de qualifier systématiquement les présences/absences.
3. **Pipeline Automatisé :** Le script officiel [train_no_show_model.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/scripts/train_no_show_model.py) permet de ré-entraîner et de re-sauvegarder le fichier `no_show_model.joblib` en une commande sans toucher au code Odoo.
