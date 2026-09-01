# 🏆 SCÉNARIO DE SOUTENANCE CLIC-PAR-CLIC & GUIDE PAS-À-PAS
## ⏱️ Durée Totale : 15 à 20 min • Guide Ultra-Précis (Que Cliquer + Que Dire au Jury)

> **Mode d'emploi le jour J :**  
> Suivez ce guide ligne par ligne. Chaque étape vous indique **exactement où cliquer avec la souris** (`🖱️ ACTION`) et **ce que vous devez dire à voix haute devant le jury** (`🎙️ VOUS DITES`). 
> Les encadrés **📝 DONNÉES DE TEST** vous indiquent exactement quoi taper.

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

## 👩‍💼 ACTE 1 : LE SECRÉTARIAT & L'ADMINISTRATION PATIENT (00:00 - 05:00)

### 🔹 Étape 1.1 : Connexion & Tour d'Horizon des Assurances
- 🖱️ **ACTION :**
  1. Allez sur **l'Onglet 1 (Odoo)**. Connectez-vous avec :
     > **📝 DONNÉES DE TEST** :
     > Identifiant : `secretaire`
     > Mot de passe : `secretaire123`
  2. Cliquez sur le menu **Assurances / Mutuelles**.
  3. 👁️ *Survolez la liste des conventions sans rien modifier (montrez les pourcentages de prise en charge).*
- 🎙️ **VOUS DITES AU JURY :**
  > *"Bonjour à tous. Notre démonstration commence au secrétariat du cabinet. Conformément aux règles de sécurité RBAC, la secrétaire a un accès restreint à son cœur de métier : la gestion administrative. C'est elle, par exemple, qui configure le répertoire des Assurances et Mutuelles, permettant au cabinet de s'adapter à n'importe quelle convention tarifaire sans toucher au code."*

### 🔹 Étape 1.2 : Prise de RDV au téléphone & IA n°1 (Machine Learning No-Show)
- 🖱️ **ACTION :**
  1. Cliquez sur le menu **Patients**, puis sur le bouton **Importer Patients (Excel)** pour montrer rapidement qu'on peut ingérer massivement des données avec contrôle strict (CIN/CNAM). Cliquez sur **Annuler**.
  2. Dans le menu, cliquez sur **Agenda / Rendez-vous**. Cliquez sur **Créer**.
  3. Dans le champ **Patient**, tapez :
     > **📝 DONNÉES DE TEST** : `Sami Trabelsi`
  4. **Démonstration ML Cas 1 (Risque Élevé)** :
     - Fixez la **Date du rendez-vous** à dans **25 jours**.
     - 👁️ *Montrez le bandeau rouge d'alerte sous le formulaire* :  
       🔴 **"Risque de No-Show Élevé (58%) - Raison : Délai de réservation lointain"**.
  5. **Démonstration ML Cas 2 (Urgence - Risque Faible)** :
     - Cochez la case **"Consultation d'urgence"** (ou ramenez la date à **Aujourd'hui**).
     - 👁️ *Montrez le bandeau qui passe au vert* :  
       🟢 **"Risque de No-Show Faible (3.2%)"**.
  6. Cliquez sur **Enregistrer**.
- 🎙️ **VOUS DITES AU JURY :**
  > *"Un patient appelle pour prendre rendez-vous. C'est ici qu'intervient notre **première IA : un modèle de Machine Learning Random Forest** entraîné sur 1 500 dossiers. En analysant en temps réel le délai du RDV et l'historique du patient, elle calcule instantanément la probabilité d'absence (le 'No-Show'). La secrétaire sait ainsi immédiatement si ce patient nécessite un rappel SMS renforcé."*

### 🔹 Étape 1.3 : IA n°2 (Assistant LLM Local Ollama/Phi-3) & Arrivée
- 🖱️ **ACTION :**
  1. Allez dans **Cabinet Médical** > **Patients**, ouvrez la fiche de `Sami Trabelsi` (qui doit avoir une date CNAM expirée).
  2. Montrez l'alerte orange CNAM et cliquez sur **"Conseil Assistant IA"** (icône d'étincelle).
  3. 👁️ *Montrez la notification popup de l'IA :*  
     ✨ **[IA Assistant]** : *"La carte CNAM du patient est échue. Veuillez inviter le patient à solliciter le document de renouvellement..."*
  4. Retournez dans les rendez-vous d'aujourd'hui, ouvrez celui de Sami, et cliquez sur **"Patient Arrivé"** (statut `Présent`).
  5. **Déconnectez-vous** du compte Secrétaire.
- 🎙️ **VOUS DITES AU JURY :**
  > *"Avant que le patient n'arrive, la secrétaire vérifie son dossier. Notre **deuxième IA** détecte que la carte CNAM est expirée. Il s'agit d'un **LLM souverain local (Phi-3 sous Ollama)**. Il tourne 100% en local sur notre serveur : le secret médical est garanti. Il assiste la secrétaire sur les démarches administratives. Le patient arrive au cabinet, la secrétaire valide sa présence en salle d'attente, et nous passons maintenant côté médical."*

