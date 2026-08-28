# -*- coding: utf-8 -*-
from odoo import models, fields, api  # type: ignore

class CabinetNotification(models.Model):
    _name = 'cabinet.notification'
    _description = 'Notification Patient'
    _order = 'date desc'

    patient_id = fields.Many2one(
        'cabinet.patient',
        string='Patient',
        required=True,
        ondelete='cascade'
    )
    title = fields.Char(string='Titre', required=True)
    message = fields.Text(string='Message', required=True)
    type = fields.Selection([
        ('rdv_present', 'Arrivée enregistrée'),
        ('rdv_annule', 'Rendez-vous annulé'),
        ('rdv_reporte', 'Rendez-vous reporté'),
        ('ordonnance', 'Nouvelle ordonnance'),
        ('facture', 'Nouvelle facture'),
        ('cnam', 'Alerte CNAM')
    ], string='Type', required=True)
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True)
    is_read = fields.Boolean(string='Lu', default=False)
    res_url = fields.Char(string='Lien vers l\'objet')

    # Computed fields for custom styling in QWeb views
    icon = fields.Char(string='Icône', compute='_compute_style')
    icon_color = fields.Char(string='Couleur Icône', compute='_compute_style')
    bg_color = fields.Char(string='Couleur Fond', compute='_compute_style')

    @api.depends('type')
    def _compute_style(self):
        for rec in self:
            if rec.type == 'rdv_present':
                rec.icon = 'fa-calendar-check-o'
                rec.icon_color = '#198754'  # green
                rec.bg_color = 'rgba(25, 135, 84, 0.08)'
            elif rec.type == 'rdv_annule':
                rec.icon = 'fa-calendar-times-o'
                rec.icon_color = '#dc3545'  # red
                rec.bg_color = 'rgba(220, 53, 69, 0.08)'
            elif rec.type == 'rdv_reporte':
                rec.icon = 'fa-calendar'
                rec.icon_color = '#fd7e14'  # orange
                rec.bg_color = 'rgba(253, 126, 20, 0.08)'
            elif rec.type == 'ordonnance':
                rec.icon = 'fa-file-text-o'
                rec.icon_color = '#10b981'  # emerald
                rec.bg_color = 'rgba(16, 185, 129, 0.08)'
            elif rec.type == 'facture':
                rec.icon = 'fa-credit-card'
                rec.icon_color = '#f59e0b'  # amber
                rec.bg_color = 'rgba(245, 158, 11, 0.08)'
            elif rec.type == 'cnam':
                rec.icon = 'fa-hospital-o'
                rec.icon_color = '#06b6d4'  # cyan
                rec.bg_color = 'rgba(6, 182, 212, 0.08)'
            else:
                rec.icon = 'fa-bell'
                rec.icon_color = '#6c757d'
                rec.bg_color = 'rgba(108, 117, 125, 0.08)'

    @api.model
    def create_notification(self, patient_id, title, message, notif_type, res_url=None, critical=False, res_model=None, res_id=None):
        """Helper method to create a patient notification and optionally send an email template."""
        # Check if patient exists
        patient = self.env['cabinet.patient'].browse(patient_id)
        if not patient.exists():
            return False

        # Create the notification record
        notif = self.create({
            'patient_id': patient.id,
            'title': title,
            'message': message,
            'type': notif_type,
            'res_url': res_url,
        })

        # Email integration for critical notifications using standard mail.template
        if critical and patient.email:
            template = False
            if notif_type == 'rdv_annule':
                template = self.env.ref('cabinet_medical.mail_template_rdv_annule', raise_if_not_found=False)
            elif notif_type == 'rdv_reporte':
                template = self.env.ref('cabinet_medical.mail_template_rdv_reporte', raise_if_not_found=False)

            if template and res_model == 'cabinet.rendezvous' and res_id:
                try:
                    # Envoi de l'email via le template en lui passant l'ID de l'objet
                    template.send_mail(res_id, force_send=True)
                except Exception:
                    pass  # Prevent email delivery failures from blocking transactions in local mode

        return notif
