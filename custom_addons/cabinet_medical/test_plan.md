# Plan de Test Exhaustif et Actionnable — Module `cabinet_medical`

Ce document constitue le référentiel de validation complet pour tester manuellement **100% des règles métier, contraintes de sécurité, boutons et comportements dynamiques** du module `cabinet_medical`.

---

## 👥 Légende des Rôles Utilisateurs
*   **Admin :** Administrateur système (accès à toute la configuration).
*   **Médecin :** Profil médical (`cabinet_medical.group_medecin`).
*   **Secrétaire :** Profil administratif (`cabinet_medical.group_secretaire`).
*   **Patient :** Compte externe accédant uniquement au portail Web.

---

## 1. GESTION DES PATIENTS

### Test 1.1 : Format du CIN (Numéro d'identité) — **CRITIQUE**
*   **Rôle :** Secrétaire
*   **Étapes :**
    1. Ouvrir le module **Patients** (ou modifier un patient existant).
    2. Saisir `"1234"` (4 chiffres) ou `"1234567A"` (contenant une lettre) dans le champ **CIN**.
    3. Tenter de sauvegarder la fiche.
*   **Résultat attendu :** Blocage immédiat de la sauvegarde. Odoo affiche le message d'erreur :
    `Le CIN doit contenir exactement 8 chiffres`