---

## 👨‍⚕️ ACTE 2 : LA CLINIQUE & LE PARAMÉTRAGE MÉDICAL (05:00 - 12:00)

### 🔹 Étape 2.1 : Configuration & Prise en charge par le Médecin
- 🖱️ **ACTION :**
  1. Connectez-vous en tant que Médecin :
     > **📝 DONNÉES DE TEST** :
     > Identifiant : `medecin`
     > Mot de passe : `medecin123`
  2. Allez dans le menu **Configuration**.
  3. 👁️ *Survolez rapidement les sous-menus pour montrer les capacités de gestion du médecin :*
     - **Tarifs CNAM (Actes Médicaux)** : le dictionnaire des actes avec leurs prix.
     - **Paramètres du cabinet** : pour gérer l'envoi d'emails et SMS (SMTP).
     - **✍️ Signature et PIN Médecin** : pour configurer la signature électronique de l'ordonnance.
  4. Allez dans **Mes Rendez-vous**, cliquez sur celui de `Sami Trabelsi` et cliquez sur **"Démarrer la consultation"**.
- 🎙️ **VOUS DITES AU JURY :**
  > *"Le médecin se connecte. Contrairement à la secrétaire, c'est lui qui définit la nomenclature tarifaire des actes médicaux, la configuration globale du cabinet (SMTP/SMS) et sa propre signature électronique, prouvant la robustesse de notre architecture de droits. Il démarre ensuite sa journée et ouvre la consultation du patient en salle d'attente. Lui seul a accès aux données cliniques."*

### 🔹 Étape 2.2 : Constantes, Acte Médical & Wizard de Suivi
- 🖱️ **ACTION :**
  1. Remplissez les données cliniques :
     > **📝 DONNÉES DE TEST** :
     > - **Diagnostic** : `Infection pulmonaire sévère`
     > - **Constantes** : Tension `14/8`, Température `38.5°C`
  2. Dans l'onglet **Actes Médicaux**, ajoutez une ligne : `Consultation Spécialiste` (Prix : 30 DT).
  3. Cliquez sur le bouton en haut **"Planifier un suivi"**.
  4. 👁️ *Montrez le calendrier personnalisé OWL.* Sélectionnez une date libre (ex: dans 15 jours à 09:00), puis cliquez sur **Enregistrer**.
- 🎙️ **VOUS DITES AU JURY :**
  > *"Après l'examen, le médecin saisit son acte médical. Grâce à un composant calendrier Web (OWL) développé sur-mesure, il peut fixer directement le prochain RDV de suivi de son patient sans avoir à solliciter de nouveau le secrétariat."*

### 🔹 Étape 2.3 : Prescription Sécurisée (IA n°3 - Hybride BDPM)
- 🖱️ **ACTION :**
  1. Dans la consultation, allez dans l'onglet **Ordonnance** et cliquez sur **Créer une Ordonnance**.
  2. 👁️ *Faites remarquer l'encadré en haut* : `Allergie : Pénicilline`.
  3. **Test Allergie & Faute de frappe** : Ajoutez la ligne :
     > **📝 DONNÉES DE TEST** : `Pénécilline 1g` (avec une faute volontaire).
  4. Cliquez sur **"🤖 Vérifier avec l'IA"**.
  5. 👁️ *Montrez l'alerte rouge* : 🔴 **"Risque allergique majeur : ... famille des Pénicillines !"**
  6. **Test Valide** : Supprimez la ligne, et ajoutez :
     > **📝 DONNÉES DE TEST** : `Paracétamol 1g` et `Azithromycine 500mg`.
  7. Re-cliquez sur **"🤖 Vérifier avec l'IA"**.
  8. 👁️ *Montrez l'alerte verte* : 🟢 **"Prescription validée"**.
  9. Cliquez sur **"Signer et Verrouiller l'Ordonnance"**. Terminez la consultation.
- 🎙️ **VOUS DITES AU JURY :**
  > *"Pour rédiger l'ordonnance, notre **3ème IA de Sécurisation Thérapeutique** entre en jeu. Le patient est allergique à la Pénicilline. Même si le médecin fait une faute de frappe ('Pénécilline'), l'algorithme de Fuzzy Matching intercepte l'erreur, consulte notre Ontologie Pharmaceutique locale (BDPM) et bloque la prescription. Une fois une molécule sûre prescrite, le médecin signe numériquement l'ordonnance, qui devient immuable."*

### 🔹 Étape 2.4 : L'IA n°4 (Claude 3.5 Haiku) pour le Dashboard
- 🖱️ **ACTION :**
  1. Allez dans le menu **Tableau de Bord IA**.
  2. 👁️ *Montrez les graphiques (Pathologies, No-Show) et la Synthèse Décisionnelle Claude en bas de page.*
  3. **Déconnectez-vous** du compte Médecin.
- 🎙️ **VOUS DITES AU JURY :**
  > *"Avant de finir sa journée, le médecin consulte son Tableau de Bord. Notre **4ème IA** agrège ici la data du cabinet et interroge l'API Anthropic Claude 3.5 pour générer en temps réel une synthèse financière et épidémiologique. Le médecin se déconnecte, laissant la secrétaire finaliser le paiement du patient."*

