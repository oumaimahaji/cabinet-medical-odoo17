# MASTER GUIDE DE SOUTENANCE & SCRIPT ORAL D'INGÉNIEUR (PFE)
## Module Odoo 17 Sur-Mesure : System Intégré de Gestion de Cabinet Médical avec IA Hybride Multi-Niveaux et Télétransmission CNAM

**Auteur :** Élève-Ingénieur  
**Spécialité :** Génie Logiciel / Système d'Information  
**Durée de la Soutenance :** 20 minutes (Présentation + Démonstration)  
**Environnement Technique Réel :** Odoo 17 Enterprise/Community (Python 3.10+, PostgreSQL 15+, OWL JS, QWeb, PyTorch, Transformers, Anthropic API, Ollama Local).

---

# SECTION 1 : AUDIT EXHAUSTIF DES COMPOSANTS ET ARCHITECTURE TECHNIQUE

---

### 🏛️ 1.1. Architecture du Module & Composants Système
Le projet est conçu comme un **module Odoo 17 autonome à 100%** nommé `cabinet_medical`, garantissant l'intégrité du noyau Odoo sans aucune altération des fichiers sources natifs.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. COUCHE PRÉSENTATION & INTERFACE OWL JS / CSS                                        │
│    - Composants Web OWL JS : ai_dashboard.js, cnam_dashboard.js, live_search.js,     │
│      rdv_filter_buttons.js, professional_ui.js, hide_app_switcher.js, user_menu_cleanup│
│    - Styling CSS Sur-Mesure : rdv_dashboard.css, hide_gear.css                        │
│    - Portail Patient Web Responsive (Bootstrap / Templates QWeb)                        │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ HTTP REST / JSON-RPC
┌───────────────────────────────────────────▼────────────────────────────────────────────┐
│ 2. COUCHE MÉTIER & CONTROLLEURS ODOO 17 (PYTHON)                                       │
│    - Modèles ORM : patient.py, rendezvous.py, consultation.py, prescription.py,        │
│      facture.py, bordereau.py, acte.py, acte_parametrage.py, assurance.py,              │
│      notification.py, res_config_settings.py, ir_http.py, ir_mail_server.py            │
│    - Contrôleurs HTTP : controllers/portal.py (Portail), controllers/main.py (Auth)   │
│    - Wizards Transactionnels : wizard_import_patients.py, wizard_creer_patient.py,    │
│      wizard_suivi.py                                                                   │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ SQL / Transaction Isolation
┌───────────────────────────────────────────▼────────────────────────────────────────────┐
│ 3. TRIPLE INGÉNIERIE IA HYBRIDE                                                        │
│    - Niveaux 1-3 Clinique (prescription.py) : Ontologie BDPM + difflib + PyTorch NLP  │
│    - IA Décisionnelle Générative (dashboard_ai.py) : Anthropic Claude 3.5 Haiku API    │
│    - IA Souveraine Embarquée (facture.py) : Ollama / Phi3 Local (Port 11434)        │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ PostgreSQL Engine
┌───────────────────────────────────────────▼────────────────────────────────────────────┐
│ 4. DONNÉES, SÉCURITÉ & AUTOMATISATION                                                  │
│    - PostgreSQL 15+ (Contraintes SQL unique, Savepoints, Indexes)                     │
│    - Sécurité XML : security.xml (RBAC) & portal_security.xml (Record Rules Row-Level)  │
│    - 7 Rapports QWeb PDF : Ordonnance, Facture, Reçu, BS1, Feuille Soins, Bordereau    │
│    - Tâche Programmée : cron_data.xml (Expiration CNAM quotidienne)                    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### ⚙️ 1.2. Justification des Choix Techniques d'Ingénierie

1. **Isolation par Addon Indépendant (`cabinet_medical`)**
   - *Raison :* Respecter les recommandations d'ingénierie d'Odoo. Permet d'installer/mettre à jour le module sans risquer de casser le noyau Odoo ou d'entraver les futures migrations.
2. **Architecture IA Hybride à Tolérance de Panne (*Graceful Degradation*)**
   - *Raison :* Sécuriser la décision clinique. Si PyTorch ou le réseau externe échoue, l'ontologie BDPM locale et l'algorithme flou `difflib` garantissent un contrôle anti-allergies déterministe sans jamais bloquer l'application.
3. **Double Déploiement LLM (Cloud Claude vs Local Ollama/Mistral)**
   - *Raison :* Concilier puissance décisionnelle et confidentialité des données de santé. Claude 3.5 Haiku analyse les statistiques anonymisées du dashboard executif, tandis qu'Ollama/Mistral tourne en local sur le port 11434 pour l'explication des erreurs de facturation sans fuite externe (Conformité HDS/RGPD).
4. **Transactionnalité PostgreSQL par `SAVEPOINT` dans les Wizards**
   - *Raison :* Traiter les fichiers d'importation Excel massifs (via `openpyxl`). Chaque ligne est exécutée sous une transaction isolée (`SAVEPOINT import_patient_row_idx`). Une erreur isole la ligne fautive sans faire échouer l'intégration des milliers d'autres.
