# Plan de Test Exhaustif - Application Cabinet Médical (Soutenance PFE)

Ce document est la checklist définitive pour tester manuellement **100% des fonctionnalités développées** dans le code. À utiliser impérativement avant votre soutenance pour vous assurer qu'aucun bug n'a échappé à votre vigilance.

---

## 1. Tests Globaux de l'Interface (UX & UI)
👤 **Profil à utiliser :** *Médecin / Secrétaire*

- [ ] **Recherche en temps réel (Live Search) :** Taper le nom d'un patient dans la barre de recherche et vérifier que la liste se filtre toute seule après 350ms (sans taper sur Entrée).
- [ ] **Menu restreint (Hide Waffle) :** Se connecter avec le compte Secrétaire ou Médecin et vérifier que l'icône Odoo des applications (les 9 petits carrés) a disparu.
- [ ] **Navigation :** Vérifier que tous les menus en haut (Patients, Consultations, Mes Rendez-vous, Tableau de bord, CNAM, Configuration) s'ouvrent sans erreur 500.

---

## 2. Module Patients (`patient.py`)
👤 **Profil à utiliser :** *Secrétaire*

- [ ] **Création et Contraintes :**
  - [ ] Créer un patient avec des données valides.
  - [ ] Mettre un email invalide (ex: `test.com` sans @) : vérifier que le système le rejette.
  - [ ] Mettre un N° de téléphone invalide : vérifier que le système le rejette.
  - [ ] Mettre une date de naissance dans le futur : vérifier que le système l'interdit.
