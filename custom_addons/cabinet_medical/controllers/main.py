import logging
import datetime
from dateutil.relativedelta import relativedelta  # type: ignore
import werkzeug

from odoo import http, fields, _  # type: ignore
from odoo.http import request  # type: ignore
from odoo.exceptions import UserError  # type: ignore
from odoo.addons.auth_signup.controllers.main import AuthSignupHome  # type: ignore
from odoo.addons.auth_signup.models.res_users import SignupError  # type: ignore
from werkzeug.urls import url_encode

_logger = logging.getLogger(__name__)

JOURS_FR = {
    0: 'Lun', 1: 'Mar', 2: 'Mer', 3: 'Jeu',
    4: 'Ven', 5: 'Sam', 6: 'Dim'
}

class CabinetMedicalController(http.Controller):

    @http.route('/cabinet_medical/get_calendar_data', type='json', auth='user')
    def get_calendar_data(self, month=None, selected_date=None, **kwargs):
        env = request.env
        params = env['ir.config_parameter'].sudo()
        
        max_normal = int(params.get_param('cabinet.max_rdv_normal', '20'))
        max_urgence = int(params.get_param('cabinet.max_rdv_urgence', '2'))
        heure_debut = float(params.get_param('cabinet.heure_debut', '8.0'))
        heure_fin = float(params.get_param('cabinet.heure_fin', '17.0'))
        work_days_str = params.get_param('cabinet.work_days', '0,1,2,3,4,5')
        work_days = [int(d.strip()) for d in work_days_str.split(',') if d.strip()]
        
        rdv_model = env['cabinet.rendezvous'].sudo()
        
        if not month:
            today = fields.Date.context_today(env['cabinet.rendezvous'])
            month = today.strftime('%Y-%m')
            
        year, m = map(int, month.split('-'))
        start_date = datetime.date(year, m, 1)
        end_date = start_date + relativedelta(day=31)
        last_day = end_date.day
        
        domain = [
            ('date', '>=', start_date),
            ('date', '<=', end_date),
            ('state', 'not in', ['annule', 'absent']),
        ]
        rdvs = rdv_model.search_read(domain, ['date', 'is_urgence'])
        
        counts_by_date = {}
        for r in rdvs:
            d_str = r['date'].strftime('%Y-%m-%d')
            is_urg = r['is_urgence']
            if d_str not in counts_by_date:
                counts_by_date[d_str] = {'normal': 0, 'urgence': 0}
            if is_urg:
                counts_by_date[d_str]['urgence'] += 1
            else:
                counts_by_date[d_str]['normal'] += 1
            
        month_data = {}
        for day in range(1, last_day + 1):
            d = datetime.date(year, m, day)
            d_str = d.strftime('%Y-%m-%d')
            if d.weekday() not in work_days:
                month_data[d_str] = {'status': 'closed', 'label': 'Fermé', 'remaining': 0}
            else:
                day_counts = counts_by_date.get(d_str, {'normal': 0, 'urgence': 0})
                normal_count = day_counts['normal']
                urg_count = day_counts['urgence']
                
                remain_normal = max(0, max_normal - normal_count)
                remain_urg = max(0, max_urgence - urg_count)
                
                if remain_normal == 0 and remain_urg == 0:
                    status = 'red'
                    label = 'COMPLET'
                elif remain_normal <= 5 or remain_urg <= 1:
                    status = 'orange'
                    label = f"{remain_normal} places<br/>{remain_urg} urg."
                else:
                    status = 'green'
                    label = f"{remain_normal} places<br/>{remain_urg} urg."
                
                month_data[d_str] = {
                    'status': status,
                    'label': label,
                    'remaining': remain_normal,
                    'remaining_normal': remain_normal,
                    'remaining_urgence': remain_urg
                }
                
        day_data = []
        if selected_date:
            sel_d = datetime.datetime.strptime(selected_date, '%Y-%m-%d').date()
            if sel_d.weekday() in work_days:
                day_rdvs = rdv_model.search_read([
                    ('date', '=', sel_d),
                    ('state', 'not in', ['annule', 'absent'])
                ], ['heure', 'display_patient_name', 'state', 'is_urgence'])
                
                occupied_hours = {r['heure']: r for r in day_rdvs}
                
                h = heure_debut
                while h <= heure_fin:
                    rdv = occupied_hours.get(h)
                    h_str = f"{int(h):02d}:{int((h%1)*60):02d}"
                    day_data.append({
                        'heure': h,
                        'label': h_str,
                        'is_free': not bool(rdv),
                        'patient_name': rdv['display_patient_name'] if rdv else '',
                        'state': rdv['state'] if rdv else '',
                        'is_urgence': rdv['is_urgence'] if rdv else False,
                        'rdv_id': rdv['id'] if rdv else None
                    })
                    h += 1.0
                    
        return {
            'month': month,
            'month_data': month_data,
            'day_data': day_data,
            'selected_date': selected_date
        }

    @http.route('/cabinet_medical/appointment_banner', type='json', auth='user')
    def appointment_banner(self, **kwargs):
        html = request.env['cabinet.rendezvous'].get_interactive_calendar_html()
        return {'html': html}


