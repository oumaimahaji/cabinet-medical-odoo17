from dateutil.relativedelta import relativedelta  # type: ignore
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class BordereauCNAM(models.Model):
    _name = 'cabinet.bordereau'
    _description = 'Bordereau d\'envoi CNAM'
    _order = 'date_creation desc'

    name = fields.Char(string='Référence', required=True, copy=False, readonly=True, default='Nouveau')
    date_creation = fields.Date(string='Date de création', default=fields.Date.context_today, required=True)
    date_debut = fields.Date(string='Période du', required=True)
    date_fin = fields.Date(string='Au', required=True)
    active = fields.Boolean(default=True, string='Actif')

    # Libellé de période lisible (ex: "Juin 2025") — utile pour les impressions
    periode_label = fields.Char(
        string='Période',
        compute='_compute_periode_label',
        store=True,
        help='Période du bordereau sous forme lisible (Mois Année)'
    )
    
    motif_rejet = fields.Text(string='Motif de rejet', help='Indiquez pourquoi la CNAM a rejeté ce bordereau')
    date_envoi = fields.Date(string='Date d\'envoi')

    @api.depends('date_debut')
    def _compute_periode_label(self):
        MOIS = {
            1: 'Janvier', 2: 'Février', 3: 'Mars', 4: 'Avril',
            5: 'Mai', 6: 'Juin', 7: 'Juillet', 8: 'Août',
            9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre'
        }
        for rec in self:
            if rec.date_debut:
                rec.periode_label = f"{MOIS.get(rec.date_debut.month, '')} {rec.date_debut.year}"
            else:
                rec.periode_label = ''


    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Validé'),
        ('sent', 'Envoyé'),
        ('partially_paid', 'Partiellement payé'),
        ('paid', 'Payé'),
        ('rejected', 'Rejeté')
    ], string='Statut', default='draft', required=True)

    facture_ids = fields.One2many('cabinet.facture', 'bordereau_id', string='Factures associées')
    
    montant_total = fields.Float(string='Total Actes (DT)', compute='_compute_totaux', store=True)
    montant_cnam_demande = fields.Float(string='Total Demandé CNAM (DT)', compute='_compute_totaux', store=True)
    nb_factures = fields.Integer(string='Nombre de factures', compute='_compute_totaux', store=True)

    @api.depends('facture_ids', 'facture_ids.montant_total', 'facture_ids.montant_cnam_cabinet')
    def _compute_totaux(self):
        for rec in self:
            rec.nb_factures = len(rec.facture_ids)
            rec.montant_total = sum(rec.facture_ids.mapped('montant_total'))
            rec.montant_cnam_demande = sum(rec.facture_ids.mapped('montant_cnam_cabinet'))

    @api.constrains('date_debut', 'date_fin')
    def _check_dates(self):
        for rec in self:
            if rec.date_debut and rec.date_fin and rec.date_debut > rec.date_fin:
                raise ValidationError("La date de début ne peut pas être supérieure à la date de fin.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code('cabinet.bordereau') or 'Nouveau'
        return super(BordereauCNAM, self).create(vals_list)

    def action_recuperer_factures(self):
        self.ensure_one()
        if self.state != 'draft':
            raise ValidationError("Vous ne pouvez récupérer les factures que si le bordereau est en brouillon.")
            
        domain = [
            ('state', '=', 'validated'),
            ('date_facture', '>=', self.date_debut),
            ('date_facture', '<=', self.date_fin),
            ('scenario', 'in', ['cnam_tiers_payant', 'apci_tiers_payant', 'cnam_tp_assur']), # Uniquement Tiers-Payant et APCI
            ('montant_cnam_cabinet', '>', 0),
            ('bordereau_id', '=', False) # Exclut les factures déjà liées
        ]
        factures = self.env['cabinet.facture'].search(domain)
        if not factures:
            return {
                'warning': {
                    'title': 'Aucune facture',
                    'message': 'Aucune facture CNAM trouvée pour cette période.'
                }
            }
        
        for f in factures:
            f.bordereau_id = self.id  # type: ignore
            f.statut_cnam = 'non_envoye'

    def action_valider(self):
        self.ensure_one()
        if not self.facture_ids:
            raise ValidationError("Impossible de valider un bordereau vide.")
        if self.name == 'Nouveau':
            self.name = self.env['ir.sequence'].next_by_code('cabinet.bordereau') or 'Nouveau'
        self.state = 'done'

    def action_envoyer(self):
        self.ensure_one()
        self.state = 'sent'
        self.date_envoi = fields.Date.context_today(self)
        for f in self.facture_ids:
            f.statut_cnam = 'envoye'

    def action_marquer_partiellement_paye(self):
        self.ensure_one()
        self.state = 'partially_paid'

    def action_marquer_paye(self):
        self.ensure_one()
        self.state = 'paid'
        for f in self.facture_ids:
            f.statut_cnam = 'paye'

    def action_rejeter(self):
        self.ensure_one()
        self.state = 'rejected'
        for f in self.facture_ids:
            f.statut_cnam = 'rejete'

    @api.model
    def get_cnam_dashboard_stats(self, month=None, year=None):
        today = fields.Date.context_today(self)
        if not month:
            month = today.month
        if not year:
            year = today.year
            
        month = int(month)
        year = int(year)
        
        first_day = today.replace(year=year, month=month, day=1)
        last_day = first_day + relativedelta(day=31)
        
        # 1. Bordereaux envoyés ce mois
        envoyes = self.search([
            ('state', 'in', ['sent', 'partially_paid', 'paid']), 
            ('date_envoi', '>=', first_day),
            ('date_envoi', '<=', last_day)
        ])
        
        # 2. En attente de paiement (statut Envoyé ou Partiellement payé, quelle que soit la date)
        en_attente = self.search([
            ('state', 'in', ['sent', 'partially_paid'])
        ])
        
        attente_jours = 0
        if en_attente:
            total_jours = sum((today - b.date_envoi).days for b in en_attente if b.date_envoi)
            attente_jours = total_jours // len(en_attente)
            
        # 3. Payés ce mois (bordereaux dont la date d'envoi est dans le mois et qui sont payés)
        payes = self.search([
            ('state', '=', 'paid'),
            ('date_envoi', '>=', first_day),
            ('date_envoi', '<=', last_day)
        ])
        
        # 4. Rejetés (quel que soit le mois pour ne pas les oublier)
        rejetes = self.search([
            ('state', '=', 'rejected')
        ])
        
        rejetes_list = []
        for r in rejetes:
            patients = list(set(r.facture_ids.mapped('patient_id.name')))
            rejetes_list.append({
                'name': r.name,
                'motif': r.motif_rejet or 'Motif non spécifié',
                'patients': patients,
                'montant': r.montant_cnam_demande
            })
            
        return {
            'envoyes': {
                'count': len(envoyes),
                'amount': sum(envoyes.mapped('montant_cnam_demande'))
            },
            'attente': {
                'count': len(en_attente),
                'amount': sum(en_attente.mapped('montant_cnam_demande')),
                'avg_days': attente_jours
            },
            'payes': {
                'count': len(payes),
                'amount': sum(payes.mapped('montant_cnam_demande'))
            },
            'rejetes': rejetes_list
        }