5. **Durcissement Authentification OWASP contre le Session Hijacking**
   - *Raison :* Surcharge de `AuthSignupHome` dans [main.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/controllers/main.py) forçant l'invalidation de session (`request.session.logout(keep_db=True)`) lors de la création/reset de mot de passe du portail.

---

# SECTION 2 : PLAN DE DÉMONSTRATION ÉTAPE PAR ÉTAPE (20 MINUTES)

---

### ⏱️ Découpage Temporel Global

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 00:00 - 02:00 ➔ INTRODUCTION & ARCHITECTURE TECHNIQUE DU PROJET                        │
│ 02:00 - 05:00 ➔ PHASE 1 : Secrétariat, Importation Excel Transactionnelle & RDV        │
│ 05:00 - 11:00 ➔ PHASE 2 : Consultation Médicale, Actes & IA Anti-Allergies 3 Niveaux   │
│ 11:00 - 14:30 ➔ PHASE 3 : Moteur des 8 Scénarios de Facturation, LLM Local & PDF       │
│ 14:30 - 17:00 ➔ PHASE 4 : Espace Portail Patient Web & Sécurité OWASP / Record Rules   │
│ 17:00 - 18:30 ➔ PHASE 5 : Tableau de Bord IA Executif & Cron d'Expiration CNAM         │
│ 18:30 - 20:00 ➔ PHASE 6 : Démonstration des Tests Réalisés & Conclusion d'Ingénieur     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### 📍 FICHE DÉTAILLÉE PAR FONCTIONNALITÉ (100% EXHAUSTIVE)

---

#### 1. Audit UX & Restriction de l'Interface (`hide_app_switcher.js`, `ir_http.py`)
* **Moment de la démonstration :** 02:00 (Début Phase 1)
* **Manipulations exactes :** Se connecter en tant que Secrétaire (`sec.cabinet@demo.com`). Montrer l'écran d'accueil sans l'icône gaufre natif Odoo.
* **🎙️ Script Oral Jury :**
  > *"Pour démarrer la journée au secrétariat, je me connecte sous le rôle Secrétaire. Vous remarquez une interface épurée où l'App Switcher natif Odoo a été masqué. Techniquement, notre classe `Http` dans `ir_http.py` surcharge `session_info()` pour injecter la variable `is_cabinet_restricted` dans le contexte JS. Notre script `hide_app_switcher.js` intercepte cette variable et masque dynamiquement le menu pour les utilisateurs non-admin."*
* **Valeur métier :** Ergonomie simplifiée, réduction des distractions et prévention des fausses manipulations.
* **Fichiers & Méthodes :** [ir_http.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/ir_http.py) (`session_info`), [hide_app_switcher.js](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/static/src/js/hide_app_switcher.js).
* **Validations :** Masquage conditionnel JS selon le groupe d'utilisateur.
* **Choix technique :** Infiltration propre du contexte `session_info` d'Odoo au lieu de hacks CSS statiques.

---

#### 2. Gestion des Patients & Calcul de Conformité (`patient.py`, `patient_views.xml`)
* **Moment de la démonstration :** 02:30
* **Manipulations exactes :** Ouvrir **Cabinet Médical > Patients**. Montrer les badges Vert (`Complet`) / Rouge (`Incomplet`).
* **🎙️ Script Oral Jury :**
  > *"Dans la vue liste des patients, un calcul d'état évalue la conformité administrative. La méthode `@api.depends` `_compute_dossier_status()` dans `patient.py` vérifie en temps réel la présence de la CIN, du téléphone, du genre et des identifiants CNAM pour afficher un badge de statut."*
* **Valeur métier :** Identification instantanée des dossiers incomplets avant la consultation.
* **Fichiers & Méthodes :** [patient.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/patient.py) (`_compute_dossier_status`), [patient_views.xml](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/views/patient_views.xml).
* **Validations :** Calcul automatique dépendant de 12 champs du formulaire patient.
* **Choix technique :** Calcul réactif stocké en base (`store=True`) pour accélérer le filtrage et les vues récapitulatives.

---

#### 3. Validation des Données Tunisiennes (CIN, Tél, CNAM) (`patient.py`)
* **Moment de la démonstration :** 03:00
* **Manipulations exactes :** Tenter de saisir un CIN invalide (ex: `"1234"` ou `"ABC"`) ou un numéro de téléphone invalide (ex: `"11223344"`). Sauvegarder.
* **🎙️ Script Oral Jury :**
  > *"Le système applique une validation stricte sur les données réglementaires tunisiennes. Si je tente de saisir une CIN non conforme, la contrainte `@api.constrains('cin')` déclenche une `ValidationError` exigeant exactement 8 chiffres. De même, `_check_telephone()` vérifie que le numéro contient 8 chiffres et débute par un préfixe mobile tunisien valide (2, 4, 5, 7 ou 9), et `_check_numero_cnam()` valide les 10 chiffres du matricule CNAM."*