- [ ] **Gestion Couvertures (CNAM & APCI) :**
  - [ ] Cocher la case "Affilié CNAM" et vérifier que le champ "Filière" apparaît.
  - [ ] Cocher la case "Patient APCI" sans renseigner de N° de décision (cela servira pour tester l'erreur de facturation plus tard).
  - [ ] Ajouter une "Assurance/Mutuelle" et renseigner le taux de couverture.
- [ ] **Accès Portail :** Tester le bouton/wizard permettant d'activer l'accès au portail Odoo pour le patient (envoi d'email de connexion).
- [ ] **Smart Buttons :** Cliquer sur les compteurs en haut à droite de la fiche (RDV, Factures, Consultations) et vérifier qu'ils filtrent bien les éléments du patient.

---

## 3. Module Rendez-vous (`rendezvous.py`)
👤 **Profil à utiliser :** *Secrétaire*

- [ ] **Création et Validations :**
  - [ ] Tenter de créer un rendez-vous à une date passée : Odoo doit afficher une erreur.
  - [ ] Tenter de créer un rendez-vous qui se chevauche avec un autre rdv du même médecin : Odoo doit afficher l'avertissement de chevauchement.
- [ ] **Workflow des Statuts :**
  - [ ] Passer le statut manuellement de `Brouillon` -> `Confirmé` -> `En salle d'attente` -> `En consultation` -> `Terminé` ou `Annulé`.
- [ ] **Vues Kanban et Calendrier :**
  - [ ] Vérifier les couleurs selon l'état du RDV (vert, gris, etc.).
  - [ ] Glisser/Déposer un rendez-vous dans le calendrier et vérifier la modification de date.

---

## 4. Module Consultation & Actes (`consultation.py`, `acte.py`)
👤 **Profil à utiliser :** *Médecin*

- [ ] **Création depuis le RDV :** Créer la consultation directement depuis le rendez-vous (le patient et le médecin doivent se remplir automatiquement).
- [ ] **Constantes & Calculs :** Saisir le Poids et la Taille, vérifier que l'IMC se calcule bien.
- [ ] **Ajout d'Actes :**
  - [ ] Ajouter plusieurs actes dans la ligne de facturation (ex: Consultation, Échographie).
  - [ ] Vérifier que le total (Montant) se calcule automatiquement sur la base du paramétrage des actes.

---

## 5. IA n°1 : Prescriptions & Allergies (`prescription.py`)
👤 **Profil à utiliser :** *Médecin*

- [ ] **Scénario d'Alerte :**
  - [ ] Saisir dans la fiche patient "Allergies" une phrase contenant le mot "Pénicilline".
  - [ ] Dans sa consultation, créer une ordonnance.
  - [ ] Ajouter un médicament dont la famille est la Pénicilline (ex: Augmentin).
  - [ ] Vérifier que le système bloque ou affiche immédiatement une Alerte Rouge IA.
- [ ] **Scénario Sécurisé :** Ajouter un médicament normal, vérifier qu'il est marqué comme "Sécurisé" par le système.
- [ ] **Impression PDF :** Imprimer l'ordonnance et vérifier l'affichage des médicaments.

---

## 6. IA n°2 & 3 : Facturation & Assistant Ollama (`facture.py`)
👤 **Profil à utiliser :** *Secrétaire / Médecin*

- [ ] **Génération Automatique :** Depuis la consultation, cliquer sur le bouton de création de facture.
- [ ] **Moteur de Calcul (Tiers Payant, CNAM, Assurances) :** 
  - [ ] *Test 1 :* Patient sans couverture = Le montant "Payé par le patient" correspond au total.
  - [ ] *Test 2 :* Patient CNAM (Tiers Payant) = Le montant total doit se diviser automatiquement entre "Montant CNAM" et "Ticket modérateur patient".
  - [ ] *Test 3 :* Patient APCI = Facturation CNAM à 100%, 0 pour le patient.
- [ ] **Détection d'Anomalies (IA n°2) & Ollama (IA n°3) :**
  - [ ] *Doublon :* Tenter de facturer deux fois le même patient le même jour. Vérifier l'apparition de l'alerte LLM générée par Ollama (`✨ [IA Assistant] : ...`).
  - [x] *APCI incomplet (Anomalie 3) :* Essayer de facturer un patient coché APCI sans N° de décision. ✅ **Validé** : message IA Ollama affiché en ~3-4s.

---

## 7. Gestion CNAM et Bordereaux (`bordereau.py`)
👤 **Profil à utiliser :** *Secrétaire*

- [ ] **Création Bordereau M5 :** Créer un bordereau CNAM.
- [ ] **Récupération des Factures :** Importer les factures du mois (vérifier que seules les factures en Tiers-Payant ou APCI montent dans le bordereau, et non celles des patients privés purs).
- [ ] **Validation :** Valider le bordereau (Génération du format M5).

---

## 8. IA n°4 : Tableau de Bord Intelligent (Claude API)
👤 **Profil à utiliser :** *Médecin*

- [ ] **Score de Santé :** Vérifier que l'indice de santé global se calcule (chiffre sur 100 avec couleur).
- [ ] **Analyse Médicale :** Vérifier que le nombre d'alertes "Allergies bloquées" est correct (s'il y en a eu dans le mois).
- [ ] **Génération Claude :** 
  - [ ] S'assurer que le rapport de Claude s'affiche bien en bas de page.
  - [ ] Vérifier que Claude mentionne vos *vraies* statistiques dans ses recommandations (ex: le vrai montant d'impayés, ou le vrai nombre de consultations).
- [ ] **Mode Secours (Fallback) :** *Optionnel pour le jury* - Couper l'internet ou enlever la clé API de Claude et rafraîchir le dashboard. Le système local de secours Python doit s'activer et afficher quand même des stats basiques sans crasher.

---

## 9. Sécurité et Rôles (`security.xml`)
👤 **Profil à utiliser :** *Tests Croisés*

- [ ] **Test Secrétaire :** Connectez-vous en secrétaire et vérifier qu'elle n'a pas accès au menu "Configuration" (ni à la définition des actes médicaux ou à la clé API).
- [ ] **Test Patient (Portail Odoo) :** Connectez-vous avec l'email d'un patient et vérifiez son espace portail (mes rendez-vous, mes ordonnances).
