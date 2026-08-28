# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request
# type: ignore
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

class PatientPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        """Valeurs légères communes à toutes les pages du portail."""
        values = super()._prepare_portal_layout_values()
        patient = request.env['cabinet.patient'].search([('user_id', '=', request.env.user.id)], limit=1)
        values['patient'] = patient
        return values

    def _prepare_home_portal_values(self, counters):
        """Valeurs spécifiques et complètes chargées UNIQUEMENT sur l'accueil du portail (/my)."""
        values = super()._prepare_home_portal_values(counters)
        
        patient = request.env['cabinet.patient'].search([('user_id', '=', request.env.user.id)], limit=1)
        values['patient'] = patient
        
        if patient:
            today = fields.Date.today()
            next_rdv = request.env['cabinet.rendezvous'].search([
                ('patient_id', '=', patient.id), 
                ('date', '>=', today), 
                ('state', '=', 'en_attente')
            ], order='date asc, heure asc', limit=1)
            
            cnam_expiring_soon = False
            if patient.is_cnam and patient.date_validite_cnam and not patient.is_cnam_expired:
                if 0 <= (patient.date_validite_cnam - today).days < 30:
                    cnam_expiring_soon = True
            
            values['next_rdv'] = next_rdv
            values['consultation_count'] = request.env['cabinet.consultation'].search_count([('patient_id', '=', patient.id)])
            values['cnam_expiring_soon'] = cnam_expiring_soon
            
            # Prénom du patient
            values['patient_firstname'] = patient.name.split()[0] if patient.name else ''
            
            # Montant total dû (somme des factures en état brouillon/non payées)
            factures = request.env['cabinet.facture'].search([('patient_id', '=', patient.id), ('state', '=', 'draft')])
            values['facture_total_du'] = sum(factures.mapped('montant_paye_cabinet'))
            
            # Statut CNAM
            if patient.is_cnam:
                values['cnam_status'] = 'Expiré' if patient.is_cnam_expired else 'Actif'
            else:
                values['cnam_status'] = 'Inactif'
            
            # Compteurs réels pour le rendu QWeb direct (uniquement RDV terminés, en attente et absent)
            values['rendezvous_count'] = request.env['cabinet.rendezvous'].search_count([
                ('patient_id', '=', patient.id),
                ('state', 'in', ['termine', 'en_attente', 'absent'])
            ])
            values['ordonnance_count'] = request.env['cabinet.prescription'].search_count([('patient_id', '=', patient.id)])
            values['facture_count'] = request.env['cabinet.facture'].search_count([('patient_id', '=', patient.id)])
            
            # Activités récentes combinées
            activities = []

            def format_dt(d):
                if not d:
                    return ""
                return d.strftime('%d/%m/%Y')

            consultations = request.env['cabinet.consultation'].search([('patient_id', '=', patient.id)], order='date_consultation desc, id desc', limit=3)
            for c in consultations:
                activities.append({
                    'type': 'consultation',
                    'title': "Consultation médicale effectuée",
                    'date': c.date_consultation,
                    'date_formatted': format_dt(c.date_consultation),
                    'icon': 'fa-stethoscope',
                    'color': 'rgba(6, 182, 212, 0.08)',
                    'text_color': '#06b6d4'
                })
                
            prescriptions = request.env['cabinet.prescription'].search([('patient_id', '=', patient.id)], order='date_prescription desc, id desc', limit=3)
            for p in prescriptions:
                med_str = f" : {p.medicaments_resume}" if p.medicaments_resume and p.medicaments_resume != '—' else ""
                activities.append({
                    'type': 'prescription',
                    'title': f"Nouvelle ordonnance disponible{med_str}",
                    'date': p.date_prescription,
                    'date_formatted': format_dt(p.date_prescription),
                    'icon': 'fa-file-text-o',
                    'color': 'rgba(16, 185, 129, 0.08)',
                    'text_color': '#10b981'
                })
                
            factures = request.env['cabinet.facture'].search([('patient_id', '=', patient.id)], order='date_facture desc, id desc', limit=3)
            for f in factures:
                fac_name_str = f" {f.name}" if f.name and f.name != 'Nouveau' else ""
                activities.append({
                    'type': 'facture',
                    'title': f"Facture de soins{fac_name_str} ({f.montant_total} DT)",
                    'date': f.date_facture,
                    'date_formatted': format_dt(f.date_facture),
                    'icon': 'fa-credit-card',
                    'color': 'rgba(245, 158, 11, 0.08)',
                    'text_color': '#f59e0b'
                })
                
            rendezvous = request.env['cabinet.rendezvous'].search([
                ('patient_id', '=', patient.id),
                ('state', 'in', ['termine', 'en_attente', 'absent'])
            ], order='date desc, id desc', limit=3)
            for r in rendezvous:
                if r.state == 'termine':
                    status_label = "terminé"
                elif r.state == 'en_attente':
                    status_label = "planifié" if r.date and r.date >= today else "passé"
                elif r.state == 'absent':
                    status_label = "non honoré"
                else:
                    status_label = "planifié"
                activities.append({
                    'type': 'rendezvous',
                    'title': f"Rendez-vous {status_label}",
                    'date': r.date,
                    'date_formatted': format_dt(r.date),
                    'icon': 'fa-calendar-check-o',
                    'color': 'rgba(79, 70, 229, 0.08)',
                    'text_color': '#4f46e5'
                })
                
            # Trier par date décroissante
            activities = sorted(activities, key=lambda x: str(x['date']) if x['date'] else '', reverse=True)[:5]
            values['recent_activities'] = activities
        else:
            values['next_rdv'] = False
            values['consultation_count'] = 0
            values['cnam_expiring_soon'] = False
            values['rendezvous_count'] = 0
            values['ordonnance_count'] = 0
            values['facture_count'] = 0
            values['recent_activities'] = []
            
        return values

    @http.route(['/my/rendezvous', '/my/rendezvous/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_rendezvous(self, page=1, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        patient = request.env['cabinet.patient'].search([('user_id', '=', request.env.user.id)], limit=1)
        
        if not patient:
            return request.redirect('/my')

        Rendezvous = request.env['cabinet.rendezvous']
        today = fields.Date.today()
        domain = [
            ('patient_id', '=', patient.id),
            '|',
                # Qualified past RDVs (termine, annule, absent) — all dates
                ('state', 'in', ['termine', 'annule', 'absent']),
                # Future (or today) en_attente only — excludes past unclosed
                '&', ('state', '=', 'en_attente'), ('date', '>=', today)
        ]

        searchbar_sortings = {
            'date': {'label': 'Date', 'order': 'date desc, heure desc'},
            'state': {'label': 'Statut', 'order': 'state'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        rdv_count = Rendezvous.search_count(domain)
        pager = portal_pager(
            url="/my/rendezvous",
            url_args={'sortby': sortby},
            total=rdv_count,
            page=page,
            step=self._items_per_page
        )
        rendezvous = Rendezvous.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'rendezvous': rendezvous,
            'page_name': 'rendezvous',
            'pager': pager,
            'default_url': '/my/rendezvous',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("cabinet_medical.portal_my_rendezvous", values)

    @http.route(['/my/consultations', '/my/consultations/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_consultations(self, **kw):
        return request.redirect('/my')

    @http.route(['/my/dossier'], type='http', auth="user", website=True)
    def portal_my_dossier(self, **kw):
        """Page 'Mes informations médicales' — lecture seule.
        Expose uniquement les données DÉCLARATIVES du patient :
        allergies, antécédents, traitements chroniques.
        Aucun champ IA (ia_statut, ia_fingerprint, alertes détectées) n'est transmis.
        """
        values = self._prepare_portal_layout_values()
        patient = request.env['cabinet.patient'].search(
            [('user_id', '=', request.env.user.id)], limit=1
        )
        if not patient:
            return request.redirect('/my')

        # Sécurité : seules les données déclaratives sont exposées
        # Les champs IA (ia_statut, ia_fingerprint) restent côté serveur
        values.update({
            'page_name': 'dossier',
            'patient': patient,
            'allergies': patient.allergies or '',
            'antecedents': patient.antecedents or '',
            'traitements_chroniques': patient.traitements_chroniques or '',
        })
        return request.render("cabinet_medical.portal_my_dossier", values)

    @http.route(['/my/ordonnances', '/my/ordonnances/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_ordonnances(self, page=1, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        patient = request.env['cabinet.patient'].search([('user_id', '=', request.env.user.id)], limit=1)
        
        if not patient:
            return request.redirect('/my')

        Prescription = request.env['cabinet.prescription']
        domain = [('patient_id', '=', patient.id)]

        searchbar_sortings = {
            'date': {'label': 'Date', 'order': 'date_prescription desc'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        count = Prescription.search_count(domain)
        pager = portal_pager(
            url="/my/ordonnances",
            url_args={'sortby': sortby},
            total=count,
            page=page,
            step=self._items_per_page
        )
        ordonnances = Prescription.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'ordonnances': ordonnances,
            'page_name': 'ordonnances',
            'pager': pager,
            'default_url': '/my/ordonnances',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("cabinet_medical.portal_my_ordonnances", values)

    @http.route(['/my/ordonnances/download/<int:ordo_id>'], type='http', auth="user", website=True)
    def portal_my_ordonnance_download(self, ordo_id, **kw):
        """Téléchargement sécurisé du PDF officiel de l'ordonnance signée par le patient propriétaire."""
        patient = request.env['cabinet.patient'].search([('user_id', '=', request.env.user.id)], limit=1)
        if not patient:
            return request.redirect('/my')

        prescription = request.env['cabinet.prescription'].search([
            ('id', '=', ordo_id),
            ('patient_id', '=', patient.id)
        ], limit=1)

        if not prescription:
            return request.redirect('/my/ordonnances')

        # Générer le rapport PDF officiel
        pdf_content, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'cabinet_medical.action_report_ordonnance',
            [prescription.id]
        )

        date_str = prescription.date_prescription.strftime('%Y%m%d') if prescription.date_prescription else 'ordonnance'
        filename = f"Ordonnance_{date_str}_{prescription.id}.pdf"
        
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', str(len(pdf_content))),
            ('Content-Disposition', f'attachment; filename="{filename}"')
        ]
        return request.make_response(pdf_content, headers=pdfhttpheaders)

    @http.route(['/my/factures', '/my/factures/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_factures(self, page=1, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        patient = request.env['cabinet.patient'].search([('user_id', '=', request.env.user.id)], limit=1)
        
        if not patient:
            return request.redirect('/my')

        Facture = request.env['cabinet.facture']
        domain = [('patient_id', '=', patient.id)]

        searchbar_sortings = {
            'date': {'label': 'Date', 'order': 'date_facture desc'},
            'name': {'label': 'Référence', 'order': 'name desc'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        count = Facture.search_count(domain)
        pager = portal_pager(
            url="/my/factures",
            url_args={'sortby': sortby},
            total=count,
            page=page,
            step=self._items_per_page
        )
        factures = Facture.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'factures': factures,
            'page_name': 'factures',
            'pager': pager,
            'default_url': '/my/factures',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("cabinet_medical.portal_my_factures", values)

    @http.route(['/my/couverture'], type='http', auth="user", website=True)
    def portal_my_couverture(self, **kw):
        values = self._prepare_portal_layout_values()
        patient = request.env['cabinet.patient'].search([('user_id', '=', request.env.user.id)], limit=1)
        
        if not patient:
            return request.redirect('/my')

        values.update({
            'patient': patient,
            'page_name': 'couverture',
        })
        return request.render("cabinet_medical.portal_my_couverture", values)

    @http.route(['/my/notifications', '/my/notifications/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_notifications(self, page=1, **kw):
        values = self._prepare_portal_layout_values()
        patient = request.env['cabinet.patient'].search([('user_id', '=', request.env.user.id)], limit=1)
        if not patient:
            return request.redirect('/my')

        Notification = request.env['cabinet.notification']
        domain = [('patient_id', '=', patient.id)]

        count = Notification.search_count(domain)
        pager = portal_pager(
            url="/my/notifications",
            total=count,
            page=page,
            step=self._items_per_page
        )
        notifications = Notification.search(domain, order='date desc', limit=self._items_per_page, offset=pager['offset'])

        has_unread = Notification.search_count([('patient_id', '=', patient.id), ('is_read', '=', False)]) > 0
        has_read = Notification.search_count([('patient_id', '=', patient.id), ('is_read', '=', True)]) > 0

        values.update({
            'notifications': notifications,
            'page_name': 'notifications',
            'pager': pager,
            'default_url': '/my/notifications',
            'has_unread': has_unread,
            'has_read': has_read,
        })
        return request.render("cabinet_medical.portal_my_notifications", values)

    @http.route(['/my/notifications/read/<int:notif_id>'], type='http', auth="user", methods=['POST'], website=True)
    def portal_notification_read(self, notif_id, **kw):
        patient = request.env['cabinet.patient'].search([('user_id', '=', request.env.user.id)], limit=1)
        if not patient:
            return request.redirect('/my')

        notif = request.env['cabinet.notification'].search([('id', '=', notif_id), ('patient_id', '=', patient.id)], limit=1)
        if notif:
            notif.is_read = True
            if notif.res_url:
                return request.redirect(notif.res_url)
        return request.redirect('/my/notifications')

    @http.route(['/my/notifications/read_all'], type='http', auth="user", methods=['POST'], website=True)
    def portal_notifications_read_all(self, **kw):
        patient = request.env['cabinet.patient'].search([('user_id', '=', request.env.user.id)], limit=1)
        if not patient:
            return request.redirect('/my')

        unread_notifs = request.env['cabinet.notification'].search([('patient_id', '=', patient.id), ('is_read', '=', False)])
        if unread_notifs:
            unread_notifs.write({'is_read': True})
        
        referer = request.httprequest.headers.get('Referer')
        if referer and '/my' in referer:
            return request.redirect(referer)
        return request.redirect('/my/notifications')

    @http.route(['/my/notifications/delete/<int:notif_id>'], type='http', auth="user", website=True)
    def portal_notification_delete(self, notif_id, **kw):
        patient = request.env['cabinet.patient'].search([('user_id', '=', request.env.user.id)], limit=1)
        if not patient:
            return request.redirect('/my')

        notif = request.env['cabinet.notification'].search([('id', '=', notif_id), ('patient_id', '=', patient.id)], limit=1)
        if notif:
            notif.sudo().unlink()
        return request.redirect('/my/notifications')

    @http.route(['/my/notifications/delete_read'], type='http', auth="user", website=True)
    def portal_notifications_delete_read(self, **kw):
        patient = request.env['cabinet.patient'].search([('user_id', '=', request.env.user.id)], limit=1)
        if not patient:
            return request.redirect('/my')

        read_notifs = request.env['cabinet.notification'].search([('patient_id', '=', patient.id), ('is_read', '=', True)])
        if read_notifs:
            read_notifs.sudo().unlink()
        return request.redirect('/my/notifications')

    @http.route(['/my/account'], type='http', auth='user', website=True)
    def account(self, redirect=None, **post):
        patient = request.env['cabinet.patient'].search([('user_id', '=', request.env.user.id)], limit=1)
        
        # Si ce n'est pas un patient de cabinet médical, conserver le comportement standard Odoo
        if not patient:
            return super().account(redirect=redirect, **post)

        partner = request.env.user.partner_id
        
        # S'assurer que le partner et user sont bien synchronisés avec le nom actuel du patient
        if patient.name and (partner.name != patient.name or request.env.user.name != patient.name):
            partner.sudo().write({'name': patient.name})
            request.env.user.sudo().write({'name': patient.name})

        values = self._prepare_portal_layout_values()
        values.update({
            'error': {},
            'error_message': [],
        })

        if post and request.httprequest.method == 'POST':
            # Validation des champs patient
            error = {}
            error_message = []
            
            name = post.get('name', '').strip().upper()
            email = post.get('email', '').strip()
            phone = post.get('phone', '').strip()
            adresse = post.get('street', '').strip()
            cin = post.get('cin', '').strip()
            # SÉCURITÉ : genre et date_naissance sont réservés au secrétariat/médecin.
            # Ces champs sont INTENTIONNELLEMENT ignorés du POST côté serveur,
            # indépendamment des noms de champs HTML envoyés par le client.
            # Un attaquant ne peut pas les modifier via une requête POST forgée.

            if not name:
                error['name'] = 'missing'
                error_message.append("Le nom complet est obligatoire.")
            if not email:
                error['email'] = 'missing'
                error_message.append("L'adresse email est obligatoire.")
            if phone and (not phone.isdigit() or len(phone) != 8 or phone[0] not in ['2', '4', '5', '7', '9']):
                error['phone'] = 'invalid'
                error_message.append("Le numéro de téléphone doit être un numéro tunisien valide à 8 chiffres (commençant par 2, 4, 5, 7 ou 9).")
            if cin and (not cin.isdigit() or len(cin) != 8):
                error['cin'] = 'invalid'
                error_message.append("Le numéro de CIN doit contenir exactement 8 chiffres.")

            if not error:
                # 1. Mettre à jour les informations personnelles du dossier patient.
                # SÉCURITÉ : genre et date_naissance sont EXCLUS explicitement —
                # modifiables uniquement par le secrétariat depuis le back-office Odoo.
                patient_vals = {
                    'name': name,
                    'email': email,
                    'telephone': phone,
                    'adresse': adresse,
                }
                if cin:
                    patient_vals['cin'] = cin
                patient.sudo().write(patient_vals)

                # 2. Mettre à jour le res.partner et l'utilisateur Odoo
                partner_vals = {
                    'name': name,
                    'email': email,
                    'phone': phone,
                    'street': adresse,
                }
                partner.sudo().write(partner_vals)
                if request.env.user.name != name or request.env.user.email != email:
                    request.env.user.sudo().write({
                        'name': name,
                        'email': email,
                        'login': email,
                    })

                if redirect:
                    return request.redirect(redirect)
                return request.redirect('/my')

            values.update({'error': error, 'error_message': error_message})
            values.update(post)

        # Liste des assurances disponibles pour le select
        assurances = request.env['cabinet.assurance'].sudo().search([])

        values.update({
            'partner': partner,
            'patient': patient,
            'assurances': assurances,
            'page_name': 'my_details',
            'redirect': redirect,
        })

        return request.render("cabinet_medical.portal_my_patient_details", values)


