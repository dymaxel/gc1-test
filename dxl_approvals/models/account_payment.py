# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError

class AccountMove(models.Model):
    _inherit = 'account.move'

    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('first_approval', 'First Approval'),
        ('second_approval', 'Second Approval'),
        ('third_approval', 'Third Approval'),
        ('fourth_approval', 'Fourth Approval'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled'),
    ], string='Status', required=True, readonly=True, copy=False, tracking=True,
    default='draft')

class AccountPayment(models.Model):
    _inherit = "account.payment"

    first_approval = fields.Boolean('First Approval', copy=False)
    second_approval = fields.Boolean('Second Approval', copy=False)
    third_approval = fields.Boolean('Third Approval', copy=False)
    fourth_approval = fields.Boolean('Fourth Approval', copy=False)
    is_approve_visible = fields.Boolean(compute='compute_is_approve_visible')

    def compute_is_approve_visible(self):
        first_approver = self.user_has_groups('dxl_approvals.group_payment_first_approval')
        second_approver = self.user_has_groups('dxl_approvals.group_payment_second_approval')
        third_approver = self.user_has_groups('dxl_approvals.group_payment_third_approval')
        fourth_approver = self.user_has_groups('dxl_approvals.group_payment_fourth_approval')
        for payment in self:
            if payment.payment_type != 'outbound':
                payment.is_approve_visible = False
                continue
            if payment.state == 'first_approval' and first_approver and not payment.first_approval:
                payment.is_approve_visible = True
            elif payment.state == 'second_approval' and second_approver and not payment.second_approval:
                payment.is_approve_visible = True
            elif payment.state == 'third_approval' and third_approver and not payment.third_approval:
                payment.is_approve_visible = True
            elif payment.state == 'fourth_approval' and fourth_approver and not payment.fourth_approval:
                payment.is_approve_visible = True
            else:
                payment.is_approve_visible = False

    def action_post(self):
        if self.payment_type == 'outbound' and self.env.user.company_id.payment_approval and self.state == 'draft':
            self.write({'state': 'first_approval'})
        else:
            return super(AccountPayment, self).action_post()

    def button_approve(self):
        company_id = self.env.user.company_id
        first_approver = self.user_has_groups('dxl_approvals.group_payment_first_approval')
        second_approver = self.user_has_groups('dxl_approvals.group_payment_second_approval')
        third_approver = self.user_has_groups('dxl_approvals.group_payment_third_approval')
        fourth_approver = self.user_has_groups('dxl_approvals.group_payment_fourth_approval')
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
            self.action_post()
