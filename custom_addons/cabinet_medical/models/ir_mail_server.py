# -*- coding: utf-8 -*-
import base64
from odoo import models, api

class IrMailServer(models.Model):
    _inherit = 'ir.mail_server'  # type: ignore

    def build_email(self, email_from, email_to, subject, body, email_cc=None, email_bcc=None, reply_to=False,
                    attachments=None, message_id=None, references=None, object_id=False, subtype='plain', headers=None,
                    body_alternative=None, subtype_alternative='plain'):
        
        # Call super to build the email message
        msg = super(IrMailServer, self).build_email(  # type: ignore
            email_from=email_from, email_to=email_to, subject=subject, body=body,
            email_cc=email_cc, email_bcc=email_bcc, reply_to=reply_to,
            attachments=attachments, message_id=message_id, references=references,
            object_id=object_id, subtype=subtype, headers=headers,
            body_alternative=body_alternative, subtype_alternative=subtype_alternative
        )

        body_str = body or ""
        body_alt_str = body_alternative or ""

        # If the email references 'cid:logo_cabinet', dynamically attach the company logo
        if "cid:logo_cabinet" in body_str or "cid:logo_cabinet" in body_alt_str:
            company = self.env.company
            if company and company.logo:
                logo_data = base64.b64decode(company.logo)
                
                # Determine mimetype from signature
                mimetype = 'image/png'
                if logo_data.startswith(b'\xff\xd8'):
                    mimetype = 'image/jpeg'
                elif logo_data.startswith(b'\x89PNG'):
                    mimetype = 'image/png'
                elif logo_data.startswith(b'GIF8'):
                    mimetype = 'image/gif'

                # Check if it's already attached to avoid duplicates
                already_attached = False
                for part in msg.walk():
                    if part.get('Content-ID') == '<logo_cabinet>':
                        already_attached = True
                        break

                if not already_attached:
                    maintype, subtype = mimetype.split('/')
                    # Attach the file
                    msg.add_attachment(logo_data, maintype, subtype, filename="logo_cabinet.png")
                    
                    # Retrieve the added part (which is the last part in the payload)
                    part = msg.get_payload()[-1]
                    
                    # Set the required CID header (angle brackets are required for standard CIDs)
                    if 'Content-ID' in part:
                        part.replace_header('Content-ID', '<logo_cabinet>')
                    else:
                        part.add_header('Content-ID', '<logo_cabinet>')

                    # Mark it as inline instead of attachment
                    if 'Content-Disposition' in part:
                        del part['Content-Disposition']
                    part.add_header('Content-Disposition', 'inline', filename="logo_cabinet.png")

        return msg
