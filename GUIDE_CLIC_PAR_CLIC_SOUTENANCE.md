# 🏆 SCÉNARIO DE SOUTENANCE CLIC-PAR-CLIC & GUIDE PAS-À-PAS
## ⏱️ Durée Totale : 15 à 20 min • Guide Ultra-Précis (Que Cliquer + Que Dire au Jury)

> **Mode d'emploi le jour J :**  
> Suivez ce guide ligne par ligne. Chaque étape vous indique **exactement où cliquer avec la souris** (`🖱️ ACTION`) et **ce que vous devez dire à voix haute devant le jury** (`🎙️ VOUS DITES`).

---

## 🧭 TABLEAU DE PRÉPARATION (AVANT D'ENTRER DEVANT LE JURY)

Ouvrez **Google Chrome** avec ces **5 onglets ouverts en plein écran** :
1. **Onglet 1 - Odoo 17** : `http://192.168.33.10:8069`
2. **Onglet 2 - Jenkins CI/CD** : `http://192.168.33.10:8080/job/cabinet-medical-pipeline/`
3. **Onglet 3 - SonarQube** : `http://192.168.33.10:9000/dashboard?id=cabinet-medical-odoo17`
4. **Onglet 4 - Nexus Registry** : `http://192.168.33.10:8081/#browse/browse:docker-repo`
5. **Onglet 5 - Grafana Monitoring** : `http://192.168.33.10:3000`

---

# 🎬 DÉBUT DE LA SOUTENANCE (00:00 - 20:00)

---

## 📞 ACTE 1 : L'APPEL TÉLÉPHONIQUE DU PATIENT & LE SECRÉTARIAT (00:00 - 04:00)

### 🔹 Étape 1.1 : Connexion au Secrétariat
- 🖱️ **ACTION :**
  1. Allez sur **l'Onglet 1 (Odoo)**.
  2. Sur l'écran de connexion personnalisé, saisissez :
     - Identifiant : `secretaire`
     - Mot de passe : `secretaire123`
  3. Cliquez sur **Se connecter** (*Log in*).
- 🎙️ **VOUS DITES AU JURY :**
  > *"Bonjour Monsieur le Président, honorables membres du jury. Nous débutons notre démonstration au secrétariat médical lors de l'appel téléphonique d'un patient. Comme vous le constatez, l'interface Odoo a été totalement personnalisée : le menu principal a été épuré pour n'exposer à la secrétaire que la gestion administrative et les plannings, sans jamais divulguer les données médicales."*

---

### 🔹 Étape 1.2 : Importation massive de patients avec contrôle strict
- 🖱️ **ACTION :**
  1. Dans le menu du haut, cliquez sur **Cabinet Médical** > **Patients**.
  2. Cliquez sur le bouton en haut à gauche **"Importer Patients (Excel)"**.
  3. *(Montrez la fenêtre modale)* Montrez les options de contrôle puis cliquez sur **Annuler** ou chargez un fichier exemple.
- 🎙️ **VOUS DITES AU JURY :**
  > *"Pour intégrer rapidement les dossiers de santé, nous avons développé un wizard d'importation Excel (`wizard_import_patients.py`). Il vérifie rigoureusement les formats tunisiens : la CIN à 8 chiffres, le matricule CNAM à 10 chiffres et le téléphone. Chaque ligne est protégée par un `SAVEPOINT` PostgreSQL pour qu'une faute de frappe n'interrompe jamais l'import global."*

---

