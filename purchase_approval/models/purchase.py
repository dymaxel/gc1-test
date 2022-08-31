# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('first_approval', 'First Approval'),
        ('second_approval', 'Second Approval'),
        ('third_approval', 'Third Approval'),
        ('fourth_approval', 'Fourth Approval'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)
    first_approval = fields.Boolean('First Approval', copy=False)
    second_approval = fields.Boolean('Second Approval', copy=False)
    third_approval = fields.Boolean('Third Approval', copy=False)
    fourth_approval = fields.Boolean('Fourth Approval', copy=False)
    is_approve_visible = fields.Boolean(compute='compute_is_approve_visible')

    def compute_is_approve_visible(self):
        for order in self:
            first_approver = self.env.user.has_group('purchase_approval.group_first_approval')
            second_approver = self.env.user.has_group('purchase_approval.group_second_approval')
            third_approver = self.env.user.has_group('purchase_approval.group_third_approval')
            fourth_approver = self.env.user.has_group('purchase_approval.group_fourth_approval')
            if order.state in ('first_approval', 'second_approval', 'third_approval', 'fourth_approval') and order.company_id.po_double_validation in ('one_step', 'two_step'):
                if order.company_id.po_double_validation == 'one_step' and (not order.first_approval and first_approver):
                    order.is_approve_visible = True
                else:
                    order.is_approve_visible = False
                if order.company_id.po_double_validation == 'two_step':
                    if (not order.first_approval and first_approver) or (not order.second_approval and second_approver) or (not order.third_approval and third_approver) or (not order.fourth_approval and fourth_approver):
                        order.is_approve_visible = True
                    else:
                        order.is_approve_visible = False
                if not first_approver and not second_approver and not third_approver and not fourth_approver:
                    order.is_approve_visible = False
            else:
                order.is_approve_visible = False

    def button_confirm(self):
        for order in self:
            if order.state not in ['draft', 'sent']:
                continue
            order._add_supplier_to_product()
            # Deal with double validation process
            if order.company_id.first_amount <= order.amount_total and order.company_id.purchase_approval and order.company_id.po_double_validation in ('one_step', 'two_step'):
                order.write({'state': 'first_approval'})
            else:
                order.button_approve()
            # if order.company_id.po_double_validation == 'one_step'\
            #         or (order.company_id.po_double_validation == 'two_step'\
            #             and order.amount_total < self.env.company.currency_id._convert(
            #                 order.company_id.po_double_validation_amount, order.currency_id, order.company_id, order.date_order or fields.Date.today()))\
            #         or order.user_has_groups('purchase.group_purchase_manager'):
            #     order.button_approve()
            # else:
            #     order.write({'state': 'to approve'})
        return True

    def button_approve(self, force=False):
        approved = False

        first_approver = self.user_has_groups('purchase_approval.group_first_approval')
        second_approver = self.user_has_groups('purchase_approval.group_second_approval')
        third_approver = self.user_has_groups('purchase_approval.group_third_approval')
        fourth_approver = self.user_has_groups('purchase_approval.group_fourth_approval')

        if self.company_id.purchase_approval and self.company_id.po_double_validation in ('one_step', 'two_step') and self.amount_total < self.company_id.first_amount:
            first_approver = True

        if (self.company_id.purchase_approval and self.company_id.po_double_validation == 'one_step') and (first_approver or self.amount_total < self.company_id.first_amount):
            approved = True
            self.write({'first_approval': True})

        if self.company_id.purchase_approval and self.company_id.po_double_validation == 'two_step':
            if first_approver:
                if self.amount_total > self.company_id.second_amount:
                    self.write({'state': 'second_approval', 'first_approval': True})
                else:
                    approved = True

            if (first_approver and second_approver and third_approver and fourth_approver):
                self.write({
                    'first_approval': True,
                    'second_approval': True,
                    'third_approval': True,
                    'fourth_approval': True,
                    'state': 'third_approval',
                })
                approved = True

            if (second_approver or third_approver or fourth_approver) and not self.first_approval:
                raise ValidationError(_('This order need to first approval!'))
            if (third_approver or fourth_approver) and not self.second_approval:
                raise ValidationError(_('This order need to second approval!'))
            if fourth_approver and not self.third_approval:
                raise ValidationError(_('This order need to third approval!'))
            if self.first_approval and (second_approver and not self.second_approval):
                if self.amount_total > self.company_id.third_amount:
                    self.write({'second_approval': True, 'state': 'third_approval'})
                else:
                    approved = True
            if self.second_approval and (third_approver and not self.third_approval):
                if self.amount_total > self.company_id.fourth_amount:
                    self.write({'third_approval': True, 'state': 'fourth_approval'})
                else:
                    approved = True
            if self.third_approval and (fourth_approver and not self.fourth_approval):
                self.write({'fourth_approval': True})
                approved = True

        if self.state not in ('first_approval', 'second_approval', 'third_approval', 'fourth_approval'):
            approved = True

        if approved or not self.company_id.purchase_approval:
            super(PurchaseOrder, self).button_approve()
        return {}

    def _create_picking(self):
        if not self.company_id.purchase_approval or (self.company_id.po_double_validation == 'one_step' and self.first_approval) or (self.company_id.po_double_validation == 'two_step' and self.second_approval):
            return super(PurchaseOrder, self)._create_picking()
        return True
