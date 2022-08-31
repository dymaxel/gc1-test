# -*- coding: utf-8 -*-
from odoo import fields, models, _


class Create_Pur_Wizard_reason(models.TransientModel):
    _name = 'create.pur.wizard.reason'
    # _description = 'Create Purchase Request Wizard Reason'

    reason_field = fields.Char(string='Reason', required=True)

    def action_resolve_pur_reason_wiz(self):
        requisition = self.env['sprogroup.purchase.request'].browse(self.env.context.get('active_id'))
        requisition.write({'reason': self.reason_field, 'state': 'rejected'})
        requisition.rejected_date = fields.Datetime.today()
        users = requisition.requested_by
        if self.env.user.has_group('fleet_service.dxl_group_procurement_manager'):
            users += requisition.assigned_to
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        base_url += '/web#id=%d&view_type=form&model=%s' % (requisition.id, requisition._name)
        message = _("<p>Purchase Request has been rejected <a href=%s >%s</a></p>") % (base_url, requisition.code)
        for user in users:
            mail_values = {
                'subject': _('PR Rejection'),
                'body_html': message,
                'author_id': self.env.user.partner_id.id,
                'email_from': self.env.company.email or self.env.user.email_formatted,
                'email_to': user.email_formatted,
            }
            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.send()
        users.notify_info(message, title="Notification")
        return
