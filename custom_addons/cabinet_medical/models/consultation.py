from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError, AccessError, UserError  # type: ignore
from datetime import datetime, timedelta

class Consultation(models.Model):
    _name = 'cabinet.consultation'
    _description = 'Consultation'
    _order = 'date_consultation desc'
    _rec_name = 'nom_patient'

    active = fields.Boolean(string='Actif', default=True, help='Désactiver pour archiver sans supprimer')

    # US13 - Fiche de consultation
    patient_id = fields.Many2one('cabinet.patient', string='Patient', required=True, ondelete='restrict')
    rdv_id = fields.Many2one('cabinet.rendezvous', string='Rendez-vous associé')
    date_consultation = fields.Datetime(string='Date de consultation', required=True, default=fields.Datetime.now)
    motif = fields.Text(string='Motif de la consultation', required=True, groups='cabinet_medical.group_medecin')
    
    # Alertes médicales (liées au patient)
    allergies = fields.Text(related='patient_id.allergies', string='Allergies', readonly=True)
    antecedents = fields.Text(related='patient_id.antecedents', string='Antécédents', readonly=True)
    is_cnam_expired = fields.Boolean(related='patient_id.is_cnam_expired', string='CNAM Expirée', readonly=True)
    is_apci_expired = fields.Boolean(related='patient_id.is_apci_expired', string='APCI Expirée', readonly=True)
    
    # US14 - Actes médicaux
    acte_ids = fields.One2many('cabinet.acte', 'consultation_id', string='Actes médicaux')
    
    # US15 - Diagnostic et notes
    diagnostic = fields.Text(string='Diagnostic', groups='cabinet_medical.group_medecin')
    notes_medicales = fields.Text(string='Notes médicales', groups='cabinet_medical.group_medecin')
    
    # US16 - Prescription/Ordonnance
    prescription_ids = fields.One2many('cabinet.prescription', 'consultation_id', string='Prescriptions')
    facture_ids = fields.One2many('cabinet.facture', 'consultation_id', string='Factures')
    
    # État de la consultation
    state = fields.Selection([
        ('draft', 'En cours'),
        ('done', 'Terminée')
    ], string='État', default='draft')



    # Champs calculés
    nom_patient = fields.Char(related='patient_id.name', string='Nom patient', readonly=True)
    total_actes = fields.Integer(compute='_compute_total_actes', string='Nombre d\'actes')
    total_montant_actes = fields.Monetary(
        string='Total actes (DT)',
        compute='_compute_total_montant_actes',
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self.env.company.currency_id,
    )
    has_facture = fields.Boolean(
        string='Facture générée',
        compute='_compute_has_facture',
        store=True,
    )


    @api.depends('acte_ids', 'acte_ids.montant', 'acte_ids.active')
    def _compute_total_montant_actes(self):
        for rec in self:
            active_actes = rec.sudo().acte_ids.filtered(lambda a: a.active)
            rec.total_montant_actes = sum(active_actes.mapped('montant')) or 0.0

    @api.depends('acte_ids', 'acte_ids.active')
    def _compute_total_actes(self):
        for record in self:
            record.total_actes = len(record.sudo().acte_ids.filtered(lambda a: a.active))

    @api.depends('facture_ids')
    def _compute_has_facture(self):
        for rec in self:
            rec.has_facture = bool(rec.facture_ids)
    
    # Contrôles de saisie
    @api.constrains('date_consultation')
    def _check_date_consultation(self):
        """Vérifier que la date de consultation n'est pas trop dans le futur"""
        for rec in self:
            if rec.date_consultation:
                now = datetime.now()
                # Permettre jusqu'à 7 jours dans le futur pour les rendez-vous planifiés
                if rec.date_consultation > now + timedelta(days=7):
                    raise ValidationError("La date de consultation ne peut pas être à plus de 7 jours dans le futur")
    
    @api.constrains('motif')
    def _check_motif(self):
        """Vérifier que le motif n'est pas vide"""
        for rec in self:
            if rec.motif and len(rec.motif.strip()) < 5:
                raise ValidationError("Le motif de consultation doit contenir au moins 5 caractères")
    
    @api.onchange('patient_id', 'date_consultation')
    def _check_duplicate_consultation(self):
        """Avertir des consultations en double pour le même patient le même jour"""
        for rec in self:
            if rec.patient_id and rec.date_consultation:
                # Vérifier s'il existe déjà une consultation le même jour
                same_day_start = rec.date_consultation.replace(hour=0, minute=0, second=0, microsecond=0)
                same_day_end = rec.date_consultation.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                domain = [
                    ('patient_id', '=', rec.patient_id.id),
                    ('date_consultation', '>=', same_day_start),
                    ('date_consultation', '<=', same_day_end)
                ]
                # En onchange, l'ID peut être un NewId, on vérifie _origin
                if getattr(rec, '_origin', False) and rec._origin.id:  # type: ignore
                    domain.append(('id', '!=', rec._origin.id))  # type: ignore
                elif isinstance(rec.id, int):  # type: ignore
                    domain.append(('id', '!=', rec.id))  # type: ignore
                
                if self.env['cabinet.consultation'].search_count(domain) > 0:
                    return {'warning': {'title': 'Attention — Consultation existante', 'message': "Ce patient a déjà une consultation aujourd'hui. Confirmez seulement si c'est une urgence."}}
    
    def name_get(self):
        result = []
        for consultation in self:
            name = f"Consultation — {consultation.patient_id.name}" if consultation.patient_id else "Consultation"
            result.append((consultation.id, name))  # type: ignore
        return result

    def action_terminer(self):
        """Marque la consultation comme terminée et met à jour le RDV"""
        self.ensure_one()
        if not (self.env.user._is_superuser() or self.env.user.id == 1 or self.env.user.has_group('cabinet_medical.group_medecin')):
            raise AccessError("Seul le Médecin peut terminer une consultation.")
        self.state = 'done'
        if self.rdv_id:
            self.rdv_id.state = 'termine'

    def action_creer_prescription(self):
        """Ouvre un formulaire pour créer une nouvelle ordonnance"""
        self.ensure_one()
        return {
            'name': 'Nouvelle Ordonnance',
            'type': 'ir.actions.act_window',
            'res_model': 'cabinet.prescription',
            'views': [(False, 'form')],
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_consultation_id': self.id,  # type: ignore
                'default_patient_id': self.patient_id.id if self.patient_id else False,
            }
        }

    def action_planifier_suivi(self):
        """Ouvre le calendrier interactif en popup pour planifier un rendez-vous de suivi"""
        self.ensure_one()
        if not (self.env.user._is_superuser() or self.env.user.id == 1 or self.env.user.has_group('cabinet_medical.group_medecin')):
            raise AccessError("Seul le Médecin peut planifier un suivi.")
        return {
            'name': 'Planifier un suivi',
            'type': 'ir.actions.act_window',
            'res_model': 'cabinet.rendezvous',
            'view_mode': 'calendar',
            'views': [(self.env.ref('cabinet_medical.view_appointment_calendar').id, 'calendar')],
            'target': 'new',
            'context': {
                'default_patient_id': self.patient_id.id,
                'default_patient_name': self.patient_id.name,
                'search_default_filter_today': 1
            }
        }

    def action_generer_facture(self):
        """Génère la facture pour cette consultation"""
        self.ensure_one()
        if not (self.env.user._is_superuser() or self.env.user.id == 1 or self.env.user.has_group('cabinet_medical.group_secretaire')):
            raise AccessError("Seule la Secrétaire peut générer une facture.")
        if self.state != 'done':
            raise UserError("Impossible de générer une facture pour une consultation qui n'est pas terminée.")
        if self.has_facture:
            raise UserError("Une facture existe déjà pour cette consultation.")
        facture = self.env['cabinet.facture'].create({
            'patient_id': self.patient_id.id,
            'consultation_id': self.id,  # type: ignore
        })
        return {
            'name': 'Facture générée',
            'type': 'ir.actions.act_window',
            'res_model': 'cabinet.facture',
            'res_id': facture.id,
            'views': [(False, 'form')],
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def _reset_currency(self):
        """Migrate existing consultations to use the TND currency if it exists.
        This method is intended to be called during module update.
        """
        tnd = self.env['res.currency'].search([('name', '=', 'TND')], limit=1)
        if tnd:
            self.search([]).write({'currency_id': tnd.id})

    def action_ia_conseil_cnam(self):
        """Délègue l'action de conseil IA CNAM au patient associé"""
        self.ensure_one()
        if self.patient_id:
            return self.patient_id.action_ia_conseil_cnam()
        return False

    def action_ia_conseil_apci(self):
        """Délègue l'action de conseil IA APCI au patient associé"""
        self.ensure_one()
        if self.patient_id:
            return self.patient_id.action_ia_conseil_apci()
        return False

