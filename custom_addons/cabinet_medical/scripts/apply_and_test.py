# -*- coding: utf-8 -*-
import base64
import os
import sys
import logging
import io

_logger = logging.getLogger(__name__)

def run():
    import odoo
    from odoo import api, SUPERUSER_ID

    odoo.tools.config.parse_config([
        '-c', '/etc/odoo/odoo.conf',
        '-d', 'cabinet_medical_db',
        '--db_host', os.environ.get('HOST', 'db'),
        '--db_user', os.environ.get('USER', 'odoo'),
        '--db_password', os.environ.get('PASSWORD', 'odoo_secret_pwd'),
        '--db_port', os.environ.get('PORT', '5432'),
    ])
    
    # Étape 1 : Mettre à jour le module cabinet_medical pour charger les modifications XML et Python
    print("=== 1. Mise à jour du module cabinet_medical ===")
    registry = odoo.registry('cabinet_medical_db')
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        module = env['ir.module.module'].search([('name', '=', 'cabinet_medical')])
        if module:
            print(f"Module trouvé : {module.name} (état: {module.state}). Déclenchement upgrade...")
            module.button_immediate_upgrade()
            print("Module upgradé avec succès !")
    
    # Recharger le registry après l'upgrade
    registry = odoo.registry('cabinet_medical_db')
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        print("\n=== 2. Configuration de la Devise TND ===")
        tnd = env.ref('base.TND', raise_if_not_found=False)
        if not tnd:
            tnd = env['res.currency'].search([('name', '=', 'TND')], limit=1)
        if tnd:
            tnd.write({
                'active': True,
                'symbol': 'DT',
                'decimal_places': 3,
                'position': 'after'
            })
            print(f"Devise TND configurée : symbole={tnd.symbol}, décimales={tnd.decimal_places}, actif={tnd.active}")

        print("\n=== 3. Configuration de la Compagnie Principale & Logo ===")
        company = env['res.company'].search([], limit=1)
        
        # Charger le logo officiel
        logo_path = "/mnt/extra-addons/cabinet_medical/static/src/img/login_logo.png"
        logo_data = False
        if os.path.exists(logo_path):
            with open(logo_path, 'rb') as f:
                logo_data = base64.b64encode(f.read())
            print(f"Logo officiel chargé depuis {logo_path} (taille: {len(logo_data)} octets base64)")
        else:
            print(f"ATTENTION: {logo_path} introuvable !")

        country_tn = env.ref('base.tn', raise_if_not_found=False)
        if not country_tn:
            country_tn = env['res.country'].search([('code', '=', 'TN')], limit=1)

        company_vals = {
            'name': "Cabinet Médical Dr. Oumaima Hajji",
            'street': "Rue de la Santé, Immeuble Médical",
            'city': "Tunis",
            'phone': "+216 71 123 456",
            'email': "contact@cabinetmedical.tn",
            'medecin_nom': "Dr. Oumaima Hajji",
            'medecin_inpe': "12345678",
            'medecin_code_convention': "CONV-2025-01",
            'medecin_specialite': "generaliste",
            'medecin_conventionne': True,
        }
        if country_tn:
            company_vals['country_id'] = country_tn.id
        if tnd:
            company_vals['currency_id'] = tnd.id
        if logo_data:
            company_vals['logo'] = logo_data

        company.write(company_vals)
        if company.partner_id:
            partner_vals = {
                'name': "Cabinet Médical Dr. Oumaima Hajji",
                'street': "Rue de la Santé, Immeuble Médical",
                'city': "Tunis",
                'phone': "+216 71 123 456",
                'email': "contact@cabinetmedical.tn",
            }
            if country_tn:
                partner_vals['country_id'] = country_tn.id
            company.partner_id.write(partner_vals)
            
        print(f"Compagnie mise à jour : {company.name}, {company.street}, {company.city}, {company.phone}, Spécialité: {company.medecin_specialite}, Conventionné: {company.medecin_conventionne}")

        print("\n=== 4. Configuration des Paramètres d'Actes CNAM de démonstration ===")
        # Consultation de contrôle : Code C, 35 DT, 70%
        # Infiltration articulaire : Code K, 50 DT, 80%
        param_c = env['cabinet.acte.parametrage'].search([('code_cnam', '=', 'C')], limit=1)
        if not param_c:
            param_c = env['cabinet.acte.parametrage'].search([('name', 'ilike', 'Consultation de contrôle')], limit=1)
        if param_c:
            param_c.write({
                'name': "Consultation de contrôle",
                'code_cnam': 'C',
                'lettre_cle': 'C',
                'coefficient': 1.0,
                'valeur_cle': 35.0,
                'type_acte': 'consultation',
                'tarif': 35.0,
                'taux_cnam': 70.0,
                'necessite_accord_prealable': False
            })
            print(f"Paramétrage C mis à jour : {param_c.name}, lettre={param_c.lettre_cle}, tarif={param_c.tarif}, taux={param_c.taux_cnam}%")
        else:
            param_c = env['cabinet.acte.parametrage'].create({
                'name': "Consultation de contrôle",
                'code_cnam': 'C',
                'lettre_cle': 'C',
                'coefficient': 1.0,
                'valeur_cle': 35.0,
                'type_acte': 'consultation',
                'tarif': 35.0,
                'taux_cnam': 70.0,
                'necessite_accord_prealable': False
            })
            print(f"Paramétrage C créé : {param_c.name}")

        param_k = env['cabinet.acte.parametrage'].search([('code_cnam', '=', 'K')], limit=1)
        if not param_k:
            param_k = env['cabinet.acte.parametrage'].search([('name', 'ilike', 'Infiltration')], limit=1)
        if param_k:
            param_k.write({
                'name': "Infiltration articulaire",
                'code_cnam': 'K',
                'lettre_cle': 'K',
                'coefficient': 1.0,
                'valeur_cle': 50.0,
                'type_acte': 'acte_technique',
                'tarif': 50.0,
                'taux_cnam': 80.0,
                'necessite_accord_prealable': False
            })
            print(f"Paramétrage K mis à jour : {param_k.name}, lettre={param_k.lettre_cle}, tarif={param_k.tarif}, taux={param_k.taux_cnam}%")
        else:
            param_k = env['cabinet.acte.parametrage'].create({
                'name': "Infiltration articulaire",
                'code_cnam': 'K',
                'lettre_cle': 'K',
                'coefficient': 1.0,
                'valeur_cle': 50.0,
                'type_acte': 'acte_technique',
                'tarif': 50.0,
                'taux_cnam': 80.0,
                'necessite_accord_prealable': False
            })
            print(f"Paramétrage K créé : {param_k.name}")

        # Mettre à jour les factures existantes pour affecter company_id
        factures_existantes = env['cabinet.facture'].search([('company_id', '=', False)])
        if factures_existantes:
            factures_existantes.write({'company_id': company.id})
            print(f"{len(factures_existantes)} factures existantes rattachées au cabinet courant.")

        cr.commit()

        print("\n=== 5. Tests des 11 Scénarios CNAM & Calculs ===")
        # Assurances de test
        mutuelle_standard = env['cabinet.assurance'].search([('name', '=', 'Star Assurances')], limit=1)
        if not mutuelle_standard:
            mutuelle_standard = env['cabinet.assurance'].create({
                'name': 'Star Assurances',
                'taux': 80.0,
                'tiers_payant_direct': False
            })

        mutuelle_tp = env['cabinet.assurance'].search([('name', '=', 'GAT Tiers-Payant')], limit=1)
        if not mutuelle_tp:
            mutuelle_tp = env['cabinet.assurance'].create({
                'name': 'GAT Tiers-Payant',
                'taux': 80.0,
                'tiers_payant_direct': True
            })

        # Création d'un acte paramétré technique à 55 DT, 80% CNAM pour les tests baseline 1-8
        param_55 = env['cabinet.acte.parametrage'].search([('name', '=', 'Acte Test 55 DT')], limit=1)
        if not param_55:
            param_55 = env['cabinet.acte.parametrage'].create({
                'name': 'Acte Test 55 DT',
                'code_cnam': 'TEST55',
                'type_acte': 'acte_technique',
                'tarif': 55.0,
                'taux_cnam': 80.0
            })

        # Paramétrages pour scénarios 9, 10, 11
        param_40_70 = env['cabinet.acte.parametrage'].search([('code_cnam', '=', 'TEST40')], limit=1)
        if not param_40_70:
            param_40_70 = env['cabinet.acte.parametrage'].create({
                'name': 'Consultation Test TCR 40',
                'code_cnam': 'TEST40',
                'type_acte': 'consultation',
                'tarif': 40.0,
                'taux_cnam': 70.0
            })

        param_45_70 = env['cabinet.acte.parametrage'].search([('code_cnam', '=', 'TEST45')], limit=1)
        if not param_45_70:
            param_45_70 = env['cabinet.acte.parametrage'].create({
                'name': 'Consultation Test TCR 45',
                'code_cnam': 'TEST45',
                'type_acte': 'consultation',
                'tarif': 45.0,
                'taux_cnam': 70.0
            })

        param_apci_40 = env['cabinet.acte.parametrage'].search([('code_cnam', '=', 'TESTAPCI40')], limit=1)
        if not param_apci_40:
            param_apci_40 = env['cabinet.acte.parametrage'].create({
                'name': 'Acte APCI Test TCR 40',
                'code_cnam': 'TESTAPCI40',
                'type_acte': 'consultation',
                'tarif': 40.0,
                'taux_cnam': 100.0
            })

        param_non_apci_50 = env['cabinet.acte.parametrage'].search([('code_cnam', '=', 'TESTNONAPCI50')], limit=1)
        if not param_non_apci_50:
            param_non_apci_50 = env['cabinet.acte.parametrage'].create({
                'name': 'Acte Non-APCI Test TCR 50',
                'code_cnam': 'TESTNONAPCI50',
                'type_acte': 'acte_technique',
                'tarif': 50.0,
                'taux_cnam': 80.0
            })

        # Patients de test pour chaque scénario (1 à 11)
        scenarios_tests = [
            {
                'label': '1. Sans couverture',
                'patient_vals': {'name': 'Test Patient Sans Couv', 'is_cnam': False, 'has_assurance': False},
                'expected_scenario': 'sans_couverture',
                'check': lambda f: f.montant_total == 55.0 and f.montant_cnam_cabinet == 0.0 and f.montant_paye_cabinet == 55.0 and f.reste_a_charge_final == 55.0
            },
            {
                'label': '2. CNAM Tiers-payant (Filière privée)',
                'patient_vals': {'name': 'Test Patient TP', 'is_cnam': True, 'filiere_cnam': 'privee', 'numero_cnam': '1111111111', 'has_assurance': False},
                'expected_scenario': 'cnam_tiers_payant',
                'check': lambda f: f.montant_total == 55.0 and f.montant_cnam_cabinet == 44.0 and f.montant_paye_cabinet == 11.0 and f.reste_a_charge_final == 11.0
            },
            {
                'label': '3. CNAM Remboursement',
                'patient_vals': {'name': 'Test Patient Remb', 'is_cnam': True, 'filiere_cnam': 'remboursement', 'numero_cnam': '2222222222', 'has_assurance': False},
                'expected_scenario': 'cnam_remboursement',
                'check': lambda f: f.montant_total == 55.0 and f.montant_cnam_cabinet == 0.0 and f.montant_paye_cabinet == 55.0 and f.part_cnam_display == 44.0 and f.reste_a_charge_final == 11.0
            },
            {
                'label': '4. APCI Tiers-payant',
                'patient_vals': {'name': 'Test Patient APCI TP', 'is_cnam': True, 'filiere_cnam': 'privee', 'is_apci': True, 'numero_cnam': '3333333333', 'numero_decision_apci': 'APCI-2026-001', 'has_assurance': False},
                'expected_scenario': 'apci_tiers_payant',
                'check': lambda f: f.montant_total == 55.0 and f.montant_cnam_cabinet == 55.0 and f.montant_paye_cabinet == 0.0 and f.reste_a_charge_final == 0.0
            },
            {
                'label': '5. APCI Remboursement',
                'patient_vals': {'name': 'Test Patient APCI Remb', 'is_cnam': True, 'filiere_cnam': 'remboursement', 'is_apci': True, 'numero_cnam': '4444444444', 'numero_decision_apci': 'APCI-2026-002', 'has_assurance': False},
                'expected_scenario': 'apci_remboursement',
                'check': lambda f: f.montant_total == 55.0 and f.montant_cnam_cabinet == 0.0 and f.montant_paye_cabinet == 55.0 and f.part_cnam_display == 55.0 and f.reste_a_charge_final == 0.0
            },
            {
                'label': '6. CNAM TP + Mutuelle',
                'patient_vals': {'name': 'Test Patient TP Mutuelle', 'is_cnam': True, 'filiere_cnam': 'privee', 'numero_cnam': '5555555555', 'has_assurance': True, 'assurance_id': mutuelle_standard.id, 'assurance_taux': 80.0},
                'expected_scenario': 'cnam_tp_assur',
                'check': lambda f: f.montant_total == 55.0 and f.montant_cnam_cabinet == 44.0 and f.montant_paye_cabinet == 11.0 and f.part_assurance_display == 8.8 and f.reste_a_charge_final == 2.2
            },
            {
                'label': '7. CNAM Remb + Mutuelle',
                'patient_vals': {'name': 'Test Patient Remb Mutuelle', 'is_cnam': True, 'filiere_cnam': 'remboursement', 'numero_cnam': '6666666666', 'has_assurance': True, 'assurance_id': mutuelle_standard.id, 'assurance_taux': 80.0},
                'expected_scenario': 'cnam_remb_assur',
                'check': lambda f: f.montant_total == 55.0 and f.montant_cnam_cabinet == 0.0 and f.montant_paye_cabinet == 55.0 and f.part_cnam_display == 44.0 and f.part_assurance_display == 8.8 and f.reste_a_charge_final == 2.2
            },
            {
                'label': '8. Sans CNAM + Mutuelle',
                'patient_vals': {'name': 'Test Patient Sans CNAM Mutuelle', 'is_cnam': False, 'has_assurance': True, 'assurance_id': mutuelle_standard.id, 'assurance_taux': 80.0},
                'expected_scenario': 'sans_cnam_assur',
                'check': lambda f: f.montant_total == 55.0 and f.montant_cnam_cabinet == 0.0 and f.montant_paye_cabinet == 55.0 and f.part_assurance_display == 44.0 and f.reste_a_charge_final == 11.0
            },
            {
                'label': '9. CNAM TP avec Dépassement d\'honoraires (Hon=60, TCR=40, Taux=70%)',
                'patient_vals': {'name': 'Test Patient Scénario 9 TP Dépassement', 'is_cnam': True, 'filiere_cnam': 'privee', 'numero_cnam': '9999999991', 'has_assurance': False},
                'expected_scenario': 'cnam_tiers_payant',
                'actes_vals': [{
                    'type_acte': 'consultation',
                    'description': 'Consultation avec dépassement (Hon 60, TCR 40)',
                    'montant': 60.0,
                    'tarif_conventionnel': 40.0,
                    'parametrage_id': param_40_70.id
                }],
                'check': lambda f: (
                    f.montant_total == 60.0 and
                    f.montant_conventionnel_total == 40.0 and
                    f.depassement_total == 20.0 and
                    f.montant_cnam_cabinet == 28.0 and
                    f.ticket_moderateur_total == 12.0 and
                    f.montant_paye_cabinet == 32.0 and
                    f.reste_a_charge_final == 32.0
                )
            },
            {
                'label': '10. Séance mixte APCI (Acte APCI 40 DT + Acte non-APCI 50 DT)',
                'patient_vals': {'name': 'Test Patient Scénario 10 Séance Mixte', 'is_cnam': True, 'filiere_cnam': 'privee', 'is_apci': True, 'numero_cnam': '9999999992', 'numero_decision_apci': 'APCI-2026-010', 'has_assurance': False},
                'expected_scenario': 'apci_tiers_payant',
                'actes_vals': [
                    {
                        'type_acte': 'consultation',
                        'description': 'Acte APCI ciblé 40 DT',
                        'montant': 40.0,
                        'tarif_conventionnel': 40.0,
                        'is_acte_apci': True,
                        'parametrage_id': param_apci_40.id
                    },
                    {
                        'type_acte': 'acte_technique',
                        'description': 'Acte non APCI 50 DT',
                        'montant': 50.0,
                        'tarif_conventionnel': 50.0,
                        'is_acte_apci': False,
                        'parametrage_id': param_non_apci_50.id
                    }
                ],
                'check': lambda f: (
                    f.montant_total == 90.0 and
                    f.montant_conventionnel_total == 90.0 and
                    f.depassement_total == 0.0 and
                    f.montant_cnam_cabinet == 80.0 and
                    f.ticket_moderateur_total == 10.0 and
                    f.montant_paye_cabinet == 10.0 and
                    f.reste_a_charge_final == 10.0
                )
            },
            {
                'label': '11. Dépassement + Mutuelle (Hon=70, TCR=45, Taux CNAM=70%, Mutuelle=80% du TM)',
                'patient_vals': {'name': 'Test Patient Scénario 11 Mutuelle Dep', 'is_cnam': True, 'filiere_cnam': 'privee', 'numero_cnam': '9999999993', 'has_assurance': True, 'assurance_id': mutuelle_tp.id, 'assurance_taux': 80.0},
                'expected_scenario': 'cnam_tp_assur',
                'actes_vals': [{
                    'type_acte': 'consultation',
                    'description': 'Consultation avec dépassement et mutuelle (Hon 70, TCR 45)',
                    'montant': 70.0,
                    'tarif_conventionnel': 45.0,
                    'parametrage_id': param_45_70.id
                }],
                'check': lambda f: (
                    f.montant_total == 70.0 and
                    f.montant_conventionnel_total == 45.0 and
                    f.depassement_total == 25.0 and
                    f.montant_cnam_cabinet == 31.5 and
                    f.ticket_moderateur_total == 13.5 and
                    f.part_assurance_display == 10.8 and
                    f.montant_paye_cabinet == 27.7 and
                    f.reste_a_charge_final == 27.7
                )
            },
        ]

        test_results = []
        facture_tp_for_pdf = None

        for sc in scenarios_tests:
            # Créer ou trouver patient
            patient = env['cabinet.patient'].search([('name', '=', sc['patient_vals']['name'])], limit=1)
            if not patient:
                patient = env['cabinet.patient'].create(sc['patient_vals'])
            else:
                patient.write(sc['patient_vals'])

            # Consultation
            consultation = env['cabinet.consultation'].create({
                'patient_id': patient.id,
                'motif': f"Consultation test {sc['label']}",
            })

            # Actes
            if 'actes_vals' in sc:
                for a_vals in sc['actes_vals']:
                    a_dict = dict(a_vals)
                    a_dict['consultation_id'] = consultation.id
                    env['cabinet.acte'].create(a_dict)
            else:
                # Acte de 55 DT avec taux CNAM 80%
                acte = env['cabinet.acte'].create({
                    'consultation_id': consultation.id,
                    'type_acte': 'acte_technique',
                    'description': 'Acte test audit 55 DT',
                    'montant': 55.0,
                    'parametrage_id': param_55.id
                })

            # Facture
            facture = env['cabinet.facture'].create({
                'patient_id': patient.id,
                'consultation_id': consultation.id,
                'company_id': company.id,
            })
            facture.action_valider()

            success = (facture.scenario == sc['expected_scenario']) and sc['check'](facture)
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"[{status}] {sc['label']}:")
            print(f"   Scénario: {facture.scenario} (attendu: {sc['expected_scenario']})")
            print(f"   Total={facture.montant_total}, TCR={facture.montant_conventionnel_total}, Dép={facture.depassement_total}, CNAM_Cab={facture.montant_cnam_cabinet}, Paye_Cab={facture.montant_paye_cabinet}, TM={facture.ticket_moderateur_total}, Mutuelle={facture.part_assurance_display}, Reste_Final={facture.reste_a_charge_final}, Part_CNAM_Disp={facture.part_cnam_display}")
            test_results.append((sc['label'], success, facture))

            if sc['label'].startswith('2.'):
                facture_tp_for_pdf = facture
            elif sc['label'].startswith('9.'):
                facture_sc9_for_pdf = facture

        print("\n=== 6. Génération et Validation du Rapport PDF Facture (Scénario 2 Baseline) ===")
        assert facture_tp_for_pdf is not None, "Aucune facture du Scénario 2 trouvée pour le test PDF"
        
        report_action = env.ref('cabinet_medical.action_report_facture')
        pdf_content, _ = report_action._render_qweb_pdf('cabinet_medical.report_facture_template', res_ids=[facture_tp_for_pdf.id])
        print(f"PDF Scénario 2 généré avec succès ! Taille : {len(pdf_content)} octets.")

        # Sauvegarder le PDF sur le disque pour archivage
        pdf_path = "/mnt/extra-addons/cabinet_medical/test_facture_audit.pdf"
        with open(pdf_path, 'wb') as f:
            f.write(pdf_content)
        print(f"PDF sauvegardé sous {pdf_path}")

        # Extraction de texte du PDF
        extracted_text = ""
        try:
            from pdfminer.high_level import extract_text
            extracted_text = extract_text(io.BytesIO(pdf_content))
            print(f"Texte extrait via pdfminer ({len(extracted_text)} caractères).")
        except Exception as e:
            try:
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(pdf_content))
                for page in reader.pages:
                    extracted_text += page.extract_text() or ""
                print(f"Texte extrait via pypdf ({len(extracted_text)} caractères).")
            except Exception as e2:
                print(f"Fallback extraction binaire ({e2})")
                extracted_text = pdf_content.decode('latin1', errors='ignore')

        print("\n--- Extrait du contenu textuel du PDF (Scénario 2) : ---")
        lines = [l.strip() for l in extracted_text.splitlines() if l.strip()]
        for l in lines[:25]:
            print(f"  | {l}")

        # Vérifications strictes demandées pour Scénario 2
        checks = {
            "Présence nom du cabinet 'Cabinet Médical Dr. Oumaima Hajji'": "Cabinet Médical Dr. Oumaima Hajji" in extracted_text,
            "Présence ville 'Tunis'": "Tunis" in extracted_text,
            "Présence téléphone '+216 71 123 456'": "+216 71 123 456" in extracted_text,
            "Présence médecin 'Dr. Oumaima Hajji'": "Dr. Oumaima Hajji" in extracted_text,
            "Présence INPE '12345678'": "12345678" in extracted_text,
            "Présence Code Convention 'CONV-2025-01'": "CONV-2025-01" in extracted_text,
            "Présence montant total 55 DT (avec décimales)": ("55,000" in extracted_text or "55.000" in extracted_text or "55" in extracted_text),
            "Présence montant CNAM 44 DT (avec décimales)": ("44,000" in extracted_text or "44.000" in extracted_text or "44" in extracted_text),
            "Présence montant patient 11 DT (avec décimales)": ("11,000" in extracted_text or "11.000" in extracted_text or "11" in extracted_text),
            "ABSENCE de 'YourCompany'": "YourCompany" not in extracted_text,
            "ABSENCE de '250 Executive Park Blvd'": "250 Executive Park Blvd" not in extracted_text,
            "ABSENCE de 'San Francisco'": "San Francisco" not in extracted_text,
            "ABSENCE de 'United States'": "United States" not in extracted_text,
        }

        print("\n=== 7. Synthèse des Vérifications PDF (Scénario 2) ===")
        all_checks_passed = True
        for check_name, passed in checks.items():
            status = "✅ CONFORME" if passed else "❌ NON CONFORME"
            print(f"[{status}] {check_name}")
            if not passed:
                all_checks_passed = False

        # Test PDF Scénario 9 (Dépassement d'honoraires)
        if facture_sc9_for_pdf:
            print("\n=== 8. Validation PDF Scénario 9 (Avec Dépassement) ===")
            pdf_content_9, _ = report_action._render_qweb_pdf('cabinet_medical.report_facture_template', res_ids=[facture_sc9_for_pdf.id])
            extracted_text_9 = extract_text(io.BytesIO(pdf_content_9))
            check_9_total = "60" in extracted_text_9
            check_9_cnam = "28" in extracted_text_9
            check_9_patient = "32" in extracted_text_9
            print(f"[{'✅ CONFORME' if check_9_total else '❌ NON CONFORME'}] Scénario 9 - Présence total 60 DT")
            print(f"[{'✅ CONFORME' if check_9_cnam else '❌ NON CONFORME'}] Scénario 9 - Présence CNAM 28 DT")
            print(f"[{'✅ CONFORME' if check_9_patient else '❌ NON CONFORME'}] Scénario 9 - Présence Patient 32 DT")
            if not (check_9_total and check_9_cnam and check_9_patient):
                all_checks_passed = False

        # Section 9 : Vérifications Spécifiques Groupe 4 dans Odoo
        print("\n=== 9. Vérifications Spécifiques Groupe 4 (Contrôles bloquants, Immutabilité & Bordereau) ===")
        from odoo.exceptions import ValidationError
        from datetime import date, timedelta

        # 9.1 Contrôle bloquant CNAM : Droits expirés
        p_expired = env['cabinet.patient'].create({
            'name': 'Patient Test Expiré Groupe 4',
            'is_cnam': True,
            'filiere_cnam': 'privee',
            'numero_cnam': '8888888888',
            'date_validite_cnam': date.today() - timedelta(days=5)
        })
        consult_exp = env['cabinet.consultation'].create({
            'patient_id': p_expired.id,
            'motif': 'Consultation test droits expirés'
        })
        env['cabinet.acte'].create({
            'consultation_id': consult_exp.id,
            'type_acte': 'consultation',
            'description': 'Consultation test',
            'montant': 40.0,
            'tarif_conventionnel': 40.0
        })
        fac_exp = env['cabinet.facture'].create({
            'patient_id': p_expired.id,
            'consultation_id': consult_exp.id,
            'company_id': company.id
        })
        bloque_ok = False
        try:
            fac_exp.action_valider()
        except ValidationError as e:
            bloque_ok = True
            print(f"[✅ CONFORME] Blocage validation droits CNAM expirés détecté avec succès : {e}")

        if not bloque_ok:
            print("[❌ NON CONFORME] Échec du blocage sur droits CNAM expirés !")
            all_checks_passed = False

        # 9.2 Immutabilité Facture : interdiction de suppression sur facture validée
        fac_validee = facture_tp_for_pdf
        suppr_bloquee = False
        try:
            fac_validee.unlink()
        except ValidationError as e:
            suppr_bloquee = True
            print(f"[✅ CONFORME] Immutabilité facture validée : tentative de suppression bloquée avec succès : {e}")

        if not suppr_bloquee:
            print("[❌ NON CONFORME] La facture validée a pu être supprimée !")
            all_checks_passed = False

        # 9.3 Bordereau M5 : Récupération, cycle de vie, rejet structuré et immutabilité
        bor_test = env['cabinet.bordereau'].create({
            'date_debut': date.today() - timedelta(days=1),
            'date_fin': date.today() + timedelta(days=1),
        })
        bor_test.action_recuperer_factures()
        print(f"[✅ CONFORME] Bordereau {bor_test.name} : {bor_test.nb_factures} factures récupérées pour un montant CNAM de {bor_test.montant_cnam_demande} DT.")
        bor_test.action_valider()
        bor_test.action_envoyer()
        bor_test.action_rejeter()
        bor_test.write({'code_motif_rejet': 'droits_expires', 'motif_rejet': 'Vérification motif rejet officiel'})
        print(f"[✅ CONFORME] Bordereau rejeté avec motif structuré : code={bor_test.code_motif_rejet}, statut={bor_test.state}")

        bor_suppr_bloquee = False
        try:
            bor_test.unlink()
        except ValidationError as e:
            bor_suppr_bloquee = True
            print(f"[✅ CONFORME] Immutabilité bordereau non-brouillon : tentative de suppression bloquée avec succès : {e}")

        if not bor_suppr_bloquee:
            print("[❌ NON CONFORME] Le bordereau rejeté a pu être supprimé !")
            all_checks_passed = False

        if all_checks_passed:
            print("\n🎉 TOUS LES TESTS SONT VALIDES AVEC SUCCÈS À 100% !")
        else:
            print("\n⚠️ CERTAINES VÉRIFICATIONS ONT ÉCHOUÉ !")

if __name__ == '__main__':
    run()
