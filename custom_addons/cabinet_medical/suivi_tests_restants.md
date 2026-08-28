# 📋 Suivi des Tests Restants & Validation IA

## 6. IA n°2 & 3 : Facturation & Assistant Ollama (`facture.py`)

- [x] **Anomalie 3 (APCI sans décision) :**
  - **Statut :** ✅ Testée et validée dans l'interface Odoo (Secrétaire → Générer Facture sur patient APCI sans numéro de décision).
  - **Résultat :** Le message reformulé par l'Assistant LLM s'affiche avec le préfixe `✨ [IA Assistant] :` en **~3-4 secondes** sans coupure.
  - **🐛 Bug trouvé et corrigé :** 
    - *Problème :* Le timeout LLM était trop court (connect 0.3s / read 5s) et le modèle Phi-3 était déchargé de la mémoire VRAM par Ollama après 5 minutes d'inactivité (temps de chargement à froid 6-8s > timeout, entraînant un fallback silencieux sur le message par défaut).
    - *Correction :* Modèle préchargé et verrouillé en VRAM avec `keep_alive: -1`, timeouts ajustés (`connect: 1.5s`, `read: 10.0s`), `num_predict` augmenté à `70` avec consigne de phrase complète terminée par un point, et préfixe Unicode `✨ [IA Assistant] :` compatible multi-plateformes.

- [x] **Nettoyage du code :**
  - Les contraintes obsolètes `_check_doublon_facture()` (Anomalie 1) et `_check_taux_apci()` (Anomalie 2) ont été retirées du fichier [facture.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/facture.py) pour ne conserver que la règle active en production : **Anomalie 3 (`_check_apci_decision`)**.

---

## 7. Assistant IA : Conseils d'expiration On-Demand (`patient.py`)

- [x] **Boutons "✨ Conseil IA" sur la fiche Patient :**
  - **Bandeau principal (haut de fiche) :** Alerte visible immédiatement avant les onglets si CNAM ou APCI est expiré, avec bouton `action_ia_conseil_global()` fournissant le conseil IA adapté (contexte ultra-détaillé : jours CNAM, jours APCI, filière, régime, pathologie et numéro de décision).
  - **Bandeau CNAM expiré (onglet CNAM) :** Bouton `action_ia_conseil_cnam()` avec calcul des jours de retard sur `date_validite_cnam`.
  - **Bandeau APCI expiré (onglet CNAM) :** Bouton `action_ia_conseil_apci()` avec calcul des jours de retard sur `date_fin_apci` et pathologie associée.
  - **Performance :** 100% On-Demand au clic (0 latence à l'ouverture de la fiche patient).
