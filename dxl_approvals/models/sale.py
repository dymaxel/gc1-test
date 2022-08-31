# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('first_approval', 'First Approval'),
        ('second_approval', 'Second Approval'),
        ('third_approval', 'Third Approval'),
        ('fourth_approval', 'Fourth Approval'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')
    first_approval = fields.Boolean('First Approval', copy=False)
    second_approval = fields.Boolean('Second Approval', copy=False)
    third_approval = fields.Boolean('Third Approval', copy=False)
    fourth_approval = fields.Boolean('Fourth Approval', copy=False)
    is_approve_visible = fields.Boolean(compute='compute_is_approve_visible')

    def compute_is_approve_visible(self):
        first_approver = self.user_has_groups('dxl_approvals.group_sale_first_approval')
        second_approver = self.user_has_groups('dxl_approvals.group_sale_second_approval')
        third_approver = self.user_has_groups('dxl_approvals.group_sale_third_approval')
        fourth_approver = self.user_has_groups('dxl_approvals.group_sale_fourth_approval')
        for order in self:
            if order.state == 'first_approval' and first_approver and not order.first_approval:
                order.is_approve_visible = True
            elif order.state == 'second_approval' and second_approver and not order.second_approval:
                order.is_approve_visible = True
            elif order.state == 'third_approval' and third_approver and not order.third_approval:
                order.is_approve_visible = True
            elif order.state == 'fourth_approval' and fourth_approver and not order.fourth_approval:
                order.is_approve_visible = True
            else:
                order.is_approve_visible = False

    def action_confirm(self):
        if self.company_id.sale_approval and self.state in ('draft', 'sent'):
            self.write({'state': 'first_approval'})
        else:
            return super(SaleOrder, self).action_confirm()

    def button_approve(self):
        first_approver = self.user_has_groups('dxl_approvals.group_sale_first_approval')
        second_approver = self.user_has_groups('dxl_approvals.group_sale_second_approval')
        third_approver = self.user_has_groups('dxl_approvals.group_sale_third_approval')
        fourth_approver = self.user_has_groups('dxl_approvals.group_sale_fourth_approval')
        approved = False
        if self.state == 'first_approval' and first_approver and not self.first_approval:
            self.write({'state': 'second_approval', 'first_approval': True})
        elif self.state == 'second_approval' and second_approver and not self.second_approval:
            self.write({'state': 'third_approval', 'second_approval': True})
        elif self.state == 'third_approval' and third_approver and not self.third_approval:
            self.write({'state': 'fourth_approval', 'third_approval': True})
        elif self.state == 'fourth_approval' and fourth_approver and not self.fourth_approval:
            self.write({'fourth_approval': True})
            approved = True
        else:
            approved = True
        if approved:
            self.action_confirm()
