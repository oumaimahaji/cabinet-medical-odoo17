# GUIDAGE CONTINU NARRATIF POUR LA DÉMONSTRATION EN DIRECT (SOUTENANCE PFE)
## Script Narratif Fluide — À suivre étape par étape pendant la démonstration en direct (20 Minutes)

---

### 🎬 ACCUEIL ET INTRODUCTION (00:00 - 02:00)

**[MANIPULATION À L'ÉCRAN]** : Affichez la page de connexion d'Odoo ou votre première diapositive d'architecture.

**[CE QUE VOUS DITES À VOIX HAUTE DEVANT LE JURY]** :  
> *"Bonjour Monsieur le Président, Messieurs les membres du jury. J'ai le plaisir de vous présenter aujourd'hui mon projet de fin d'études portant sur la conception d'un système intégré de gestion de cabinet médical sur Odoo 17, intégrant une architecture IA hybride multi-niveaux et la télétransmission CNAM. L'objectif de ce projet est d'automatiser l'ensemble du workflow d'un cabinet médical en Tunisie, de l'accueil de la patientèle jusqu'à la télétransmission des bordereaux CNAM, tout en sécurisant la décision médicale grâce à l'Intelligence Artificielle. Pour cela, j'ai développé un addon Odoo 17 autonome nommé `cabinet_medical` sans modifier le cœur d'Odoo. Je vous propose de suivre maintenant cette démonstration en direct qui simule une journée de travail réelle au cabinet."*

---

### 🏥 PHASE 1 : SECRÉTARIAT, VALIDATION ET PRISE DE RDV (02:00 - 05:00)

**[MANIPULATION À L'ÉCRAN]** : Connectez-vous avec le compte Secrétaire (`sec.cabinet@demo.com`). Naviguez vers le menu **Cabinet Médical > Patients**.

**[CE QUE VOUS DITES À VOIX HAUTE ET MANIPULATION COMBINÉE]** :  
> *"Je démarre la journée au secrétariat en me connectant sous le rôle Secrétaire. Vous remarquez une interface professionnelle où le menu 'gaufre' natif d'Odoo a été masqué via notre script `hide_app_switcher.js` piloté par le contexte serveur `ir_http.py`. Sur la liste des patients, le système évalue automatiquement la conformité administrative grâce à la méthode `_compute_dossier_status()` dans `patient.py`, affichant un badge vert pour les dossiers complets et un badge rouge si des pièces manquent.*

**[MANIPULATION À L'ÉCRAN]** : Cliquez sur **Patients > Importer Patients (Excel)**. Téléversez le fichier `patients_demo.xlsx` et cliquez sur **Importer**.

**[CE QUE VOUS DITES À VOIX HAUTE]** :  
> *Pour la gestion des flux d'admission importants, j'ai développé le wizard `wizard_import_patients.py` basé sur `openpyxl`. Il applique une validation stricte des identifiants tunisiens : contrôles regex sur la CIN à 8 chiffres via `_check_cin()`, sur le téléphone mobile tunisien à 8 chiffres (débutant par 2, 4, 5, 7 ou 9) et sur le matricule CNAM à 10 chiffres. Du point de vue base de données, chaque ligne est exécutée sous un `SAVEPOINT` PostgreSQL (`import_patient_row_idx`) : si une ligne comporte une erreur ou un doublon de CIN, elle subit un `ROLLBACK` ciblé sans bloquer l'intégration des 500 autres lignes.*

**[MANIPULATION À L'ÉCRAN]** : Allez dans **Cabinet Médical > Agenda / RDV**. Cliquez sur 09:00. Tapez le nom seul : `"KARIM BEN AMAR"`. Sauvegardez. Cliquez sur le bouton **"Compléter le dossier patient"**. Renseignez la CIN (`08812345`), le téléphone (`98123456`), et cochez **Assuré CNAM** (Filière Privée, APCI Diabète, N° Décision: `APCI-2026-99`). Validez.

**[CE QUE VOUS DITES À VOIX HAUTE]** :  
> *Lorsqu'un patient appelle au téléphone, la secrétaire saisit rapidement son nom sur l'agenda. Lors de son arrivée en salle d'attente, notre wizard dédié `cabinet.rendezvous.creer.patient` s'ouvre pour qualifier sa fiche administrative (CIN, CNAM, APCI, Mutuelle) et remplacer automatiquement l'enregistrement temporaire par la clé étrangère du patient en base. De plus, notre méthode `_check_appointments_limit()` dans `rendezvous.py` contrôle en temps réel les quotas journaliers configurables — 20 consultations normales et 2 urgences — et la méthode `_onchange_date_heure()` intercepte les chevauchements de créneaux.*

**[MANIPULATION À L'ÉCRAN]** : Sur la fiche du rendez-vous, cliquez sur **"Patient Arrivé"**.

**[CE QUE VOUS DITES À VOIX HAUTE]** :  
> *En cliquant sur 'Patient Arrivé', le statut du rendez-vous passe à 'Présent'. La méthode `action_patient_arrive()` alimente la file d'attente du médecin et déclenche le système de notifications temps réel `create_notification()` pour avertir le patient sur son espace web."*

---

### 🩺 PHASE 2 : CONSULTATION MÉDICALE ET IA ANTI-ALLERGIES (05:00 - 11:00)

**[MANIPULATION À L'ÉCRAN]** : Déconnectez-vous ou changez d'onglet pour vous connecter sous le profil Médecin (`doc.cabinet@demo.com`). Ouvrez **Cabinet Médical > Rendez-vous du jour**. Sélectionnez Karim Ben Amar (`Présent`). Cliquez sur **"Démarrer la consultation"**.

**[CE QUE VOUS DITES À VOIX HAUTE]** :  
> *"Je me positionne maintenant en tant que Médecin. Depuis les rendez-vous du jour, je clique sur 'Démarrer la consultation'. La méthode `action_demarrer_consultation()` instancie la fiche médicale. Vous observez que les champs confidentiels — motif, diagnostic et notes cliniques — sont parfaitement visibles. En vertu des règles de sécurité RBAC configurées dans `security.xml`, ces champs sont totalement masqués pour le secrétariat.*

**[MANIPULATION À L'ÉCRAN]** : Dans l'onglet **Actes Médicaux**, ajoutez la ligne d'acte **"Consultation Spécialiste"** (Code `C01`).

**[CE QUE VOUS DITES À VOIX HAUTE]** :  
> *Dans l'onglet Actes Médicaux, lors de la sélection de l'acte 'Consultation Spécialiste', la méthode `_onchange_parametrage_id()` interroge le référentiel conventionnel `cabinet.acte.parametrage`. Elle injecte automatiquement le tarif réglementaire de 30 DT et la couverture CNAM de 70%, tandis que `_compute_total_acte()` calcule la part due par le patient.*

**[MANIPULATION À L'ÉCRAN]** : Cliquez sur **"Créer Ordonnance"**. Sur la fiche, montrez l'allergie du patient : `"Allergique à la Pénicilline"`. Dans les lignes de médicaments, ajoutez `"Amoxicilline 1g"`. Montrez l'alerte rouge. Puis tapez `"Pénécilline 500mg"` (avec faute de frappe). Lancez l'analyse IA.

**[CE QUE VOUS DITES À VOIX HAUTE]** :  
> *Voici l'innovation majeure de mon PFE : l'IA Hybride Anti-Allergies implémentée dans `_verify_ia_in_memory()` dans `prescription.py`. Elle combine 3 niveaux de sécurité :  
> 1. **Ontologie BDPM** : Chargement des fichiers officiels `CIS_bdpm.txt` et `CIS_COMPO_bdpm.txt` via `_get_bdpm_ontology()`. L'IA détecte immédiatement que l'Amoxicilline est une Pénicilline.  
> 2. **Fuzzy Matching Orthographique** : Utilisation de `difflib.SequenceMatcher` (seuil 82%) qui intercepte les fautes de frappe comme 'Pénécilline' avec une précision de 89%.  
> 3. **NLP Deep Learning** : Inférence du modèle Transformer `paraphrase-multilingual-MiniLM-L12-v2` sous PyTorch (`import torch`) calculant la similarité cosinus (seuil 70%) sur les phrases d'allergies complexes. Si le réseau est indisponible, les niveaux ontologiques et flous assurent une sécurité déterministe intégrale.*

**[MANIPULATION À L'ÉCRAN]** : Remplacez le médicament par `"Paracétamol 1g"`. Constatez le statut Vert (`Aucun risque allergique`). Cliquez sur **"Planifier un suivi"**, choisissez une date dans 15 jours, puis cliquez sur **"Terminer la consultation"**.

**[CE QUE VOUS DITES À VOIX HAUTE]** :  
> *Une fois le médicament remplacé par une molécule sûre, l'IA valide l'ordonnance. La méthode `action_planifier_suivi()` ouvre notre wizard `cabinet.suivi.wizard` pour programmer la visite de contrôle, puis `action_terminer()` clôture la consultation et passe le rendez-vous au statut 'Terminé'."*

---

### 💰 PHASE 3 : FACTURATION MULTI-SCÉNARIOS, LLM ET PDF (11:00 - 15:00)

**[MANIPULATION À L'ÉCRAN]** : Depuis la consultation terminée, cliquez sur **"Générer la Facture"**.

**[CE QUE VOUS DITES À VOIX HAUTE]** :  
> *"Depuis la consultation, je clique sur 'Générer la Facture'. Notre méthode `_compute_scenario()` dans `facture.py` évalue automatiquement la couverture sociale du patient parmi 8 scénarios réglementaires (CNAM Tiers-payant, Remboursement, APCI 100%, Mutuelle). Ici, le système identifie le scénario 'CNAM Tiers-payant + Mutuelle' et la méthode `_compute_parts()` ventile les montants : 21 DT (70%) pour la CNAM et 9 DT pour le ticket modérateur.*

**[MANIPULATION À L'ÉCRAN]** : Sur une facture d'un patient APCI, tentez de forcer le montant CNAM à 0 DT et enregistrez.

**[CE QUE VOUS DITES À VOIX HAUTE]** :  
> *Pour assister les utilisateurs lors des erreurs de saisie comptable, nous avons intégré un 3ème composant d'IA : un LLM souverain local Ollama exécutant le modèle Phi3 sur le port 11434 (`_get_llm_alert()`). Lors d'une anomalie détectée par `_check_taux_apci()`, le système transmet le contexte à Ollama qui formule une explication claire en français pour la secrétaire, garantissant qu'aucune donnée de santé ne quitte le serveur local.*

**[MANIPULATION À L'ÉCRAN]** : Validez la facture. Ouvrez le menu **Imprimer** et montrez successivement : la Facture, le Reçu de Paiement, le BS1 CNAM, la Feuille de Soins, et l'Ordonnance.

**[CE QUE VOUS DITES À VOIX HAUTE]** :  
> *L'application produit l'ensemble des 6 documents PDF officiels requis par le système de santé tunisien : facture de soins, reçu de paiement, bulletin de soins BS1 CNAM, feuille de maladie, ordonnance médicale et bordereau de télétransmission.*

**[MANIPULATION À L'ÉCRAN]** : Allez dans **Cabinet Médical > CNAM > Bordereaux**. Cliquez sur **Créer**. Sélectionnez le mois en cours, cliquez sur **"Récupérer les factures"**, puis sur **Valider** et **Envoyer à la CNAM**.

**[CE QUE VOUS DITES À VOIX HAUTE]** :  
> *Pour la télétransmission, la méthode `action_recuperer_factures()` dans `bordereau.py` extrait toutes les factures Tiers-Payant/APCI validées du mois, génère le bordereau M5 et bascule automatiquement les factures au statut 'Envoyé'."*

---

### 🌐 PHASE 4 : PORTAIL PATIENT WEB ET SÉCURITÉ OWASP (15:00 - 17:30)

**[MANIPULATION À L'ÉCRAN]** : Sur la fiche patient, cliquez sur **"Créer accès portail"**. Sur le navigateur privé, ouvrez le lien d'invitation, définissez le mot de passe et validez.

**[CE QUE VOUS DITES À VOIX HAUTE]** :  
> *"Sur le plan de la sécurité web, j'ai surchargé le contrôleur `AuthSignupHome` dans `controllers/main.py`. Conformément aux exigences OWASP, lors de la création du mot de passe, l'instruction `request.session.logout(keep_db=True)` détruit immédiatement la session temporaire afin de prévenir les attaques de Session Hijacking. Le patient est redirigé vers le Login avec un message de succès.*

**[MANIPULATION À L'ÉCRAN]** : Connectez-vous au portail `/my` en tant que Patient. Naviguez dans Mes RDV, Mes Ordonnances (téléchargez le PDF), Ma Couverture CNAM et les Notifications.

**[CE QUE VOUS DITES À VOIX HAUTE]** :  
> *Le contrôleur `PatientPortal` dans `portal.py` fournit au patient un espace web responsive lui permettant de télécharger ses ordonnances PDF et de consulter ses notifications. Du point de vue de la sécurité des données, des Record Rules PostgreSQL déclarées dans `portal_security.xml` (`domain_force="[('patient_id.user_id', '=', user.id)]"`) garantissent au niveau de la base de données qu'un patient ne peut accéder sous aucun prétexte aux documents d'un tiers."*

---

### 📊 PHASE 5 : DASHBOARD IA EXÉCUTIF ET CRON AUTOMATIQUE (17:30 - 19:00)

**[MANIPULATION À L'ÉCRAN]** : Connectez-vous en Médecin et ouvrez **Cabinet Médical > Tableau de Bord IA**.

**[CE QUE VOUS DITES À VOIX HAUTE]** :  
> *"Le Tableau de Bord IA est un composant Web réactif développé en JavaScript OWL (`ai_dashboard.js`) intégrant des graphiques Chart.js. Côté serveur, la méthode `get_ai_insights()` dans `dashboard_ai.py` calcule un Score de Santé sur 100 et transmet un payload JSON structuré à l'API Anthropic Claude 3.5 Haiku (`claude-haiku-4-5-20251001`) pour générer une synthèse décisionnelle. Si le réseau est coupé, la méthode `_generate_local_fallback()` produit les métriques localement sans interrompre l'affichage.*

**[MANIPULATION À L me L'ÉCRAN]** : Allez dans **Configuration > Technique > Actions Programmées** et montrez la tâche `"Cabinet Médical : Vérification de la validité CNAM"`.

**[CE QUE VOUS DITES À VOIX HAUTE]** :  
> *Enfin, pour prévenir les rejets CNAM, une tâche cron quotidienne exécute `_cron_check_cnam_expiration()` dans `patient.py` afin d'alerter automatiquement les patients à J-7 et au jour J de l'échéance de leurs droits."*

---

### 🧪 PHASE 6 : DEMONSTRATION DES TESTS ET CONCLUSION (19:00 - 20:00)

**[MANIPULATION À L'ÉCRAN]** : Montrez rapidement le fichier de test `tests/test_bdpm_ontology.py` et la matrice de test `test_complet_final.md`.

**[CE QUE VOUS DITES À VOIX HAUTE ET CONCLUSION FINAL]** :  
> *"Pour garantir la qualité du code, nous avons développé une suite de tests unitaires Odoo `TransactionCase` (`test_bdpm_ontology.py`) et formalisé des matrices de recette fonctionnelle.
>
> En conclusion, ce projet apporte quatre contributions majeures :  
> 1. Une architecture modulaire autonome sur Odoo 17 préservant le cœur du système.  
> 2. Une ingénierie IA hybride à triple niveau (Sécurité clinique locale BDPM/Fuzzy/NLP, synthèse décisionnelle Claude et assistance souveraine Ollama/Phi3).  
> 3. Une modélisation intégrale du système de santé tunisien (8 scénarios de facturation, APCI 100%, bordereaux M5 et 6 PDF officiels).  
> 4. Une sécurité et une transactionnalité industrielles (RBAC, Record Rules, déconnexion OWASP et SAVEPOINTs PostgreSQL).  
>
> Je vous remercie pour votre attention et je suis prêt à répondre à vos questions."*
