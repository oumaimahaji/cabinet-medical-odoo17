from odoo import models, fields, api  # type: ignore


class ActeParametrage(models.Model):
    _name = 'cabinet.acte.parametrage'
    _description = 'Paramétrage des Actes CNAM'
    _order = 'name'

    name = fields.Char(string='Nom de l\'acte', required=True)
    code_cnam = fields.Char(string='Code CNAM', help='Code utilisé par la CNAM pour cet acte (ex: C, CS, K, B, Z...)')

    # --- Type d'acte (détermine le taux CNAM applicable selon la réalité tunisienne) ---
    type_acte = fields.Selection([
        ('consultation', 'Consultation médicale'),
        ('acte_technique', 'Acte technique / Médical'),
        ('biologie', 'Analyse biologique'),
        ('radiologie', 'Radiologie / Imagerie'),
        ('dentaire', 'Acte dentaire'),
        ('autre', 'Autre'),
    ], string='Type d\'acte', required=True, default='consultation')

    # Tarif de base (tarif conventionné CNAM)
    tarif = fields.Float(string='Tarif conventionné (DT)', required=True, default=0.0)

    # Devise — nécessaire pour le widget monetary dans les vues
    currency_id = fields.Many2one(
        'res.currency', string='Devise',
        default=lambda self: self.env.company.currency_id,
        readonly=True
    )

    # Taux CNAM calculé automatiquement selon le type d'acte
    # (70% consultation, 80% acte technique, 75% biologie/radio, 50% dentaire)
    taux_cnam = fields.Float(
        string='Taux CNAM (%)',
        compute='_compute_taux_cnam',
        store=True,
        help='Taux de prise en charge CNAM selon le type d\'acte (réalité tunisienne)'
    )

    # Part calculée automatiquement
    tarif_cnam = fields.Float(
        string='Part CNAM (DT)',
        compute='_compute_parts',
        store=True,
        help='Montant pris en charge par la CNAM'
    )
    part_patient = fields.Float(
        string='Ticket modérateur patient (DT)',
        compute='_compute_parts',
        store=True,
        help='Montant restant à la charge du patient (ticket modérateur)'
    )

    is_remboursable = fields.Boolean(string='Remboursable CNAM', default=True)
    active = fields.Boolean(string='Actif', default=True)

    @api.depends('type_acte')
    def _compute_taux_cnam(self):
        """Calcule le taux CNAM selon le type d'acte — réalité tunisienne 2025."""
        IrParam = self.env['ir.config_parameter'].sudo()
        taux_map = {
            'consultation':   float(IrParam.get_param('cabinet.cnam_taux_consultation',   '70.0')),
            'acte_technique': float(IrParam.get_param('cabinet.cnam_taux_acte_technique', '80.0')),
            'biologie':       float(IrParam.get_param('cabinet.cnam_taux_biologie',       '75.0')),
            'radiologie':     float(IrParam.get_param('cabinet.cnam_taux_radiologie',     '75.0')),
            'dentaire':       float(IrParam.get_param('cabinet.cnam_taux_dentaire',       '50.0')),
            'autre':          float(IrParam.get_param('cabinet.cnam_taux_consultation',   '70.0')),
        }
        for rec in self:
            rec.taux_cnam = taux_map.get(str(rec.type_acte or ''), 70.0)

    @api.depends('tarif', 'taux_cnam')
    def _compute_parts(self):
        """Calcule la part CNAM et le ticket modérateur patient."""
        for rec in self:
            rec.tarif_cnam = rec.tarif * (rec.taux_cnam / 100.0)
            rec.part_patient = rec.tarif - rec.tarif_cnam

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.name} - {record.tarif} DT"
            if record.code_cnam:
                name = f"[{record.code_cnam}] {name}"
            result.append((record.id, name))  # type: ignore
        return result