* **Valeur métier :** Élimination des erreurs de saisie à la source et garantie de conformité pour la télétransmission CNAM.
* **Fichiers & Méthodes :** [patient.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/patient.py) (`_check_cin`, `_check_telephone`, `_check_numero_cnam`, `cin_unique` SQL Constraint).
* **Validations :** Erreurs bloquantes Python + Contrainte SQL d'unicité `cin_unique` en PostgreSQL.
* **Choix technique :** Double verrou de sécurité (Python Constraints + SQL Database Constraints) pour une intégrité absolue.

---

#### 4. Importation Excel Transactionnelle & Détection de Doublons (`wizard_import_patients.py`)
* **Moment de la démonstration :** 03:30
* **Manipulations exactes :** Naviguer vers **Cabinet Médical > Patients > Importer Patients (Excel)**. Téléverser `patients_demo.xlsx` et lancer l'importation.
* **🎙️ Script Oral Jury :**
  > *"Pour l'importation massive de dossiers, notre wizard `wizard_import_patients.py` s'appuie sur la bibliothèque `openpyxl`. Il vérifie l'unicité du CIN par rapport à la base de données et au sein du fichier Excel lui-même. Du point de vue de l'ingénierie base de données, chaque ligne est exécutée sous un `SAVEPOINT` PostgreSQL (`import_patient_row_idx`). Si la ligne 15 contient un doublon de CIN, elle subit un `ROLLBACK` ciblé sans bloquer les 500 autres lignes."*
* **Valeur métier :** Reprise d'historique rapide et sécurisée sans risque de corruption globale de la base de données.
* **Fichiers & Méthodes :** [wizard_import_patients.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/wizard_import_patients.py) (`action_importer`), [wizard_import_patients_view.xml](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/views/wizard_import_patients_view.xml).
* **Validations :** Isolation transactionnelle par `SAVEPOINT` / `RELEASE` / `ROLLBACK TO SAVEPOINT`.
* **Choix technique :** Utilisation d'un cache mémoire des assurances `assurance_cache` et de `search_read` sur les CINs existantes pour optimiser les performances d'importation.

---

#### 5. Prise de RDV Rapide & Wizard de Création de Dossier (`rendezvous.py`, `wizard_creer_patient.py`)
* **Moment de la démonstration :** 04:15
* **Manipulations exactes :** Dans l'Agenda, créer un RDV à 09:00 avec le nom seul `"KARIM BEN AMAR"`. Sauvegarder. Cliquer sur le bouton **"Compléter le dossier patient"**. Renseigner CIN, Tél, CNAM (Tiers-payant Privée) et APCI (Diabète, N° Décision `APCI-2026-99`). Valider.
* **🎙️ Script Oral Jury :**
  > *"Lors d'un appel téléphonique rapide, la secrétaire crée un RDV en inscrivant uniquement le nom du patient (`patient_name`). À l'arrivée du patient, un Wizard dédié `cabinet.rendezvous.creer.patient` permet de qualifier l'ensemble de sa fiche sociale (CNAM, APCI, Mutuelle). La méthode `action_confirmer()` instancie le patient en base et remplace le nom temporaire par la relation ORM `patient_id`."*
* **Valeur métier :** Prise de RDV en 3 secondes au téléphone puis qualification complète à l'accueil sans perte de données.
* **Fichiers & Méthodes :** [rendezvous.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/rendezvous.py) (`_compute_show_buttons`), [wizard_creer_patient.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/wizard_creer_patient.py) (`action_confirmer`).
* **Validations :** Remplacement dynamique de l'enregistrement temporaire par la clé étrangère du patient.
* **Choix technique :** Modèle Transient (`TransientModel`) fermé automatiquement après exécution sans surcharger la base de données.

---

#### 6. Agenda Interactif OWL, Quotas et Détection des Chevauchements (`rendezvous.py`, `main.py`)
* **Moment de la démonstration :** 04:45
* **Manipulations exactes :** Montrer le tableau de bord des disponibilités de l'Agenda interactif. Tenter de créer un 21ème RDV normal ou un RDV à la même heure.
* **🎙️ Script Oral Jury :**
  > *"L'agenda interactif est rendu via du JavaScript OWL connecté au contrôleur `/cabinet_medical/get_calendar_data`. Notre méthode `@api.constrains` `_check_appointments_limit()` interroge les paramètres système (`cabinet.max_rdv_normal` fixé à 20 et `cabinet.max_rdv_urgence` fixé à 2). De plus, la méthode `_check_duplicate_appointment()` et la méthode `@api.onchange('date', 'heure')` `_onchange_date_heure()` interceptent immédiatement tout chevauchement de créneau."*
* **Valeur métier :** Maîtrise de la charge de travail du médecin et évitement des erreurs de double réservation.
* **Fichiers & Méthodes :** [rendezvous.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/rendezvous.py) (`_check_appointments_limit`, `_check_duplicate_appointment`, `_onchange_date_heure`, `get_interactive_calendar_html`), [main.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/controllers/main.py) (`get_calendar_data`).
* **Validations :** Détection en temps réel au clic (Onchange) et validation stricte à l'enregistrement (Constrains).
* **Choix technique :** Paramétrage dynamique des limites via `ir.config_parameter` sans modifier le code Python lors des ajustements de quotas.

