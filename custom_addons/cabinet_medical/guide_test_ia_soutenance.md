# 🤖 Guide de Test des Intelligences Artificielles (Soutenance)

Ce document décrit pas à pas comment faire la démonstration des 4 niveaux d'Intelligence Artificielle intégrés dans votre projet Odoo lors de votre soutenance.

---

## 🟢 IA n°1 : Intelligence Clinique (Détection des Allergies)
**Objectif :** Prouver que l'IA analyse le texte libre des antécédents médicaux et le croise avec une ontologie de médicaments pour protéger la santé du patient.

### Étapes de démonstration :
1. Allez dans le menu **Patients** et ouvrez le dossier d'un patient (ex: Jean Dupont).
2. Dans le champ **Allergies** (texte libre), écrivez : *"Le patient signale faire de graves réactions allergiques à la pénicilline."*
3. Sauvegardez le patient et allez dans **Consultations**.
4. Créez une nouvelle consultation pour ce patient.
5. Allez dans l'onglet **Ordonnance** (ou cliquez sur Créer une ordonnance).
6. Ajoutez une ligne de médicament et sélectionnez *"Augmentin"* (qui contient de la pénicilline) ou *"Amoxicilline"*.
7. **Résultat :** Au moment de l'ajout, le système bloquera ou affichera une **Alerte Rouge** générée par l'IA (hybride NLP/Ontologie) indiquant un risque allergique majeur.

---

## 🟡 IA n°2 & n°3 : Anomalies de Facturation & Assistant Local Ollama
**Objectif :** Montrer le système expert (IA n°2) qui détecte les fraudes/erreurs, couplé à un grand modèle de langage LLM (IA n°3 - Mistral via Ollama) exécuté localement pour reformuler l'alerte.

### Prérequis avant la soutenance :
- Assurez-vous que l'application **Ollama** tourne sur votre ordinateur en arrière-plan avec le modèle Mistral (commande : `ollama run mistral`).

### Étapes de démonstration :
1. Allez dans **Consultations** ou **Patients** et générez une **Facture** pour un patient à la date d'aujourd'hui. Validez la facture.
2. Revenez sur le patient et tentez de créer une **deuxième facture** pour lui à la même date (simulation d'une erreur de la secrétaire ou d'un doublon de facturation CNAM).
3. Cliquez sur **Sauvegarder** ou **Valider**.
4. **Résultat :** Le système va charger brièvement. L'IA n°2 détecte le doublon. L'IA n°3 (Ollama) prend le relais et génère une belle fenêtre d'avertissement commençant par :
   > *"🤖 [IA Assistant] : Attention, une facture a déjà été émise pour ce patient aujourd'hui. Souhaitez-vous vraiment créer un doublon ?"*

---

## 🔵 IA n°4 : Pilotage Stratégique du Cabinet (Tableau de Bord Claude)
**Objectif :** Démontrer comment une IA Cloud de haut niveau (Claude d'Anthropic) ingère les données brutes de gestion et de santé pour conseiller le médecin.

### Étapes de démonstration :
1. Connectez-vous avec le compte **Médecin**.
2. Cliquez sur le menu principal **Tableau de Bord**.
3. **Résultat immédiat :** Un écran de chargement affiche *"Analyse intelligente de l'activité en cours..."*.
4. **Mettez en valeur devant le jury :**
   - **L'Indice de Santé (sur 100)** : Montrez comment il synthétise le financier et le médical.
   - **L'Intelligence Clinique (IA)** : Pointez le compteur *"Alertes Allergies bloquées"*. Si vous avez fait le Test n°1 juste avant, le compteur affichera **1** !
   - **Analyse IA Globale** : Lisez les recommandations générées par Claude au bas de la page. Montrez au jury que Claude justifie ses conseils avec vos *vraies* données (ex: "Vu qu'il y a 24 DT d'impayés, nous recommandons des relances").
   - **Prévisions (Mois prochain)** : Montrez l'estimation de l'affluence future et son *Niveau de confiance*.

---

*Bonne chance pour votre soutenance, votre intégration de l'IA est techniquement très riche et cohérente avec les besoins d'un cabinet médical moderne !*