*   **Fichier & Méthode :** [models/patient.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/patient.py#L362-L368) -> `_check_cin`

### Test 1.2 : Unicité du CIN — **CRITIQUE**
*   **Rôle :** Secrétaire
*   **Étapes :**
    1. Ouvrir un Patient A existant et lui attribuer le CIN `"12345678"`. Sauvegarder.
    2. Ouvrir un Patient B existant, saisir le même CIN `"12345678"`. Tenter de sauvegarder.
    *(Note : Si vous créez un nouveau patient, cela se fait via l'agenda des rendez-vous en choisissant "Nouveau Patient", les mêmes contraintes s'appliquent)*
*   **Résultat attendu :** Rejet de la base de données. Odoo affiche le message d'erreur :
    `Erreur : Ce numéro de CIN (12345678) est déjà utilisé par un autre patient !`
*   **Fichier & Méthode :** [models/patient.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/patient.py#L14-L22) -> `_check_cin_unique`

### Test 1.3 : Format du Téléphone Tunisien
*   **Rôle :** Secrétaire
*   **Étapes :**
    1. Ouvrir une fiche patient.
    2. Tester avec `"123"` (trop court) : tenter de sauvegarder.
    3. Tester avec `"31234567"` (commence par 3, non valide en Tunisie) : tenter de sauvegarder.
*   **Résultat attendu :** 
    *   Pour trop court : `Le téléphone doit contenir 8 chiffres`
    *   Pour indicatif invalide : `Le téléphone doit commencer par 2, 4, 5, 7 ou 9 (numéro tunisien)`
*   **Fichier & Méthode :** [models/patient.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/patient.py#L369-L377) -> `_check_telephone`

### Test 1.4 : Date de naissance dans le futur
*   **Rôle :** Secrétaire
*   **Étapes :**
    1. Ouvrir une fiche patient.
    2. Saisir une date de naissance dans le futur (ex: demain). Tenter de sauvegarder.
*   **Résultat attendu :** Blocage. Message d'erreur :
    `La date de naissance ne peut pas être dans le futur`
*   **Fichier & Méthode :** [models/patient.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/patient.py#L378-L383) -> `_check_date_naissance`

### Test 1.5 : Format du Matricule CNAM — **CRITIQUE**
*   **Rôle :** Secrétaire
*   **Étapes :**
    1. Cocher la case **Assuré CNAM**.
    2. Saisir `"01234"` (5 chiffres) dans le champ **Matricule CNAM**. Tenter de sauvegarder.
*   **Résultat attendu :** Blocage. Message d'erreur :
    `Le matricule CNAM doit être composé de 10 chiffres exactement.`
*   **Fichier & Méthode :** [models/patient.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/patient.py#L384-L390) -> `_check_numero_cnam`

### Test 1.6 : Expiration de la couverture CNAM / APCI
*   **Rôle :** Secrétaire
*   **Étapes :**
    1. Sur un patient CNAM, saisir une **Date validité CNAM** passée (ex: hier). Sauvegarder.
    2. Sur un patient APCI, saisir une **Date fin APCI** passée (ex: hier). Sauvegarder.
*   **Résultat attendu :** Les indicateurs techniques cachés `is_cnam_expired` et `is_apci_expired` passent automatiquement à `True`.
*   **Fichier & Méthode :** [models/patient.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/patient.py#L175-L185) -> `_compute_cnam_expired` & `_compute_apci_expired`

### Test 1.7 : Badge/Ruban "Dossier Complet"
*   **Rôle :** Secrétaire
*   **Étapes :**
    1. Renseigner tous les champs requis : Nom complet, CIN (8 chiffres), Téléphone (8 chiffres), Date de naissance, Genre.
    2. Si le patient est CNAM : renseigner aussi Matricule CNAM (10 chiffres) et Filière CNAM.
    3. Si le patient est APCI : renseigner aussi Numéro décision APCI.
    4. Si le patient a une assurance privée : sélectionner l'Assurance.
*   **Résultat attendu :** Un ruban vert `"Dossier Complet"` apparaît en haut à droite de la fiche du patient. Le champ technique `is_dossier_complet` passe à `True`.
*   **Fichier & Méthode :** [models/patient.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/patient.py#L210-L240) -> `_compute_dossier_status`

### Test 1.8 : Interdiction de suppression physique du dossier — **CRITIQUE**
*   **Rôle :** Secrétaire / Admin
*   **Étapes :**
    1. Ouvrir la fiche d'un patient.
    2. Cliquer sur le menu **Actions > Supprimer**.
*   **Résultat attendu :** Blocage de la suppression avec le message :
    `Les dossiers patients ne peuvent pas être supprimés physiquement pour des raisons médico-légales. Si ce dossier est un doublon ou n'est plus actif, veuillez utiliser la fonction d'archivage (bouton Actif/Inactif).`
*   **Fichier & Méthode :** [models/patient.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/patient.py#L392-L394) -> `unlink`

### Test 1.9 : Création d'Accès Portail (Bouton et Email personnalisé)
*   **Rôle :** Secrétaire
*   **Étapes :**
    1. Saisir une adresse email valide sur la fiche d'un patient (ex: `test@patient.com`). Sauvegarder.
    2. Cliquer sur le bouton **Créer Accès Portail** (icône globe).
*   **Résultat attendu :** 
    *   Un compte utilisateur Odoo (`res.users`) est généré.
    *   Un email d'invitation personnalisé rédigé en français avec le logo du cabinet dans l'en-tête est envoyé.
    *   Le bouton "Créer Accès Portail" disparaît du formulaire.
*   **Fichier & Méthode :** [models/patient.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/patient.py#L255-L319) -> `action_create_portal_user`

---

## 2. AGENDA ET RENDEZ-VOUS

### Test 2.1 : Interdiction de créer un rendez-vous dans le passé
*   **Rôle :** Secrétaire
*   **Étapes :**
    1. Aller dans **Rendez-vous > Créer**.
    2. Renseigner une date antérieure à aujourd'hui. Sauvegarder.
*   **Résultat attendu :** Blocage. Message d'erreur :
    `Impossible de créer un rendez-vous à une date passée.`
*   **Fichier & Méthode :** [models/rendezvous.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/rendezvous.py#L324-L327) -> `_check_date_past`

### Test 2.2 : Jours ouvrés du médecin
*   **Rôle :** Secrétaire
*   **Étapes :**
    1. Tenter de planifier un rendez-vous un dimanche (si exclu des jours configurés dans les paramètres). Sauvegarder.
*   **Résultat attendu :** Blocage. Message d'erreur :
    `Le médecin ne travaille pas ce jour-là`
*   **Fichier & Méthode :** [models/rendezvous.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/rendezvous.py#L329-L341) -> `_check_work_days`

### Test 2.3 : Plage horaire autorisée
*   **Rôle :** Secrétaire
*   **Étapes :**
    1. Configurer les horaires de 08:00 à 17:00 dans les paramètres.
    2. Créer un rendez-vous à 19:30. Sauvegarder.
*   **Résultat attendu :** Blocage. Message d'erreur :
    `L'heure du rendez-vous doit être comprise entre 08:00 et 17:00`
*   **Fichier & Méthode :** [models/rendezvous.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/rendezvous.py#L343-L359) -> `_check_hours`

### Test 2.4 : Quotas du jour (Normaux et Urgences) — **CRITIQUE**
*   **Rôle :** Secrétaire
*   **Étapes :**
    1. Configurer le quota quotidien à 20 places normales et 2 urgences dans les paramètres.
    2. Planifier 20 rendez-vous normaux à la date D. Tenter de planifier un 21ème.
    3. Planifier 2 urgences (case à cocher "Urgence" active) à la date D. Tenter d'en planifier une 3ème.
*   **Résultat attendu :** 
    *   Blocage normal : `Plus de créneau normal disponible ce jour (20/20 atteint)`
    *   Blocage urgence : `Quota urgence atteint pour cette date (2/2 atteint)`
*   **Fichier & Méthode :** [models/rendezvous.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/rendezvous.py#L361-L417) -> `_check_quotas`

### Test 2.5 : Unicité d'un patient par jour
*   **Rôle :** Secrétaire
*   **Étapes :**
    1. Créer un rendez-vous pour le patient "A" à la date D à 09:00.
    2. Tenter de créer un second rendez-vous pour le même patient "A" à la même date D à 14:00.
*   **Résultat attendu :** Blocage. Message d'erreur :
    `Ce patient a déjà un rendez-vous programmé pour cette date`
*   **Fichier & Méthode :** [models/rendezvous.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/rendezvous.py#L419-L438) -> `_check_patient_uniq_date`

### Test 2.6 : Chevauchement de créneau horaire
*   **Rôle :** Secrétaire
*   **Étapes :**
    1. Créer un rendez-vous à la date D à 10:00.
    2. Créer un autre rendez-vous à la même date D à 10:00.
*   **Résultat attendu :** Blocage. Message d'erreur :
    `Un rendez-vous existe déjà à cette heure`
*   **Fichier & Méthode :** [models/rendezvous.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/rendezvous.py#L440-L456) -> `_check_time_overlap`

### Test 2.7 : Patient temporaire invisible pour le Médecin — **CRITIQUE**
*   **Rôle :** Secrétaire / Médecin (Vérification croisée)
*   **Étapes :**
    1. En Secrétaire, créer un nouveau rendez-vous en choisissant **"Nouveau Patient"** (saisie du nom et téléphone). Le rendez-vous est sauvegardé.
    2. Se déconnecter et se connecter en Médecin.
    3. Aller dans le menu **Patients**. Rechercher le nom du patient temporaire créé.
*   **Résultat attendu :** Le patient temporaire n'apparaît pas dans la liste des patients du médecin (il n'a pas encore fait sa consultation ni validé son dossier).
*   **Fichier & Méthode :** [models/rendezvous.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/rendezvous.py#L532) & [views/patient_views.xml](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/views/patient_views.xml)

### Test 2.8 : Interdiction de suppression physique du RDV
*   **Rôle :** Secrétaire
*   **Étapes :**
    1. Ouvrir un rendez-vous existant.
    2. Cliquer sur **Actions > Supprimer**.
*   **Résultat attendu :** Blocage. Message d'erreur :
    `Les rendez-vous ne peuvent pas être supprimés physiquement pour des raisons de traçabilité et d'historique. Si le rendez-vous n'a pas lieu, veuillez cliquer sur 'Patient absent' ou utiliser le statut 'Annulé'.`
*   **Fichier & Méthode :** [models/rendezvous.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/rendezvous.py#L916-L922) -> `unlink`

### Test 2.9 : Action Planifier un suivi — **CRITIQUE**
*   **Rôle :** Médecin
*   **Étapes :**
    1. Depuis une consultation ouverte, cliquer sur le bouton **Planifier un suivi** dans l'en-tête.
*   **Résultat attendu :** Le calendrier des rendez-vous s'ouvre sous forme de popup avec le nom et l'ID du patient pré-remplis en contexte.
*   **Fichier & Méthode :** [models/consultation.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/consultation.py#L146-L163) -> `action_planifier_suivi`

---

## 3. CONSULTATIONS

### Test 3.1 : Date de consultation future trop éloignée
*   **Rôle :** Médecin
*   **Étapes :**
    1. Créer une consultation.
    2. Saisir une date supérieure à `Aujourd'hui + 7 jours`. Tenter de sauvegarder.
*   **Résultat attendu :** Blocage. Message d'erreur :
    `La date de consultation ne peut pas être à plus de 7 jours dans le futur`
*   **Fichier & Méthode :** [models/consultation.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/consultation.py#L79-L86) -> `_check_date_consultation`

### Test 3.2 : Motif de consultation minimum
*   **Rôle :** Médecin
*   **Étapes :**
    1. Créer une consultation.
    2. Saisir un motif très court comme `"maux"`. Tenter de sauvegarder.
*   **Résultat attendu :** Blocage. Message d'erreur :
    `Le motif de consultation doit contenir au moins 5 caractères`
*   **Fichier & Méthode :** [models/consultation.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/consultation.py#L88-L93) -> `_check_motif`


### Test 3.4 : Masquage du secret médical (Motif/Diagnostic) — **CRITIQUE**
*   **Rôle :** Secrétaire (Vérification croisée)
*   **Étapes :**
    1. Se connecter en Secrétaire.
    2. Ouvrir la liste des consultations ou la fiche patient contenant son historique.
*   **Résultat attendu :** Les colonnes et champs **Motif** et **Diagnostic** sont invisibles. Même par export de données (Excel/CSV) ou requête RPC directe, la Secrétaire ne peut pas y accéder (champs protégés au niveau Python).
*   **Fichier & Méthode :** [models/consultation.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/consultation.py#L22-L24) -> Attribut `groups="cabinet_medical.group_medecin"` sur les champs `motif`, `diagnostic` et `notes_medicales`.

---

## 4. PRESCRIPTIONS

### Test 4.1 : Date de prescription dans le futur
*   **Rôle :** Médecin
*   **Étapes :**
    1. Créer une ordonnance.
    2. Choisir une date future. Tenter de sauvegarder.
*   **Résultat attendu :** Blocage. Message d'erreur :
    `La date de prescription ne peut pas être dans le futur`
*   **Fichier & Méthode :** [models/prescription.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/prescription.py#L145-L150) -> `_check_date_prescription`

### Test 4.2 : Longueur des instructions
*   **Rôle :** Médecin
*   **Étapes :**
    1. Créer une ordonnance.
    2. Saisir `"ok"` dans les **Instructions générales**. Tenter de sauvegarder.
*   **Résultat attendu :** Blocage. Message d'erreur :
    `Les instructions générales doivent contenir au moins 5 caractères si elles sont renseignées`
*   **Fichier & Méthode :** [models/prescription.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/prescription.py#L152-L157) -> `_check_instructions`

### Test 4.3 : Au moins un médicament obligatoire
*   **Rôle :** Médecin
*   **Étapes :**
    1. Créer une ordonnance sans ajouter de ligne de médicament. Tenter de sauvegarder.
*   **Résultat attendu :** Blocage. Message d'erreur :
    `Une ordonnance doit contenir au moins un médicament`
*   **Fichier & Méthode :** [models/prescription.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/prescription.py#L159-L164) -> `_check_ordonnance_lines`

### Test 4.4 : Règles sur les médicaments prescrits
*   **Rôle :** Médecin
*   **Étapes :**
    1. Ajouter un médicament avec le nom `"A"` (moins de 2 caractères).
    2. Ajouter un médicament sans dosage.
    3. Saisir `"1/j"` (moins de 5 caractères) dans la posologie.
*   **Résultat attendu :** Blocage de la sauvegarde avec les validations correspondantes :
    *   `Le nom du médicament doit contenir au moins 2 caractères`
    *   `Le dosage ne peut pas être vide`
    *   `La posologie doit contenir au moins 5 caractères`
*   **Fichier & Méthode :** [models/prescription.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/prescription.py#L410-L430) -> `_check_medicament`, `_check_dosage`, `_check_posologie`

### Test 4.5 : IA Détection Risque Allergique (Fuzzy 82% & Transformer 70%) — **CRITIQUE**
*   **Rôle :** Médecin
*   **Étapes :**
    1. Sur la fiche du patient, saisir dans le champ **Allergies** : `"Allergie grave à la pénicilline"`. Sauvegarder.
    2. Créer une ordonnance pour ce patient.
    3. Ajouter le médicament `"Augmentin"` (DCI: Amoxicilline).
    4. Ajouter le médicament `"Penecilline"` (faute d'orthographe volontaire, match flou fuzzy > 82%).
    5. Cliquer sur le bouton **Vérifier Risques IA** (ou déclencher l'onchange automatique).
*   **Résultat attendu :** 
    *   Le statut de l'IA passe à **"Risque Allergique Détecté"**.
    *   Une notification rouge et persistante s'affiche à l'écran, listant les médicaments dangereux avec leur taux de fiabilité sémantique (Transformers NLP > 70%) ou orthographique (Fuzzy > 82%).
*   **Fichier & Méthode :** [models/prescription.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/prescription.py#L192-L346) -> `_verify_ia_in_memory`

### Test 4.6 : Interdiction de suppression physique d'ordonnance — **CRITIQUE**
*   **Rôle :** Médecin / Secrétaire / Admin
*   **Étapes :**
    1. Sélectionner une ordonnance.
    2. Cliquer sur **Actions > Supprimer**.
*   **Résultat attendu :** Blocage. Message d'erreur :
    `Les ordonnances médicales doivent être conservées à vie pour l'historique pharmacologique. Veuillez les archiver si elles ne sont plus valides.`
*   **Fichier & Méthode :** [models/prescription.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/prescription.py#L382-L384) -> `unlink`

### Test 4.7 : Archivage individuel d'une ordonnance
*   **Rôle :** Médecin
*   **Étapes :**
    1. Ouvrir une ordonnance existante (dans son pop-up ou en vue formulaire).
    2. Cliquer sur le bouton **Archiver** (bouton orange/warning dans l'en-tête).
*   **Résultat attendu :** L'ordonnance est archivée (`active = False`), le pop-up se ferme automatiquement. Dans l'onglet "Prescriptions/Ordonnances" de la consultation, cette ordonnance n'est plus listée (masquage automatique d'Odoo).
*   **Fichier & Méthode :** [models/prescription.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/prescription.py#L386-L389) -> `action_archive_prescription` et [views/prescription_views.xml](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/views/prescription_views.xml#L9)

---

## 5. FACTURATION

### Test 5.1 : Tarif plancher de 30 DT — **CRITIQUE**
*   **Rôle :** Secrétaire
*   **Étapes :**
    1. Générer une facture pour une consultation ne contenant aucun acte médical.
*   **Résultat attendu :** Le montant total de la facture est automatiquement défini à **`30.0 DT`** (tarif forfaitaire de base).
*   **Fichier & Méthode :** [models/facture.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/facture.py#L45-L49) -> `_compute_montant_total`

### Test 5.2 : Scénarios de Couverture (Calculs exacts) — **CRITIQUE**
*   **Rôle :** Secrétaire
*   **Étapes :**
    Tester un total de 100 DT facturé (ex: actes à 100 DT) pour les cas suivants :

    1. **Sans couverture :** Patient standard privé.
       *   *Résultat attendu :* Patient paie = `100 DT`, CNAM = `0 DT`, Reste à charge = `100 DT`.
    2. **APCI Tiers-Payant :** Patient APCI.
       *   *Résultat attendu :* Patient paie = `0 DT`, CNAM = `100 DT`, Reste à charge = `0 DT`.
    3. **APCI Remboursement :** Patient APCI filière remboursement.
       *   *Résultat attendu :* Patient paie = `100 DT`, CNAM = `0 DT` (au cabinet), Reste à charge = `0 DT` (remboursé après).
    4. **CNAM Tiers-Payant :** Patient CNAM filière privée (taux acte à 70%).
       *   *Résultat attendu :* Patient paie = `30 DT`, CNAM = `70 DT`, Reste à charge = `30 DT`.
    5. **CNAM Remboursement :** Patient CNAM filière remboursement.
       *   *Résultat attendu :* Patient paie = `100 DT`, CNAM = `0 DT`, Reste à charge = `30 DT` (70% remboursés).
    6. **CNAM Remboursement + Assurance (Tiers payant direct mutuelle 80%) :**
       *   *Résultat attendu :* Patient paie = `76 DT` (`total - (reste_cnam * 80%)`), CNAM = `0 DT`, Reste à charge = `6 DT` (`reste_cnam * 20%`).
    7. **CNAM Tiers-Payant + Mutuelle (Tiers payant direct 80%) :**
       *   *Résultat attendu :* Patient paie = `6 DT` (`30 DT * 20%`), CNAM = `70 DT`, Reste à charge = `6 DT`.
    8. **Sans CNAM + Assurance (Tiers payant direct 80%) :**
       *   *Résultat attendu :* Patient paie = `20 DT`, CNAM = `0 DT`, Reste à charge = `20 DT`.
*   **Fichier & Méthode :** [models/facture.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/facture.py#L72-L152) -> `_compute_parts`

### Test 5.3 : IA Anomalie 1 — Doublon de facturation — **CRITIQUE**
*   **Rôle :** Secrétaire
*   **Étapes :**
    1. Créer une facture pour Patient A le 09/07/2026. La sauvegarder.
    2. Créer une seconde facture pour Patient A le même jour 09/07/2026. Tenter de la sauvegarder.
*   **Résultat attendu :** Blocage. Message d'erreur reformulé par l'IA Ollama locale, ou message par défaut :
    `Anomalie 1 : Ce patient a déjà été facturé aujourd'hui.`
*   **Fichier & Méthode :** [models/facture.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/facture.py#L197-L204) -> `_check_doublon_facture`

### Test 5.4 : IA Anomalie 2 — Taux CNAM incohérent APCI — **CRITIQUE**
*   **Rôle :** Secrétaire
*   **Étapes :**
    1. Sur une facture d'un patient APCI, modifier les lignes d'actes pour forcer une part payée par la CNAM inférieure au total (ex: CNAM = 80 DT sur 100 DT). Sauvegarder.
*   **Résultat attendu :** Blocage. Message d'erreur reformulé par Ollama ou par défaut :
    `Anomalie 2 : Taux incohérent. Un patient APCI doit être facturé à 100% à la CNAM.`
*   **Fichier & Méthode :** [models/facture.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/facture.py#L206-L214) -> `_check_taux_apci`

### Test 5.5 : IA Anomalie 3 — APCI sans décision formelle — **CRITIQUE**
*   **Rôle :** Secrétaire
*   **Étapes :**
    1. Sur un patient, cocher **Patient APCI** mais laisser le champ **Numéro décision APCI** vide.
    2. Essayer de créer une facture pour ce patient. Tenter de sauvegarder.
*   **Résultat attendu :** Blocage. Message d'erreur :
    `Anomalie 3 : APCI sans décision. Le statut APCI est activé mais aucune décision CNAM n'est enregistrée pour ce patient.`
*   **Fichier & Méthode :** [models/facture.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/facture.py#L216-L223) -> `_check_apci_decision`

---

## 6. BORDEREAUX CNAM

### Test 6.1 : Récupération automatique des factures éligibles
*   **Rôle :** Secrétaire
*   **Étapes :**
    1. Aller dans **CNAM > Bordereaux**. Cliquer sur **Créer**.
    2. Choisir une période (ex: du 01/07/2026 au 31/07/2026). Sauvegarder.
    3. Cliquer sur **Récupérer factures**.
*   **Résultat attendu :** Odoo importe automatiquement toutes les factures de la période qui :
    *   Sont à l'état `"validated"`.
    *   Appartiennent à un scénario avec Tiers-Payant (`cnam_tiers_payant`, `apci_tiers_payant`, `cnam_tp_assur`).
    *   Ne sont pas déjà rattachées à un autre bordereau.
*   **Fichier & Méthode :** [models/bordereau.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/bordereau.py#L74-L99) -> `action_recuperer_factures`

### Test 6.2 : Cycle de vie du bordereau — **CRITIQUE**
*   **Rôle :** Secrétaire
*   **Étapes :**
    1. Sur un bordereau contenant des factures, cliquer sur **Valider** -> Passe à l'état **Validé** (`done`).
    2. Cliquer sur **Envoyer à la CNAM** -> Passe à l'état **Envoyé** (`sent`). Les factures associées passent à `"Envoyé (En attente)"`.
    3. Cliquer sur **Partiellement Payé** -> Passe à l'état **Partiellement payé** (`partially_paid`).
    4. Cliquer sur **Marquer comme Payé** -> Passe à l'état **Payé** (`paid`). Les factures associées passent à `"Payé"`.
    5. Cliquer sur **Rejeter** -> Saisir le motif de rejet dans le pop-up. Le bordereau passe à **Rejeté** (`rejected`), les factures passent à `"Rejeté"`.
*   **Résultat attendu :** Changement correct des états et propagation instantanée sur le statut CNAM des factures liées.
*   **Fichier & Méthode :** [models/bordereau.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/bordereau.py#L100-L128)

---

## 7. SÉCURITÉ ET DROITS D'ACCÈS

### Test 7.1 : Actions de modification de RDV réservées à la Secrétaire — **CRITIQUE**
*   **Rôle :** Médecin
*   **Étapes :**
    1. Se connecter en Médecin.
    2. Ouvrir un rendez-vous à l'état "Présent" ou "Confirmé".
    3. Tenter de forcer l'appel des méthodes `action_annuler` ou `action_patient_absent` (via RPC).
*   **Résultat attendu :** Rejet du serveur et levée d'une erreur d'accès :
    `Seule la Secrétaire peut annuler un rendez-vous ou marquer un patient absent.`
*   **Fichier & Méthode :** [models/rendezvous.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/rendezvous.py#L765-L781) -> `action_annuler` & `action_patient_absent`

### Test 7.2 : Création de suivi réservée au Médecin — **CRITIQUE**
*   **Rôle :** Secrétaire
*   **Étapes :**
    1. Se connecter en Secrétaire.
    2. Tenter d'ouvrir une consultation et d'appeler la méthode `action_planifier_suivi`.
*   **Résultat attendu :** Rejet du serveur et levée de l'erreur :
    `Seul le Médecin peut planifier un suivi.`
*   **Fichier & Méthode :** [models/consultation.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/consultation.py#L149-L150) -> `action_planifier_suivi`

### Test 7.3 : Factures en lecture seule pour le Médecin — **CRITIQUE**
*   **Rôle :** Médecin
*   **Étapes :**
    1. Se connecter en Médecin.
    2. Accéder au menu **Facturations** (le nouveau menu en lecture seule).
    3. Ouvrir une facture de la liste. Tenter de cliquer sur **Modifier** ou sur le bouton **Valider**.
*   **Résultat attendu :**
    *   Le bouton "Nouveau" n'est pas présent dans la liste.
    *   Le bouton "Modifier" est masqué dans le formulaire.
    *   Le bouton "Valider" est masqué.
    *   Toute tentative de modification par script ou RPC renvoie une exception d'accès.
*   **Fichier & Méthode :** [security/ir.model.access.csv](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/security/ir.model.access.csv#L17) (Ligne 17) & [views/facturation_views.xml](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/views/facturation_views.xml#L27)

### Test 7.4 : Masquage du menu Odoo (Waffle Menu) — **CRITIQUE**
*   **Rôle :** Secrétaire / Médecin
*   **Étapes :**
    1. Se connecter en Secrétaire ou en Médecin.
*   **Résultat attendu :** L'icône de la grille d'applications Odoo (les 9 carrés en haut à gauche) est complètement invisible. L'utilisateur est confiné dans l'application `cabinet_medical`.
*   **Fichier & Méthode :** [static/src/css/hide_apps_menu.css](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/static/src/css/hide_apps_menu.css)

---

## 8. PORTAIL PATIENT EN LIGNE

### Test 8.1 : Accès aux pages du portail patient
*   **Rôle :** Patient
*   **Étapes :**
    1. Se connecter au portail patient via l'URL `/my`.
    2. Naviguer vers les 4 sections du menu :
        *   **Vos Rendez-vous** (`/my/rendezvous`)
        *   **Vos Ordonnances** (`/my/ordonnances`)
        *   **Vos Factures** (`/my/factures`)
        *   **Couverture Médicale** (`/my/couverture`)
*   **Résultat attendu :** Les pages s'affichent sans erreur et affichent uniquement les données liées à l'utilisateur connecté.
*   **Fichier & Méthode :** [controllers/portal.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/controllers/portal.py) -> `PatientPortal`

### Test 8.2 : Alerte expiration CNAM sur le portail
*   **Rôle :** Patient (avec couverture expirée)
*   **Étapes :**
    1. Configurer un patient avec une date de validité CNAM dépassée.
    2. Se connecter avec ce patient sur le portail Web.
*   **Résultat attendu :** Une grande alerte rouge `"🚨 Votre couverture CNAM est expirée. Veuillez contacter le secrétariat."` apparaît en haut du tableau de bord du portail.
*   **Fichier & Méthode :** [controllers/portal.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/controllers/portal.py#L36-L39) -> `cnam_expiring_soon`

---

## 9. DASHBOARD IA

### Test 9.1 : Score de santé global
*   **Rôle :** Médecin
*   **Étapes :**
    1. Accéder au menu **Tableau de bord**.
*   **Résultat attendu :** Un indicateur coloré affiche le **Score de Santé** du cabinet calculé sur 100 points, justifié par une baisse ou hausse d'activité, le montant d'impayés, et les alertes d'allergies bloquées par l'IA.
*   **Fichier & Méthode :** [models/dashboard_ai.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/dashboard_ai.py#L328-L357) -> `_calculate_health_index`

### Test 9.2 : Mode secours (Local Fallback) — **CRITIQUE**
*   **Rôle :** Médecin / Admin
*   **Étapes :**
    1. En Admin, vider le champ **Clé API Claude** dans les paramètres généraux.
    2. Repasser en Médecin et rafraîchir le **Tableau de bord**.
*   **Résultat attendu :** Aucun crash ou écran blanc. Le tableau de bord affiche des résumés textuels générés localement en Python à partir des statistiques de la base de données.
*   **Fichier & Méthode :** [models/dashboard_ai.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/dashboard_ai.py#L467-L482) -> `_generate_local_fallback`

---

## 10. INTERFACE GÉNÉRALE (UX/UI)

### Test 10.1 : Recherche en temps réel (Debounce 350ms)
*   **Rôle :** Secrétaire / Médecin
*   **Étapes :**
    1. Aller dans la liste des Patients.
    2. Saisir rapidement le nom d'un patient dans la barre de recherche, **sans presser Entrée**.
*   **Résultat attendu :** La liste se recharge et filtre automatiquement les résultats 350ms après l'arrêt de la saisie au clavier.
*   **Fichier & Méthode :** [static/src/js/live_search.js](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/static/src/js/live_search.js)

### Test 10.2 : Bandeau de filtrage rapide des rendez-vous
*   **Rôle :** Secrétaire / Médecin
*   **Étapes :**
    1. Aller dans la liste des Rendez-vous (en vue liste/tree).
    2. Cliquer sur les différents boutons en haut de la vue : **"Aujourd'hui"**, **"À venir"**, **"Présent"**, **"En attente"**.
*   **Résultat attendu :** La liste est instantanément filtrée selon l'état choisi. Le bouton actif passe sur un fond blanc et texte bleu, tandis que les autres restent transparents avec texte blanc.
*   **Fichier & Méthode :** [static/src/js/rdv_filter_buttons.js](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/static/src/js/rdv_filter_buttons.js)
