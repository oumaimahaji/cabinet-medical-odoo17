from odoo import models, fields, api  # type: ignore

class CabinetSuiviWizard(models.TransientModel):
    _name = 'cabinet.suivi.wizard'
    _description = 'Wizard pour planifier un suivi'

    patient_id = fields.Many2one('cabinet.patient', string='Patient', required=True)
    calendar_html = fields.Html(string='Calendrier', sanitize=False, readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super(CabinetSuiviWizard, self).default_get(fields_list)
        if res.get('patient_id'):
            res['calendar_html'] = self.env['cabinet.rendezvous'].get_interactive_calendar_html(patient_id=res['patient_id'])
        return res