---

#### 7. Workflow des États du RDV & Protection contre la Suppression (`rendezvous.py`)
* **Moment de la démonstration :** 05:00
* **Manipulations exactes :** Cliquer sur **"Patient Arrivé"**. Statut passe à `Présent`. Tenter de supprimer le RDV.
* **🎙️ Script Oral Jury :**
  > *"Le workflow fait évoluer l'état du RDV : `en_attente` ➔ `present` ➔ `en_consultation` ➔ `termine`. Pour des raisons d'historique médical et de traçabilité, la méthode `unlink()` a été surchargée pour bloquer la suppression physique des RDV et obliger l'utilisation des statuts 'Annulé' ou 'Absent'."*
* **Valeur métier :** Traçabilité et historique complet de la patientèle sans perte de données.
* **Fichiers & Méthodes :** [rendezvous.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/rendezvous.py) (`action_patient_arrive`, `unlink`).
* **Validations :** Blocage de la suppression physique par `ValidationError`.
* **Choix technique :** Surcharge de la méthode système `unlink()` sur l'ensemble des objets critiques (`Patient`, `Appointment`, `Prescription`).

---

#### 8. Prise en Charge Médecin & Sécurité des Champs Médicaux (RBAC) (`consultation.py`, `security.xml`)
* **Moment de la démonstration :** 05:30 (Début Phase 2)
* **Manipulations exactes :** Se connecter en Médecin (`doc.cabinet@demo.com`). Ouvrir le RDV et cliquer sur **"Démarrer la consultation"**.
* **🎙️ Script Oral Jury :**
  > *"Je bascule sur le compte du Médecin. En démarrant la consultation, la méthode `action_demarrer_consultation()` instancie la fiche `cabinet.consultation`. Grâce au groupe de sécurité `group_medecin` défini dans `security.xml` et appliqué aux champs via `groups="cabinet_medical.group_medecin"`, le médecin est le seul à visualiser les champs confidentiels : motif, diagnostic et notes médicales."*
* **Valeur métier :** Respect de la confidentialité médicale et séparation stricte des rôles administratifs et cliniques.
* **Fichiers & Méthodes :** [rendezvous.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/rendezvous.py) (`action_demarrer_consultation`), [consultation.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/consultation.py), [security.xml](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/security/security.xml), [consultation_views.xml](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/views/consultation_views.xml).
* **Validations :** Masquage dynamique au niveau du framework Odoo selon les droits de l'utilisateur connecté.
* **Choix technique :** Déclaration XML native `groups` assurant une étanchéité totale au niveau serveur.

---

#### 9. Saisie des Actes Médicaux & Référentiel Paramétré (`acte.py`, `acte_parametrage.py`)
* **Moment de la démonstration :** 06:15
* **Manipulations exactes :** Ajouter l'acte conventionné **"Consultation Spécialiste"** (Code `C01`).
* **🎙️ Script Oral Jury :**
  > *"Dans l'onglet Actes Médicaux, le médecin sélectionne un acte du référentiel `cabinet.acte.parametrage`. La méthode `_onchange_parametrage_id()` dans `acte.py` injecte automatiquement la description, le tarif conventionné de 30 DT et le taux CNAM de 70%. La méthode `_compute_total_acte()` calcule immédiatement la part à payer par le patient selon sa couverture."*
* **Valeur métier :** Gain de temps pour le praticien et automatisation de la tarification réglementée.
* **Fichiers & Méthodes :** [acte.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/acte.py) (`_onchange_parametrage_id`, `_compute_total_acte`), [acte_parametrage.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/acte_parametrage.py).
* **Validations :** Calcul dynamique de la part patient selon le statut APCI, Tiers-Payant ou Remboursement.
* **Choix technique :** Liaison non-intrusive `Many2one` vers le référentiel des actes avec surchargabilité des montants.

---

#### 10. IA Hybride Anti-Allergies à 3 Niveaux (BDPM + Fuzzy + SentenceTransformer) (`prescription.py`)
* **Moment de la démonstration :** 07:00
* **Manipulations exactes :** Créer une ordonnance pour Karim Ben Amar (allergique à la Pénicilline).
  - Test 1 : Saisir `"Amoxicilline 1g"`.
  - Test 2 : Saisir `"Pénécilline 500mg"` (avec faute de frappe).
  - Test 3 : Lancer la vérification IA.
* **🎙️ Script Oral Jury :**
  > *"Je vous présente l'innovation majeure de notre PFE : le système IA Hybride Anti-Allergies implémenté dans `_verify_ia_in_memory()` dans `prescription.py`.
  > Il comporte 3 niveaux d'analyse :
  > 1. **Ontologie BDPM** : Chargement de `CIS_bdpm.txt` et `CIS_COMPO_bdpm.txt` via `_get_bdpm_ontology()`. L'IA associe l'Amoxicilline à la famille des Pénicillines.
  > 2. **Fuzzy Matching Orthographique** : Utilisation de `difflib.SequenceMatcher` avec un seuil de 82% pour rattraper les erreurs de saisie comme 'Pénécilline'.
  > 3. **NLP Deep Learning** : Inférence du modèle Transformer `paraphrase-multilingual-MiniLM-L12-v2` via PyTorch (`import torch`) calculant la similarité cosinus (seuil 70%) sur les phrases d'allergies complexes. En cas d'absence de GPU ou de réseau, les niveaux ontologiques et flous assurent la continuité de service."*