_SUCCESS_MESSAGE = (
    "Votre mot de passe a été réinitialisé avec succès. "
    "Veuillez vous connecter avec votre nouveau mot de passe."
)


class CabinetAuthSignupHome(AuthSignupHome):
    """Override the auth_signup controller to redirect after a password reset
    instead of auto-authenticating the user."""

    # ------------------------------------------------------------------
    # /web/signup  (token-based reset sent by Odoo's "reset password" mail)
    # ------------------------------------------------------------------
    @http.route('/web/signup', type='http', auth='public', website=True, sitemap=False)
    def web_auth_signup(self, *args, **kw):
        qcontext = self.get_auth_signup_qcontext()
        token = qcontext.get('token')

        # Detect whether this signup request is actually a *password reset*
        is_reset = False
        if token:
            partner = request.env['res.partner'].sudo().search(
                [('signup_token', '=', token)], limit=1
            )
            is_reset = bool(partner) and partner.signup_type == 'reset'

        if is_reset and 'error' not in qcontext and request.httprequest.method == 'POST':
            try:
                if not request.env['ir.http']._verify_request_recaptcha_token('signup'):
                    raise UserError(_("Suspicious activity detected by Google reCaptcha."))

                # Use Odoo's standard signup path (handles commit + session correctly),
                # then immediately log out so the user is NOT auto-authenticated.
                self.do_signup(qcontext)
                request.session.logout(keep_db=True)

                # Redirect to login page with a success banner
                params = {'message': _SUCCESS_MESSAGE}
                if qcontext.get('login'):
                    params['login'] = qcontext['login']
                return request.redirect('/web/login?%s' % url_encode(params))

            except UserError as e:
                qcontext['error'] = e.args[0]
            except (SignupError, AssertionError) as e:
                qcontext['error'] = str(e)

            response = request.render('auth_signup.signup', qcontext)
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'
            response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
            return response

        # For normal (non-reset) signups, fall through to the standard behaviour
        return super().web_auth_signup(*args, **kw)

    # ------------------------------------------------------------------
    # /web/reset_password  (step 1: send email  |  step 2: set new pwd)
    # ------------------------------------------------------------------
    @http.route('/web/reset_password', type='http', auth='public', website=True, sitemap=False)
    def web_auth_reset_password(self, *args, **kw):
        qcontext = self.get_auth_signup_qcontext()

        if not qcontext.get('token') and not qcontext.get('reset_password_enabled'):
            raise werkzeug.exceptions.NotFound()

        if 'error' not in qcontext and request.httprequest.method == 'POST':
            try:
                if not request.env['ir.http']._verify_request_recaptcha_token('password_reset'):
                    raise UserError(_("Suspicious activity detected by Google reCaptcha."))

                if qcontext.get('token'):
                    # Token present → user is setting a new password.
                    # Use Odoo's standard signup path (handles commit + session correctly),
                    # then immediately log out so the user is NOT auto-authenticated.
                    self.do_signup(qcontext)
                    request.session.logout(keep_db=True)

                    # Redirect to login page with a success banner
                    params = {'message': _SUCCESS_MESSAGE}
                    if qcontext.get('login'):
                        params['login'] = qcontext['login']
                    return request.redirect('/web/login?%s' % url_encode(params))

                else:
                    # No token → user is requesting the reset email
                    login = qcontext.get('login')
                    assert login, _("No login provided.")
                    _logger.info(
                        "Password reset attempt for <%s> by user <%s> from %s",
                        login, request.env.user.login, request.httprequest.remote_addr,
                    )
                    request.env['res.users'].sudo().reset_password(login)
                    qcontext['message'] = _("Password reset instructions sent to your email")

            except UserError as e:
                qcontext['error'] = e.args[0]
            except SignupError:
                qcontext['error'] = _("Could not reset your password")
            except Exception as e:
                qcontext['error'] = str(e)

        elif 'signup_email' in qcontext:
            user = request.env['res.users'].sudo().search(
                [('email', '=', qcontext.get('signup_email')), ('state', '!=', 'new')], limit=1
            )
            if user:
                return request.redirect(
                    '/web/login?%s' % url_encode({'login': user.login, 'redirect': '/web'})
                )

        response = request.render('auth_signup.reset_password', qcontext)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response
