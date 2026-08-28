"# Référentiel Exhaustif des Fonctionnalités Réelles — Module `cabinet_medical`

Ce document dresse l'inventaire complet et exhaustif de toutes les fonctionnalités réellement implémentées dans le code du module `cabinet_medical`, avec l'indication exacte des fichiers et des numéros de lignes pour faciliter la phase de tests d'assurance qualité avant mise en production.

---

## 1. MODÈLES DE DONNÉES (models/*.py)

### 1.1 Modèle Acte Médical (`cabinet.acte`)
*   **Fichier :** `[acte.py](file:///c:/odoo%20-%20Copie/custom_addons/cabinet_medical/models/acte.py)`
*   **Champs :**
    *   `consultation_id` (Many2one vers `cabinet.consultation`) : Consultation parente liée (L.13).
    *   `patient_id` (Many2one related vers `patient_id` de la consultation) : Patient recevant l'acte, en lecture seule (L.14).
    *   `invoice_id` (Many2one vers `cabinet.facture`) : Facture associée à cet acte (L.15).
    *   `currency_id` (Many2one related) : Devise héritée de la consultation ou valeur par défaut TND (L.16-18, L.43-47).
    *   `parametrage_id` (Many2one vers `cabinet.acte.parametrage`) : Liaison vers le référentiel de tarification conventionné (L.21).
    *   `type_acte` (Selection) : Type d'acte technique ou clinique (L.24-36).
    *   `description` (Text) : Description textuelle libre de l'acte (L.38).
    *   `date_acte` (Datetime) : Date de réalisation (L.39).
    *   `code_acte` (Char) : Code CNAM associé pour remboursement (L.42).
    *   `montant` (Monetary) : Tarif de base appliqué au cabinet (L.48-52).
    *   `total_acte_dt` (Monetary calculé) : Part finale à payer par le patient (ticket modérateur) (L.53-58).
    *   `state` (Selection) : État de l'acte (`draft` = Brouillon, `done` = Validé) (L.61-64).
*   **Méthodes, Boutons et Contraintes :**
    *   `_onchange_parametrage_id` (L.66-74) : Rplit automatiquement `type_acte`, `description`, `code_acte` et `montant` à partir des valeurs définies dans le référentiel CNAM paramétré.
    *   `_compu
<truncated 46485 bytes>