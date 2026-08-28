from odoo import models, fields, api  # type: ignore

class Assurance(models.Model):
    _name = 'cabinet.assurance'
    _description = 'Assurances Privées'
    _order = 'name asc'

    name = fields.Char(string='Nom de l\'assurance', required=True)
    taux = fields.Float(string='Taux de couverture (%)', required=True, default=80.0, help='Taux de couverture de l\'assurance en pourcentage')
    description = fields.Text(string='Description', help='Description détaillée de l\'assurance')
    active = fields.Boolean(string='Active', default=True, help='Désactivez pour masquer cette assurance dans les sélections')
    tiers_payant_direct = fields.Boolean(
        string='Tiers-Payant Direct', 
        default=False, 
        help='Si coché, le cabinet ne fait pas payer la part mutuelle au patient (le cabinet se fait payer par la mutuelle). Si décoché (standard), le patient paie la totalité du ticket modérateur et se fait rembourser.'
    )
    
    # Champ calculé pour affichage
    taux_affichage = fields.Char(string='Taux', compute='_compute_taux_affichage', store=True)
    
    @api.depends('taux')
    def _compute_taux_affichage(self):
        for rec in self:
            rec.taux_affichage = f"{rec.taux}%" if rec.taux else "0%"
    
    def name_get(self):
        result = []
        for record in self:
            name = f"{record.name} ({record.taux}%)" if record.taux else record.name
            result.append((record.id, name))  # type: ignore
        return result
