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

    # --- Nomenclature NGAP officielle CNAM & Lettres-clés ---
    lettre_cle = fields.Selection([
        ('C', 'C — Consultation omnipraticien / médecin généraliste'),
        ('CS', 'CS — Consultation médecin spécialiste'),
        ('V', 'V — Visite à domicile omnipraticien'),
        ('VS', 'VS — Visite à domicile spécialiste'),
        ('K', 'K — Acte de chirurgie / acte technique'),
        ('KE', 'KE — Acte d\'échographie / explorations ultrasoniques'),
        ('ATM', 'ATM — Actes de traitement médical'),
        ('P', 'P — Acte de petite chirurgie / pansement'),
        ('D', 'D — Acte dentaire'),
        ('B', 'B — Biologie médicale'),
        ('Z', 'Z — Radiologie / imagerie conventionnelle'),
        ('autre', 'Autre lettre-clé'),
    ], string='Lettre-clé NGAP', help='Lettre-clé officielle selon la Nomenclature Générale des Actes Professionnels (NGAP)')
    coefficient = fields.Float(string='Coefficient', default=1.0, help='Coefficient multiplicateur de la lettre-clé (ex: K 10, KE 25)')
    valeur_cle = fields.Float(string='Valeur de la clé (DT)', help='Valeur unitaire de la lettre-clé fixée par convention/avenant')

    # Validité temporelle (Avenants conventionnels)
    date_debut_validite = fields.Date(
        string='Date de début de validité',
        default=fields.Date.today,
        help='Date de prise d\'effet de ce tarif conventionnel'
    )
    date_fin_validite = fields.Date(
        string='Date de fin de validité',
        help='Date d\'expiration du tarif (laisser vide si actuellement en vigueur)'
    )

    # Accord préalable & Conditions
    necessite_accord_prealable = fields.Boolean(
        string='Accord préalable obligatoire (AP)',
        default=False,
        help='Cocher si cet acte nécessite l\'accord préalable écrit de la CNAM (art. 22 Convention sectorielle)'
    )
    conditions_prise_en_charge = fields.Text(
        string='Conditions de prise en charge',
        help='Indications ou restrictions fixées par la convention ou la nomenclature'
    )

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

    @api.onchange('coefficient', 'valeur_cle')
    def _onchange_ngap(self):
        """Met à jour automatiquement le tarif conventionné si coefficient et valeur_clé sont définis."""
        if self.coefficient and self.valeur_cle:
            self.tarif = round(self.coefficient * self.valeur_cle, 3)

    def is_valid_at_date(self, check_date):
        """Vérifie si le tarif conventionné est en vigueur à une date donnée."""
        self.ensure_one()
        if not check_date:
            return True
        if self.date_debut_validite and check_date < self.date_debut_validite:
            return False
        if self.date_fin_validite and check_date > self.date_fin_validite:
            return False
        return True

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

