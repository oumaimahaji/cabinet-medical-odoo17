# -*- coding: utf-8 -*-
from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError, UserError, AccessError  # type: ignore
from passlib.context import CryptContext  # type: ignore

pin_crypt_context = CryptContext(schemes=['pbkdf2_sha512'], deprecated='auto')

class ResUsers(models.Model):
    _inherit = 'res.users'

    signature_medecin = fields.Binary(
        string='Signature du Médecin',
        attachment=True,
        help="Image de signature manuscrite du médecin (PNG/JPG) réutilisée pour les ordonnances."
    )
    pin_signature_hash = fields.Char(
        string='Hash PIN Signature',
        copy=False,
        help="PIN haché de manière sécurisée avec PBKDF2-SHA512, jamais stocké en clair."
    )
    has_signature = fields.Boolean(
        string='Signature configurée',
        compute='_compute_signature_status',
        store=False
    )
    has_signature_pin = fields.Boolean(
        string='PIN configuré',
        compute='_compute_signature_status',
        store=False
    )

    @api.depends('signature_medecin')
    def _compute_signature_status(self):
        for user in self:
            user.has_signature = bool(user.signature_medecin)
            user.has_signature_pin = bool(user.sudo().pin_signature_hash)



    def set_signature_pin(self, new_pin):
        """Définit le PIN personnel du médecin après vérification de format."""
        self.ensure_one()
        # Sécurité : seul l'utilisateur lui-même ou un administrateur système peut modifier le PIN
        if self.env.user.id != self.id and not self.env.is_admin():
            raise AccessError("Vous ne pouvez modifier que votre propre code PIN de signature.")
        
        if not new_pin or not str(new_pin).strip().isdigit() or len(str(new_pin).strip()) < 4 or len(str(new_pin).strip()) > 8:
            raise ValidationError("Le code PIN doit être composé de 4 à 8 chiffres exclusivement.")
        
        pin_hashed = pin_crypt_context.hash(str(new_pin).strip())
        self.sudo().write({'pin_signature_hash': pin_hashed})
        return True

    def verify_signature_pin(self, pin_to_check):
        """Vérifie si le PIN fourni correspond au hash stocké."""
        self.ensure_one()
        if not self.pin_signature_hash:
            return False
        if not pin_to_check:
            return False
        try:
            return pin_crypt_context.verify(str(pin_to_check).strip(), self.pin_signature_hash)
        except Exception:
            return False

    def action_clear_signature(self):
        """Supprime la signature du profil médecin."""
        self.ensure_one()
        if self.env.user.id != self.id and not self.env.is_admin():
            raise AccessError("Vous ne pouvez modifier que votre propre profil.")
        self.sudo().write({'signature_medecin': False})