---

## 💰 ACTE 3 : LA FACTURATION & TÉLÉTRANSMISSION (12:00 - 14:00)

### 🔹 Étape 3.1 : Facture et Formulaires Légaux (Compte Secrétaire)
- 🖱️ **ACTION :**
  1. Reconnectez-vous en tant que **Secrétaire** (`secretaire` / `secretaire123`).
  2. Allez dans **Consultations** (ou Facturation), et ouvrez la consultation terminée de Sami.
  3. Cliquez sur **"Générer la Facture"**.
  4. 👁️ *Montrez la ventilation automatique :* (Total : 30 DT / CNAM : 21 DT / Patient : 9 DT).
  5. Cliquez sur **Valider**.
  6. Cliquez sur le bouton d'impression en haut pour montrer le **Bulletin de Soins BS1 CNAM** (PDF Cerfa) et l'**Ordonnance Médicale** (PDF).
- 🎙️ **VOUS DITES AU JURY :**
  > *"De retour au secrétariat, conformément aux règles RBAC, c'est l'administration qui encaisse. Le moteur de facturation gère automatiquement la ventilation Tiers-Payant (CNAM vs Patient). En un clic, la secrétaire édite les documents légaux conformes : le Cerfa BS1 pour le remboursement et l'ordonnance sécurisée."*

### 🔹 Étape 3.2 : Bordereau de Télétransmission M5
- 🖱️ **ACTION :**
  1. Allez dans le menu **CNAM** > **Bordereaux**.
  2. Cliquez sur **Créer**, puis **"Récupérer les factures du mois"**.
  3. Cliquez sur Imprimer pour générer le **Bordereau M5**.
- 🎙️ **VOUS DITES AU JURY :**
  > *"En fin de mois, le module regroupe toutes les créances de la sécurité sociale dans le Bordereau officiel M5, verrouillant les factures pour empêcher tout doublon de télétransmission."*

---

## 🌐 ACTE 4 : L'EXPÉRIENCE PATIENT & CYBERSÉCURITÉ OWASP (14:00 - 16:00)

### 🔹 Étape 4.1 : Connexion Web du Patient
- 🖱️ **ACTION :**
  1. Ouvrez une **fenêtre de navigation privée**.
  2. Connectez-vous avec le compte du patient :
     > **📝 DONNÉES DE TEST** :
     > Identifiant : `sami.trabelsi@gmail.com`
     > Mot de passe : `patient123`
  3. Cliquez sur **Mes Rendez-vous** et **Mes Ordonnances**. Téléchargez le PDF.
- 🎙️ **VOUS DITES AU JURY :**
  > *"Le patient, de retour chez lui, accède à son espace Web personnel. La cybersécurité est ici au centre de notre conception : nous appliquons les règles **OWASP**. Grâce aux 'Record Rules PostgreSQL', les requêtes SQL sont filtrées directement dans la base de données. Il est mathématiquement impossible pour un patient d'intercepter les données cliniques d'un tiers."*

---

## 🚀 ACTE 5 : L'USINE LOGICIELLE DEVOPS (16:00 - 19:00)

### 🔹 Étape 5.1 : Démonstration de l'Infrastructure Qualité
- 🖱️ **ACTION :**
  1. Passez sur **l'Onglet 2 (Jenkins)**.
     - 👁️ *Montrez les étapes vertes de compilation et la section des **tests unitaires**.*
  2. Passez sur **l'Onglet 3 (SonarQube)**.
     - 👁️ *Montrez le statut "PASSED", la sécurité (Note A).*
  3. Passez sur **l'Onglet 4 (Nexus)** et **l'Onglet 5 (Grafana)**.
- 🎙️ **VOUS DITES AU JURY :**
  > *"Pour garantir la haute disponibilité de ce système de santé critique, tout le code est encadré par une usine logicielle CI/CD.*
  > *Sur Jenkins, plus de 100 tests unitaires valident mathématiquement nos algorithmes d'IA à chaque mise à jour.*
  > *SonarQube audite le code et nous garantit un zéro défaut de sécurité (Note A).*
  > *Enfin, l'application est empaquetée via Nexus et surveillée en temps réel par Grafana. C'est un produit prêt pour la production."*

---

## 🎯 CONCLUSION DE LA SOUTENANCE (19:00 - 20:00)

- 🎙️ **VOUS DITES AU JURY :**
  > *"Pour conclure, ce projet de fin d'études apporte une véritable réponse industrielle à la digitalisation médicale :*
  > 1. **Un workflow métier exhaustif** strictement segmenté (Médecin / Secrétariat).
  > 2. **Une approche IA pionnière à 4 strates** : Prédictive (No-Show), Générative (Phi-3 / Claude), et Hybride experte (Ontologie BDPM).
  > 3. **Un socle cloud-native** infaillible reposant sur les meilleures pratiques DevSecOps.
  >
  > *Je vous remercie pour votre attention et serai ravi(e) de répondre à vos questions."*