* **Valeur métier :** Sécurité clinique absolue et prévention des risques d'accidents allergiques iatrogènes.
* **Fichiers & Méthodes :** [prescription.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/prescription.py) (`_verify_ia_in_memory`, `_get_bdpm_ontology`), [CIS_bdpm.txt](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/data/CIS_bdpm.txt).
* **Validations :** Affichage dynamique d'alertes rouges clignotantes et basculement du statut `ia_statut = 'allergy_risk'`.
* **Choix technique :** Architecture hybride déterministe / probabiliste assurant la tolérance aux pannes (*Graceful Degradation*).

---

#### 11. Planification du Suivi & Clôture Consultation (`consultation.py`, `wizard_suivi.py`)
* **Moment de la démonstration :** 08:30
* **Manipulations exactes :** Corriger le médicament (`"Paracétamol 1g"`). Cliquer sur **"Planifier un suivi"**. Choisir une date dans 15 jours. Cliquer sur **"Terminer la consultation"**.
* **🎙️ Script Oral Jury :**
  > *"Le médicament étant remplacé par une molécule sans risque, l'IA valide l'ordonnance. La méthode `action_planifier_suivi()` ouvre notre wizard `cabinet.suivi.wizard` pré-remplissant l'agenda pour la consultation de contrôle, puis `action_terminer()` clôture la consultation."*
* **Valeur métier :** Suivi continu du patient et automatisation des rendez-vous de contrôle.
* **Fichiers & Méthodes :** [consultation.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/consultation.py) (`action_planifier_suivi`, `action_terminer`), [wizard_suivi.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/wizard_suivi.py).
* **Validations :** Synchronisation automatique de l'état du rendez-vous lié à `Terminé`.
* **Choix technique :** Réutilisation du composant d'agenda interactif au sein du wizard de suivi.

---

#### 12. Moteur des 8 Scénarios de Facturation (`facture.py`)
* **Moment de la démonstration :** 11:00 (Début Phase 3)
* **Manipulations exactes :** Cliquer sur **"Générer la Facture"**.
* **🎙️ Script Oral Jury :**
  > *"La méthode `_compute_scenario()` dans `facture.py` évalue automatiquement la couverture sociale du patient parmi 8 scénarios réglementaires tunisiens :
  > 1. Sans couverture
  > 2. CNAM Remboursement
  > 3. CNAM Tiers-payant
  > 4. APCI Tiers-payant (100%)
  > 5. APCI Remboursement (BS1)
  > 6. CNAM Remboursement + Mutuelle
  > 7. CNAM Tiers-payant + Mutuelle
  > 8. Sans CNAM + Mutuelle.
  > La méthode `_compute_parts()` calcule ensuite la part CNAM, la part mutuelle et le reste à charge exact du patient."*
* **Valeur métier :** Conformité totale avec le système de santé tunisien et élimination des erreurs de calcul comptable.
* **Fichiers & Méthodes :** [facture.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/facture.py) (`_compute_scenario`, `_compute_parts`), [facturation_views.xml](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/views/facturation_views.xml).
* **Validations :** Calculs réactifs de 4 montants monétaires selon les règles de la convention CNAM.
* **Choix technique :** Déduction configurable des taux depuis `ir.config_parameter` (70% consultation, 80% actes techniques, 100% APCI).

---

#### 13. Assistant IA LLM Souverain Embarqué (Ollama / Phi3) (`facture.py`)
* **Moment de la démonstration :** 12:00
* **Manipulations exactes :** Tenter de forcer manuellement le montant CNAM à 0 DT sur un dossier APCI et enregistrer.
* **🎙️ Script Oral Jury :**
  > *"Pour assister les utilisateurs lors des erreurs comptables, nous avons intégré un LLM local Ollama exécutant le modèle Mistral sur le port 11434 (`_get_llm_alert()`). Lors d'une anomalie détectée par `_check_taux_apci()`, le système envoie le contexte technique à Ollama qui formule une explication pédagogique en français pour la secrétaire. Cela garantit un hébergement 100% local des données de santé sans aucune dépendance cloud."*
* **Valeur métier :** Assistance intelligente des utilisateurs et respect strict de la confidentialité médicale (HDS/RGPD).
* **Fichiers & Méthodes :** [facture.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/facture.py) (`_get_llm_alert`, `_check_taux_apci`, `_check_doublon_facture`).
* **Validations :** Requête REST HTTP locale avec fallback gracieux si le service Ollama est arrêté.
* **Choix technique :** Utilisation d'un conteneur ou service Ollama local sur le port 11434 avec timeout de sécurité.

---

