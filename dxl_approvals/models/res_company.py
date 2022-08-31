# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

    po_double_validation = fields.Selection([
        ('one_step', 'Confirm purchase orders in one step'),
        ('two_step', 'Get 4 levels of approvals to confirm a purchase order')
        ], string="Levels of Approvals", default='one_step',
        help="Provide a double validation mechanism for purchases")

    purchase_approval = fields.Boolean('Purchase Approval')
    first_amount = fields.Float('First Approval Amount')
    second_amount = fields.Float('Second Approval Amount')
    third_amount = fields.Float('Third Approval Amount')
    fourth_amount = fields.Float('Fourth Approval Amount')

    sale_approval = fields.Boolean('Sale Approval')
    sale_first_amount = fields.Float('First Approval Amount')
    sale_second_amount = fields.Float('Second Approval Amount')
    sale_third_amount = fields.Float('Third Approval Amount')
    sale_fourth_amount = fields.Float('Fourth Approval Amount')

    payment_approval = fields.Boolean('Payment Approval')
