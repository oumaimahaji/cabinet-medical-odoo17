from odoo import models, fields, api  # type: ignore
from odoo.tools.float_utils import float_is_zero
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
    tarif_conventionnel = fields.Monetary(
        string='Tarif conventionnel (DT)',
        currency_field='currency_id',
        default=0.0,
        help='Tarif de référence opposable fixé par la convention CNAM'
    )
    montant = fields.Monetary(
        string='Montant (DT)',
        currency_field='currency_id',
        required=True,
        help='Honoraires réels facturés par le médecin'
    )
    depassement_honoraire = fields.Monetary(
        string='Dépassement d\'honoraires (DT)',
        compute='_compute_depassement',
        store=True,
        currency_field='currency_id',
        help='Excédent facturé au-delà du tarif conventionnel (art. 17 Convention)'
    )

    # Prise en charge ciblée APCI (Décret n° 2005-1367 art. 19)
    is_acte_apci = fields.Boolean(
        string='Acte lié à l\'APCI',
        default=False,
        help='Cocher si cet acte se rapporte directement à l\'affection de longue durée prise en charge à 100%'
    )

    # Accord préalable CNAM (Convention sectorielle art. 22)
    necessite_accord_prealable = fields.Boolean(
        string='Accord préalable requis',
        related='parametrage_id.necessite_accord_prealable',
        readonly=True
    )
    statut_accord_prealable = fields.Selection([
        ('non_requis', 'Non requis'),
        ('demande', 'Demandé'),
        ('accorde', 'Accordé'),
        ('refuse', 'Refusé')
    ], string='Statut AP', default='non_requis')
    numero_accord_prealable = fields.Char(string='N° Accord Préalable CNAM')

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

    @api.onchange('consultation_id')
    def _onchange_consultation_id(self):
        if self.consultation_id and self.consultation_id.is_consultation_apci:
            self.is_acte_apci = True

    @api.onchange('parametrage_id')
    def _onchange_parametrage_id(self):
        """Pré-remplit les champs automatiquement si un acte du référentiel est choisi."""
        if self.parametrage_id:
            self.type_acte = self.parametrage_id.type_acte
            self.description = self.parametrage_id.name
            self.code_acte = self.parametrage_id.code_cnam
            self.tarif_conventionnel = self.parametrage_id.tarif
            if not self.montant or float_is_zero(self.montant, precision_digits=3):
                self.montant = self.parametrage_id.tarif
            if self.parametrage_id.necessite_accord_prealable:
                self.statut_accord_prealable = 'demande'
            else:
                self.statut_accord_prealable = 'non_requis'

    @api.depends('montant', 'tarif_conventionnel')
    def _compute_depassement(self):
        for rec in self:
            if rec.tarif_conventionnel and rec.tarif_conventionnel > 0:
                rec.depassement_honoraire = max(0.0, (rec.montant or 0.0) - rec.tarif_conventionnel)
            else:
                rec.depassement_honoraire = 0.0

    @api.depends('montant', 'consultation_id.patient_id.is_cnam',
                 'consultation_id.patient_id.filiere_cnam',
                 'consultation_id.patient_id.is_apci',
                 'parametrage_id.taux_cnam',
                 'is_acte_apci')
    def _compute_total_acte(self):
        """Calcule la part à payer par le patient pour cet acte.
        - APCI : patient ne paie rien (exonéré totalement) si acte APCI ou mode universel compatible
        - Tiers-payant : patient paie le ticket modérateur (montant - part CNAM)
        - Remboursement / Sans CNAM : patient avance tout le montant
        """
        for rec in self:
            patient = rec.consultation_id.patient_id
            if patient.is_apci and (rec.is_acte_apci or not rec.consultation_id.is_consultation_apci):
                # Exonération totale APCI — patient ne paie rien
                rec.total_acte_dt = 0.0
            elif patient.is_cnam and patient.filiere_cnam == 'privee':
                # Tiers-payant : patient paie uniquement le ticket modérateur
                if rec.parametrage_id and rec.parametrage_id.taux_cnam is not False and rec.parametrage_id.taux_cnam is not None:
                    taux_cnam = float(rec.parametrage_id.taux_cnam)
                else:
                    ir_config_param = rec.env['ir.config_parameter'].sudo()
                    taux_cnam = float(ir_config_param.get_param('cabinet.cnam_taux_consultation', '70.0'))
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

    @api.constrains('statut_accord_prealable', 'parametrage_id', 'state')
    def _check_accord_prealable(self):
        """Vérifier l'accord préalable obligatoire pour les actes conventionnés (Convention sectorielle art. 22)."""
        for rec in self:
            if rec.state == 'done' and rec.parametrage_id and rec.parametrage_id.necessite_accord_prealable:
                patient = rec.consultation_id.patient_id
                if patient and patient.is_cnam and patient.filiere_cnam == 'privee':
                    if rec.statut_accord_prealable != 'accorde' or not rec.numero_accord_prealable:
                        raise ValidationError(
                            f"L'acte '{rec.parametrage_id.name}' requiert un accord préalable écrit de la CNAM avec son numéro avant validation (art. 22 Convention sectorielle)."
                        )
    
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
