from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore


class WizardCreerPatient(models.TransientModel):
    """Wizard pour créer un dossier patient complet depuis un rendez-vous rapide.

    La secrétaire l'ouvre depuis le formulaire du RDV (bouton "Créer le dossier
    patient"). Le wizard pré-remplit le nom depuis patient_name, la secrétaire
    saisit les infos CNAM / assurance / médicales, puis confirme. Le patient
    est créé et lié automatiquement au RDV.
    """

    _name = 'cabinet.rendezvous.creer.patient'
    _description = 'Wizard — Créer le dossier patient depuis un RDV rapide'

    # ── Lien vers le RDV d'origine ─────────────────────────────────────────
    rendezvous_id = fields.Many2one(
        'cabinet.rendezvous',
        string='Rendez-vous',
        required=True,
        ondelete='cascade',
    )

    # ── Informations civiles ────────────────────────────────────────────────
    name = fields.Char(string='Nom complet', required=True)
    genre = fields.Selection([
        ('', '---'),
        ('homme', 'Homme'),
        ('femme', 'Femme'),
    ], string='Genre')
    date_naissance = fields.Date(string='Date de naissance')
    telephone = fields.Char(string='Téléphone')
    cin = fields.Char(string='CIN')
    adresse = fields.Text(string='Adresse')

    # ── Alertes médicales ───────────────────────────────────────────────────
    allergies = fields.Text(
        string='Allergies',
        help='Ex : Pénicilline, Arachides…',
    )
    antecedents = fields.Text(
        string='Antécédents médicaux',
        help='Maladies chroniques, chirurgies passées…',
    )

    # ── CNAM ────────────────────────────────────────────────────────────────
    is_cnam = fields.Boolean(string='Assuré CNAM')
    numero_cnam = fields.Char(string='Numéro CNAM')
    regime_cnam = fields.Selection([
        ('salarie', 'Salarié'),
        ('retraite', 'Retraité'),
    ], string='Régime CNAM')
    filiere_cnam = fields.Selection([
        ('privee', 'Tiers-payant (Filière Privée)'),
        ('remboursement', 'Remboursement des Frais')
    ], string='Filière CNAM')
    date_validite_cnam = fields.Date(string='Date validité CNAM')
    is_apci = fields.Boolean(string='Patient APCI')
    numero_decision_apci = fields.Char(string='Numéro décision APCI')

    date_fin_apci = fields.Date(string='Date fin APCI')

    # ── Assurance privée ────────────────────────────────────────────────────
    has_assurance = fields.Boolean(string='Assurance privée')
    assurance_id = fields.Many2one('cabinet.assurance', string='Assurance')
    assurance_numero = fields.Char(string="Numéro d'affiliation")

    # ── Pré-remplissage automatique depuis le RDV ───────────────────────────
    @api.onchange('rendezvous_id')
    def _onchange_rendezvous_id(self):
        if self.rendezvous_id and self.rendezvous_id.patient_name:
            self.name = self.rendezvous_id.patient_name

    # ── Validation ──────────────────────────────────────────────────────────
    @api.constrains('telephone')
    def _check_telephone(self):
        for rec in self:
            if rec.telephone:
                if not rec.telephone.isdigit() or len(rec.telephone) != 8:
                    raise ValidationError(
                        'Le téléphone doit contenir exactement 8 chiffres.'
                    )
                if rec.telephone[0] not in ['2', '4', '5', '7', '9']:
                    raise ValidationError(
                        'Le téléphone doit commencer par 2, 4, 5, 7 ou 9.'
                    )

    @api.constrains('cin')
    def _check_cin(self):
        for rec in self:
            if rec.cin and (not rec.cin.isdigit() or len(rec.cin) != 8):
                raise ValidationError('Le CIN doit contenir exactement 8 chiffres.')

    # ── Action principale ───────────────────────────────────────────────────
    def action_confirmer(self):
        """Créer le patient, le lier au RDV et fermer le wizard."""
        self.ensure_one()

        if not self.name or not self.name.strip():
            raise ValidationError("Le nom du patient est obligatoire.")

        # Préparer les valeurs du patient
        patient_vals = {
            'name': (self.name or '').strip().upper(),
            'genre': self.genre or '',
            'date_naissance': self.date_naissance,
            'telephone': self.telephone,
            'cin': self.cin,
            'adresse': self.adresse,
            'allergies': self.allergies,
            'antecedents': self.antecedents,
            # CNAM
            'is_cnam': self.is_cnam,
            'numero_cnam': self.numero_cnam if self.is_cnam else False,
            'regime_cnam': self.regime_cnam if self.is_cnam else False,
            'filiere_cnam': self.filiere_cnam if self.is_cnam else False,
            'date_validite_cnam': self.date_validite_cnam if self.is_cnam else False,
            'is_apci': self.is_apci if self.is_cnam else False,
            'numero_decision_apci': self.numero_decision_apci if self.is_apci else False,

            'date_fin_apci': self.date_fin_apci if self.is_apci else False,
            # Assurance
            'has_assurance': self.has_assurance,
            'assurance_id': self.assurance_id.id if self.has_assurance and self.assurance_id else False,
            'assurance_numero': self.assurance_numero if self.has_assurance else False,
        }

        # Créer le patient (sans passer from_rendezvous_id dans le contexte
        # car on fait le lien manuellement ici pour éviter les conflits)
        patient = self.env['cabinet.patient'].create(patient_vals)

        # Lier le patient au RDV et vider le nom temporaire
        self.rendezvous_id.write({
            'patient_id': patient.id,
            'patient_name': False,
        })

        # Notification de succès + rechargement de la vue
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Dossier créé',
                'message': f'Le dossier de {patient.name} a été créé et lié au rendez-vous.',
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }

    def action_annuler(self):
        """Fermer le wizard sans rien créer."""
        return {'type': 'ir.actions.act_window_close'}
