from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    medecin_nom = fields.Char(string='Nom du Médecin')
    medecin_inpe = fields.Char(string='INPE Médecin')
    medecin_code_convention = fields.Char(string='Code Convention CNAM')
    medecin_specialite = fields.Selection([
        ('generaliste', 'Médecin Généraliste'),
        ('specialiste', 'Médecin Spécialiste')
    ], string='Spécialité du Médecin', default='generaliste')
    medecin_conventionne = fields.Boolean(string='Médecin Conventionné CNAM', default=True)

    def check_access_rights(self, operation, raise_exception=True):
        if operation in ('read', 'write') and (
            self.env.user.has_group('cabinet_medical.group_medecin') or
            self.env.user.has_group('cabinet_medical.group_secretaire')
        ):
            return True
        return super().check_access_rights(operation, raise_exception)
