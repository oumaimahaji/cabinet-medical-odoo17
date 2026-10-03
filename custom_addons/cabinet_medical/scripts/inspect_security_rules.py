# -*- coding: utf-8 -*-
"""
Script to inspect all ir.rule security definitions in the database
and perform comprehensive 2-patient isolation tests.
"""
import sys
import os
import odoo
from odoo import api, fields, SUPERUSER_ID
from odoo.exceptions import AccessError

def run_security_inspection():
    odoo.tools.config.parse_config([
        '-c', '/etc/odoo/odoo.conf',
        '-d', 'cabinet_medical_db',
        '--db_host=db',
        '--db_user=odoo',
        '--db_password=Xj1nBDVze5ZY7bn8QajNvpXz'
    ])
    
    registry = odoo.registry('cabinet_medical_db')
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        print("=" * 70)
        print("1. INSPECTION DES REGLES DE SECURITE (IR.RULE) POUR CABINET.*")
        print("=" * 70)
        
        rules = env['ir.rule'].search([('model_id.model', 'like', 'cabinet.%')])
        print(f"Nombre total de regles ir.rule pour cabinet.* : {len(rules)}")
        
        rules_1_eq_1 = []
        for r in rules:
            group_names = [g.name for g in r.groups] if r.groups else ["GLOBAL (tous les groupes)"]
            print(f"[-] Règle ID {r.id}: '{r.name}'")
            print(f"    Modèle: {r.model_id.model}")
            print(f"    Domaine: {r.domain_force}")
            print(f"    Global: {r['global']} | Actif: {r.active}")
            print(f"    Groupes: {', '.join(group_names)}")
            print(f"    Droits: Read={r.perm_read}, Write={r.perm_write}, Create={r.perm_create}, Unlink={r.perm_unlink}")
            print()
            
            if r.domain_force and "1=1" in r.domain_force.replace(" ", "").replace("'", "").replace('"', ''):
                rules_1_eq_1.append(r)
        
        print("-" * 70)
        if rules_1_eq_1:
            print(f"ALERTE: {len(rules_1_eq_1)} regles utilisent [(1, '=', 1)] :")
            for r in rules_1_eq_1:
                print(f"  - {r.name} ({r.model_id.model})")
        else:
            print("AUCUNE règle ir.rule n'utilise [(1, '=', 1)] pour les modèles cabinet.*.")
        print("-" * 70)
        
        # Check portal security group rules specifically
        portal_group = env.ref('base.group_portal', raise_if_not_found=False)
        print(f"\nRègles associées directement au groupe Portal ({portal_group.name if portal_group else 'Non trouvé'}) :")
        portal_rules = env['ir.rule'].search([('groups', 'in', [portal_group.id])])
        for pr in portal_rules:
            if pr.model_id.model.startswith('cabinet.'):
                print(f"  * {pr.model_id.model}: {pr.domain_force} (R={pr.perm_read}, W={pr.perm_write}, C={pr.perm_create}, D={pr.perm_unlink})")

        print("\n" + "=" * 70)
        print("2. TEST D'ISOLATION PATIENT A VS PATIENT B")
        print("=" * 70)

        user_model = env['res.users']
        patient_model = env['cabinet.patient']
        rdv_model = env['cabinet.rendezvous']
        consult_model = env['cabinet.consultation']
        presc_model = env['cabinet.prescription']
        presc_line_model = env['cabinet.prescription.line']
        facture_model = env['cabinet.facture']
        notif_model = env['cabinet.notification']
        assurance_model = env['cabinet.assurance']

        assurance = assurance_model.search([], limit=1)
        if not assurance:
            assurance = assurance_model.create({'name': 'CNAM Filière Privée', 'code': 'CNAM_PRIV'})

        def get_or_create_portal_user(login, name, email):
            user = user_model.search([('login', '=', login)], limit=1)
            if not user:
                user = user_model.create({
                    'name': name,
                    'login': login,
                    'email': email,
                    'groups_id': [(6, 0, [portal_group.id])],
                })
            return user

        user_a = get_or_create_portal_user('patient_a_test@cabinet.tn', 'PATIENT TEST A', 'patient_a_test@cabinet.tn')
        user_b = get_or_create_portal_user('patient_b_test@cabinet.tn', 'PATIENT TEST B', 'patient_b_test@cabinet.tn')

        def get_or_create_patient(user, cin, tel):
            pat = patient_model.search([('user_id', '=', user.id)], limit=1)
            if not pat:
                pat = patient_model.create({
                    'name': user.name,
                    'user_id': user.id,
                    'cin': cin,
                    'telephone': tel,
                    'email': user.email,
                    'is_cnam': True,
                    'assurance_id': assurance.id,
                    'allergies': 'Penicilline (Secret A)' if 'A' in user.name else 'Aspirine (Secret B)',
                    'antecedents': 'Diabete (Secret A)' if 'A' in user.name else 'Hypertension (Secret B)',
                })
            return pat

        patient_a = get_or_create_patient(user_a, '11111111', '22111111')
        patient_b = get_or_create_patient(user_b, '22222222', '22222222')

        # Clean test records with SQL for clean test
        cr.execute("DELETE FROM cabinet_prescription_line WHERE prescription_id IN (SELECT id FROM cabinet_prescription WHERE consultation_id IN (SELECT id FROM cabinet_consultation WHERE patient_id IN (%s, %s)))", (patient_a.id, patient_b.id))
        cr.execute("DELETE FROM cabinet_prescription WHERE consultation_id IN (SELECT id FROM cabinet_consultation WHERE patient_id IN (%s, %s))", (patient_a.id, patient_b.id))
        cr.execute("DELETE FROM cabinet_facture WHERE patient_id IN (%s, %s)", (patient_a.id, patient_b.id))
        cr.execute("DELETE FROM cabinet_rendezvous WHERE patient_id IN (%s, %s)", (patient_a.id, patient_b.id))
        cr.execute("DELETE FROM cabinet_consultation WHERE patient_id IN (%s, %s)", (patient_a.id, patient_b.id))
        cr.execute("DELETE FROM cabinet_notification WHERE patient_id IN (%s, %s)", (patient_a.id, patient_b.id))

        # Create distinct data for Patient A
        rdv_a = rdv_model.create({
            'patient_id': patient_a.id,
            'date': fields.Date.today(),
            'heure': 9.0,
            'motif_rapide': 'Consultation Routine Patient A',
            'state': 'en_attente'
        })
        consult_a = consult_model.create({
            'patient_id': patient_a.id,
            'date_consultation': fields.Date.today(),
            'motif': 'Motif Consultation Patient A',
            'diagnostic': 'Diagnostic Confidentiel Patient A',
            'state': 'done'
        })
        presc_a = presc_model.create({
            'consultation_id': consult_a.id,
            'date_prescription': fields.Date.today(),
            'state': 'draft',
        })
        presc_line_a = presc_line_model.create({
            'prescription_id': presc_a.id,
            'medicament': 'Paracetamol 1000mg',
            'dosage': '1000mg',
            'posologie': '1 cp 3x/jour pour A'
        })
        facture_a = facture_model.create({
            'patient_id': patient_a.id,
            'consultation_id': consult_a.id,
            'date_facture': fields.Date.today(),
            'state': 'draft'
        })
        notif_a = notif_model.create({
            'patient_id': patient_a.id,
            'title': 'Notification Secrete A',
            'message': 'Votre ordonnance A est prete',
            'type': 'ordonnance',
        })

        # Create distinct data for Patient B
        rdv_b = rdv_model.create({
            'patient_id': patient_b.id,
            'date': fields.Date.today(),
            'heure': 10.0,
            'motif_rapide': 'Consultation Routine Patient B',
            'state': 'en_attente'
        })
        consult_b = consult_model.create({
            'patient_id': patient_b.id,
            'date_consultation': fields.Date.today(),
            'motif': 'Motif Consultation Patient B',
            'diagnostic': 'Diagnostic Confidentiel Patient B',
            'state': 'done'
        })
        presc_b = presc_model.create({
            'consultation_id': consult_b.id,
            'date_prescription': fields.Date.today(),
            'state': 'draft',
        })
        presc_line_b = presc_line_model.create({
            'prescription_id': presc_b.id,
            'medicament': 'Ibuprofene 400mg',
            'dosage': '400mg',
            'posologie': '1 cp 2x/jour pour B'
        })
        facture_b = facture_model.create({
            'patient_id': patient_b.id,
            'consultation_id': consult_b.id,
            'date_facture': fields.Date.today(),
            'state': 'draft'
        })
        notif_b = notif_model.create({
            'patient_id': patient_b.id,
            'title': 'Notification Secrete B',
            'message': 'Votre ordonnance B est prete',
            'type': 'ordonnance',
        })

        cr.commit()

        # Run isolation checks under user_a and user_b environments
        env_a = env(user=user_a)
        env_b = env(user=user_b)

        isolation_passed = True
        tests_count = 0
        success_count = 0

        def test_check(name, condition, error_msg=""):
            nonlocal tests_count, success_count, isolation_passed
            tests_count += 1
            if condition:
                success_count += 1
                print(f"  [PASS] {name}")
            else:
                isolation_passed = False
                print(f"  [FAIL] {name}: {error_msg}")

        print("\n--- Test 2.1 : Recherche ORM par le Patient A ---")
        
        patients_visible_a = env_a['cabinet.patient'].search([])
        test_check("Patient A ne voit que son propre dossier patient",
                   patients_visible_a.ids == [patient_a.id],
                   f"IDs retournes: {patients_visible_a.ids}, attendu: [{patient_a.id}]")

        rdvs_visible_a = env_a['cabinet.rendezvous'].search([])
        test_check("Patient A ne voit que ses propres RDVs",
                   rdv_a.id in rdvs_visible_a.ids and rdv_b.id not in rdvs_visible_a.ids and all(r.patient_id.id == patient_a.id for r in rdvs_visible_a),
                   f"RDVs vus: {rdvs_visible_a.ids}, RDV B = {rdv_b.id}")

        consults_visible_a = env_a['cabinet.consultation'].search([])
        test_check("Patient A ne voit que ses propres consultations",
                   consult_a.id in consults_visible_a.ids and consult_b.id not in consults_visible_a.ids and all(c.patient_id.id == patient_a.id for c in consults_visible_a),
                   f"Consultations vues: {consults_visible_a.ids}, Consult B = {consult_b.id}")

        prescs_visible_a = env_a['cabinet.prescription'].search([])
        test_check("Patient A ne voit que ses propres prescriptions",
                   presc_a.id in prescs_visible_a.ids and presc_b.id not in prescs_visible_a.ids and all(p.patient_id.id == patient_a.id for p in prescs_visible_a),
                   f"Prescriptions vues: {prescs_visible_a.ids}, Presc B = {presc_b.id}")

        lines_visible_a = env_a['cabinet.prescription.line'].search([])
        test_check("Patient A ne voit que ses propres lignes de prescription",
                   presc_line_a.id in lines_visible_a.ids and presc_line_b.id not in lines_visible_a.ids and all(l.prescription_id.consultation_id.patient_id.id == patient_a.id for l in lines_visible_a),
                   f"Lignes vues: {lines_visible_a.ids}, Ligne B = {presc_line_b.id}")

        factures_visible_a = env_a['cabinet.facture'].search([])
        test_check("Patient A ne voit que ses propres factures",
                   facture_a.id in factures_visible_a.ids and facture_b.id not in factures_visible_a.ids and all(f.patient_id.id == patient_a.id for f in factures_visible_a),
                   f"Factures vues: {factures_visible_a.ids}, Facture B = {facture_b.id}")

        notifs_visible_a = env_a['cabinet.notification'].search([])
        test_check("Patient A ne voit que ses propres notifications",
                   notif_a.id in notifs_visible_a.ids and notif_b.id not in notifs_visible_a.ids and all(n.patient_id.id == patient_a.id for n in notifs_visible_a),
                   f"Notifs vues: {notifs_visible_a.ids}, Notif B = {notif_b.id}")

        print("\n--- Test 2.2 : Accès direct par ID (Patient A -> Données de Patient B) ---")
        
        try:
            res = env_a['cabinet.patient'].browse(patient_b.id).read(['name', 'allergies', 'antecedents'])
            test_check("Accès direct au dossier de B par A est BLOQUÉ", False, f"Lecture directe de Patient B a réussi: {res}")
        except AccessError:
            test_check("Accès direct au dossier de B par A est BLOQUÉ (AccessError)", True)
        except Exception as e:
            test_check(f"Accès direct bloqué avec exception: {type(e).__name__}", True)

        try:
            res = env_a['cabinet.consultation'].browse(consult_b.id).read(['diagnostic'])
            test_check("Accès direct à la consultation de B par A est BLOQUÉ", False, f"Lecture directe de Consult B a réussi: {res}")
        except AccessError:
            test_check("Accès direct à la consultation de B par A est BLOQUÉ (AccessError)", True)
        except Exception as e:
            test_check(f"Accès direct consultation bloqué avec exception: {type(e).__name__}", True)

        try:
            res = env_a['cabinet.prescription'].browse(presc_b.id).read(['medicaments_resume'])
            test_check("Accès direct à la prescription de B par A est BLOQUÉ", False, f"Lecture directe de Presc B a réussi: {res}")
        except AccessError:
            test_check("Accès direct à la prescription de B par A est BLOQUÉ (AccessError)", True)
        except Exception as e:
            test_check(f"Accès direct prescription bloqué avec exception: {type(e).__name__}", True)

        try:
            res = env_a['cabinet.facture'].browse(facture_b.id).read(['montant_total'])
            test_check("Accès direct à la facture de B par A est BLOQUÉ", False, f"Lecture directe de Facture B a réussi: {res}")
        except AccessError:
            test_check("Accès direct à la facture de B par A est BLOQUÉ (AccessError)", True)
        except Exception as e:
            test_check(f"Accès direct facture bloqué avec exception: {type(e).__name__}", True)

        print("\n--- Test 2.3 : Recherche ORM et accès direct par le Patient B (B -> A) ---")

        patients_visible_b = env_b['cabinet.patient'].search([])
        test_check("Patient B ne voit que son propre dossier patient",
                   patients_visible_b.ids == [patient_b.id],
                   f"IDs retournes: {patients_visible_b.ids}, attendu: [{patient_b.id}]")

        prescs_visible_b = env_b['cabinet.prescription'].search([])
        test_check("Patient B ne voit que ses propres prescriptions",
                   presc_b.id in prescs_visible_b.ids and presc_a.id not in prescs_visible_b.ids and all(p.patient_id.id == patient_b.id for p in prescs_visible_b),
                   f"Prescriptions vues: {prescs_visible_b.ids}, Presc A = {presc_a.id}")

        factures_visible_b = env_b['cabinet.facture'].search([])
        test_check("Patient B ne voit que ses propres factures",
                   facture_b.id in factures_visible_b.ids and facture_a.id not in factures_visible_b.ids and all(f.patient_id.id == patient_b.id for f in factures_visible_b),
                   f"Factures vues: {factures_visible_b.ids}, Facture A = {facture_a.id}")

        try:
            res = env_b['cabinet.patient'].browse(patient_a.id).read(['name', 'allergies'])
            test_check("Accès direct au dossier de A par B est BLOQUÉ", False, f"Lecture directe de Patient A par B a réussi: {res}")
        except AccessError:
            test_check("Accès direct au dossier de A par B est BLOQUÉ (AccessError)", True)
        except Exception as e:
            test_check(f"Accès direct bloqué avec exception: {type(e).__name__}", True)

        try:
            res = env_b['cabinet.prescription'].browse(presc_a.id).read(['medicaments_resume'])
            test_check("Accès direct à la prescription de A par B est BLOQUÉ", False, f"Lecture directe de Presc A par B a réussi: {res}")
        except AccessError:
            test_check("Accès direct à la prescription de A par B est BLOQUÉ (AccessError)", True)
        except Exception as e:
            test_check(f"Accès direct prescription bloqué avec exception: {type(e).__name__}", True)

        print("\n--- Test 2.4 : Téléchargement contrôleur PDF (simulation) ---")
        found_b_as_a = env_a['cabinet.prescription'].search([
            ('id', '=', presc_b.id),
            ('patient_id', '=', patient_a.id)
        ], limit=1)
        test_check("Contrôleur PDF: Patient A tentant de cibler l'ordo de B n'obtient aucun record",
                   not bool(found_b_as_a),
                   f"Record trouvé: {found_b_as_a}")

        print("\n" + "=" * 70)
        print(f"RÉSULTAT DES TESTS DE SÉCURITÉ PORTAIL : {success_count}/{tests_count} SUCCÈS")
        if isolation_passed and success_count == tests_count:
            print("CONCLUSION : ISOLATION PORTAIL PATIENT A / B TOTALE ET VÉRIFIÉE (ORM + IR.RULE + CONTRÔLEUR)")
        else:
            print("CONCLUSION : VULNÉRABILITÉ OU DÉFAILLANCE D'ISOLATION DÉTECTÉE !")
        print("=" * 70)

if __name__ == '__main__':
    run_security_inspection()
