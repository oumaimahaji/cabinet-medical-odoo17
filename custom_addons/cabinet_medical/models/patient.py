from odoo import models, fields, api # type: ignore
from odoo.exceptions import ValidationError  # type: ignore
from datetime import date
from dateutil.relativedelta import relativedelta # type: ignore

class Patient(models.Model):
    _name = 'cabinet.patient'
    _description = 'Gestion des Patients du Cabinet Médical'

    _sql_constraints = [
        ('cin_unique', 'UNIQUE(cin)', 'Erreur : Ce numéro de CIN est déjà utilisé par un autre patient !'),
        ('email_unique', 'UNIQUE(email)', 'Erreur : Cette adresse email est déjà utilisée par un autre patient !')
    ]

    @api.constrains('email')
    def _check_email_unique(self):
        for rec in self:
            if rec.email and rec.email.strip():
                domain = [('email', '=', rec.email.strip().lower()), ('id', '!=', rec.id)] # type: ignore
                if self.search_count(domain) > 0:
                    raise ValidationError("Erreur : L'adresse email '%s' est déjà associée à un autre dossier patient !" % rec.email.strip())

    @api.constrains('cin')
    def _check_cin_unique(self):
        for rec in self:
            if rec.cin and rec.cin.strip():
                # Chercher si un autre patient a le même CIN
                domain = [('cin', '=', rec.cin.strip()), ('id', '!=', rec.id)] # type: ignore
                if self.search_count(domain) > 0:
                    raise ValidationError("Erreur : Ce numéro de CIN (%s) est déjà utilisé par un autre patient !" % rec.cin)

    is_secretaire = fields.Boolean(compute='_compute_is_secretaire')

    def _compute_is_secretaire(self):
        for rec in self:
            rec.is_secretaire = self.env.user.has_group('cabinet_medical.group_secretaire')

    active = fields.Boolean(string='Actif', default=True, help='Désactiver pour archiver le patient sans supprimer son historique')
    name = fields.Char(string='Nom complet', required=True)
    name_error = fields.Char(compute='_compute_name_error')
    date_naissance = fields.Date(string='Date de naissance', required=False)
    date_error = fields.Char(compute='_compute_date_error')
    genre = fields.Selection([
        ('', '---'),
        ('homme', 'Homme'),
        ('femme', 'Femme')
    ], string='Genre', required=False)
    telephone = fields.Char(string='Téléphone', required=False)
    telephone_error = fields.Char(compute='_compute_telephone_error')
    email = fields.Char(string='Email', help="Requis pour l'accès au portail patient")
    user_id = fields.Many2one('res.users', string='Utilisateur Portail', readonly=True, help="L'utilisateur Odoo lié à ce patient pour l'accès portail.")
    cin = fields.Char(string='CIN', required=False)
    cin_error = fields.Char(compute='_compute_cin_error')
    adresse = fields.Text(string='Adresse')
    
    # Alertes Médicales
    allergies = fields.Text(string='Allergies', help='Allergies connues (ex: Pénicilline, Arachides...)')
    allergies_display = fields.Char(string='Allergies (Résumé)', compute='_compute_allergies_display')
    antecedents = fields.Text(string='Antécédents médicaux', help='Maladies chroniques, chirurgies passées...')
    traitements_chroniques = fields.Text(
        string='Traitements chroniques',
        help='Médicaments pris en continu (ex: Metformine 500mg, Bisoprolol 5mg...)'
    )

    @api.depends('allergies')
    def _compute_allergies_display(self):
        for rec in self:
            rec.allergies_display = rec.allergies if rec.allergies else "Aucune allergie connue"

    is_cnam = fields.Boolean(string='Assuré CNAM')
    numero_cnam = fields.Char(string='Matricule CNAM', help='10 chiffres obligatoires (ex: 0123456789)')
    code_beneficiaire_cnam = fields.Selection([
        ('00', '00 - Assuré principal'),
        ('01', '01 - Conjoint'),
        ('02', '02 - Enfant 1'),
        ('03', '03 - Enfant 2'),
        ('04', '04 - Enfant 3'),
        ('05', '05 - Enfant 4'),
        ('06', '06 - Ascendant à charge'),
        ('autre', 'Autre ayant droit'),
    ], string='Code Bénéficiaire', default='00')
    carte_labes_active = fields.Boolean(string='Carte LABES / e-Houwiya', default=False, help='Indique si la carte LABES du patient est active')
    regime_cnam = fields.Selection([
        ('cnss_salarie',        'CNSS — Salarié secteur privé'),
        ('cnss_independant',    'CNSS — Travailleur indépendant'),
        ('cnrps_fonctionnaire', 'CNRPS — Fonctionnaire secteur public'),
        ('cnrps_militaire',     'CNRPS — Militaire / Forces de sécurité'),
        ('retraite_cnss',       'Retraité CNSS'),
        ('retraite_cnrps',      'Retraité CNRPS'),
        ('etudiant',            'Étudiant'),
        ('autre',               'Autre'),
    ], string='Caisse d\'affiliation CNAM',
       help='Indique l\'origine de l\'affiliation sociale du patient (CNSS = secteur privé, CNRPS = secteur public)')
    filiere_cnam = fields.Selection([
        ('privee', 'Tiers-payant (Filière Privée)'),
        ('remboursement', 'Remboursement des Frais'),
        ('publique', 'Filière Publique (Structures hospitalières)'),
    ], string='Filière CNAM')
    date_validite_cnam = fields.Date(string='Date validité CNAM')
    cnam_active = fields.Boolean(string='CNAM Active', default=True)

    is_apci = fields.Boolean(string='Patient APCI')
    apci_pathologie = fields.Selection([
        ('diabete',            'Diabète sucré'),
        ('hypertension',       'Hypertension artérielle'),
        ('cardiopathie',       'Cardiopathie chronique'),
        ('cancer',             'Affection maligne (cancer)'),
        ('insuffisance_renale','Insuffisance rénale chronique'),
        ('epilepsie',          'Épilepsie'),
        ('asthme',             'Asthme persistant'),
        ('autre',              'Autre affection APCI'),
    ], string='Pathologie APCI',
       help='Type de maladie chronique ouvrant droit à la prise en charge intégrale CNAM')
    numero_decision_apci = fields.Char(string='Numéro décision APCI')
    date_fin_apci = fields.Date(string='Date fin APCI')
    date_debut_apci = fields.Date(string='Date début APCI')
    is_cnam_expired = fields.Boolean(string='CNAM expirée', compute='_compute_cnam_expired')
    is_apci_expired = fields.Boolean(string='APCI expirée', compute='_compute_apci_expired')

    profil_couverture = fields.Selection([
        ('sans', 'Sans CNAM'),
        ('cnam', 'CNAM Simple'),
        ('apci', 'APCI')
    ], string='Profil de couverture', compute='_compute_profil_couverture', store=True)

    @api.depends('is_cnam', 'is_apci')
    def _compute_profil_couverture(self):
        for rec in self:
            if rec.is_cnam and rec.is_apci:
                rec.profil_couverture = 'apci'
            elif rec.is_cnam:
                rec.profil_couverture = 'cnam'
            else:
                rec.profil_couverture = 'sans'
    @api.onchange('is_cnam')
    def _onchange_is_cnam(self):
        """Reset APCI fields when CNAM is unchecked"""
        if not self.is_cnam:
            self.is_apci = False
            self.numero_decision_apci = False
            self.date_debut_apci = False
            self.date_fin_apci = False

    has_assurance = fields.Boolean(string='Assurance privée')
    assurance_type = fields.Char(string='Type assurance privée')
    # Exemple : COMAR, Star, GAT, Maghrebia...
    assurance_id = fields.Many2one('cabinet.assurance', string='Assurance')
    assurance_numero = fields.Char(string='Numéro d\'affiliation')
    assurance_taux = fields.Float(string='Taux de couverture (%)', related='assurance_id.taux', readonly=True, store=True)

    consultation_ids = fields.One2many('cabinet.consultation', 'patient_id', string='Consultations')
    nb_consultations = fields.Integer(string='Nombre de consultations', compute='_compute_nb_consultations')
    
    rendezvous_ids = fields.One2many('cabinet.rendezvous', 'patient_id', string='Rendez-vous')
    nb_rendezvous = fields.Integer(string='Nombre de rendez-vous', compute='_compute_nb_rendezvous')
    
    notification_ids = fields.One2many('cabinet.notification', 'patient_id', string='Notifications')
    unread_notification_count = fields.Integer(string='Notifications non lues', compute='_compute_unread_notification_count')

    # Statut du dossier : complet si les infos essentielles sont remplies
    is_dossier_complet = fields.Boolean(
        string='Dossier complet',
        compute='_compute_dossier_status',
        store=True
    )
    dossier_status = fields.Char(
        string='Statut dossier',
        compute='_compute_dossier_status',
        store=True
    )

    @api.depends('name')
    def _compute_name_error(self):
        for rec in self:
            rec.name_error = False

    @api.depends('date_naissance')
    def _compute_date_error(self):
        for rec in self:
            rec.date_error = False
            if rec.date_naissance and rec.date_naissance > date.today():
                rec.date_error = "La date de naissance ne peut pas être dans le futur"

    @api.depends('telephone')
    def _compute_telephone_error(self):
        for rec in self:
            rec.telephone_error = False
            if rec.telephone:
                if not rec.telephone.isdigit() or len(rec.telephone) != 8:
                    rec.telephone_error = 'Le numéro de téléphone doit contenir exactement 8 chiffres'

    @api.depends('cin')
    def _compute_cin_error(self):
        for rec in self:
            rec.cin_error = False
            if rec.cin:
                if not rec.cin.isdigit() or len(rec.cin) != 8:
                    rec.cin_error = 'Le CIN doit contenir exactement 8 chiffres'

    @api.depends('date_validite_cnam', 'is_cnam')
    def _compute_cnam_expired(self):
        today = date.today()
        for rec in self:
            rec.is_cnam_expired = bool(rec.is_cnam and rec.date_validite_cnam and rec.date_validite_cnam < today)

    @api.depends('date_fin_apci', 'is_apci', 'is_cnam')
    def _compute_apci_expired(self):
        today = date.today()
        for rec in self:
            rec.is_apci_expired = bool(rec.is_cnam and rec.is_apci and rec.date_fin_apci and rec.date_fin_apci < today)

    # --- Assistant IA : Conseils d'expiration On-Demand ---
    def action_ia_conseil_global(self):
        """Conseil IA intelligent déclenché depuis le bandeau principal en haut de fiche"""
        self.ensure_one()
        if self.is_cnam_expired and self.is_apci_expired:
            jours_cnam = (fields.Date.today() - self.date_validite_cnam).days if self.date_validite_cnam else 'inconnu'
            jours_apci = (fields.Date.today() - self.date_fin_apci).days if self.date_fin_apci else 'inconnu'
            patho_label = dict(self._fields['apci_pathologie'].selection).get(self.apci_pathologie, self.apci_pathologie or 'Non spécifiée')
            contexte = (
                f"Patient: {self.name}, "
                f"CNAM expiré depuis {jours_cnam} jours ({self.date_validite_cnam}), Filière: {self.filiere_cnam or 'Non spécifiée'}, Régime: {self.regime_cnam or 'Non spécifié'} | "
                f"APCI expiré depuis {jours_apci} jours ({self.date_fin_apci}), Pathologie: {patho_label}, Décision APCI: {self.numero_decision_apci or 'Non renseignée'}"
            )
            default_msg = (
                f"La carte CNAM (expirée depuis {jours_cnam} jours) et la prise en charge APCI ({patho_label}, décision {self.numero_decision_apci or 'N/A'}, expirée depuis {jours_apci} jours) de {self.name} "
                f"sont toutes deux échues. Veuillez solliciter le renouvellement simultané des deux dossiers auprès de la CNAM."
            )
            conseil_ia = self.env['cabinet.facture']._get_llm_alert("Double expiration CNAM et APCI", contexte, default_msg)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Conseil Assistant IA (CNAM & APCI)',
                    'message': conseil_ia,
                    'type': 'warning',
                    'sticky': True,
                }
            }
        elif self.is_apci_expired:
            return self.action_ia_conseil_apci()
        else:
            return self.action_ia_conseil_cnam()

    def action_ia_conseil_cnam(self):
        self.ensure_one()
        if not self.date_validite_cnam:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Conseil IA (CNAM)',
                    'message': "Aucune date de validité renseignée pour ce patient.",
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        jours_retard = (fields.Date.today() - self.date_validite_cnam).days
        contexte = f"Patient: {self.name}, Date validite CNAM expiree depuis {jours_retard} jours ({self.date_validite_cnam}), Filiere: {self.filiere_cnam or 'Non specifiee'}, Regime: {self.regime_cnam or 'Non specifie'}"
        default_msg = f"La carte CNAM du patient {self.name} est expirée depuis {jours_retard} jours ({self.date_validite_cnam}). Veuillez inviter le patient à fournir son attestation de renouvellement avant la prise en charge."
        
        conseil_ia = self.env['cabinet.facture']._get_llm_alert("Expiration des droits CNAM", contexte, default_msg)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Conseil Assistant IA (CNAM)',
                'message': conseil_ia,
                'type': 'warning',
                'sticky': True,
            }
        }

    def action_ia_conseil_apci(self):
        self.ensure_one()
        if not self.date_fin_apci:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Conseil IA (APCI)',
                    'message': "Aucune date de fin APCI renseignée pour ce patient.",
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        jours_retard = (fields.Date.today() - self.date_fin_apci).days
        patho_label = dict(self._fields['apci_pathologie'].selection).get(self.apci_pathologie, self.apci_pathologie or 'Non spécifiée')
        contexte = f"Patient: {self.name}, Prise en charge APCI expiree depuis {jours_retard} jours ({self.date_fin_apci}), Pathologie: {patho_label}, Decision: {self.numero_decision_apci or 'Non renseignee'}"
        default_msg = f"La prise en charge APCI ({patho_label}) du patient {self.name} est échue depuis {jours_retard} jours ({self.date_fin_apci}). Veuillez solliciter le renouvellement de la décision auprès de la CNAM."
        
        conseil_ia = self.env['cabinet.facture']._get_llm_alert("Expiration de la prise en charge APCI", contexte, default_msg)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Conseil Assistant IA (APCI)',
                'message': conseil_ia,
                'type': 'warning',
                'sticky': True,
            }
        }

    @api.depends('consultation_ids', 'consultation_ids.date_consultation')
    def _compute_nb_consultations(self):
        for rec in self:
            rec.nb_consultations = len(rec.consultation_ids)
            
            # Calculer la date de dernière consultation
            consults = rec.consultation_ids.filtered(lambda c: c.date_consultation).sorted('date_consultation', reverse=True)
            if consults:
                rec.date_derniere_consultation = consults[0].date_consultation
            else:
                rec.date_derniere_consultation = False

    date_derniere_consultation = fields.Datetime(
        string='Dernière consultation',
        compute='_compute_nb_consultations',
        store=False
    )

    @api.depends('rendezvous_ids')
    def _compute_nb_rendezvous(self):
        for rec in self:
            rec.nb_rendezvous = len(rec.rendezvous_ids)

    @api.depends(
        'name', 'cin', 'telephone', 'date_naissance', 'genre',
        'is_cnam', 'numero_cnam', 'filiere_cnam',
        'is_apci', 'numero_decision_apci',
        'has_assurance', 'assurance_id'
    )
    def _compute_dossier_status(self):
        """Dossier complet selon les règles définies"""
        for rec in self:
            # Vérification des champs de base
            complet = bool(
                rec.name and 
                rec.cin and 
                rec.telephone and 
                rec.date_naissance and 
                rec.genre and rec.genre != ''
            )
            
            # Vérifications conditionnelles
            if complet and rec.is_cnam:
                complet = bool(rec.numero_cnam and rec.filiere_cnam)
                
            if complet and rec.is_apci:
                complet = bool(rec.numero_decision_apci)
                
            if complet and rec.has_assurance:
                complet = bool(rec.assurance_id)
                
            rec.is_dossier_complet = complet
            rec.dossier_status = 'Complet' if complet else 'Incomplet'


    def action_creer_rendezvous(self):
        self.ensure_one()
        return {
            'name': 'Créer rendez-vous',
            'type': 'ir.actions.act_window',
            'res_model': 'cabinet.rendezvous',
            'views': [(False, 'form')],
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_patient_id': self.id, # type: ignore
            }
        }
        
    def action_create_portal_user(self):
        self.ensure_one()
        if not self.email:
            raise ValidationError("Veuillez d'abord saisir l'email du patient avant de créer son accès portail.")
        
        if self.user_id:
            raise ValidationError("Ce patient possède déjà un accès portail.")
            
        email_clean = self.email.strip().lower()
        # Chercher si un utilisateur avec cet email existe déjà
        existing_user = self.env['res.users'].sudo().search(['|', ('login', '=', email_clean), ('email', '=', email_clean)], limit=1)
        if existing_user:
            # Vérifier si cet utilisateur est déjà lié à un autre patient
            other_patient = self.env['cabinet.patient'].sudo().search([('user_id', '=', existing_user.id), ('id', '!=', self.id)], limit=1)
            if other_patient:
                raise ValidationError(
                    f"Impossible de créer ou lier cet accès : Le compte utilisateur ({existing_user.name} - {existing_user.login}) "
                    f"est déjà lié au dossier patient '{other_patient.name}' (ID: {other_patient.id}). "
                    f"Chaque patient doit disposer d'une adresse email et d'un compte portail uniques."
                )
            self.sudo().user_id = existing_user.id
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Accès Lié',
                    'message': 'Un compte avec cet email existait déjà, il a été lié à ce patient.',
                    'sticky': False,
                    'type': 'success',
                }
            }
            
        # Chercher si le contact (partner) existe déjà avec cet email
        partner = self.env['res.partner'].sudo().search([('email', '=', self.email)], limit=1)
        if not partner:
            # Créer le partner s'il n'existe pas
            partner = self.env['res.partner'].sudo().create({
                'name': self.name,
                'email': self.email,
                'phone': self.telephone,
                'tz': 'Africa/Tunis',
            })
            
        # Créer l'utilisateur manuellement pour éviter les crashs SMTP du wizard en local
        # Utiliser l'assistant officiel du portail pour créer l'utilisateur sans crasher sur le SMTP
        try:
            # 1. Créer le wizard
            wizard = self.env['portal.wizard'].sudo().create({
                'partner_ids': [(4, partner.id)]
            })
            
            if wizard.user_ids:
                wizard_user = wizard.user_ids[0]
                
                # Appeler la méthode native d'Odoo qui gère tout (création, token, et envoi du bon lien)
                wizard_user.with_context(use_custom_portal_template=True).sudo().action_grant_access()
                
                # Lier l'utilisateur fraîchement créé au dossier patient
                if partner.user_ids:
                    self.sudo().user_id = partner.user_ids[0].id
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Accès Créé',
                    'message': 'Le compte portail a été créé avec succès et l\'email d\'invitation officiel a été envoyé instantanément.',
                    'sticky': False,
                    'type': 'success',
                }
            }
        except Exception as e:
            raise ValidationError(f"Erreur lors de la création de l'accès portail : {str(e)}")

    def action_resend_portal_invite(self):
        self.ensure_one()
        if not self.email:
            raise ValidationError("Veuillez d'abord saisir l'email du patient.")
        if not self.user_id:
            raise ValidationError("Ce patient n'a pas encore de compte portail créé.")
            
        user = self.user_id.sudo()
        partner = user.partner_id.sudo()
        
        # If the email was changed on the patient card, update the user login and partner email
        if self.email != user.login:
            # Check for conflicts
            conflicting_user = self.env['res.users'].sudo().search([('login', '=', self.email), ('id', '!=', user.id)], limit=1)
            if conflicting_user:
                raise ValidationError(f"Un autre compte utilisateur utilise déjà l'email {self.email}.")
            user.login = self.email
            user.email = self.email
            partner.email = self.email
            
        try:
            # Create portal wizard to resend invitation
            wizard = self.env['portal.wizard'].sudo().create({
                'partner_ids': [(4, partner.id)]
            })
            if wizard.user_ids:
                wizard_user = wizard.user_ids[0]
                wizard_user.with_context(use_custom_portal_template=True).sudo().action_invite_again()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Invitation Renvoyée',
                    'message': f"L'email d'invitation a été renvoyé avec succès à l'adresse {self.email}.",
                    'sticky': False,
                    'type': 'success',
                }
            }
        except Exception as e:
            raise ValidationError(f"Erreur lors du renvoi de l'invitation : {str(e)}")

    def action_view_consultations(self):
        self.ensure_one()
        return {
            'name': 'Consultations du patient',
            'type': 'ir.actions.act_window',
            'res_model': 'cabinet.consultation',
            'views': [(False, 'tree'), (False, 'form')],
            'view_mode': 'tree,form',
            'domain': [('patient_id', '=', self.id)], # type: ignore
            'context': {'default_patient_id': self.id}, # type: ignore
        }

    def action_view_rendezvous(self):
        self.ensure_one()
        return {
            'name': 'Rendez-vous du patient',
            'type': 'ir.actions.act_window',
            'res_model': 'cabinet.rendezvous',
            'views': [(False, 'tree'), (False, 'form')],
            'view_mode': 'tree,form',
            'domain': [('patient_id', '=', self.id)], # type: ignore
            'context': {'default_patient_id': self.id}, # type: ignore
        }

    @api.model_create_multi
    def create(self, vals_list):
        """Créer un patient avec des valeurs par défaut et lier au rendez-vous si nécessaire"""
        for vals in vals_list:
            # S'assurer que le nom est en majuscules
            if vals.get('name'):
                vals['name'] = vals['name'].strip().upper()
        
        # Créer les patients
        patients = super(Patient, self).create(vals_list)
        
        for patient in patients:
            # Synchroniser les informations vers le partner et l'utilisateur lié si existant
            if patient.user_id:
                user = patient.user_id.sudo()
                partner = user.partner_id.sudo()
                partner_vals = {}
                if patient.name and partner.name != patient.name:
                    partner_vals['name'] = patient.name
                if patient.email and partner.email != patient.email:
                    partner_vals['email'] = patient.email
                if patient.telephone and partner.phone != patient.telephone:
                    partner_vals['phone'] = patient.telephone
                if patient.adresse and partner.street != patient.adresse:
                    partner_vals['street'] = patient.adresse
                if partner_vals:
                    partner.write(partner_vals)
                if patient.name and user.name != patient.name:
                    user.write({'name': patient.name})

            # Vérifier si ce patient est créé depuis un rendez-vous
            from_rendezvous_id = self._context.get('from_rendezvous_id')
            if from_rendezvous_id:
                rdv = self.env['cabinet.rendezvous'].browse(from_rendezvous_id)
                if rdv.exists():
                    rdv.patient_id = patient.id
        return patients

    def write(self, vals):
        """Mettre à jour le patient et synchroniser immédiatement vers res.partner et res.users pour cohérence portail"""
        if vals.get('name'):
            vals['name'] = vals['name'].strip().upper()
        res = super(Patient, self).write(vals)
        for rec in self:
            if rec.user_id:
                user = rec.user_id.sudo()
                partner = user.partner_id.sudo()
                partner_vals = {}
                if 'name' in vals and partner.name != rec.name:
                    partner_vals['name'] = rec.name
                if 'email' in vals and partner.email != rec.email:
                    partner_vals['email'] = rec.email
                if 'telephone' in vals and partner.phone != rec.telephone:
                    partner_vals['phone'] = rec.telephone
                if 'adresse' in vals and partner.street != rec.adresse:
                    partner_vals['street'] = rec.adresse
                if partner_vals:
                    partner.write(partner_vals)
                if 'name' in vals and user.name != rec.name:
                    user.write({'name': rec.name})
        return res

    @api.constrains('cin')
    def _check_cin(self):
        for rec in self:
            if rec.cin:
                if not rec.cin.isdigit() or len(rec.cin) != 8:
                    raise ValidationError("Le CIN doit contenir exactement 8 chiffres")

    @api.constrains('telephone')
    def _check_telephone(self):
        for rec in self:
            if rec.telephone:
                if not rec.telephone.isdigit() or len(rec.telephone) != 8:
                    raise ValidationError("Le téléphone doit contenir 8 chiffres")
                if rec.telephone[0] not in ['2', '4', '5', '7', '9']:
                    raise ValidationError("Le téléphone doit commencer par 2, 4, 5, 7 ou 9 (numéro tunisien)")

    @api.constrains('date_naissance')
    def _check_date_naissance(self):
        for rec in self:
            if rec.date_naissance and rec.date_naissance > date.today():
                raise ValidationError("La date de naissance ne peut pas être dans le futur")

    @api.constrains('numero_cnam', 'is_cnam')
    def _check_numero_cnam(self):
        for rec in self:
            if rec.is_cnam and rec.numero_cnam:
                if not rec.numero_cnam.isdigit() or len(rec.numero_cnam) != 10:
                    raise ValidationError("Le matricule CNAM doit être composé de 10 chiffres exactement.")

    
    def unlink(self):
        """Bloquer la suppression physique des patients (Règle éthique et légale)"""
        raise ValidationError("Les dossiers patients ne peuvent pas être supprimés physiquement pour des raisons médico-légales. Si ce dossier est un doublon ou n'est plus actif, veuillez utiliser la fonction d'archivage (bouton Actif/Inactif).")

    def _compute_unread_notification_count(self):
        for rec in self:
            rec.unread_notification_count = self.env['cabinet.notification'].search_count([
                ('patient_id', '=', getattr(rec, 'id')),
                ('is_read', '=', False)
            ])

    @api.model
    def _cron_check_cnam_expiration(self):
        """Cron scheduler method to alert patients on CNAM expiration and 7-day warning."""
        from datetime import date, timedelta
        today = date.today()
        seven_days_later = today + timedelta(days=7)
        
        # 1. Check patients expiring today
        expiring_today = self.search([
            ('is_cnam', '=', True),
            ('date_validite_cnam', '=', today)
        ])
        for patient in expiring_today:
            self.env['cabinet.notification'].create_notification(
                patient_id=getattr(patient, 'id'),
                title="Couverture CNAM expirée",
                message="Votre couverture CNAM a expiré aujourd'hui. Veuillez contacter le secrétariat pour la mettre à jour.",
                notif_type='cnam',
                res_url='/my/couverture'
            )
            
        # 2. Check patients expiring in exactly 7 days
        expiring_soon = self.search([
            ('is_cnam', '=', True),
            ('date_validite_cnam', '=', seven_days_later)
        ])
        for patient in expiring_soon:
            self.env['cabinet.notification'].create_notification(
                patient_id=getattr(patient, 'id'),
                title="Expiration CNAM proche (7 jours)",
                message=f"Votre couverture CNAM expire dans 7 jours (le {patient.date_validite_cnam.strftime('%d/%m/%Y')}). Pensez à renouveler vos droits.",
                notif_type='cnam',
                res_url='/my/couverture'
            )



class PortalWizardUser(models.TransientModel):
    _inherit = 'portal.wizard.user'  # type: ignore

    def _send_email(self):
        self.ensure_one()
        if self._context.get('use_custom_portal_template'):
            template = self.env.ref('cabinet_medical.mail_template_portal_welcome_custom', raise_if_not_found=False)
            if template:
                user = self.user_id.sudo()  # type: ignore
                lang = user.lang
                partner = user.partner_id

                portal_url = partner.with_context(signup_force_type_in_url='', lang=lang)._get_signup_url_for_action()[partner.id]
                partner.signup_prepare()

                template.with_context(dbname=self._cr.dbname, portal_url=portal_url, lang=lang).send_mail(self.id, force_send=True)  # type: ignore
                return True
        return super(PortalWizardUser, self)._send_email()  # type: ignore