#### 14. Édition des 6 Documents PDF Officiels (`reports/`)
* **Moment de la démonstration :** 12:45
* **Manipulations exactes :** Imprimer les documents depuis les boutons de l'interface :
  1. Facture de Soins
  2. Reçu de Paiement
  3. Bulletin de Soins BS1 CNAM
  4. Feuille de Soins / Maladie
  5. Ordonnance Médicale
  6. Bordereau d'envoi CNAM
* **🎙️ Script Oral Jury :**
  > *"Notre module intègre l'édition de l'ensemble des 6 documents PDF réglementaires via le moteur de rapport QWeb d'Odoo : facture, reçu de paiement, bulletin BS1 CNAM, feuille de maladie, ordonnance médicale et bordereau d'envoi M5."*
* **Valeur métier :** Délivrance instantanée de documents officiels normalisés pour les patients et la CNAM.
* **Fichiers & Méthodes :** [facture_template.xml](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/reports/facture_template.xml), [recu_template.xml](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/reports/recu_template.xml), [bs1_template.xml](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/reports/bs1_template.xml), [feuille_soins_template.xml](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/reports/feuille_soins_template.xml), [ordonnance_report.xml](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/reports/ordonnance_report.xml), [bordereau_report.xml](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/reports/bordereau_report.xml).
* **Validations :** Rendu PDF conforme aux gabarits officiels tunisiens avec en-tête et signatures.
* **Choix technique :** Gabarits QWeb XML modulaires réutilisant les composants de style du cabinet.

---

#### 15. Bordereau CNAM M5 & Télétransmission (`bordereau.py`, `cnam_dashboard.js`)
* **Moment de la démonstration :** 13:15
* **Manipulations exactes :** Ouvrir **Cabinet Médical > CNAM > Bordereaux**. Créer un bordereau mensuel, cliquer sur **"Récupérer les factures"**, valider et cliquer sur **Envoyer à la CNAM**.
* **🎙️ Script Oral Jury :**
  > *"Pour la gestion du Tiers-Payant, la méthode `action_recuperer_factures()` dans `bordereau.py` extrait l'ensemble des factures validées sous régime CNAM de la période, calcule les montants réclamés et génère le bordereau M5. La méthode `action_envoyer()` fait passer les factures associées au statut 'Envoyé'."*
* **Valeur métier :** Dématérialisation et simplification du processus de télétransmission et de recouvrement CNAM.
* **Fichiers & Méthodes :** [bordereau.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/bordereau.py) (`action_recuperer_factures`, `action_envoyer`, `get_cnam_dashboard_stats`), [cnam_dashboard.js](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/static/src/js/cnam_dashboard.js).
* **Validations :** Filtrage strict des factures Tiers-Payant/APCI non encore rattachées à un bordereau.
* **Choix technique :** Suivi par machine à états (`draft` ➔ `done` ➔ `sent` ➔ `partially_paid` / `paid` / `rejected`).

---

#### 16. Portail Patient & Durcissement Sécurité OWASP (`controllers/main.py`, `portal.py`)
* **Moment de la démonstration :** 14:30 (Début Phase 4)
* **Manipulations exactes :** Sur la fiche d'un patient, cliquer sur **"Créer accès portail"** ou **"Renvoyer l'invitation"**. Définir le mot de passe sur le lien reçu et valider.
* **🎙️ Script Oral Jury :**
  > *"Sur le plan de la sécurité web, nous avons surchargé le contrôleur `AuthSignupHome` dans `controllers/main.py`. Conformément aux préconisations OWASP, lors du réglage du mot de passe, l'instruction `request.session.logout(keep_db=True)` détruit immédiatement la session temporaire pour se prémunir contre les attaques de type Session Hijacking. Le patient est redirigé vers la page de login avec un message de succès."*
* **Valeur métier :** Protection renforcée des comptes patients contre les accès non autorisés.
* **Fichiers & Méthodes :** [main.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/controllers/main.py) (`CabinetAuthSignupHome`), [portal.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/controllers/portal.py) (`action_create_portal_user`, `action_resend_portal_invite`).
* **Validations :** Invalidation forcée des jetons d'accès temporaires après soumission du mot de passe.
* **Choix technique :** Surcharge propre des routes `/web/signup` et `/web/reset_password` d'Odoo.

---

#### 17. E-Espace Patient Web & Gestion des Notifications (`controllers/portal.py`, `notification.py`)
* **Moment de la démonstration :** 15:30
* **Manipulations exactes :** Se connecter avec le compte du patient (`patient.demo@email.com`) sur `/my`. Naviguer dans les rubriques Mes RDV, Mes Ordonnances, Ma Couverture CNAM et Notifications.
* **🎙️ Script Oral Jury :**
  > *"Le contrôleur `PatientPortal` dans `portal.py` offre au patient un espace web responsive pour consulter ses rendez-vous, télécharger ses ordonnances PDF et suivre son centre de notifications en temps réel (`portal_my_notifications`). Le système de notifications ([notification.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/notification.py)) alerte le patient lors de l'enregistrement de son arrivée, de l'émission d'une ordonnance ou de l'échéance de ses droits CNAM."*
