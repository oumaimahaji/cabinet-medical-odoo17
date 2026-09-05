from odoo import models

KEY_RESTRICTED = 'is_cabinet_restricted'
GROUP_MEDECIN = 'cabinet_medical.group_medecin'
GROUP_SECRETAIRE = 'cabinet_medical.group_secretaire'
GROUP_SYSTEM = 'base.group_system'

class Http(models.AbstractModel):
    _inherit = 'ir.http'  # type: ignore

    def session_info(self):
        try:
            result = super(Http, self).session_info()  # type: ignore
            user = self.env.user
            is_admin = user.has_group(GROUP_SYSTEM)
            is_staff = user.has_group(GROUP_MEDECIN) or user.has_group(GROUP_SECRETAIRE)
            result[KEY_RESTRICTED] = bool(not is_admin and is_staff)
            return result
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Erreur session_info")
            raise


