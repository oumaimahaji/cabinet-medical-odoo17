from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    medecin_nom = fields.Char(string='Nom du Médecin')
    medecin_inpe = fields.Char(string='INPE Médecin')
    medecin_code_convention = fields.Char(string='Code Convention CNAM')