* **Valeur métier :** Autonomie du patient, baisse des appels au secrétariat et amélioration de l'observance thérapeutique.
* **Fichiers & Méthodes :** [portal.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/controllers/portal.py), [notification.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/notification.py), [portal_templates.xml](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/views/portal_templates.xml).
* **Validations :** Marquage dynamique des notifications comme lues (`portal_notification_read`) ou supprimées.
* **Choix technique :** Héritage de `CustomerPortal` Odoo avec pagination web (`portal_pager`).

---

#### 18. Isolation Row-Level Security des Données Patient (Record Rules) (`portal_security.xml`)
* **Moment de la démonstration :** 16:30
* **Manipulations exactes :** Tenter d'accéder par URL directe à l'ordonnance d'un autre patient.
* **🎙️ Script Oral Jury :**
  > *"L'isolation au niveau de la base de données est garantie par des Record Rules PostgreSQL déclarées dans `portal_security.xml`. La règle `domain_force="[('patient_id.user_id', '=', user.id)]"` garantit qu'un patient connecté ne peut accéder sous aucun prétexte aux enregistrements d'un tiers."*
* **Valeur métier :** Respect strict du secret médical et conformité avec les réglementations sur les données de santé (RGPD/HDS).
* **Fichiers & Méthodes :** [portal_security.xml](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/security/portal_security.xml) (`rule_cabinet_patient_portal`, `rule_cabinet_prescription_portal`).
* **Validations :** Filtre SQL automatique injecté par l'ORM d'Odoo sur toutes les requêtes du portail.
* **Choix technique :** Sécurité ancrée dans la couche ORM/SQL plutôt que dans l'interface utilisateur.

---

#### 19. Dashboard IA Executif (Composant Web OWL JS & API Claude 3.5 Haiku) (`dashboard_ai.py`, `ai_dashboard.js`)
* **Moment de la démonstration :** 17:00 (Début Phase 5)
* **Manipulations exactes :** Ouvrir **Cabinet Médical > Tableau de Bord IA**.
* **🎙️ Script Oral Jury :**
  > *"Le Tableau de Bord IA est un composant Web réactif développé en JavaScript OWL (`ai_dashboard.js`) intégrant des graphiques Chart.js (US35 à US39). Côté serveur, la méthode `get_ai_insights()` dans `dashboard_ai.py` calcule un Score de Santé sur 100 et transmet un payload JSON structuré à l'API Anthropic Claude 3.5 Haiku (`claude-haiku-4-5-20251001`) pour générer une synthèse décisionnelle. En cas de perte de connexion réseau, la méthode `_generate_local_fallback()` assure le rendu local des métriques sans interrompre l'expérience utilisateur."*
* **Valeur métier :** Pilotage stratégique du cabinet médical et suivi analytique de l'activité.
* **Fichiers & Méthodes :** [dashboard_ai.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/dashboard_ai.py) (`get_ai_insights`, `_call_claude_api`, `_generate_local_fallback`), [ai_dashboard.js](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/static/src/js/ai_dashboard.js), [dashboard_views.xml](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/views/dashboard_views.xml).
* **Validations :** Rendu asynchrone OWL JS avec gestion du mode dégradé local.
* **Choix technique :** Utilisation du framework OWL (Odoo Web Library) v2 natif d'Odoo 17.

---

#### 20. Tâche Planifiée Automatique (Cron Expiration CNAM) (`cron_data.xml`, `patient.py`)
* **Moment de la démonstration :** 18:00
* **Manipulations exactes :** Ouvrir **Configuration > Technique > Actions Programmées** et montrer `"Cabinet Médical : Vérification de la validité CNAM"`.
* **🎙️ Script Oral Jury :**
  > *"Pour éliminer les rejets de télétransmission dus aux cartes expirées, la tâche planifiée `ir_cron_check_cnam_expiration` exécutée chaque jour appelle `_cron_check_cnam_expiration()` dans `patient.py`. Elle identifie les assurés CNAM expirant à J-7 ou au jour J et émet des notifications automatiques d'avertissement."*
* **Valeur métier :** Proactivité administrative et réduction du taux d'impayés CNAM.
* **Fichiers & Méthodes :** [cron_data.xml](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/data/cron_data.xml), [patient.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/patient.py) (`_cron_check_cnam_expiration`).
* **Validations :** Exécution automatique en arrière-plan sans intervention humaine.
* **Choix technique :** Intégration dans le scheduler natif `ir.cron` d'Odoo.

---

#### 21. Validation par la Suite de Tests Automatisés (`tests/test_bdpm_ontology.py`)
* **Moment de la démonstration :** 18:45 (Début Phase 6)
* **Manipulations exactes :** Montrer la suite de tests unitaires Odoo dans `tests/test_bdpm_ontology.py` et les fichiers de recette `test_complet_final.md`.
* **🎙️ Script Oral Jury :**
  > *"Pour garantir la qualité et la non-régression de notre code, nous avons formalisé une suite de tests unitaires sous Odoo `TransactionCase` (`test_bdpm_ontology.py`) validant le chargement des ontologies médicales BDPM, la classification des DCI et les règles de calcul de facturation."*
