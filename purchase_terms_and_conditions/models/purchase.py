# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.onchange('partner_id', 'company_id')
    def onchange_partner_id(self):
        if self.partner_id and self.partner_id.vendor_type_id:
            self.notes = self.partner_id.vendor_type_id.notes
        return super(PurchaseOrder, self).onchange_partner_id()
