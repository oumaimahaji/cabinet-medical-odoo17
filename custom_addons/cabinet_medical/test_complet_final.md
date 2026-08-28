# 🏥 MATRICE DE TEST EXHAUSTIVE - APPLICATION CABINET MÉDICAL

Ce guide de test manuel a été conçu pour valider **100% des fonctionnalités** développées pour votre module Odoo `cabinet_medical`. Il couvre tous les rôles, tous les processus métier, et intègre les toutes dernières améliorations de sécurité, d'IA, et du portail patient.

---

## 👥 RÔLES ET ACCÈS

Votre application gère la sécurité de façon stricte. Les tests doivent être effectués avec 3 utilisateurs distincts :
1. **Administrateur** (Configuration système)
2. **Médecin** (Consultations, Dossiers Médicaux, Dashboard IA)
3. **Secrétaire** (Prise de RDV, Facturation, Création Patients)
4. **Patient** (Accès limité au Portail Odoo)

---

## ⚙️ 1. CONFIGURATION (Rôle : Administrateur)

### Test 1.1 : Configuration de la Clé API et Paramètres
- **Action** : Aller dans `Configuration > Paramètres`
- **Cas Positif** : Saisir la "Clé API Claude", les horaires, l'INPE. Sauvegarder.
- **Résultat Attendu** : Les paramètres sont bien sauvegardés. La clé API est masquée `***`.

### Test 1.2 : Configuration du Dictionnaire des Actes
- **Action** : Aller dans `Configuration > Dictionnaire des Actes`
- **Cas Positif** : Créer un acte "Consultation Spécialiste" (Code: C, Prix: 60 DT, CNAM: 45 DT).
- **Résultat Attendu** : L'acte est disponible pour la facturation future.

---

## 👩‍💼 2. GESTION DES PATIENTS & PORTAIL (Rôle : Secrétaire)

### Test 2.1 : Création d'un Patient (Via RDV Uniquement)
*Règle métier : La secrétaire ne peut pas créer un patient de zéro, elle doit passer par l'assistant de RDV.*
- **Action** : Aller dans `Patients`. Tenter de cliquer sur "Créer".
- **Cas Négatif** : Le bouton "Créer" n'existe pas. C'est le comportement attendu.

### Test 2.2 : Complétion du Dossier Patient (Sécurité CIN)
- **Action** : Ouvrir un patient existant. Remplir le CIN, Sexe, Date de Naissance, Téléphone.
- **Test CIN invalide** : Saisir "1234ABCD" ou "123" dans le champ CIN et enregistrer.
- **Résultat Attendu** : ❌ **BLOQUÉ**. Odoo affiche une erreur bloquante : "Le CIN doit contenir exactement 8 chiffres". La sauvegarde est empêchée.
- **Test CIN valide** : Saisir "12345678".
- **Résultat Attendu** : ✅ La sauvegarde réussit. Un ruban vert "Dossier Complet" s'affiche en haut à droite.

