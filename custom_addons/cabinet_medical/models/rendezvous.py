from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError, AccessError  # type: ignore
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)

class Appointment(models.Model):
    _name = 'cabinet.rendezvous'
    _description = 'Rendez-vous médical'
    _order = 'date asc'
    _rec_name = 'display_patient_name'

    active = fields.Boolean(string='Actif', default=True, help='Désactiver pour archiver le rendez-vous sans le supprimer')

    # Patient (optionnel pour création rapide)
    patient_id = fields.Many2one(
        'cabinet.patient',
        string='Patient',
        required=False,
        ondelete='restrict'
    )
    is_cnam_expired = fields.Boolean(related='patient_id.is_cnam_expired', string='CNAM Expirée', readonly=True)
    is_apci_expired = fields.Boolean(related='patient_id.is_apci_expired', string='APCI Expirée', readonly=True)
    
    # Nom du patient pour création rapide
    patient_name = fields.Char(
        string='Nom du patient',
        required=False,
        help='Utilisé pour les rendez-vous rapides quand le patient n\'existe pas encore'
    )
    
    # Nom du patient affiché (champ unifié)
    display_patient_name = fields.Char(
        string='Nom du patient affiché',
        compute='_compute_display_patient_name',
        store=True
    )

    # Indicateur : RDV rapide sans dossier patient complet
    is_nouveau_patient = fields.Boolean(
        string='Nouveau patient (dossier à compléter)',
        compute='_compute_is_nouveau_patient',
        store=True,
        help='Vrai si le RDV a été créé avec un nom temporaire sans dossier patient existant'
    )

    # Motif rapide saisi à la prise de rendez-vous
    motif_rapide = fields.Char(
        string='Motif (bref)',
        help='Motif rapide saisi par la secrétaire lors de la prise de rendez-vous'
    )



    # Date du rendez-vous
    date = fields.Date(
        string='Date du RDV',
        required=True
    )
    
    date_start_datetime = fields.Datetime(
        string='Date de début (Calculée)',
        compute='_compute_date_start_datetime',
        inverse='_inverse_date_start_datetime',
        store=True,
        help='Date et heure de début calculées pour le calendrier'
    )

    @api.depends('date', 'heure')
    def _compute_date_start_datetime(self):
        from datetime import datetime, time
        import pytz
        for rec in self:
            if rec.date and rec.heure is not False:
                hours = int(rec.heure)
                minutes = int(round((rec.heure - hours) * 60))
                if minutes >= 60:
                    hours += 1
                    minutes = 0
                try:
                    local_dt = datetime.combine(rec.date, time(hours, minutes))
                    user_tz = self.env.user.tz or 'UTC'
                    local_tz = pytz.timezone(user_tz)
                    local_dt = local_tz.localize(local_dt)
                    utc_dt = local_dt.astimezone(pytz.utc)
                    rec.date_start_datetime = fields.Datetime.to_string(utc_dt.replace(tzinfo=None))
                except Exception:
                    rec.date_start_datetime = False
            else:
                rec.date_start_datetime = False

    def _inverse_date_start_datetime(self):
        import pytz
        for rec in self:
            if rec.date_start_datetime:
                user_tz = self.env.user.tz or 'UTC'
                utc_dt = fields.Datetime.from_string(rec.date_start_datetime)
                if utc_dt:
                    if not utc_dt.tzinfo:
                        utc_dt = pytz.utc.localize(utc_dt)
                    local_dt = utc_dt.astimezone(pytz.timezone(user_tz))
                    rec.date = local_dt.date()
                    rec.heure = local_dt.hour + local_dt.minute / 60.0
    
    # Date au format français pour l'affichage
    date_fr = fields.Char(
        string='Date (FR)',
        compute='_compute_date_fr',
        store=True
    )
    
    # Computed fields simples pour contrôler les boutons (non-stored pour calcul dynamique client)
    show_arrive_absent_buttons = fields.Boolean(
        string='Afficher boutons arrivé/absent',
        compute='_compute_show_buttons',
        store=False
    )
    
    show_complete_button = fields.Boolean(
        string='Afficher bouton compléter',
        compute='_compute_show_buttons',
        store=False
    )

    show_cancel_button = fields.Boolean(
        string='Afficher bouton annuler',
        compute='_compute_show_buttons',
        store=False
    )

    show_demarrer_consultation_button = fields.Boolean(
        string='Afficher bouton démarrer consultation',
        compute='_compute_show_buttons',
        store=False
    )

    show_termine_button = fields.Boolean(
        string='Afficher bouton terminé',
        compute='_compute_show_buttons',
        store=False
    )
    
    # Heure du rendez-vous
    heure = fields.Float(
        string='Heure du RDV',
        required=True
    )
    
    # État du rendez-vous
    state = fields.Selection([
        ('en_attente', 'En attente'),
        ('present', 'Présent'),
        ('en_consultation', 'En consultation'),
        ('termine', 'Terminé'),
        ('annule', 'Annulé'),
        ('absent', 'Absent')
    ], string='État', required=True, default='en_attente', readonly=True)
    
    # Type de rendez-vous
    is_urgence = fields.Boolean(string='Urgence', default=False, help='Cochez si c\'est un rendez-vous d\'urgence')
    
    appointment_type = fields.Selection([
        ('normal', 'Normal'),
        ('urgence', 'Urgence')
    ], string='Type de RDV', compute='_compute_appointment_type', store=True)

    @api.depends('is_urgence')
    def _compute_appointment_type(self):
        for rec in self:
            rec.appointment_type = 'urgence' if rec.is_urgence else 'normal'
    
    # Champ calculé pour le compteur
    today_appointments_count = fields.Integer(
        string='RDV aujourd\'hui',
        compute='_compute_today_appointments',
        store=False
    )
    
    calendar_color = fields.Integer(
        string='Couleur Agenda',
        compute='_compute_calendar_color',
        store=True
    )
    
    remaining_slots = fields.Integer(
        string='Places restantes',
        compute='_compute_today_appointments',
        store=False
    )
    
    # Disponibilité pour la date sélectionnée
    date_appointments_count = fields.Integer(
        string='RDV pour cette date',
        compute='_compute_date_appointments',
        store=False
    )
    
    date_remaining_slots = fields.Integer(
        string='Places restantes pour cette date',
        compute='_compute_date_appointments',
        store=False
    )
    
    slot_availability_status = fields.Html(
        string='Statut de disponibilité',
        compute='_compute_slot_availability_status',
        store=False
    )

    # Dossier incomplet : patient sans dossier ou dossier incomplet
    is_dossier_incomplet = fields.Boolean(
        string='Dossier incomplet',
        compute='_compute_is_dossier_incomplet',
        store=False
    )

    # Statut d'affichage pour le portail patient (affiche 'Passé' si RDV antérieur à aujourd'hui et non clôturé)
    portal_state_label = fields.Char(
        string='Statut Portail Patient',
        compute='_compute_portal_state_label',
        store=False
    )
    portal_state_badge_class = fields.Char(
        string='Classe Badge Portail',
        compute='_compute_portal_state_label',
        store=False
    )

    @api.depends('date', 'state')
    def _compute_portal_state_label(self):
        today = fields.Date.today()
        for rec in self:
            is_past = bool(rec.date and rec.date < today)
            if is_past:
                if rec.state == 'termine':
                    rec.portal_state_label = "Terminé"
                    rec.portal_state_badge_class = "text-bg-success"
                elif rec.state == 'annule':
                    rec.portal_state_label = "Annulé"
                    rec.portal_state_badge_class = "text-bg-danger"
                elif rec.state == 'absent':
                    rec.portal_state_label = "Absent"
                    rec.portal_state_badge_class = "bg-secondary text-white"
                else:
                    # Past unclosed (en_attente not yet closed by secretary) —
                    # these are excluded from the patient portal by the domain filter.
                    # This fallback is kept for completeness only (e.g. secretary views).
                    rec.portal_state_label = "Passé"
                    rec.portal_state_badge_class = "bg-secondary text-white"
            else:
                if rec.state == 'en_attente':
                    rec.portal_state_label = "En attente"
                    rec.portal_state_badge_class = "text-bg-warning"
                elif rec.state in ('present', 'en_consultation'):
                    rec.portal_state_label = "Confirmé"
                    rec.portal_state_badge_class = "text-bg-success"
                elif rec.state == 'termine':
                    rec.portal_state_label = "Terminé"
                    rec.portal_state_badge_class = "text-bg-success"
                elif rec.state == 'annule':
                    rec.portal_state_label = "Annulé"
                    rec.portal_state_badge_class = "text-bg-danger"
                elif rec.state == 'absent':
                    rec.portal_state_label = "Absent"
                    rec.portal_state_badge_class = "bg-secondary text-white"
                else:
                    rec.portal_state_label = dict(self._fields['state'].selection).get(rec.state, rec.state or '')
                    rec.portal_state_badge_class = "text-bg-light"

    # -------------------------------------------------------------
    # Étape 1 : Détection des RDV passés non clôturés
    # -------------------------------------------------------------
    is_past_unclosed = fields.Boolean(
        string='RDV passé non clôturé',
        compute='_compute_is_past_unclosed',
        search='_search_is_past_unclosed',
        help='Vrai si la date du RDV est antérieure à aujourd\'hui et le statut est resté En attente'
    )

    @api.depends('date', 'state')
    def _compute_is_past_unclosed(self):
        today = fields.Date.today()
        for rec in self:
            rec.is_past_unclosed = bool(rec.date and rec.date < today and rec.state == 'en_attente')

    def _search_is_past_unclosed(self, operator, value):
        today = fields.Date.today()
        if operator in ('=', '!='):
            expected = (value and operator == '=') or (not value and operator == '!=')
            if expected:
                return [('date', '<', today), ('state', '=', 'en_attente')]
            else:
                return ['|', ('date', '>=', today), ('state', '!=', 'en_attente')]
        return []

    @api.model
    def action_open_unclosed_past_appointments(self):
        """Action pour ouvrir la liste des RDV passés non clôturés"""
        today = fields.Date.today()
        return {
            'name': '⚠️ Rendez-vous passés à clôturer',
            'type': 'ir.actions.act_window',
            'res_model': 'cabinet.rendezvous',
            'view_mode': 'tree,form',
            'domain': [('date', '<', today), ('state', '=', 'en_attente')],
            'context': {'search_default_en_attente': 1},
        }

    @api.model
    def get_unclosed_past_count(self):
        """Compte les RDV passés restés en attente"""
        today = fields.Date.today()
        return self.search_count([('date', '<', today), ('state', '=', 'en_attente')])

    # -------------------------------------------------------------
    # Étape 2 : Prédiction de No-Show (Machine Learning PoC)
    # -------------------------------------------------------------
    no_show_risk_score = fields.Float(
        string='Risque No-Show (%)',
        compute='_compute_no_show_risk',
        store=True,
        help='Estimation probabiliste du risque d\'absence (Modèle Random Forest PoC)'
    )
    no_show_risk_level = fields.Selection([
        ('faible', 'Faible (< 25%)'),
        ('moyen', 'Moyen (25-45%)'),
        ('eleve', 'Élevé (> 45%)')
    ], string='Niveau de Risque', compute='_compute_no_show_risk', store=True)

    no_show_risk_badge = fields.Html(
        string='Risque No-Show',
        compute='_compute_no_show_risk_badge',
        store=False
    )
    no_show_risk_factors = fields.Char(
        string='Facteurs de risque',
        compute='_compute_no_show_risk_badge',
        store=False
    )

    @api.depends('date', 'heure', 'create_date', 'patient_id', 'patient_name', 'is_urgence', 'is_nouveau_patient', 'state')
    def _compute_no_show_risk(self):
        from .ml_no_show import predict_no_show_risk
        today = fields.Date.today()
        for rec in self:
            has_patient = bool(rec.patient_id) or bool(rec.patient_name and rec.patient_name.strip())
            if not has_patient:
                rec.no_show_risk_score = 0.0
                rec.no_show_risk_level = False
                continue

            if rec.create_date and rec.date:
                create_d = fields.Date.to_date(rec.create_date)
                lead_days = max(0, (rec.date - create_d).days)
            elif rec.date:
                lead_days = max(0, (rec.date - today).days)
            else:
                lead_days = 0

            day_of_week = rec.date.weekday() if rec.date else 0
            is_afternoon = 1 if (rec.heure and rec.heure >= 13.0) else 0
            is_urgence = 1 if rec.is_urgence else 0
            is_nouveau = 1 if (rec.is_nouveau_patient or not rec.patient_id) else 0

            prev_count = 0
            hist_rate = 0.0
            if rec.patient_id:
                rec_id = rec._origin.id if (hasattr(rec, '_origin') and rec._origin and rec._origin.id) else (rec.id or 0)
                past_rdvs = self.search([
                    ('patient_id', '=', rec.patient_id.id),
                    ('id', '!=', rec_id),
                    ('state', 'in', ['present', 'en_consultation', 'termine', 'absent', 'annule'])
                ])
                prev_count = len(past_rdvs)
                if prev_count > 0:
                    absent_count = len(past_rdvs.filtered(lambda r: r.state == 'absent'))
                    hist_rate = float(absent_count) / float(prev_count)

            score, level, _ = predict_no_show_risk(
                lead_days=lead_days,
                day_of_week=day_of_week,
                is_afternoon=is_afternoon,
                is_urgence=is_urgence,
                is_nouveau_patient=is_nouveau,
                patient_previous_rdv_count=prev_count,
                patient_historical_noshow_rate=hist_rate
            )

            rec.no_show_risk_score = score
            rec.no_show_risk_level = level

    @api.depends('no_show_risk_score', 'no_show_risk_level', 'date', 'create_date', 'patient_id', 'patient_name', 'is_urgence', 'is_nouveau_patient')
    def _compute_no_show_risk_badge(self):
        from .ml_no_show import predict_no_show_risk
        today = fields.Date.today()
        for rec in self:
            has_patient = bool(rec.patient_id) or bool(rec.patient_name and rec.patient_name.strip())
            if not has_patient:
                rec.no_show_risk_factors = False
                rec.no_show_risk_badge = (
                    '<span style="display:inline-flex; align-items:center; gap:5px; padding:3px 10px; '
                    'border-radius:12px; font-weight:500; font-size:12px; color:#6c757d; background-color:#f8f9fa; '
                    'border:1px dashed #ced4da;">'
                    '<i class="fa fa-info-circle"></i> Sélectionnez un patient pour voir l\'estimation du risque'
                    '</span>'
                )
                continue

            score = rec.no_show_risk_score or 0.0
            level = rec.no_show_risk_level or 'faible'

            if rec.create_date and rec.date:
                create_d = fields.Date.to_date(rec.create_date)
                lead_days = max(0, (rec.date - create_d).days)
            elif rec.date:
                lead_days = max(0, (rec.date - today).days)
            else:
                lead_days = 0

            day_of_week = rec.date.weekday() if rec.date else 0
            is_afternoon = 1 if (rec.heure and rec.heure >= 13.0) else 0
            is_urgence = 1 if rec.is_urgence else 0
            is_nouveau = 1 if (rec.is_nouveau_patient or not rec.patient_id) else 0

            prev_count = 0
            hist_rate = 0.0
            if rec.patient_id:
                rec_id = rec._origin.id if (hasattr(rec, '_origin') and rec._origin and rec._origin.id) else (rec.id or 0)
                past_rdvs = self.search([
                    ('patient_id', '=', rec.patient_id.id),
                    ('id', '!=', rec_id),
                    ('state', 'in', ['present', 'en_consultation', 'termine', 'absent', 'annule'])
                ])
                prev_count = len(past_rdvs)
                if prev_count > 0:
                    absent_count = len(past_rdvs.filtered(lambda r: r.state == 'absent'))
                    hist_rate = float(absent_count) / float(prev_count)

            _, _, factors = predict_no_show_risk(
                lead_days=lead_days,
                day_of_week=day_of_week,
                is_afternoon=is_afternoon,
                is_urgence=is_urgence,
                is_nouveau_patient=is_nouveau,
                patient_previous_rdv_count=prev_count,
                patient_historical_noshow_rate=hist_rate
            )

            rec.no_show_risk_factors = " • ".join(factors)

            if level == 'faible':
                color = "#198754"
                bg = "#d1e7dd"
                icon = "fa-check-circle"
                label = f"Faible ({score}%)"
            elif level == 'moyen':
                color = "#fd7e14"
                bg = "#ffe5d0"
                icon = "fa-exclamation-circle"
                label = f"Moyen ({score}%)"
            else:
                color = "#dc3545"
                bg = "#f8d7da"
                icon = "fa-warning"
                label = f"Élevé ({score}%)"

            rec.no_show_risk_badge = (
                f'<span style="display:inline-flex; align-items:center; gap:5px; padding:3px 8px; '
                f'border-radius:12px; font-weight:600; font-size:12px; color:{color}; background-color:{bg}; '
                f'border:1px solid {color}33;">'
                f'<i class="fa {icon}"></i> {label}'
                f'</span>'
            )

    @api.depends('date', 'heure', 'is_urgence')
    def _compute_slot_availability_status(self):
        for rec in self:
            if not rec.date and not rec.heure:
                rec.slot_availability_status = ''
                continue

            # Mask availability message if the appointment is already saved and slot is not being modified
            rec_id = getattr(rec, 'id', False)
            is_saved = isinstance(rec_id, int)
            origin = getattr(rec, '_origin', False)
            is_modifying_slot = False
            if is_saved and origin and not isinstance(origin, bool):
                orig_date = getattr(origin, 'date', False)
                orig_heure = getattr(origin, 'heure', False)
                is_modifying_slot = (orig_date != rec.date or orig_heure != rec.heure)

            if is_saved and not is_modifying_slot:
                rec.slot_availability_status = ''
                continue

            params = self.env['ir.config_parameter'].sudo()
            max_normal = int(params.get_param('cabinet.max_rdv_normal', '20'))
            max_urgence = int(params.get_param('cabinet.max_rdv_urgence', '2'))
            heure_debut = float(params.get_param('cabinet.heure_debut', '8.0'))
            heure_fin = float(params.get_param('cabinet.heure_fin', '17.0'))
            work_days_str = params.get_param('cabinet.work_days', '0,1,2,3,4,5')
            work_days = [int(d.strip()) for d in work_days_str.split(',') if d.strip()]

            # 1. Vérifier le jour travaillé
            if rec.date:
                weekday = rec.date.weekday()
                if weekday not in work_days:
                    rec.slot_availability_status = (
                        '<div style="color:#dc3545;font-weight:bold;margin-top:6px;padding:6px 10px;'
                        'background:#fff5f5;border-radius:6px;border-left:4px solid #dc3545;">'
                        '❌ Le médecin ne travaille pas ce jour.</div>'
                    )
                    continue

            # 2. Vérifier les heures de travail
            if rec.heure is not False and rec.heure:
                if rec.heure < heure_debut or rec.heure > heure_fin:
                    h_d = f"{int(heure_debut):02d}:{int((heure_debut % 1)*60):02d}"
                    h_f = f"{int(heure_fin):02d}:{int((heure_fin % 1)*60):02d}"
                    rec.slot_availability_status = (
                        f'<div style="color:#dc3545;font-weight:bold;margin-top:6px;padding:6px 10px;'
                        f'background:#fff5f5;border-radius:6px;border-left:4px solid #dc3545;">'
                        f'❌ Hors heures de travail ({h_d} – {h_f}).</div>'
                    )
                    continue

            if not rec.date or rec.heure is False:
                rec.slot_availability_status = ''
                continue

            # Base domain for counting (exclude self)
            base_domain_kwargs = []
            rec_id = False
            if getattr(rec, '_origin', False) and getattr(rec._origin, 'id', False):
                rec_id = rec._origin.id
            elif getattr(rec, 'id', False):
                rec_id = rec.id
            if isinstance(rec_id, int):
                base_domain_kwargs.append(('id', '!=', rec_id))

            # 4. Vérifier créneau occupé
            domain_slot = [
                ('date', '=', rec.date),
                ('heure', '=', rec.heure),
                ('state', 'not in', ['annule', 'absent'])
            ] + base_domain_kwargs
            duplicate = self.search_count(domain_slot)
            if duplicate > 0:
                rec.slot_availability_status = (
                    '<div style="color:#721c24;font-weight:bold;margin-top:6px;padding:6px 10px;'
                    'background:#f8d7da;border-radius:6px;border-left:4px solid #f5c6cb;">'
                    '❌ Créneau déjà occupé — choisissez une autre heure.</div>'
                )
                continue

            # 5. Calculer places restantes pour ce jour
            domain_day = [
                ('date', '=', rec.date),
                ('state', 'not in', ['annule', 'absent']),
                ('is_urgence', '=', False)
            ] + base_domain_kwargs
            normal_count = self.search_count(domain_day)
            remaining_normal = max(0, max_normal - normal_count)

            # 6. Créneau urgence dispo
            domain_urg = [
                ('date', '=', rec.date),
                ('state', 'not in', ['annule', 'absent']),
                ('is_urgence', '=', True)
            ] + base_domain_kwargs
            urg_count = self.search_count(domain_urg)
            remaining_urg = max(0, max_urgence - urg_count)

            if rec.is_urgence:
                if remaining_urg <= 0:
                    rec.slot_availability_status = (
                        f'<div style="color:#856404;font-weight:bold;margin-top:6px;padding:6px 10px;'
                        f'background:#fff3cd;border-radius:6px;border-left:4px solid #856404;">'
                        f'⚠️ Quota d\'urgences complet ({max_urgence}/{max_urgence}). L\'enregistrement sera bloqué. '
                        f'(Places normales: {remaining_normal} restantes)</div>'
                    )
                else:
                    rec.slot_availability_status = (
                        f'<div style="color:#155724;font-weight:bold;margin-top:6px;padding:6px 10px;'
                        f'background:#d4edda;border-radius:6px;border-left:4px solid #155724;">'
                        f'✅ Créneau disponible — {remaining_urg} urgence(s) et {remaining_normal} place(s) normale(s).</div>'
                    )
            else:
                if remaining_normal <= 0:
                    rec.slot_availability_status = (
                        f'<div style="color:#856404;font-weight:bold;margin-top:6px;padding:6px 10px;'
                        f'background:#fff3cd;border-radius:6px;border-left:4px solid #856404;">'
                        f'⚠️ Quota journalier normal atteint ({max_normal}/{max_normal}). L\'enregistrement sera bloqué. '
                        f'(Urgences: {remaining_urg} restantes)</div>'
                    )
                else:
                    rec.slot_availability_status = (
                        f'<div style="color:#155724;font-weight:bold;margin-top:6px;padding:6px 10px;'
                        f'background:#d4edda;border-radius:6px;border-left:4px solid #155724;">'
                        f'✅ Créneau disponible — {remaining_normal} place(s) normale(s) et {remaining_urg} urgence(s).</div>'
                    )

    @api.constrains('date', 'is_urgence')
    def _check_appointments_limit(self):
        for rec in self:
            if rec.date:
                max_normal = int(self.env['ir.config_parameter'].sudo().get_param('cabinet.max_rdv_normal', '20'))
                max_urgence = int(self.env['ir.config_parameter'].sudo().get_param('cabinet.max_rdv_urgence', '2'))
                max_total = max_normal + max_urgence
                
                domain_all = [('date', '=', rec.date), ('state', 'not in', ['annule', 'absent'])]
                domain_normal = [('date', '=', rec.date), ('state', 'not in', ['annule', 'absent']), ('is_urgence', '=', False)]
                
                rec_id = False
                if getattr(rec, '_origin', False) and getattr(rec._origin, 'id', False):
                    rec_id = rec._origin.id
                elif getattr(rec, 'id', False):
                    rec_id = rec.id
                if isinstance(rec_id, int):
                    domain_all.append(('id', '!=', rec_id))
                    domain_normal.append(('id', '!=', rec_id))
                
                total_count = self.search_count(domain_all)
                normal_count = self.search_count(domain_normal)
                
                if not rec.is_urgence and normal_count >= max_normal:
                    raise ValidationError(f"Plus de créneau normal disponible ce jour ({max_normal}/{max_normal} atteint)")
                elif total_count >= max_total:
                    raise ValidationError(f"Capacité totale de {max_total} rendez-vous atteinte.")

    @api.constrains('date', 'is_urgence')
    def _check_urgence_limit(self):
        """Vérifier la limite de rendez-vous d'urgence par jour"""
        for rec in self:
            if rec.date and rec.is_urgence:
                max_urgence = int(self.env['ir.config_parameter'].sudo().get_param('cabinet.max_rdv_urgence', '2'))
                domain = [
                    ('date', '=', rec.date),
                    ('is_urgence', '=', True),
                    ('state', 'not in', ['annule', 'absent'])
                ]
                rec_id = False
                if getattr(rec, '_origin', False) and getattr(rec._origin, 'id', False):
                    rec_id = rec._origin.id
                elif getattr(rec, 'id', False):
                    rec_id = rec.id
                if isinstance(rec_id, int):
                    domain.append(('id', '!=', rec_id))
                urgence_count = self.search_count(domain)
                if urgence_count >= max_urgence:
                    raise ValidationError(f"Quota urgence atteint pour cette date ({max_urgence}/{max_urgence} atteint)")
    
    @api.constrains('date', 'patient_id', 'patient_name')
    def _check_patient_same_day(self):
        """Vérifier qu'un patient n'a pas déjà un rendez-vous le même jour"""
        for rec in self:
            if rec.date:
                # Vérifier pour les patients existants
                if rec.patient_id:
                    domain = [
                        ('date', '=', rec.date),
                        ('patient_id', '=', rec.patient_id.id),
                        ('state', 'not in', ['annule', 'absent'])
                    ]
                # Vérifier pour les patients avec nom simple
                elif rec.patient_name:
                    domain = [
                        ('date', '=', rec.date),
                        ('patient_name', '=', rec.patient_name),
                        ('patient_id', '=', False),
                        ('state', 'not in', ['annule', 'absent'])
                    ]
                else:
                    continue
                
                rec_id = False
                if getattr(rec, '_origin', False) and getattr(rec._origin, 'id', False):
                    rec_id = rec._origin.id
                elif getattr(rec, 'id', False):
                    rec_id = rec.id
                if isinstance(rec_id, int):
                    domain.append(('id', '!=', rec_id))  # type: ignore
                
                existing = self.search_count(domain)
                if existing > 0:
                    raise ValidationError("Ce patient a déjà un rendez-vous programmé pour cette date")
    
    @api.constrains('date', 'heure')
    def _check_duplicate_appointment(self):
        """Vérifier qu'il n'y a pas déjà un rendez-vous à la même heure et date"""
        for rec in self:
            if rec.date and rec.heure:
                domain = [
                    ('date', '=', rec.date),
                    ('heure', '=', rec.heure),
                    ('state', 'not in', ['annule', 'absent'])
                ]
                rec_id = False
                if getattr(rec, '_origin', False) and getattr(rec._origin, 'id', False):
                    rec_id = rec._origin.id
                elif getattr(rec, 'id', False):
                    rec_id = rec.id
                if isinstance(rec_id, int):
                    domain.append(('id', '!=', rec_id))  # type: ignore
                duplicate = self.search_count(domain)
                if duplicate > 0:
                    raise ValidationError("Un rendez-vous existe déjà à cette heure")

    def _format_float_time(self, float_time):
        """Formate une heure au format float (ex: 10.5) en chaîne (ex: 10:30)"""
        hours = int(float_time)
        minutes = int(round((float_time - hours) * 60))
        return f"{hours:02d}:{minutes:02d}"

    @api.onchange('date', 'heure')
    def _onchange_date_heure(self):
        """Avertir immédiatement si le créneau est déjà pris par un autre patient"""
        for rec in self:
            if rec.date and rec.heure:
                domain = [
                    ('date', '=', rec.date),
                    ('heure', '=', rec.heure),
                    ('state', 'not in', ['annule', 'absent'])
                ]
                rec_id = False
                if getattr(rec, '_origin', False) and getattr(rec._origin, 'id', False):
                    rec_id = rec._origin.id
                elif getattr(rec, 'id', False):
                    rec_id = rec.id
                if isinstance(rec_id, int):
                    domain.append(('id', '!=', rec_id))  # type: ignore
                
                duplicate = self.env['cabinet.rendezvous'].search(domain, limit=1)
                if duplicate:
                    patient_name = duplicate.display_patient_name or "un autre patient"
                    date_str = rec.date_fr or rec.date.strftime('%d/%m/%Y')
                    time_str = self._format_float_time(rec.heure)
                    return {
                        'warning': {
                            'title': '⚠️ Créneau déjà occupé !',
                            'message': f"Ce créneau ({date_str} à {time_str}) est déjà réservé pour {patient_name}."
                        }
                    }
    
    @api.depends('patient_id', 'patient_name')
    def _compute_display_patient_name(self):
        """Calculer le nom du patient à afficher de manière unifiée"""
        for rec in self:
            if rec.patient_id:
                rec.display_patient_name = rec.patient_id.name
            elif rec.patient_name:
                rec.display_patient_name = rec.patient_name
            else:
                rec.display_patient_name = ''

    @api.depends('patient_id', 'patient_name')
    def _compute_is_nouveau_patient(self):
        """Vrai si le RDV a été créé avec un nom temporaire sans dossier existant"""
        for rec in self:
            rec.is_nouveau_patient = bool(rec.patient_name) and not bool(rec.patient_id)
    
    @api.constrains('patient_id', 'patient_name', 'date', 'date_start_datetime')
    def _check_patient_info(self):
        """Vérifier qu'il y a soit un patient existant soit un nom de patient"""
        for rec in self:
            if not rec.patient_id and not rec.patient_name:
                raise ValidationError(
                    "Vous devez soit sélectionner un patient existant, "
                    "soit entrer le nom du patient pour un rendez-vous rapide."
                )
            # Permettre la transition de patient_name vers patient_id lors de la création
            # mais vérifier que patient_name correspond bien au patient lié
            if rec.patient_id and rec.patient_name:
                # Vérifier si le nom correspond au patient lié
                if rec.patient_id.name.lower() != rec.patient_name.lower():
                    raise ValidationError(
                        "Le nom du patient ne correspond pas au patient sélectionné."
                    )
    
    @api.model
    def default_get(self, fields_list):
        res = super(Appointment, self).default_get(fields_list)
        
        # Récupérer la date et l'heure à partir du contexte du calendrier
        default_date_val = self._context.get('default_date_start_datetime') or self._context.get('default_date')
        if default_date_val:
            dt = False
            from datetime import datetime, date
            if isinstance(default_date_val, str):
                try:
                    dt = fields.Datetime.from_string(default_date_val)
                except Exception:
                    try:
                        dt = fields.Date.from_string(default_date_val)
                    except Exception:
                        pass
            elif isinstance(default_date_val, datetime):
                dt = default_date_val
            elif isinstance(default_date_val, date):
                dt = datetime.combine(default_date_val, datetime.min.time())
            
            if dt:
                import pytz
                user_tz = self.env.user.tz or 'UTC'
                try:
                    if isinstance(dt, datetime):
                        if not dt.tzinfo:
                            dt = pytz.utc.localize(dt)
                        local_dt = dt.astimezone(pytz.timezone(user_tz))
                    else:
                        local_dt = dt

                    if 'date' in fields_list and not res.get('date'):
                        res['date'] = local_dt.date() if isinstance(local_dt, datetime) else local_dt
                    
                    if 'heure' in fields_list and not res.get('heure'):
                        # Vérifier s'il y a une heure spécifiée dans le contexte original
                        has_time = False
                        if isinstance(default_date_val, str) and ':' in default_date_val:
                            has_time = True
                        elif isinstance(default_date_val, datetime) and (default_date_val.hour > 0 or default_date_val.minute > 0):
                            has_time = True
                        
                        if has_time and isinstance(local_dt, datetime):
                            res['heure'] = local_dt.hour + local_dt.minute / 60.0
                except Exception:
                    pass
        return res

    @api.model_create_multi
    def create(self, vals_list):
        import traceback
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info("========== RENDEZVOUS CREATE CALLED ==========")
        _logger.info(f"VALS: {vals_list}")
        _logger.info("TRACEBACK:\n" + "".join(traceback.format_stack()))
        
        for vals in vals_list:
            if 'name' in vals:
                if not vals.get('patient_name'):
                    vals['patient_name'] = vals['name']
                vals.pop('name', None)
                
            # Création automatique du patient si seul le nom est fourni
            if vals.get('patient_name') and not vals.get('patient_id'):
                patient = self.env['cabinet.patient'].create({'name': vals['patient_name']})
                vals['patient_id'] = patient.id
                
        records = super(Appointment, self).create(vals_list)
        
        for record in records:
            if record.patient_id and record.state == 'present':
                self.env['cabinet.notification'].create_notification(
                    patient_id=record.patient_id.id,
                    title="Arrivée enregistrée",
                    message="Votre présence au cabinet a été enregistrée. Votre consultation sera prise en charge prochainement.",
                    notif_type='rdv_present',
                    res_url='/my/rendezvous'
                )
        return records

    def write(self, vals):
        if 'name' in vals:
            if not vals.get('patient_name'):
                vals['patient_name'] = vals['name']
            vals.pop('name', None)
            
        # Création auto si on modifie le rendez-vous en ajoutant un nom sans patient_id
        if vals.get('patient_name') and not vals.get('patient_id'):
            for rec in self:
                if not rec.patient_id:
                    patient = self.env['cabinet.patient'].create({'name': vals['patient_name']})
                    vals['patient_id'] = patient.id
                    break # On crée un seul patient même si on modifie un lot de RDV
                    
        # Store state, date, and hour for comparison before write
        pre_vals = {getattr(rec, 'id'): (rec.state, rec.date, rec.heure, getattr(rec.patient_id, 'id') or False) for rec in self}
        
        res = super(Appointment, self).write(vals)
        
        # Track changes and notify
        for record in self:
            if not record.patient_id:
                continue
                
            old_state, old_date, old_heure, old_patient_id = pre_vals.get(getattr(record, 'id'), (False, False, False, False))
            
            # 1. State changes
            if 'state' in vals and old_state != record.state:
                if record.state == 'present':
                    self.env['cabinet.notification'].create_notification(
                        patient_id=record.patient_id.id,
                        title="Arrivée enregistrée",
                        message="Votre présence au cabinet a été enregistrée. Votre consultation sera prise en charge prochainement.",
                        notif_type='rdv_present',
                        res_url='/my/rendezvous'
                    )
                elif record.state in ('annule', 'absent'):
                    self.env['cabinet.notification'].create_notification(
                        patient_id=record.patient_id.id,
                        title="Rendez-vous annulé",
                        message=f"Votre rendez-vous du {record.date_fr} à {record._format_float_time(record.heure)} a été annulé.",
                        notif_type='rdv_annule',
                        res_url='/my/rendezvous',
                        critical=True,
                        res_model='cabinet.rendezvous',
                        res_id=getattr(record, 'id')
                    )
            
            # 2. Date or hour changes (only if it was already created)
            if ('date' in vals or 'heure' in vals) and (old_date and old_heure) and (old_date != record.date or old_heure != record.heure):
                self.env['cabinet.notification'].create_notification(
                    patient_id=record.patient_id.id,
                    title="Rendez-vous reporté",
                    message=f"Votre rendez-vous a été reporté au {record.date_fr} à {record._format_float_time(record.heure)}.",
                    notif_type='rdv_reporte',
                    res_url='/my/rendezvous',
                    critical=True,
                    res_model='cabinet.rendezvous',
                    res_id=getattr(record, 'id')
                )
        return res

    @api.model
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        params = self._context.get('params', {})
        view_type = params.get('view_type') or self._context.get('view_type')
        
        if view_type in ('list', 'tree'):
            # Médecin
            if self.env.user.has_group('cabinet_medical.group_medecin'):
                domain = domain + [('is_nouveau_patient', '=', False)]
                    
        return super(Appointment, self).web_search_read(domain, specification, offset=offset, limit=limit, order=order, count_limit=count_limit)  # type: ignore
    
    def action_creer_patient_complet(self):
        """Ouvrir directement la fiche du patient pour compléter son dossier."""
        self.ensure_one()

        # Le patient a été auto-créé, on ouvre donc sa fiche
        if not self.patient_id:
            return False

        return {
            'name': 'Compléter le dossier patient',
            'type': 'ir.actions.act_window',
            'res_model': 'cabinet.patient',
            'res_id': self.patient_id.id,
            'views': [(False, 'form')],
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'form_view_initial_mode': 'edit',
            }
        }
    
    def action_creer_rendez_avec_patient(self):
        """Créer un nouveau rendez-vous avec le nom du patient pré-rempli"""
        self.ensure_one()
        patient_name = self.display_patient_name
        return {
            'name': 'Nouveau rendez-vous',
            'type': 'ir.actions.act_window',
            'res_model': 'cabinet.rendezvous',
            'views': [(False, 'form')],
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_patient_name': patient_name,
                'form_view_initial_mode': 'edit',
            }
        }

    # Actions pour les boutons
    def action_patient_arrive(self):
        """Marquer le patient comme arrivé (présent) et rafraîchir la vue.
        Retourne une action client qui déclenche le rechargement du formulaire.
        """
        self.ensure_one()
        self.state = 'present'
        # Forcer le recalcul des champs dépendants (boutons)
        self._compute_show_buttons()
        # Retourner l'action de rechargement pour mettre à jour l'interface
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_demarrer_consultation(self):
        """Marquer le patient comme étant en consultation et ouvrir la fiche de consultation"""
        from datetime import datetime
        self.ensure_one()
        self.state = 'en_consultation'
        self._compute_show_buttons()
        
        # 1. Chercher si une consultation existe déjà aujourd'hui pour ce patient (pour éviter les doublons)
        today_start = datetime.now().replace(hour=0, minute=0, second=0)
        today_end = datetime.now().replace(hour=23, minute=59, second=59)
        existing_consult = self.env['cabinet.consultation'].search([
            ('patient_id', '=', self.patient_id.id),
            ('date_consultation', '>=', today_start),
            ('date_consultation', '<=', today_end)
        ], limit=1)
        
        if existing_consult:
            consultation_id = existing_consult.id
        else:
            # 2. Créer DIRECTEMENT la consultation dans la base de données
            new_consult = self.env['cabinet.consultation'].create({
                'patient_id': self.patient_id.id,
                'rdv_id': self.id,  # type: ignore
                'motif': "Consultation programmée", # Remplit le champ obligatoire
            })
            consultation_id = new_consult.id
            
        # 3. Ouvrir la consultation (qui est déjà sauvegardée !)
        return {
            'name': 'Démarrer consultation',
            'type': 'ir.actions.act_window',
            'res_model': 'cabinet.consultation',
            'res_id': consultation_id,
            'views': [(False, 'form')],
            'view_mode': 'form',
            'target': 'current',
        }

    def action_ouvrir_consultation(self):
        """Rouvrir la fiche de consultation existante pour ce rendez-vous."""
        self.ensure_one()
        # Chercher la consultation liée à ce rdv
        consult = self.env['cabinet.consultation'].search([('rdv_id', '=', self.id)], limit=1)  # type: ignore
        if not consult:
            # Fallback si rdv_id n'était pas rempli mais même patient/date
            from datetime import datetime
            today_start = datetime.now().replace(hour=0, minute=0, second=0)
            today_end = datetime.now().replace(hour=23, minute=59, second=59)
            consult = self.env['cabinet.consultation'].search([
                ('patient_id', '=', self.patient_id.id),
                ('date_consultation', '>=', today_start),
                ('date_consultation', '<=', today_end)
            ], limit=1)
            
        if consult:
            return {
                'name': 'Consultation',
                'type': 'ir.actions.act_window',
                'res_model': 'cabinet.consultation',
                'res_id': consult.id,
                'views': [(False, 'form')],
                'view_mode': 'form',
                'target': 'current',
            }

    def action_termine(self):
        """Marquer le rendez-vous comme terminé"""
        self.ensure_one()
        self.state = 'termine'
        self._compute_show_buttons()
        
        # Ouvrir la fiche du patient lié pour compléter les informations
        if self.patient_id:
            return {
                'name': 'Compléter la fiche patient',
                'type': 'ir.actions.act_window',
                'res_model': 'cabinet.patient',
                'res_id': self.patient_id.id,
                'views': [(False, 'form')],
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'form_view_initial_mode': 'edit',
                }
            }
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }
    
    def action_annuler(self):
        """Annuler le rendez-vous"""
        self.ensure_one()
        if not (self.env.user._is_superuser() or self.env.user.id == 1 or self.env.user.has_group('cabinet_medical.group_secretaire')):
            raise AccessError("Seule la Secrétaire peut annuler un rendez-vous ou marquer un patient absent.")
        if self.state not in ('en_attente', 'present'):
            raise ValidationError("Ce rendez-vous ne peut plus être annulé dans son état actuel.")
        self.state = 'annule'
        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }

    def action_patient_absent(self):
        """Marquer le patient comme absent"""
        self.ensure_one()
        if not (self.env.user._is_superuser() or self.env.user.id == 1 or self.env.user.has_group('cabinet_medical.group_secretaire')):
            raise AccessError("Seule la Secrétaire peut annuler un rendez-vous ou marquer un patient absent.")
        self.state = 'absent'
        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }

    def action_save(self):
        """Méthode de sauvegarde explicite pour le popup de création"""
        self.ensure_one()
        return {'type': 'ir.actions.act_window_close'}
    
    
