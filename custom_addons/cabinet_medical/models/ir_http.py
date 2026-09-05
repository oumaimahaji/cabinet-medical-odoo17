from odoo import models

class Http(models.AbstractModel):
    _inherit = 'ir.http'  # type: ignore

    def session_info(self):
        try:
            result = super(Http, self).session_info()  # type: ignore
            user = self.env.user
            is_admin = user.has_group('base.group_system')
            if not is_admin:
                is_medecin = user.has_group('cabinet_medical.group_medecin')
                is_secretaire = user.has_group('cabinet_medical.group_secretaire')
                if is_medecin or is_secretaire:
                    result['is_cabinet_restricted'] = True
                else:
                    result['is_cabinet_restricted'] = False
            else:
                result['is_cabinet_restricted'] = False
            return result
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Erreur session_info")
            raise