* **Valeur métier :** Fiabilité logicielle, stabilité des livrables et sérénité lors des déploiements.
* **Fichiers & Méthodes :** [test_bdpm_ontology.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/tests/test_bdpm_ontology.py), [test_complet_final.md](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/test_complet_final.md).
* **Validations :** Exécution des assertions unitaires Python sous le runner de test d'Odoo.
* **Choix technique :** Emploi des classes de test isolées `TransactionCase` d'Odoo.

---

# SECTION 3 : CHECK-LIST EXHAUSTIVE DE SOUTENANCE (100% DU TRAVAIL)

| N° | ✅ Fonctionnalité Démontrée | 📁 Fichier / Composant Concerné | ⏱️ Temps Prévu |
| :--- | :--- | :--- | :--- |
| 1 | **Architecture du Module & Styling UI** | [hide_app_switcher.js](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/static/src/js/hide_app_switcher.js), [ir_http.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/ir_http.py) | 02:00 - 02:30 |
| 2 | **Gestion Patients & Conformité Dossier** | [patient.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/patient.py) (`_compute_dossier_status`) | 02:30 - 03:00 |
| 3 | **Validation Données Tunisiennes (CIN/Tél/CNAM)** | [patient.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/patient.py) (`_check_cin`, `_check_telephone`) | 03:00 - 03:30 |
| 4 | **Importation Excel & Savepoints PostgreSQL** | [wizard_import_patients.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/wizard_import_patients.py) (`action_importer`) | 03:30 - 04:15 |
| 5 | **RDV Rapide & Wizard Création Dossier** | [wizard_creer_patient.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/wizard_creer_patient.py) (`action_confirmer`) | 04:15 - 04:45 |
| 6 | **Agenda OWL JS, Quotas & Chevauchements** | [rendezvous.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/rendezvous.py) (`_check_appointments_limit`, `_onchange_date_heure`) | 04:45 - 05:00 |
| 7 | **Workflow RDV & Protection Suppression** | [rendezvous.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/rendezvous.py) (`unlink`, `action_patient_arrive`) | 05:00 - 05:30 |
| 8 | **Confidentialité Dossier Médical (RBAC)** | [security.xml](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/security/security.xml), [consultation.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/consultation.py) | 05:30 - 06:15 |
| 9 | **Actes Médicaux & Référentiel Tarifs** | [acte.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/acte.py) (`_onchange_parametrage_id`, `_compute_total_acte`) | 06:15 - 07:00 |
| 10 | **IA Anti-Allergies 3 Niveaux (BDPM/Fuzzy/NLP)** | [prescription.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/prescription.py) (`_verify_ia_in_memory`, `_get_bdpm_ontology`) | 07:00 - 08:30 |
| 11 | **Planification Suivi & Clôture Consultation** | [consultation.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/consultation.py), [wizard_suivi.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/wizard_suivi.py) | 08:30 - 09:30 |
| 12 | **Moteur des 8 Scénarios de Facturation** | [facture.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/facture.py) (`_compute_scenario`, `_compute_parts`) | 11:00 - 12:00 |
| 13 | **IA LLM Souverain Embarqué (Ollama/Mistral)** | [facture.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/facture.py) (`_get_llm_alert`, `_check_taux_apci`) | 12:00 - 12:45 |
| 14 | **Édition des 6 Documents PDF Officiels** | Rapports QWeb ([facture_template.xml](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/reports/facture_template.xml), [bs1_template.xml](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/reports/bs1_template.xml)...) | 12:45 - 13:15 |
| 15 | **Bordereau CNAM M5 & Télétransmission** | [bordereau.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/bordereau.py) (`action_recuperer_factures`, `action_envoyer`) | 13:15 - 13:30 |
| 16 | **Portail Patient & Durcissement OWASP** | [main.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/controllers/main.py) (`CabinetAuthSignupHome`), [portal.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/controllers/portal.py) | 14:30 - 15:30 |
| 17 | **E-Espace Patient Web & Notifications** | [portal.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/controllers/portal.py), [notification.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/notification.py) | 15:30 - 16:30 |
| 18 | **Isolation Record Rules (Row-Level Security)** | [portal_security.xml](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/security/portal_security.xml) (`rule_cabinet_prescription_portal`) | 16:30 - 17:00 |
| 19 | **Dashboard IA Executif (OWL JS + Claude)** | [dashboard_ai.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/dashboard_ai.py), [ai_dashboard.js](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/static/src/js/ai_dashboard.js) | 17:00 - 18:00 |
| 20 | **Cron Automatique Expiration CNAM** | [cron_data.xml](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/data/cron_data.xml), [patient.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/patient.py) (`_cron_check_cnam_expiration`) | 18:00 - 18:30 |
| 21 | **Démonstration Suite de Tests & Recette** | [test_bdpm_ontology.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/tests/test_bdpm_ontology.py), [test_complet_final.md](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/test_complet_final.md) | 18:30 - 19:00 |
| 22 | **Bilan & Contributions Ingénieur (Clôture)** | Conclusion générale d'ingénieur | 19:00 - 20:00 |

---

**Fin du Master Guide de Soutenance d'Ingénieur.**