# ... (reste du code inchangé)
    @api.depends('date')
    def _compute_today_appointments(self):
        for rec in self:
            today = fields.Date.today()
            # Compter les RDV d'aujourd'hui (sauf annulés et absents)
            today_count = self.search_count([
                ('date', '=', today),
                ('state', 'not in', ['annule', 'absent'])
            ])
            rec.today_appointments_count = today_count
            
            max_normal = int(self.env['ir.config_parameter'].sudo().get_param('cabinet.max_rdv_normal', '20'))
            max_urgence = int(self.env['ir.config_parameter'].sudo().get_param('cabinet.max_rdv_urgence', '2'))
            max_total = max_normal + max_urgence

            # Afficher les places restantes normales ou totales
            if today_count < max_normal:
                rec.remaining_slots = max(0, max_normal - today_count)
            else:
                rec.remaining_slots = max(0, max_total - today_count)
    
    @api.depends('patient_id', 'patient_name', 'patient_id.is_dossier_complet')
    def _compute_is_dossier_incomplet(self):
        """Vrai si le patient n'a pas de dossier ou si son dossier est incomplet"""
        for rec in self:
            if not rec.patient_id:
                # Patient sans dossier (nom temporaire)
                rec.is_dossier_incomplet = bool(rec.patient_name)
            else:
                rec.is_dossier_incomplet = not rec.patient_id.is_dossier_complet

    @api.depends('date')
    def _compute_date_fr(self):
        """Calculer la date au format français"""
        for rec in self:
            if rec.date:
                rec.date_fr = rec.date.strftime('%d/%m/%Y')
            else:
                rec.date_fr = ''
    
    @api.depends('state', 'patient_name', 'patient_id', 'patient_id.is_dossier_complet')
    def _compute_show_buttons(self):
        """Calculer la visibilité des boutons selon l'état du rendez-vous.
        On utilise isinstance(rec.id, int) pour détecter si l'enregistrement est
        réellement sauvegardé en base. Pendant la création, Odoo attribue un NewId
        (non entier), ce qui rend cette vérification fiable même en contexte onchange.
        """
        for rec in self:
            # Un enregistrement réellement sauvegardé a un ID entier
            rec_id = getattr(rec, 'id', False)
            is_saved = isinstance(rec_id, int)

            # État 'en_attente' → boutons Arrivé / Absent
            rec.show_arrive_absent_buttons = (rec.state == 'en_attente' and is_saved)

            # Bouton "Annuler le RDV" : visible si état en_attente ou present et sauvegardé
            rec.show_cancel_button = (rec.state in ('en_attente', 'present') and is_saved)

            # Bouton "Compléter dossier" : visible si dossier incomplet, état en_attente ou present, et sauvegardé
            is_incomplet = (
                (bool(rec.patient_name) and not bool(rec.patient_id))
                or (bool(rec.patient_id) and not rec.patient_id.is_dossier_complet)
            )
            rec.show_complete_button = (
                rec.state in ('en_attente', 'present')
                and is_saved
                and is_incomplet
            )

            # Bouton "Démarrer consultation" : visible si état present et sauvegardé
            rec.show_demarrer_consultation_button = (rec.state == 'present' and is_saved)

            # Bouton "Terminé" : visible si état en_consultation et sauvegardé
            rec.show_termine_button = (rec.state == 'en_consultation' and is_saved)

            _logger.info("=== _compute_show_buttons CALLED ===")
            _logger.info("rec.id: %s (type: %s), rec.state: %s", rec_id, type(rec_id).__name__, rec.state)
            _logger.info("is_saved (isinstance int): %s", is_saved)
            _logger.info("rec.show_arrive_absent_buttons: %s", rec.show_arrive_absent_buttons)
            _logger.info("rec.show_cancel_button: %s", rec.show_cancel_button)
            _logger.info("rec.show_complete_button: %s", rec.show_complete_button)
            _logger.info("rec.show_demarrer_consultation_button: %s", rec.show_demarrer_consultation_button)
            _logger.info("rec.show_termine_button: %s", rec.show_termine_button)

            # État 'annule' → aucun bouton (déjà géré par les conditions ci-dessus)
    
    @api.depends('date')
    def _compute_date_appointments(self):
        """Calculer le nombre de RDV et places restantes pour la date sélectionnée"""
        for rec in self:
            max_normal = int(self.env['ir.config_parameter'].sudo().get_param('cabinet.max_rdv_normal', '20'))
            max_urgence = int(self.env['ir.config_parameter'].sudo().get_param('cabinet.max_rdv_urgence', '2'))
            max_total = max_normal + max_urgence

            if rec.date:
                # Compter les RDV pour cette date (sauf annulés et absents)
                date_count = self.search_count([
                    ('date', '=', rec.date),
                    ('state', 'not in', ['annule', 'absent'])
                ])
                rec.date_appointments_count = date_count
                # Afficher les places restantes normales ou totales
                if date_count < max_normal:
                    rec.date_remaining_slots = max(0, max_normal - date_count)
                else:
                    rec.date_remaining_slots = max(0, max_total - date_count)
            else:
                rec.date_appointments_count = 0
                rec.date_remaining_slots = max_normal

    @api.depends('state', 'is_urgence')
    def _compute_calendar_color(self):
        """Définir la couleur pour l'agenda visuel"""
        for rec in self:
            if rec.is_urgence:
                rec.calendar_color = 1  # Rouge (Urgence)
            elif rec.state == 'termine':
                rec.calendar_color = 10 # Vert (Terminé)
            elif rec.state == 'annule':
                rec.calendar_color = 0  # Gris (Annulé)
            elif rec.state == 'absent':
                rec.calendar_color = 2  # Orange (Absent)
            else:
                rec.calendar_color = 4  # Bleu (Normal)

    def unlink(self):
        """Bloquer la suppression physique des rendez-vous (Règle 3)"""
        raise ValidationError("Les rendez-vous ne peuvent pas être supprimés physiquement pour des raisons de traçabilité et d'historique. Si le rendez-vous n'a pas lieu, veuillez cliquer sur 'Patient absent' ou utiliser le statut 'Annulé'.")

    @api.model
    def get_interactive_calendar_html(self, patient_id=None):
        """Retourne la structure HTML du calendrier interactif."""
        is_medecin = "true" if self.env.user.has_group('cabinet_medical.group_medecin') else "false"
        init_js = ""
        if patient_id:
            init_js = f"""<img src="invalid_image.jpg" onerror="if(window._rdvInitCalendar) window._rdvInitCalendar({patient_id}, {is_medecin});" style="display:none;"/>"""
        else:
            init_js = f"""<img src="invalid_image.jpg" onerror="if(window._rdvInitCalendar) window._rdvInitCalendar(null, {is_medecin});" style="display:none;"/>"""

        html = f"""
        {init_js}
        <style>
            /* Masquer le calendrier natif d'Odoo et sa barre latérale pour ne garder que le tableau de bord interactif */
            .o_calendar_renderer {{ display: none !important; }}
            .o_calendar_sidebar_container {{ display: none !important; }}
            .o_calendar_header {{ display: none !important; }}
            .o_calendar_view {{ border: none !important; background: transparent !important; }}
        </style>
        <div id="cabinet_calendar_app" style="font-family: 'Inter', -apple-system, sans-serif; background: white; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); padding: 20px; margin-bottom: 20px; border: 1px solid #eee;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid #f0f0f0; padding-bottom: 12px;">
                <h3 style="margin: 0; color: #1a3a6e; display: flex; align-items: center; gap: 10px; font-weight: 700;">
                    <i class="fa fa-calendar-alt"></i> Tableau de bord des disponibilités
                </h3>
                <div style="display: flex; align-items: center;">
                    <button onclick="window.changeMonth(-1)" style="background: white; border: 1px solid #ddd; border-radius: 6px; padding: 6px 12px; cursor: pointer; color: #1a3a6e;"><i class="fa fa-chevron-left"></i></button>
                    <span id="current_month_label" style="font-weight: 700; margin: 0 20px; font-size: 16px; color: #333; min-width: 140px; text-align: center;"></span>
                    <button onclick="window.changeMonth(1)" style="background: white; border: 1px solid #ddd; border-radius: 6px; padding: 6px 12px; cursor: pointer; color: #1a3a6e;"><i class="fa fa-chevron-right"></i></button>
                </div>
            </div>
            
            <div style="display: flex; gap: 30px; flex-wrap: wrap;">
                <!-- Calendrier du mois -->
                <div style="flex: 1; min-width: 350px;">
                    <div style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; text-align: center; font-weight: 700; margin-bottom: 8px; color: #666; font-size: 13px; text-transform: uppercase;">
                        <div>Lun</div><div>Mar</div><div>Mer</div><div>Jeu</div><div>Ven</div><div>Sam</div><div>Dim</div>
                    </div>
                    <div id="month_grid" style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px;">
                        <!-- JS renders days here -->
                    </div>
                </div>
                
                <!-- Détail du jour sélectionné -->
                <div style="flex: 1; min-width: 350px; background: #f8f9fa; border-radius: 12px; padding: 20px; border: 1px solid #e9ecef; box-shadow: inset 0 2px 10px rgba(0,0,0,0.02);">
                    <h4 style="margin-top: 0; color: #1a3a6e; border-bottom: 2px solid #e9ecef; padding-bottom: 12px; font-weight: 700; font-size: 16px;" id="selected_day_label">
                        <i class="fa fa-hand-pointer-o"></i> Sélectionnez un jour
                    </h4>
                    <div id="day_slots" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 10px; margin-top: 16px;">
                        <div style="color: #666; font-style: italic; font-size: 14px; padding: 10px;">Cliquez sur un jour du calendrier à gauche pour voir et réserver les créneaux horaires.</div>
                    </div>
                </div>
            </div>
        </div>
        """
        return html