### 🔹 Étape 1.3 : Prise de RDV au téléphone & IA n°1 (Machine Learning No-Show)
- 🖱️ **ACTION :**
  1. Dans le menu, cliquez sur **Agenda / Rendez-vous** (ou **Rendez-vous**).
  2. Cliquez sur le bouton **Créer** (ou *Nouveau*).
  3. Dans le champ **Patient**, sélectionnez : `Mohamed Ben Salem` (ou tapez un nom de patient existant).
  4. **Démonstration ML Cas 1 (Risque Élevé)** :
     - Modifiez la **Date du rendez-vous** pour la fixer dans **25 jours** à l'avance.
     - 👁️ *Montrez le bandeau d'alerte qui apparaît automatiquement sous le formulaire* :  
       🔴 **"Risque de No-Show Élevé (58%) - Raison : Délai de réservation lointain"**.
  5. **Démonstration ML Cas 2 (Urgence - Risque Faible)** :
     - Cochez la case **"Consultation d'urgence"**.
     - 👁️ *Montrez le bandeau qui se recalcule instantanément en vert* :  
       🟢 **"Risque de No-Show Faible (3.2%) - Raison : Urgence médicale"**.
  6. Décochez l'urgence, remettez la date à **Aujourd'hui** et cliquez sur le bouton **Enregistrer**.
- 🎙️ **VOUS DITES AU JURY :**
  > *"Lors de la fixation du rendez-vous téléphonique, notre **première IA entre en action : un modèle de Machine Learning Random Forest** (`ml_no_show.py`), entraîné sur 1 500 dossiers cliniques. En évaluant 7 variables comme le délai de prise de RDV, le statut d'urgence et les antécédents, l'IA calcule instantanément la probabilité que le patient ne vienne pas ('No-Show'). Cela permet à la secrétaire de déclencher des rappels ciblés ou d'optimiser l'agenda."*

---

### 🔹 Étape 1.4 : IA n°3 (Assistant LLM Local Ollama/Phi-3 pour les Droits CNAM)
- 🖱️ **ACTION :**
  1. Allez dans **Cabinet Médical** > **Patients**.
  2. Cliquez sur la fiche du patient (qui a une carte CNAM expirée).
  3. Montrez le bandeau d'alerte orange en haut de la fiche du patient et cliquez sur le bouton **"Conseil Assistant IA"** (ou sur l'alerte).
  4. 👁️ *Montrez la notification popup qui s'affiche en haut à droite avec le texte reformulé :*  
     ✨ **[IA Assistant]** : *"La carte CNAM du patient est échue depuis 42 jours. Veuillez solliciter le document de renouvellement..."*
- 🎙️ **VOUS DITES AU JURY :**
  > *"Ici intervient notre **troisième IA : un LLM souverain local (Phi-3 sous Ollama)** (`facture.py`). Il analyse les dates de validité CNAM et APCI et génère une recommandation d'action claire pour la secrétaire, en local sur le serveur, garantissant qu'aucune donnée de santé ne fuite sur Internet."*

---

## 🩺 ACTE 2 : ARRIVÉE DU PATIENT & CONSULTATION MÉDICALE (04:00 - 07:00)

### 🔹 Étape 2.1 : Validation de la présence en salle d'attente
- 🖱️ **ACTION :**
  1. Retournez dans **Rendez-vous**.
  2. Ouvrez le rendez-vous d'aujourd'hui.
  3. Cliquez sur le bouton en haut **"Patient Arrivé"** (le statut passe en vert : `Présent`).
  4. Déconnectez-vous en cliquant sur l'avatar en haut à droite > **Déconnexion** (*Log out*).
- 🎙️ **VOUS DITES AU JURY :**
  > *"Le patient arrive au cabinet. La secrétaire clique sur 'Patient Arrivé', ce qui l'insère automatiquement dans la file d'attente active du médecin. Déconnectons-nous pour passer côté docteur."*

---

### 🔹 Étape 2.2 : Prise en charge par le Médecin & Secret Médical
- 🖱️ **ACTION :**
  1. Sur la page de connexion, connectez-vous en tant que Médecin :
     - Identifiant : `oumaima.hajji@esprit.tn` (ou `admin`)
     - Mot de passe : `medecin123` (ou `admin`)
  2. Cliquez sur **Cabinet Médical** > **Rendez-vous du jour** (ou **Consultations**).
  3. Cliquez sur le rendez-vous de `Mohamed Ben Salem` (Statut : `Présent`).
  4. Cliquez sur le bouton en haut **"Démarrer la consultation"**.
  5. 👁️ *Montrez les onglets médicaux confidentiels* :
     - Renseignez un diagnostic : `Infection respiratoire aiguë`.
     - Renseignez les constantes : Tension `13/8`, Température `38.5°C`.
  6. Dans l'onglet **Actes Médicaux**, cliquez sur **Ajouter une ligne** :
     - Sélectionnez : `Consultation Spécialiste` (Code `C01`, Montant `30 DT`, Prise en charge CNAM `70%`).