### Test 2.3 : Création de l'Accès Portail Patient
*C'est la secrétaire qui octroie l'accès au patient.*
- **Action** : Ouvrir la fiche d'un patient. 
- **Prérequis** : Le patient doit obligatoirement avoir une adresse e-mail valide.
- **Cas Positif** : Cliquer sur le bouton gris en haut à gauche **"Créer Accès Portail"**.
- **Résultat Attendu** : 
  1. Odoo crée un utilisateur portail lié à ce patient.
  2. Un e-mail d'invitation est automatiquement envoyé au patient pour qu'il choisisse son mot de passe.
  3. Le bouton "Créer Accès Portail" disparaît de la vue (car l'accès existe déjà).

### Test 2.4 : Import de Patients en Masse (Wizard)
- **Action** : Aller dans `Patients > Favoris > Importer (Excel)`.
- **Cas Positif** : Téléverser un fichier Excel avec "Nom, Telephone, CIN".
- **Résultat Attendu** : L'assistant crée les patients automatiquement et affiche un rapport de succès.

---

## 📅 3. AGENDA ET RENDEZ-VOUS (Rôle : Secrétaire)

### Test 3.1 : Création d'un Rendez-vous (Nouveau Patient)
- **Action** : Aller dans `Rendez-vous`, cliquer sur "Créer". Sélectionner "Nouveau Patient".
- **Cas Positif** : Un formulaire s'ouvre pour saisir le nom et le téléphone.
- **Résultat Attendu** : Le RDV est créé à l'état "En Attente", ET le patient est automatiquement créé dans la base de données de manière invisible.

### Test 3.2 : Création d'un Rendez-vous (Patient Existant)
- **Action** : Aller dans `Rendez-vous`, cliquer sur "Créer". Sélectionner "Patient Existant".
- **Cas Positif** : Rechercher le patient dans la liste, valider.
- **Résultat Attendu** : RDV créé.

### Test 3.3 : Changement de Statut d'un RDV
- **Action** : Sur un RDV "En Attente", cliquer sur "Marquer Présent".
- **Résultat Attendu** : Le RDV passe en statut "Présent". La couleur change dans la liste. 
- **Important** : Le bouton "Passer en consultation" apparaît, mais la secrétaire **n'a pas le droit** de cliquer dessus.

---

## 🩺 4. CONSULTATION MÉDICALE (Rôle : Médecin)

### Test 4.1 : Démarrer une Consultation
- **Action** : Se connecter en tant que Médecin. Aller dans `Rendez-vous`.
- **Cas Positif** : Cliquer sur un RDV "Présent", puis cliquer sur **"Passer en Consultation"**.
- **Résultat Attendu** : Le statut du RDV passe à "En Consultation". Un nouveau document "Consultation" est généré, et le médecin est redirigé vers ce document de consultation.

### Test 4.2 : Remplir la Consultation
- **Action** : Saisir le motif, le diagnostic et les notes médicales confidentielles.
- **Résultat Attendu** : Ces champs sont masqués pour la secrétaire.

### Test 4.3 : Prescrire des Médicaments (Ordonnance)
- **Action** : Dans l'onglet "Prescriptions" de la consultation, cliquer sur "Créer Ordonnance".
- **Cas Positif** : Ajouter des lignes de médicaments (ex: Doliprane 1000mg, Posologie: 3/jour pendant 5 jours).
- **Résultat Attendu** : L'ordonnance est générée. Cliquer sur "Imprimer Ordonnance" génère un PDF formaté au nom du cabinet.

### Test 4.4 : Actes Médicaux
- **Action** : Dans l'onglet "Actes", ajouter l'acte "Consultation Spécialiste" créé à l'étape 1.
- **Résultat Attendu** : Le prix se calcule automatiquement.

### Test 4.5 : Clôturer la Consultation
- **Action** : Cliquer sur **"Terminer la Consultation"**.
- **Résultat Attendu** : 
  1. Le statut de la consultation passe à "Terminé".
  2. Le RDV d'origine passe au statut "Terminé".
  3. Une **Facture brouillon** est générée automatiquement pour la secrétaire.

---

## 💰 5. FACTURATION ET CNAM (Rôle : Secrétaire)

### Test 5.1 : Valider une Facture
- **Action** : Aller dans `Facturation`. Ouvrir la facture générée par le médecin.
- **Cas Positif** : La facture indique le prix des actes. Si le patient est CNAM, la prise en charge CNAM est automatiquement déduite du "Montant à payer" par le patient !
- **Action** : Cliquer sur "Confirmer" puis sur "Enregistrer un paiement".

### Test 5.2 : Impression des Documents Comptables
- **Action** : Sur la facture payée, cliquer sur "Imprimer".
- **Testez l'impression de** :
  1. La **Facture standard** (PDF).
  2. Le **Reçu de Paiement** (Petit format).
  3. Le **Bulletin de Soin (BS1)** (Si le patient est CNAM).
  4. La **Feuille de Maladie** (Si demandé).

### Test 5.3 : Générer le Bordereau CNAM
- **Action** : Aller dans `CNAM > Bordereaux`. Cliquer sur Créer.
- **Cas Positif** : Ajouter des factures de patients CNAM de la semaine. Valider le bordereau.
- **Résultat Attendu** : Impression du bordereau récapitulatif PDF pour l'envoyer à l'assurance.

---

## 🤖 6. INTELLIGENCE ARTIFICIELLE (Rôle : Médecin)

### Test 6.1 : Résumé IA du Dossier Patient
- **Action** : Ouvrir un Patient. Cliquer sur l'onglet **"Analyse IA"**. Cliquer sur le bouton "Générer un résumé IA".
- **Cas Positif** : L'IA se connecte à Claude, analyse l'historique des consultations, les allergies, l'âge, et génère un texte de synthèse médicale.
- **Cas Négatif (Hors ligne)** : Si vous n'avez pas internet ou pas de clé valide, l'application affichera un message élégant de secours au lieu de crasher.

### Test 6.2 : Tableau de Bord Analytique (Dashboard IA)
- **Action** : Aller dans `Tableau de Bord`.
- **Résultat Attendu** : 
  1. Les KPI (Chiffre d'affaire, Nombre de RDV, Nouveaux patients) s'affichent correctement.
  2. Si l'IA est implémentée, elle doit générer une analyse sur les tendances (pics d'affluence, recommandations).

---

## 🌐 7. PORTAIL PATIENT EN LIGNE (Rôle : Patient)

### Test 7.1 : Connexion au Portail
- **Action** : Ouvrir une fenêtre de navigation privée. Aller sur `http://localhost:8069/my`.
- **Prérequis** : Utiliser l'e-mail et le mot de passe du patient créés lors du Test 2.3.
- **Cas Positif** : Le patient se connecte avec succès et accède à l'écran d'accueil Odoo.

### Test 7.2 : Tableau de Bord Patient Personnalisé
- **Action** : Sur la page d'accueil du portail (/my/home), vérifier les blocs :
  1. **Vos Rendez-vous** : Le patient voit-il le nombre de ses RDV ?
  2. **Vos Ordonnances** : Le patient peut-il cliquer pour télécharger ses ordonnances en PDF ?
  3. **Vos Factures** : Le patient peut-il voir et télécharger ses factures validées ?

### Test 7.3 : Alertes Intelligentes CNAM
- **Action** : Connectez-vous avec un patient dont la date de validité CNAM est dépassée (modifier cette date via le compte secrétaire avant).
- **Cas Positif** : Une grande alerte rouge "🚨 Votre couverture CNAM est expirée" doit s'afficher sur le portail du patient !

### Test 7.4 : Accès Bloqué aux Données Médicales
- **Action** : Le patient doit chercher à voir les notes médicales confidentielles saisies par le médecin.
- **Cas Positif** : Ces données n'existent nulle part sur le portail ! Le patient n'a accès qu'à l'administratif (Factures) et aux documents de sortie (Ordonnances imprimables).

---

## 🔒 8. CONTRÔLE DE SÉCURITÉ FINAL (Tests Croisés)

1. **Test Secrétaire sur Dossier Médical** : La secrétaire ouvre une consultation. Les champs "Motif" et "Diagnostic" doivent être 100% invisibles.
2. **Test Médecin sur Facturation** : Le médecin ne doit pas pouvoir valider un paiement.
3. **Test Patient sur l'URL interne** : Le patient modifie son URL pour accéder à `http://localhost:8069/web`. Il doit être bloqué et redirigé vers son portail.

---
**Fin du Guide de Test.**
Si toutes ces étapes sont validées, votre projet est prêt à 100% pour la soutenance.
