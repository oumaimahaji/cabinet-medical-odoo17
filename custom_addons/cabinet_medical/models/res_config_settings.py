from odoo import models, fields, api  # type: ignore

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cabinet_nom = fields.Char(related='company_id.name', readonly=False, string='Nom du cabinet')
    cabinet_adresse = fields.Char(related='company_id.street', readonly=False, string='Adresse')
    cabinet_telephone = fields.Char(related='company_id.phone', readonly=False, string='Téléphone')
    cabinet_logo = fields.Binary(related='company_id.logo', readonly=False, string='Logo du cabinet')

    cnam_actif = fields.Boolean(
        string='Activer la gestion CNAM',
        config_parameter='cabinet.cnam_actif',
        default=True
    )

    # --- Taux CNAM différenciés par type d'acte (réalité tunisienne 2025) ---
    cnam_taux_consultation = fields.Float(
        string='Taux consultation (%)',
        config_parameter='cabinet.cnam_taux_consultation',
        default=70.0,
        help='Taux de remboursement CNAM pour les consultations médicales (défaut : 70%)'
    )
    cnam_taux_acte_technique = fields.Float(
        string='Taux actes techniques (%)',
        config_parameter='cabinet.cnam_taux_acte_technique',
        default=80.0,
        help='Taux de remboursement CNAM pour les actes techniques/médicaux (défaut : 80%)'
    )
    cnam_taux_biologie = fields.Float(
        string='Taux biologie / analyses (%)',
        config_parameter='cabinet.cnam_taux_biologie',
        default=75.0,
        help='Taux de remboursement CNAM pour les analyses biologiques (défaut : 75%)'
    )
    cnam_taux_radiologie = fields.Float(
        string='Taux radiologie / imagerie (%)',
        config_parameter='cabinet.cnam_taux_radiologie',
        default=75.0,
        help='Taux de remboursement CNAM pour la radiologie et l\'imagerie médicale (défaut : 75%)'
    )
    cnam_taux_assurance = fields.Float(
        string='Taux de couverture Assurance par défaut (%)',
        config_parameter='cabinet_medical.taux_assurance',
        default=80.0
    )
    claude_api_key = fields.Char(
        string='Clé API Claude (Anthropic)',
        config_parameter='cabinet_medical.claude_api_key',
        help='Clé API pour générer les insights intelligents du tableau de bord.'
    )
    ollama_url = fields.Char(
        string='URL Service Ollama',
        config_parameter='cabinet_medical.ollama_url',
        default='http://ollama:11434/api/generate',
        help='URL du endpoint Ollama local (ex: http://ollama:11434/api/generate)'
    )
    ollama_model = fields.Char(
        string='Modèle Ollama',
        config_parameter='cabinet_medical.ollama_model',
        default='tinyllama',
        help='Nom du modèle Ollama (ex: tinyllama, phi3)'
    )
    cnam_taux_dentaire = fields.Float(
        string='Taux actes dentaires (%)',
        config_parameter='cabinet.cnam_taux_dentaire',
        default=50.0,
        help='Taux de remboursement CNAM pour les actes dentaires (défaut : 50%)'
    )
    # Taux global remboursement (filière verte — patient avance et CNAM rembourse)
    cnam_taux_remboursement = fields.Float(
        string='Taux remboursement global (%)',
        config_parameter='cabinet.cnam_taux_remboursement',
        default=70.0,
        help='Taux de remboursement CNAM pour la filière remboursement (carte verte)'
    )
    cnam_taux_apci = fields.Float(
        string='Taux APCI (%)',
        config_parameter='cabinet.cnam_taux_apci',
        default=100.0,
        help='Taux de prise en charge pour les patients APCI (maladies chroniques) — défaut : 100%'
    )


    medecin_nom = fields.Char(related='company_id.medecin_nom', readonly=False, string='Nom du Médecin')
    medecin_inpe = fields.Char(related='company_id.medecin_inpe', readonly=False, string='INPE Médecin')
    medecin_code_convention = fields.Char(related='company_id.medecin_code_convention', readonly=False, string='Code Convention CNAM')
    medecin_specialite = fields.Selection(related='company_id.medecin_specialite', readonly=False, string='Spécialité du Médecin')
    medecin_conventionne = fields.Boolean(related='company_id.medecin_conventionne', readonly=False, string='Médecin Conventionné CNAM')

    work_days = fields.Char(
        string='Jours de travail',
        config_parameter='cabinet.work_days',
        default='0,1,2,3,4,5'
    )

    max_rdv_normal = fields.Integer(
        string='RDV normaux par jour',
        config_parameter='cabinet.max_rdv_normal',
        default=20
    )

    max_rdv_urgence = fields.Integer(
        string='RDV urgences par jour',
        config_parameter='cabinet.max_rdv_urgence',
        default=2
    )

    heure_debut = fields.Float(
        string='Heure début',
        config_parameter='cabinet.heure_debut',
        default=8.0
    )

    heure_fin = fields.Float(
        string='Heure fin',
        config_parameter='cabinet.heure_fin',
        default=17.0
    )

    def check_access_rights(self, operation, raise_exception=True):
        if self.env.user.has_group('cabinet_medical.group_medecin') or self.env.user.has_group('cabinet_medical.group_secretaire'):
            return True
        return super().check_access_rights(operation, raise_exception)

    def default_get(self, fields_list):
        """Override pour permettre au médecin ou à la secrétaire de charger les paramètres."""
        if self.env.user.has_group('cabinet_medical.group_medecin') or self.env.user.has_group('cabinet_medical.group_secretaire'):
            return super(ResConfigSettings, self.sudo()).default_get(fields_list)
        return super().default_get(fields_list)

    @api.model_create_multi
    def create(self, vals_list):
        """Override pour permettre la création de la configuration (écriture related sur res.company via sudo)."""
        if self.env.user.has_group('cabinet_medical.group_medecin') or self.env.user.has_group('cabinet_medical.group_secretaire'):
            return super(ResConfigSettings, self.sudo()).create(vals_list)
        return super().create(vals_list)

    def write(self, vals):
        """Override pour permettre la modification de la configuration via sudo."""
        if self.env.user.has_group('cabinet_medical.group_medecin') or self.env.user.has_group('cabinet_medical.group_secretaire'):
            return super(ResConfigSettings, self.sudo()).write(vals)
        return super().write(vals)

    def get_values(self):
        """Override pour charger les valeurs avec sudo si médecin ou secrétaire."""
        if self.env.user.has_group('cabinet_medical.group_medecin') or self.env.user.has_group('cabinet_medical.group_secretaire'):
            return super(ResConfigSettings, self.sudo()).get_values()
        return super().get_values()

    def set_values(self):
        """Override pour enregistrer les paramètres avec sudo si médecin ou secrétaire."""
        if self.env.user.has_group('cabinet_medical.group_medecin') or self.env.user.has_group('cabinet_medical.group_secretaire'):
            return super(ResConfigSettings, self.sudo()).set_values()
        return super().set_values()

    def execute(self):
        """Override pour permettre au médecin ou à la secrétaire de sauvegarder les paramètres."""
        if self.env.user.has_group('cabinet_medical.group_medecin') or self.env.user.has_group('cabinet_medical.group_secretaire'):
            return super(ResConfigSettings, self.sudo()).execute()
        return super().execute()

    def cancel(self):
        """Override pour permettre au médecin ou à la secrétaire d'utiliser le bouton Ignorer."""
        if self.env.user.has_group('cabinet_medical.group_medecin') or self.env.user.has_group('cabinet_medical.group_secretaire'):
            return super(ResConfigSettings, self.sudo()).cancel()
        return super().cancel()