- 🎙️ **VOUS DITES AU JURY :**
  > *"Le médecin démarre la séance. En vertu des règles de sécurité RBAC définies dans `security.xml`, l'ensemble du dossier clinique, les antécédents et les constantes vitales sont réservés au médecin. Après examen, le médecin saisit l'acte médical conventionné à 30 DT. Nous passons alors à la prescription médicamenteuse."*

---

## 🤖 ACTE 3 : PRESCRIPTION SÉCURISÉE PAR L'IA n°2 HYBRIDE (07:00 - 11:00)

### 🔹 Étape 3.1 : Détection d'Allergie par l'Ontologie Pharmaceutique BDPM
- 🖱️ **ACTION :**
  1. Dans la consultation, cliquez sur le bouton **"Créer une Ordonnance"** (ou allez dans l'onglet Ordonnance).
  2. 👁️ *Montrez l'antécédent affiché en haut* : `Allergie connue : Pénicilline` | `Traitement en cours : Spironolactone`.
  3. **Test Ontologie BDPM** :
     - Dans le tableau des médicaments, cliquez sur **Ajouter une ligne**.
     - Sélectionnez ou tapez : `Amoxicilline 1g` (Posologie : 1 comprimé 2 fois par jour).
     - Cliquez sur le bouton violet avec l'icône robot : **"🤖 Vérifier avec l'IA"**.
     - 👁️ *Montrez le grand bandeau rouge d'alerte critique* :  
       🔴 **"Risque allergique majeur : Amoxicilline appartient à la famille des Pénicillines !"**
- 🎙️ **VOUS DITES AU JURY :**
  > *"Voici le cœur clinique de notre système : **l'IA Hybride de Sécurisation Thérapeutique** (`prescription.py`). Le patient est allergique à la Pénicilline, mais le médecin a saisi 'Amoxicilline'. Grâce à notre **Ontologie pharmaceutique BDPM locale** (`CIS_bdpm.txt`) de 15 000 médicaments, l'IA fait immédiatement le lien de parenté chimique et bloque la prescription."*

---

### 🔹 Étape 3.2 : Tolérance aux fautes de frappe (Fuzzy Matching 82%)
- 🖱️ **ACTION :**
  1. Modifiez le nom du médicament avec une faute d'orthographe : tapez `Augmantin` (avec un 'a') ou `Pénécilline`.
  2. Cliquez sur **"🤖 Vérifier avec l'IA"**.
  3. 👁️ *Montrez que l'alerte rouge persiste* : le système intercepte la faute de frappe.
- 🎙️ **VOUS DITES AU JURY :**
  > *"Même si le praticien commet une faute de frappe dans la précipitation, notre algorithme de **Fuzzy Matching** (`SequenceMatcher` avec seuil à 82%) rattrape l'erreur phonétique et maintient la sécurité."*

---

### 🔹 Étape 3.3 : Détection d'Interaction Médicamenteuse Sévère (Type B)
- 🖱️ **ACTION :**
  1. Supprimez la ligne d'antibiotique (icône poubelle).
  2. Ajoutez une ligne : `Ramipril 5mg` (médicament pour la tension).
  3. Cliquez sur **"🤖 Vérifier avec l'IA"**.
  4. 👁️ *Montrez l'alerte d'interaction orange/rouge* :  
     🟠 **"Interaction Médicamenteuse Sévère : Association Spironolactone (traitement en cours) + Ramipril (IEC) ➔ Risque vital d'hyperkaliémie."**
- 🎙️ **VOUS DITES AU JURY :**
  > *"L'IA croise également l'ordonnance avec l'historique des traitements en cours du patient. Elle détecte ici une interaction pharmacologique majeure entre le diurétique du patient et l'IEC prescrit, évitant un accident cardiaque grave."*

---

### 🔹 Étape 3.4 : Validation Thérapeutique Safe & Signature Immuable
- 🖱️ **ACTION :**
  1. Supprimez la ligne à risque et ajoutez un traitement sûr :
     - Ligne 1 : `Paracétamol 1g`
     - Ligne 2 : `Azithromycine 500mg` (Macrolide toléré)
  2. Cliquez sur **"🤖 Vérifier avec l'IA"**.
  3. 👁️ *Montrez le bandeau vert qui s'affiche* :  
     🟢 **"Prescription validée : Aucun conflit allergique ni interaction détectée."**
  4. Cliquez sur **"Signer et Verrouiller l'Ordonnance"**.
  5. 👁️ *Montrez au jury que le statut passe à 'Signé' et qu'il est désormais impossible d'ajouter ou supprimer une ligne.*
  6. Cliquez sur le fil d'Ariane pour revenir à la consultation et cliquez sur **"Terminer la consultation"**.
- 🎙️ **VOUS DITES AU JURY :**
  > *"Avec des molécules compatibles, l'IA valide la prescription en vert. Le médecin signe l'ordonnance qui devient strictement immuable et infalsifiable. Nous clôturons la séance médicale."*

---

## 💰 ACTE 4 : FACTURATION CNAM & TÉLÉTRANSMISSION BORDEREAU M5 (11:00 - 14:00)

### 🔹 Étape 4.1 : Génération et Ventilation Automatique de la Facture
- 🖱️ **ACTION :**
  1. Depuis la consultation terminée, cliquez sur le bouton **"Générer la Facture"**.
  2. 👁️ *Montrez la ventilation financière calculée automatiquement :*
     - **Scénario CNAM :** `CNAM Tiers-Payant (Filière Privée)`
     - **Montant Total :** `30.000 DT`
     - **Part Prise en Charge CNAM (70%) :** `21.000 DT`
     - **Ticket Modérateur Patient (30%) :** `9.000 DT`
  3. Cliquez sur le bouton **"Valider la Facture"**.
- 🎙️ **VOUS DITES AU JURY :**
  > *"Le moteur de facturation (`facture.py`) prend le relais. Il gère les 8 scénarios de la réglementation tunisienne (Filière privée, Remboursement, APCI 100%, Mutuelles). Ici, la ventilation conventionnelle est instantanée : 21 DT pris en charge par la CNAM et 9 DT réglés sur place par le patient."*

---

### 🔹 Étape 4.2 : Impression des Formulaires Légaux Officiels
- 🖱️ **ACTION :**
  1. En haut de la facture, cliquez sur le menu **Imprimer** :
     - Cliquez sur **Bulletin de Soins BS1 CNAM** (le PDF s'ouvre avec le cerfa officiel).
     - Cliquez sur **Ordonnance Médicale Sécurisée** (PDF avec en-tête et code-barres).
     - Cliquez sur **Reçu de Paiement / Facture**.
- 🎙️ **VOUS DITES AU JURY :**
  > *"L'application édite automatiquement l'ensemble des documents légaux conformes aux exigences de l'Ordre des Médecins et de la CNAM : le bulletin de soins BS1 rempli, l'ordonnance sécurisée et la quittance de paiement."*

---

### 🔹 Étape 4.3 : Télétransmission Mensuelle (Bordereau Récapitulatif M5)
- 🖱️ **ACTION :**
  1. Allez dans le menu **Cabinet Médical** > **CNAM** > **Bordereaux**.
  2. Cliquez sur **Créer**.
  3. Sélectionnez le mois en cours et cliquez sur le bouton **"Récupérer les factures du mois"**.
  4. Cliquez sur **Valider** > **Imprimer le Bordereau M5**.
  5. 👁️ *Montrez le PDF du Bordereau M5 avec la liste des créances et le total dû par la CNAM.*
- 🎙️ **VOUS DITES AU JURY :**
  > *"En fin de mois, le module de télétransmission (`bordereau.py`) regroupe toutes les créances dans le **Bordereau Officiel M5**, verrouille les factures pour empêcher les doublons et prépare le dossier de remboursement pour la caisse de sécurité sociale."*

---

## 🌐 ACTE 5 : PORTAIL PATIENT WEB RÉACTIF & CYBERSÉCURITÉ OWASP (14:00 - 16:00)

### 🔹 Étape 5.1 : Connexion au Portail Patient
- 🖱️ **ACTION :**
  1. Ouvrez une **nouvelle fenêtre de navigation privée** (ou un nouvel onglet) :
     - URL : `http://192.168.33.10:8069/my`
  2. Connectez-vous avec le compte du patient :
     - Identifiant : `mohamed.bensalem@gmail.com`
     - Mot de passe : `patient123`
  3. 👁️ *Montrez le portail patient :*
     - Cliquez sur **Mes Rendez-vous** : le patient voit son RDV d'aujourd'hui terminé.
     - Cliquez sur **Mes Ordonnances** : le patient clique sur **Télécharger PDF** pour récupérer son ordonnance sécurisée signée.
- 🎙️ **VOUS DITES AU JURY :**
  > *"Le patient dispose de son propre portail web réactif (`portal.py`). Il peut télécharger ses ordonnances et suivre ses rendez-vous depuis son smartphone ou son ordinateur.*
  >
  > *Sur le plan de la cybersécurité, notre système respecte les normes **OWASP** :*
  > - *Des **Record Rules PostgreSQL** (`portal_security.xml`) filtrent directement les requêtes SQL en base de données : un patient ne peut techniquement jamais voir les dossiers d'un autre patient.*
  > - *Les jetons de session sont détruits à chaque modification sensible pour contrer le Session Hijacking."*

---

## 🚀 ACTE 6 : IA n°4 DASHBOARD CLAUDE & L'USINE LOGICIELLE DEVOPS (16:00 - 19:00)

### 🔹 Étape 6.1 : IA n°4 - Tableau de Bord Décisionnel Exécutif (Claude 3.5 Haiku)
- 🖱️ **ACTION :**
  1. Revenez sur **l'Onglet 1 (Odoo)** sur le compte Médecin.
  2. Allez dans **Cabinet Médical** > **Tableau de Bord IA**.
  3. 👁️ *Montrez les graphiques interactifs Chart.js (Répartition des pathologies, No-Show, Recouvrement CNAM).*
  4. 👁️ *Descendez en bas de page et montrez le bloc :*  
     **"Synthèse Décisionnelle de l'Assistant Claude"**.
- 🎙️ **VOUS DITES AU JURY :**
  > *"Voici notre **quatrième IA : le Tableau de Bord Décisionnel** développé en JavaScript OWL (`ai_dashboard.js`) et Chart.js. Côté serveur, la méthode `get_ai_insights()` agrège les statistiques réelles et interroge l'API **Anthropic Claude 3.5 Haiku** pour fournir au médecin une analyse financière et clinique complète, avec un mécanisme de secours local Python en cas de coupure Internet."*

---

### 🔹 Étape 6.2 : Démonstration du Pipeline Jenkins CI/CD (100% Vert)
- 🖱️ **ACTION :**
  1. Basculez sur **l'Onglet 2 (Jenkins)** (`http://192.168.33.10:8080`).
  2. Montrez la **Stage View avec les 9 étapes vertes** :
     - Stage 1 : `Checkout SCM` (GitHub)
     - Stage 2 : `Install Dependencies` (Venv IA)
     - Stage 3 : `Unit Tests` (**102 tests unitaires réussis à 100%**)
     - Stage 4 : `SonarQube Analysis`
     - Stage 5 : `Quality Gate` (Passé via API REST)
     - Stage 6 : `Docker Build`
     - Stage 7 : `Push to Nexus`
     - Stage 8 : `Deploy Application`
     - Stage 9 : `Health Check` (HTTP 303 validé)
- 🎙️ **VOUS DITES AU JURY :**
  > *"Pour garantir la haute disponibilité et la qualité de ce système médical critique, nous avons mis en place une usine logicielle CI/CD complète sur Jenkins.*
  >
  > *À chaque commit, la suite de **102 tests unitaires** (`run_unit_tests.py`) est exécutée en 25 secondes pour valider mathématiquement l'ontologie BDPM, les règles d'interactions et le modèle No-Show avant tout déploiement."*

---

### 🔹 Étape 6.3 : SonarQube, Nexus et Monitoring Grafana
- 🖱️ **ACTION :**
  1. Basculez sur **l'Onglet 3 (SonarQube)** :
     - Montrez le statut **Quality Gate : PASSED**.
     - Montrez **Security : Note A (0 Vulnérabilité)**.
     - Montrez **Reliability : Note C (2 points identifiés)**.
  2. Basculez sur **l'Onglet 4 (Nexus)** :
     - Montrez dans `docker-repo` la présence de l'image de conteneur d'entreprise `cabinet-medical-odoo:17.0.X`.
  3. Basculez sur **l'Onglet 5 (Grafana)** :
     - Montrez les jauges de charge serveur (CPU, RAM, Uptime) collectées par Prometheus.
- 🎙️ **VOUS DITES AU JURY :**
  > *"Sur **SonarQube**, le Quality Gate est franchi avec une **Note A en sécurité (0 faille)** garantissant la protection des données de santé, et 2 points d'amélioration en fiabilité qui guident notre refactorisation continue.*
  >
  > *L'application est empaquetée dans une image Docker d'entreprise sur notre registre privé **Nexus** (port 8083), puis déployée sans interruption de service sous la surveillance en temps réel du couple **Prometheus & Grafana**."*

---

## 🎯 CONCLUSION DE LA SOUTENANCE (19:00 - 20:00)

- 🎙️ **VOUS DITES AU JURY :**
  > *"Pour conclure, ce projet de fin d'études apporte une réponse industrielle et innovante aux défis de la santé numérique :*
  > 1. **Un métier médical tunisien modélisé avec exactitude** (CNAM, 8 scénarios de facturation, bordereaux M5, RBAC).
  > 2. **Une ingénierie IA hybride à 4 niveaux** (Machine Learning No-Show, Ontologie locale BDPM, LLM local Phi-3 et synthèse Claude).
  > 3. **Une chaîne DevOps moderne et sécurisée** (Jenkins, SonarQube, Docker, Nexus, Grafana et conformité OWASP).
  >
  > *Je vous remercie pour votre attention et je suis ravie de répondre à vos questions."*

---

## 💡 ANTI-SÈCHE EXPRESS : RÉPONSES AUX 4 QUESTIONS DU JURY

| Question probable du Jury | Votre réponse percutante |
| :--- | :--- |
| **"Et si la connexion Internet est coupée au cabinet ?"** | *"L'ontologie BDPM, le Fuzzy Matching, le modèle ML No-Show et la facturation tournent **100% en local** sur le serveur. Le cabinet reste totalement autonome sans Internet."* |
| **"Pourquoi la Note C en fiabilité sur SonarQube ?"** | *"Le Quality Gate est validé et la sécurité est irréprochable (Note A, 0 faille). SonarQube a identifié 2 détails mineurs de typage dans le code Python, ce qui prouve la précision de notre analyse statique et constitue notre backlog pour la version 2.0."* |
| **"Pourquoi avoir combiné Ontologie BDPM et NLP Transformer ?"** | *"L'ontologie garantit un risque zéro absolu sur les molécules répertoriées, tandis que le NLP et le Fuzzy gèrent le langage naturel et les fautes de frappe des médecins."* |
| **"Comment garantissez-vous le secret médical entre patients sur le portail ?"** | *"Par des Record Rules PostgreSQL (`portal_security.xml`) appliquées au niveau de la requête SQL. Un patient ne peut techniquement requêter que son propre identifiant `user_id`."* |
