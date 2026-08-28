from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore
from datetime import datetime

# Note : le modèle cabinet.acte.parametrage est défini dans acte_parametrage.py
# (classe supprimée ici pour éviter le conflit de doublon)

class ActeMedical(models.Model):
    _name = 'cabinet.acte'
    _description = 'Acte Médical'
    _order = 'date_acte desc'

    active = fields.Boolean(string='Actif', default=True)

    consultation_id = fields.Many2one('cabinet.consultation', string='Consultation', required=True, ondelete='cascade')

    def action_archive(self):
        self.write({'active': False})

    def action_unarchive(self):
        self.write({'active': True})
    patient_id = fields.Many2one(related='consultation_id.patient_id', string='Patient', readonly=True)
    invoice_id = fields.Many2one('cabinet.facture', string='Facture', ondelete='set null')
    currency_id = fields.Many2one(
        'res.currency', string='Devise', related='consultation_id.currency_id', readonly=True,
    )
    
    # Liaison non-intrusive vers le référentiel paramétré
    parametrage_id = fields.Many2one('cabinet.acte.parametrage', string='Acte Conventionné')

    # Types d'actes médicaux (conservé pour rétrocompatibilité)
    type_acte = fields.Selection([
        ('consultation', 'Consultation médicale'),
        ('acte_technique', 'Acte technique / Médical'),
        ('biologie', 'Analyse biologique'),
        ('radiologie', 'Radiologie / Imagerie'),
        ('dentaire', 'Acte dentaire'),
        ('injection', 'Injection'),
        ('pansement', 'Pansement'),
        ('suture', 'Suture'),
        ('vaccination', 'Vaccination'),
        ('examen', 'Examen'),
        ('autre', 'Autre'),
    ], string='Type d\'acte', required=True)
    
    description = fields.Text(string='Description de l\'acte', required=True)
    date_acte = fields.Datetime(string='Date de l\'acte', required=True, default=fields.Datetime.now)
    
    # Tarification (optionnel pour facturation future)
    code_acte = fields.Char(string='Code acte')
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self.env.ref('base.TND') if self.env.ref('base.TND', raise_if_not_found=False) else self.env.company.currency_id
    )
    montant = fields.Monetary(
        string='Montant (DT)',
        currency_field='currency_id',
        required=True
    )
    total_acte_dt = fields.Monetary(
        string='Total acte (DT)',
        compute='_compute_total_acte',
        currency_field='currency_id',
        store=True,
    )

    # État de l'acte
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Validé')
    ], string='État', default='draft')

    @api.onchange('parametrage_id')
    def _onchange_parametrage_id(self):
        """Pré-remplit les champs automatiquement si un acte du référentiel est choisi."""
        if self.parametrage_id:
            self.type_acte = self.parametrage_id.type_acte
            self.description = self.parametrage_id.name
            self.code_acte = self.parametrage_id.code_cnam
            # Utilise 'tarif' (champ actuel du parametrage consolidé)
            self.montant = self.parametrage_id.tarif

    @api.depends('montant', 'consultation_id.patient_id.is_cnam',
                 'consultation_id.patient_id.filiere_cnam',
                 'consultation_id.patient_id.is_apci',
                 'parametrage_id.taux_cnam')
    def _compute_total_acte(self):
        """Calcule la part à payer par le patient pour cet acte.
        - APCI : patient ne paie rien (exonéré totalement)
        - Tiers-payant : patient paie le ticket modérateur (montant - part CNAM)
        - Remboursement / Sans CNAM : patient avance tout le montant
        """
        for rec in self:
            patient = rec.consultation_id.patient_id
            if patient.is_apci:
                # Exonération totale APCI — patient ne paie rien
                rec.total_acte_dt = 0.0
            elif patient.is_cnam and patient.filiere_cnam == 'privee':
                # Tiers-payant : patient paie uniquement le ticket modérateur
                taux_cnam = rec.parametrage_id.taux_cnam if rec.parametrage_id else 70.0
                rec.total_acte_dt = rec.montant * (1.0 - taux_cnam / 100.0)
            else:
                # Remboursement ou sans CNAM : patient avance la totalité
                rec.total_acte_dt = rec.montant
    
    # Contrôles de saisie
    @api.constrains('date_acte')
    def _check_date_acte(self):
        """Vérifier que la date de l'acte n'est pas dans le futur"""
        for rec in self:
            if rec.date_acte and rec.date_acte > datetime.now():
                raise ValidationError("La date de l'acte ne peut pas être dans le futur")
    
    @api.constrains('montant')
    def _check_montant(self):
        """Vérifier que le montant est positif"""
        for rec in self:
            if rec.montant and rec.montant < 0:
                raise ValidationError("Le montant ne peut pas être négatif")
    
    @api.constrains('description')
    def _check_description(self):
        """Vérifier que la description n'est pas vide"""
        for rec in self:
            if rec.description and len(rec.description.strip()) < 3:
                raise ValidationError("La description doit contenir au moins 3 caractères")
    
    def name_get(self):
        result = []
        for acte in self:
            name = f"{acte.type_acte} - {acte.patient_id.name}"
            result.append((acte.id, name))  # type: ignore
        return result

    def action_valider(self):
        """Valider l'acte médical (accessible uniquement au médecin)"""
        self.ensure_one()
        self.state = 'done'
