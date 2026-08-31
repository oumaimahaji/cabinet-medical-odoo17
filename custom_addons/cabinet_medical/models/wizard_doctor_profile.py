# -*- coding: utf-8 -*-
from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError, AccessError  # type: ignore

class DoctorProfileWizard(models.TransientModel):
    _name = 'cabinet.doctor.profile.wizard'
    _description = 'Configuration Signature et PIN Médecin'

    user_id = fields.Many2one('res.users', string='Utilisateur Médecin', default=lambda self: self.env.user, required=True, readonly=True)
    medecin_nom = fields.Char(string='Nom du Médecin', related='user_id.name', readonly=True)
    signature_medecin = fields.Binary(
        string='Image de la Signature (PNG/JPG)',
        attachment=True,
        help="Téléchargez l'image de votre signature manuscrite. Elle sera apposée sur vos ordonnances."
    )
    has_existing_signature = fields.Boolean(
        string='Signature enregistrée',
        compute='_compute_existing_status'
    )
    has_existing_pin = fields.Boolean(
        string='PIN configuré',
        compute='_compute_existing_status'
    )
    new_pin = fields.Char(
        string='Nouveau Code PIN (4 à 8 chiffres)',
        help="Définissez ou modifiez votre code PIN secret de signature."
    )
    confirm_pin = fields.Char(
        string='Confirmer le Code PIN',
        help="Retapez le même code PIN pour confirmation."
    )

    @api.depends('user_id')
    def _compute_existing_status(self):
        for rec in self:
            rec.has_existing_signature = bool(rec.user_id.signature_medecin)
            rec.has_existing_pin = bool(rec.user_id.sudo().pin_signature_hash)


    @api.model
    def default_get(self, fields_list):
        res = super(DoctorProfileWizard, self).default_get(fields_list)
        user = self.env.user
        if 'signature_medecin' in fields_list:
            res['signature_medecin'] = user.signature_medecin
        return res

    def action_save_profile(self):
        self.ensure_one()
        user = self.user_id
        
        # 1. Mise à jour de la signature
        user.sudo().write({'signature_medecin': self.signature_medecin})

        # 2. Mise à jour du code PIN si renseigné
        if self.new_pin or self.confirm_pin:
            if not self.new_pin or not self.confirm_pin:
                raise ValidationError("Veuillez saisir et confirmer votre code PIN.")
            if self.new_pin.strip() != self.confirm_pin.strip():
                raise ValidationError("Les deux codes PIN saisis ne correspondent pas.")
            user.set_signature_pin(self.new_pin.strip())

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Profil Médecin Mis à Jour',
                'message': "Votre signature et vos paramètres de sécurité PIN ont été enregistrés avec succès.",
                'sticky': False,
                'type': 'success',
            }
        }

    def action_delete_signature(self):
        self.ensure_one()
        self.user_id.action_clear_signature()
        self.signature_medecin = False
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Signature Supprimée',
                'message': "Votre signature a été retirée de votre profil.",
                'sticky': False,
                'type': 'info',
            }
        }
