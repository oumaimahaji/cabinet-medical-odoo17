# -*- coding: utf-8 -*-
from odoo import models, fields, api  # type: ignore
from odoo.exceptions import ValidationError, UserError, AccessError  # type: ignore

class CabinetPrescriptionSignWizard(models.TransientModel):
    _name = 'cabinet.prescription.sign.wizard'
    _description = 'Confirmation de signature de l ordonnance'

    prescription_id = fields.Many2one(
        'cabinet.prescription',
        string='Ordonnance',
        required=True,
        readonly=True
    )
    pin = fields.Char(
        string='Code PIN personnel',
        required=True,
        help="Saisissez votre code PIN secret de médecin pour signer cette ordonnance."
    )

    def action_confirm_signature(self):
        self.ensure_one()
        current_user = self.env.user
        
        # 1. Vérification des droits : Seul un médecin peut signer
        if not current_user.has_group('cabinet_medical.group_medecin'):
            raise AccessError("Seul un médecin est habilité à signer des ordonnances médicales.")

        # 2. Vérification des prérequis de signature sur le profil médecin
        if not current_user.signature_medecin:
            raise ValidationError(
                "Vous n'avez pas encore enregistré votre image de signature dans votre profil médecin. "
                "Veuillez enregistrer votre signature dans 'Mon Profil' ou 'Configuration > Profil Médecin' avant de signer."
            )
            
        if not current_user.has_signature_pin:
            raise ValidationError(
                "Vous n'avez pas encore configuré votre code PIN de signature dans votre profil médecin. "
                "Veuillez définir votre code PIN secret avant de procéder à la signature."
            )

        # 3. Vérification de l'authenticité du code PIN saisi
        if not current_user.sudo().verify_signature_pin(self.pin):
            raise ValidationError(
                "Le code PIN saisi est incorrect. La signature a été refusée et l'ordonnance n'a pas été modifiée."
            )

        # 4. Exécuter l'apposition immuable de la signature sur l'ordonnance
        self.prescription_id.action_apply_signature(current_user)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Ordonnance Signée avec Succès',
                'message': f"L'ordonnance a été signée par le Dr. {current_user.name} et est maintenant verrouillée.",
                'sticky': False,
                'type': 'success',
            }
        }
