# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    reconcile_invoice_ids = fields.One2many('account.payment.reconcile', 'payment_id', string="Invoices", copy=False)

    @api.onchange('partner_id', 'payment_type', 'partner_type')
    def _onchange_partner_id(self):
        if not self.partner_id:
            return
        partner_id = self.partner_id
        self.reconcile_invoice_ids = [(5,)]
        move_type = {'outbound': 'in_invoice', 'inbound': 'out_invoice'}
        moves = self.env['account.move'].sudo().search(
            [('partner_id', '=', self.partner_id.id), ('state', '=', 'posted'),
             ('payment_state', 'not in', ['paid', 'reversed', 'in_payment']),
             ('move_type', '=', move_type[self.payment_type])])
        vals = []
        for move in moves:
            vals.append((0, 0, {
                'payment_id': self.id,
                'invoice_id': move.id,
                'already_paid': sum([payment['amount'] for payment in move._get_reconciled_info_JSON_values()]),
                'amount_residual': move.amount_residual,
                'amount_untaxed': move.amount_untaxed,
                'amount_tax': move.amount_tax,
                'currency_id': move.currency_id.id,
                'amount_total': move.amount_total,
            }))
        self.reconcile_invoice_ids = vals
        self.partner_id = partner_id.id
        return

    @api.onchange('reconcile_invoice_ids')
    def _onchnage_reconcile_invoice_ids(self):
        # amount_sum = 0
        # for rec in self.reconcile_invoice_ids:
        #     amount_sum = amount_sum + rec.amount_paid
        #     self.amount = amount_sum
        self.amount = sum(self.reconcile_invoice_ids.filtered(lambda x: x.reconcile).mapped('amount_paid'))

    # @api.onchange('amount', 'sales_tds_tax_id')
    # def check_amount(self):
    #     for payment in self:
    #         if payment.sales_tds_type == "excluding":
    #             if payment.amount:
    #                 if payment.sales_tds_tax_id:
    #                     payment.sales_tds_amt = payment.amount * (payment.sales_tds_tax_id.amount / 100)
    #         else:
    #             if payment.amount:
    #                 if payment.sales_tds_tax_id:
    #                     payment.sales_tds_amt = payment.amount * (payment.sales_tds_tax_id.amount / 100)

    def action_post(self):
        res = super(AccountPayment, self).action_post()
        for payment in self:
            # move_lines = self.env['account.move.line']
            # invoice_ids = payment.reconcile_invoice_ids.filtered(lambda x: x.reconcile).mapped('invoice_id')
            # invoice_move = invoice_ids.mapped('line_ids').filtered(
            #     lambda r: not r.reconciled and r.account_id.internal_type in ('payable', 'receivable'))
            # payment_move = payment.invoice_line_ids.filtered(
            #     lambda r: not r.reconciled and r.account_id.internal_type in ('payable', 'receivable'))
            # move_lines |= (invoice_move + payment_move)
            if ((payment.sales_tds_type in ['excluding',
                                            'including'] and payment.sales_tds_tax_id and payment.sales_tds_amt and payment.bill_type == 'non_bill') and not payment.tds_tax_id):
                if payment.payment_type == 'outbound' and payment.partner_type == 'supplier':
                    sales_tds_amt = payment.amount - payment.sales_tds_amt
                    sales_tax_repartition_lines = payment.sales_tds_tax_id.invoice_repartition_line_ids.filtered(
                        lambda x: x.repartition_type == 'tax')
                    if payment.sales_tds_type == "excluding":
                        sales_excld_amt = payment.amount + payment.sales_tds_amt
                        payment.move_id.button_draft()
                        creditacc = 0
                        debitacc = 0
                        creditref = 0
                        debitref = 0
                        currency = payment.move_id.currency_id.id
                        for rec in payment.move_id.line_ids:
                            if rec.debit == 0:
                                creditacc = rec.account_id.id
                                creditref = rec.name
                            if rec.credit == 0:
                                debitacc = rec.account_id.id
                                debitref = rec.name
                        payment.move_id.line_ids.unlink()
                        vals = []
                        vals.append({'name': debitref,
                                     'amount_currency': sales_excld_amt,
                                     'debit': sales_excld_amt,
                                     'credit': 0,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'currency_id': currency,
                                     'account_id': debitacc,
                                     # 'payment_id': payment.id,
                                     # 'move_id': payment.move_id.id
                                     })
                        vals.append({'name': creditref,
                                     'amount_currency': payment.amount,
                                     'debit': 0,
                                     'credit': payment.amount,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': creditacc,
                                     'currency_id': currency,
                                     # 'payment_id': payment.id,
                                     # 'move_id': payment.move_id.id
                                     })
                        vals.append({'name': _('Sale Tax Withhold'),
                                     'amount_currency': payment.sales_tds_amt,
                                     'debit': 0,
                                     'credit': payment.sales_tds_amt,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': sales_tax_repartition_lines.id and sales_tax_repartition_lines.account_id.id,
                                     'currency_id': currency,
                                     # 'payment_id': payment.id,
                                     # 'move_id': payment.move_id.id
                                     })
                        lines = [(0, 0, line_move) for line_move in vals]
                        payment.move_id.write({'line_ids': lines})
                        payment.move_id.write({'currency_id': currency})
                        payment.move_id.action_post()
                    if payment.sales_tds_type == "including":
                        payment.move_id.button_draft()
                        creditacc = 0
                        debitacc = 0
                        creditref = 0
                        debitref = 0
                        currency = payment.move_id.currency_id.id
                        for rec in payment.move_id.line_ids:
                            if rec.debit == 0:
                                creditacc = rec.account_id.id
                                creditref = rec.name
                            if rec.credit == 0:
                                debitacc = rec.account_id.id
                                debitref = rec.name
                        payment.move_id.line_ids.unlink()
                        vals = []
                        vals.append({'name': debitref,
                                     'amount_currency': payment.amount,
                                     'debit': payment.amount,
                                     'credit': 0,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': debitacc,
                                     'currency_id': currency,
                                     # 'payment_id': payment.id,
                                     # 'move_id': payment.move_id.id
                                     })
                        vals.append({'name': creditref,
                                     'amount_currency': sales_tds_amt,
                                     'debit': 0,
                                     'credit': sales_tds_amt,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': creditacc,
                                     'currency_id': currency,
                                     # 'payment_id': payment.id,
                                     # 'move_id': payment.move_id.id
                                     })
                        vals.append({'name': _('Sale Tax Withhold'),
                                     'amount_currency': payment.sales_tds_amt,
                                     'debit': 0,
                                     'credit': payment.sales_tds_amt,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': sales_tax_repartition_lines.id and sales_tax_repartition_lines.account_id.id,
                                     'currency_id': currency,
                                     # 'payment_id': payment.id,
                                     # 'move_id': payment.move_id.id
                                     })
                        lines = [(0, 0, line_move) for line_move in vals]
                        payment.move_id.write({'line_ids': lines})
                        payment.move_id.write({'currency_id': currency})
                        payment.move_id.action_post()

            if ((payment.tds_type in ['excluding',
                                      'including'] and payment.tds_tax_id and payment.tds_amt and payment.bill_type == 'non_bill') and not payment.sales_tds_tax_id):
                if payment.payment_type == 'outbound' and payment.partner_type == 'supplier':
                    tds_amt = payment.amount - payment.tds_amt
                    tax_repartition_lines = payment.tds_tax_id.invoice_repartition_line_ids.filtered(
                        lambda x: x.repartition_type == 'tax')
                    if payment.tds_type == "excluding":
                        excld_amt = payment.amount + payment.tds_amt
                        payment.move_id.button_draft()
                        creditacc = 0
                        debitacc = 0
                        creditref = 0
                        debitref = 0
                        currency = payment.move_id.currency_id.id
                        for rec in payment.move_id.line_ids:
                            if rec.debit == 0:
                                creditacc = rec.account_id.id
                                creditref = rec.name
                            if rec.credit == 0:
                                debitacc = rec.account_id.id
                                debitref = rec.name
                        payment.move_id.line_ids.unlink()
                        vals = []
                        vals.append({'name': debitref,
                                     'amount_currency': excld_amt,
                                     'debit': excld_amt,
                                     'credit': 0,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'currency_id': currency,
                                     'account_id': debitacc,
                                     # 'payment_id': payment.id,
                                     # 'move_id': payment.move_id.id
                                     })
                        vals.append({'name': creditref,
                                     'amount_currency': payment.amount,
                                     'debit': 0,
                                     'credit': payment.amount,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': creditacc,
                                     'currency_id': payment.currency_id.id,
                                     # 'payment_id': payment.id,
                                     # 'move_id': payment.move_id.id
                                     })
                        vals.append({'name': _('Income Tax Withhold'),
                                     'amount_currency': payment.tds_amt,
                                     'debit': 0,
                                     'credit': payment.tds_amt,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': tax_repartition_lines.id and tax_repartition_lines.account_id.id,
                                     'currency_id': currency,
                                     # 'payment_id': payment.id,
                                     # 'move_id': payment.move_id.id
                                     })
                        lines = [(0, 0, line_move) for line_move in vals]
                        payment.move_id.write({'line_ids': lines})
                        payment.move_id.write({'currency_id': currency})
                        payment.move_id.action_post()
                    if payment.tds_type == "including":
                        payment.move_id.button_draft()
                        creditacc = 0
                        debitacc = 0
                        creditref = 0
                        debitref = 0
                        currency = payment.move_id.currency_id.id
                        for rec in payment.move_id.line_ids:
                            if rec.debit == 0:
                                creditacc = rec.account_id.id
                                creditref = rec.name
                            if rec.credit == 0:
                                debitacc = rec.account_id.id
                                debitref = rec.name
                        payment.move_id.line_ids.unlink()
                        vals = []
                        vals.append({'name': debitref,
                                     'amount_currency': payment.amount,
                                     'debit': payment.amount,
                                     'credit': 0,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': debitacc,
                                     'currency_id': currency,
                                     # 'payment_id': payment.id,
                                     # 'move_id': payment.move_id.id
                                     })
                        vals.append({'name': creditref,
                                     'amount_currency': tds_amt,
                                     'debit': 0,
                                     'credit': tds_amt,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': creditacc,
                                     'currency_id': currency,
                                     # 'payment_id': payment.id,
                                     # 'move_id': payment.move_id.id
                                     })
                        vals.append({'name': _('Income Tax Withhold'),
                                     'amount_currency': payment.tds_amt,
                                     'debit': 0,
                                     'credit': payment.tds_amt,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': tax_repartition_lines.id and tax_repartition_lines.account_id.id,
                                     'currency_id': currency,
                                     # 'payment_id': payment.id,
                                     # 'move_id': payment.move_id.id
                                     })
                        lines = [(0, 0, line_move) for line_move in vals]
                        payment.move_id.write({'line_ids': lines})
                        payment.move_id.write({'currency_id': currency})
                        payment.move_id.action_post()
            if ((payment.tds_type in ['excluding', 'including'] and payment.sales_tds_type in ['excluding',
                                                                                               'including'] and payment.tds_tax_id and payment.tds_amt and payment.sales_tds_tax_id and payment.sales_tds_amt and payment.bill_type == 'non_bill')):
                if payment.payment_type == 'outbound' and payment.partner_type == 'supplier':
                    if payment.tds_type == 'including' or payment.sales_tds_type == 'including':

                        payment.move_id.button_draft()
                        tax_repartition_lines = payment.tds_tax_id.invoice_repartition_line_ids.filtered(
                            lambda x: x.repartition_type == 'tax')
                        sales_tax_repartition_lines = payment.sales_tds_tax_id.invoice_repartition_line_ids.filtered(
                            lambda x: x.repartition_type == 'tax')
                        creditacc = 0
                        debitacc = 0
                        creditref = 0
                        debitref = 0
                        currency = payment.move_id.currency_id.id
                        payamt = payment.amount
                        for rec in payment.move_id.line_ids:
                            if rec.debit == 0:
                                creditacc = rec.account_id.id
                                creditref = rec.name
                            if rec.credit == 0:
                                debitacc = rec.account_id.id
                                debitref = rec.name
                        payment.move_id.line_ids.unlink()
                        tds_amt_inc = payment.amount - (payment.tds_amt + payment.sales_tds_amt)
                        vals = []
                        vals.append({'name': debitref,
                                     'amount_currency': payment.amount,
                                     'debit': payment.amount,
                                     'credit': 0,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': debitacc,
                                     'currency_id': currency,
                                     # 'move_id': payment.move_id.id
                                     })
                        vals.append({'name': creditref,
                                     'amount_currency': tds_amt_inc,
                                     'debit': 0,
                                     'credit': tds_amt_inc,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': creditacc,
                                     'currency_id': currency,
                                     # 'move_id': payment.move_id.id
                                     })
                        vals.append({'name': _('Income Tax Withhold'),
                                     'amount_currency': payment.tds_amt,
                                     'debit': 0,
                                     'credit': payment.tds_amt,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': tax_repartition_lines.id and tax_repartition_lines.account_id.id,
                                     'currency_id': currency,
                                     # 'move_id': payment.move_id.id
                                     })
                        vals.append({'name': _('Sale Tax Withhold'),
                                     'amount_currency': payment.sales_tds_amt,
                                     'debit': 0,
                                     'credit': payment.sales_tds_amt,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': sales_tax_repartition_lines.id and sales_tax_repartition_lines.account_id.id,
                                     'currency_id': currency,
                                     # 'move_id': payment.move_id.id
                                     })
                        lines = [(0, 0, line_move) for line_move in vals]
                        payment.move_id.write({'line_ids': lines})
                        payment.move_id.write({'currency_id': currency})
                        payment.move_id.action_post()

            if ((payment.tds_type in ['excluding'] and payment.sales_tds_type in [
                'excluding'] and payment.tds_tax_id and payment.tds_amt and payment.sales_tds_tax_id and payment.sales_tds_amt and payment.bill_type == 'non_bill')):
                if payment.payment_type == 'outbound' and payment.partner_type == 'supplier':
                    if payment.tds_type == 'excluding' and payment.sales_tds_type == 'excluding':

                        payment.move_id.button_draft()
                        tax_repartition_lines = payment.tds_tax_id.invoice_repartition_line_ids.filtered(
                            lambda x: x.repartition_type == 'tax')
                        sales_tax_repartition_lines = payment.sales_tds_tax_id.invoice_repartition_line_ids.filtered(
                            lambda x: x.repartition_type == 'tax')
                        creditacc = 0
                        debitacc = 0
                        creditref = 0
                        debitref = 0
                        currency = payment.move_id.currency_id.id
                        payamt = payment.amount
                        for rec in payment.move_id.line_ids:
                            if rec.debit == 0:
                                creditacc = rec.account_id.id
                                creditref = rec.name
                            if rec.credit == 0:
                                debitacc = rec.account_id.id
                                debitref = rec.name
                        payment.move_id.line_ids.unlink()
                        tds_amt_inc = payment.amount - (payment.tds_amt + payment.sales_tds_amt)
                        vals = []
                        excluding_debit = payment.amount + payment.tds_amt + payment.sales_tds_amt
                        vals.append({'name': debitref,
                                     'amount_currency': payment.amount,
                                     'debit': excluding_debit,
                                     'credit': 0,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': debitacc,
                                     'currency_id': currency,
                                     # 'move_id': payment.move_id.id
                                     })
                        vals.append({'name': creditref,
                                     'amount_currency': tds_amt_inc,
                                     'debit': 0,
                                     'credit': payment.amount,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': creditacc,
                                     'currency_id': currency,
                                     # 'move_id': payment.move_id.id
                                     })
                        vals.append({'name': _('Income Tax Withhold'),
                                     'amount_currency': payment.tds_amt,
                                     'debit': 0,
                                     'credit': payment.tds_amt,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': tax_repartition_lines.id and tax_repartition_lines.account_id.id,
                                     'currency_id': currency,
                                     # 'move_id': payment.move_id.id
                                     })
                        vals.append({'name': _('Sale Tax Withhold'),
                                     'amount_currency': payment.sales_tds_amt,
                                     'debit': 0,
                                     'credit': payment.sales_tds_amt,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': sales_tax_repartition_lines.id and sales_tax_repartition_lines.account_id.id,
                                     'currency_id': currency,
                                     # 'move_id': payment.move_id.id
                                     })
                        lines = [(0, 0, line_move) for line_move in vals]
                        payment.move_id.write({'line_ids': lines})
                        payment.move_id.write({'currency_id': currency})
                        payment.move_id.action_post()
            # payment.amount = payamt

            # Bill Type = Bill
            if ((payment.sales_tds_type in ['excluding',
                                            'including'] and payment.sales_tds_tax_id and payment.sales_tds_amt and payment.bill_type == 'bill') and not payment.tds_tax_id):
                if payment.payment_type == 'outbound' and payment.partner_type == 'supplier':
                    sales_tds_amt = payment.amount - payment.sales_tds_amt
                    sales_tax_repartition_lines = payment.sales_tds_tax_id.invoice_repartition_line_ids.filtered(
                        lambda x: x.repartition_type == 'tax')
                    if payment.sales_tds_type == "excluding":
                        sales_excld_amt = payment.amount + payment.sales_tds_amt
                        payment.move_id.button_draft()
                        creditacc = 0
                        debitacc = 0
                        creditref = 0
                        debitref = 0
                        currency = payment.move_id.currency_id.id
                        for rec in payment.move_id.line_ids:
                            if rec.debit == 0:
                                creditacc = rec.account_id.id
                                creditref = rec.name
                            if rec.credit == 0:
                                debitacc = rec.account_id.id
                                debitref = rec.name
                        payment.move_id.line_ids.unlink()
                        vals = []
                        vals.append({'name': debitref,
                                     'amount_currency': sales_excld_amt,
                                     'debit': sales_excld_amt,
                                     'credit': 0,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'currency_id': currency,
                                     'account_id': debitacc,
                                     # 'payment_id': payment.id,
                                     # 'move_id': payment.move_id.id
                                     })
                        vals.append({'name': creditref,
                                     'amount_currency': payment.amount,
                                     'debit': 0,
                                     'credit': payment.amount,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': creditacc,
                                     'currency_id': currency,
                                     # 'payment_id': payment.id,
                                     # 'move_id': payment.move_id.id
                                     })
                        vals.append({'name': _('Sale Tax Withhold'),
                                     'amount_currency': payment.sales_tds_amt,
                                     'debit': 0,
                                     'credit': payment.sales_tds_amt,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': sales_tax_repartition_lines.id and sales_tax_repartition_lines.account_id.id,
                                     'currency_id': currency,
                                     # 'payment_id': payment.id,
                                     # 'move_id': payment.move_id.id
                                     })
                        lines = [(0, 0, line_move) for line_move in vals]
                        payment.move_id.write({'line_ids': lines})
                        payment.move_id.write({'currency_id': currency})
                        payment.move_id.action_post()
                    if payment.sales_tds_type == "including":
                        payment.move_id.button_draft()
                        creditacc = 0
                        debitacc = 0
                        creditref = 0
                        debitref = 0
                        currency = payment.move_id.currency_id.id
                        for rec in payment.move_id.line_ids:
                            if rec.debit == 0:
                                creditacc = rec.account_id.id
                                creditref = rec.name
                            if rec.credit == 0:
                                debitacc = rec.account_id.id
                                debitref = rec.name
                        payment.move_id.line_ids.unlink()
                        vals = []
                        vals.append({'name': debitref,
                                     'amount_currency': payment.amount,
                                     'debit': payment.amount,
                                     'credit': 0,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': debitacc,
                                     'currency_id': currency,
                                     # 'payment_id': payment.id,
                                     # 'move_id': payment.move_id.id
                                     })
                        vals.append({'name': creditref,
                                     'amount_currency': sales_tds_amt,
                                     'debit': 0,
                                     'credit': sales_tds_amt,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': creditacc,
                                     'currency_id': currency,
                                     # 'payment_id': payment.id,
                                     # 'move_id': payment.move_id.id
                                     })
                        vals.append({'name': _('Sale Tax Withhold'),
                                     'amount_currency': payment.sales_tds_amt,
                                     'debit': 0,
                                     'credit': payment.sales_tds_amt,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': sales_tax_repartition_lines.id and sales_tax_repartition_lines.account_id.id,
                                     'currency_id': currency,
                                     # 'payment_id': payment.id,
                                     # 'move_id': payment.move_id.id
                                     })
                        lines = [(0, 0, line_move) for line_move in vals]
                        payment.move_id.write({'line_ids': lines})
                        payment.move_id.write({'currency_id': currency})
                        payment.move_id.action_post()

            if ((payment.tds_type in ['excluding',
                                      'including'] and payment.tds_tax_id and payment.tds_amt and payment.bill_type == 'bill') and not payment.sales_tds_tax_id):
                if payment.payment_type == 'outbound' and payment.partner_type == 'supplier':
                    tds_amt = payment.amount - payment.tds_amt
                    tax_repartition_lines = payment.tds_tax_id.invoice_repartition_line_ids.filtered(
                        lambda x: x.repartition_type == 'tax')
                    if payment.tds_type == "excluding":
                        excld_amt = payment.amount + payment.tds_amt
                        payment.move_id.button_draft()
                        creditacc = 0
                        debitacc = 0
                        creditref = 0
                        debitref = 0
                        currency = payment.move_id.currency_id.id
                        for rec in payment.move_id.line_ids:
                            if rec.debit == 0:
                                creditacc = rec.account_id.id
                                creditref = rec.name
                            if rec.credit == 0:
                                debitacc = rec.account_id.id
                                debitref = rec.name
                        payment.move_id.line_ids.unlink()
                        vals = []
                        vals.append({'name': debitref,
                                     'amount_currency': excld_amt,
                                     'debit': excld_amt,
                                     'credit': 0,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'currency_id': currency,
                                     'account_id': debitacc,
                                     # 'payment_id': payment.id,
                                     # 'move_id': payment.move_id.id
                                     })
                        vals.append({'name': creditref,
                                     'amount_currency': payment.amount,
                                     'debit': 0,
                                     'credit': payment.amount,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': creditacc,
                                     'currency_id': currency,
                                     # 'payment_id': payment.id,
                                     # 'move_id': payment.move_id.id
                                     })
                        vals.append({'name': _('Income Tax Withhold'),
                                     'amount_currency': payment.tds_amt,
                                     'debit': 0,
                                     'credit': payment.tds_amt,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': tax_repartition_lines.id and tax_repartition_lines.account_id.id,
                                     'currency_id': currency,
                                     # 'payment_id': payment.id,
                                     # 'move_id': payment.move_id.id
                                     })
                        lines = [(0, 0, line_move) for line_move in vals]
                        payment.move_id.write({'line_ids': lines})
                        payment.move_id.write({'currency_id': currency})
                        payment.move_id.action_post()
                    if payment.tds_type == "including":
                        payment.move_id.button_draft()
                        creditacc = 0
                        debitacc = 0
                        creditref = 0
                        debitref = 0
                        currency = payment.move_id.currency_id.id
                        for rec in payment.move_id.line_ids:
                            if rec.debit == 0:
                                creditacc = rec.account_id.id
                                creditref = rec.name
                            if rec.credit == 0:
                                debitacc = rec.account_id.id
                                debitref = rec.name
                        payment.move_id.line_ids.unlink()
                        vals = []
                        vals.append({'name': debitref,
                                     'amount_currency': payment.amount,
                                     'debit': payment.amount,
                                     'credit': 0,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': debitacc,
                                     'currency_id': currency,
                                     # 'payment_id': payment.id,
                                     # 'move_id': payment.move_id.id
                                     })
                        vals.append({'name': creditref,
                                     'amount_currency': tds_amt,
                                     'debit': 0,
                                     'credit': tds_amt,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': creditacc,
                                     'currency_id': currency,
                                     # 'payment_id': payment.id,
                                     # 'move_id': payment.move_id.id
                                     })
                        vals.append({'name': _('Income Tax Withhold'),
                                     'amount_currency': payment.tds_amt,
                                     'debit': 0,
                                     'credit': payment.tds_amt,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': tax_repartition_lines.id and tax_repartition_lines.account_id.id,
                                     'currency_id': currency,
                                     # 'payment_id': payment.id,
                                     # 'move_id': payment.move_id.id
                                     })
                        lines = [(0, 0, line_move) for line_move in vals]
                        payment.move_id.write({'line_ids': lines})
                        payment.move_id.write({'currency_id': currency})
                        payment.move_id.action_post()
            if ((payment.tds_type in ['excluding', 'including'] and payment.sales_tds_type in ['excluding',
                                                                                               'including'] and payment.tds_tax_id and payment.tds_amt and payment.sales_tds_tax_id and payment.sales_tds_amt and payment.bill_type == 'bill')):
                if payment.payment_type == 'outbound' and payment.partner_type == 'supplier':
                    if payment.tds_type == 'including' or payment.sales_tds_type == 'including':
                        payment.move_id.button_draft()
                        tax_repartition_lines = payment.tds_tax_id.invoice_repartition_line_ids.filtered(
                            lambda x: x.repartition_type == 'tax')
                        sales_tax_repartition_lines = payment.sales_tds_tax_id.invoice_repartition_line_ids.filtered(
                            lambda x: x.repartition_type == 'tax')
                        creditacc = 0
                        debitacc = 0
                        creditref = 0
                        debitref = 0
                        currency = payment.move_id.currency_id.id
                        payamt = payment.amount
                        for rec in payment.move_id.line_ids:
                            if rec.debit == 0:
                                creditacc = rec.account_id.id
                                creditref = rec.name
                            if rec.credit == 0:
                                debitacc = rec.account_id.id
                                debitref = rec.name
                        payment.move_id.line_ids.unlink()
                        tds_amt_inc = payment.amount - (payment.tds_amt + payment.sales_tds_amt)
                        vals = []
                        vals.append({'name': debitref,
                                     'amount_currency': payment.amount,
                                     'debit': payment.amount,
                                     'credit': 0,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': debitacc,
                                     'currency_id': currency,
                                     # 'move_id': payment.move_id.id
                                     })
                        vals.append({'name': creditref,
                                     'amount_currency': tds_amt_inc,
                                     'debit': 0,
                                     'credit': tds_amt_inc,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': creditacc,
                                     'currency_id': currency,
                                     # 'move_id': payment.move_id.id
                                     })
                        vals.append({'name': _('Income Tax Withhold'),
                                     'amount_currency': payment.tds_amt,
                                     'debit': 0,
                                     'credit': payment.tds_amt,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': tax_repartition_lines.id and tax_repartition_lines.account_id.id,
                                     'currency_id': currency,
                                     # 'move_id': payment.move_id.id
                                     })
                        vals.append({'name': _('Sale Tax Withhold'),
                                     'amount_currency': payment.sales_tds_amt,
                                     'debit': 0,
                                     'credit': payment.sales_tds_amt,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': sales_tax_repartition_lines.id and sales_tax_repartition_lines.account_id.id,
                                     'currency_id': currency,
                                     # 'move_id': payment.move_id.id
                                     })
                        lines = [(0, 0, line_move) for line_move in vals]
                        payment.move_id.write({'line_ids': lines})
                        payment.move_id.write({'currency_id': currency})
                        payment.move_id.action_post()

            if ((payment.tds_type in ['excluding'] and payment.sales_tds_type in [
                'excluding'] and payment.tds_tax_id and payment.tds_amt and payment.sales_tds_tax_id and payment.sales_tds_amt and payment.bill_type == 'bill')):
                if payment.payment_type == 'outbound' and payment.partner_type == 'supplier':
                    if payment.tds_type == 'excluding' and payment.sales_tds_type == 'excluding':

                        payment.move_id.button_draft()
                        tax_repartition_lines = payment.tds_tax_id.invoice_repartition_line_ids.filtered(
                            lambda x: x.repartition_type == 'tax')
                        sales_tax_repartition_lines = payment.sales_tds_tax_id.invoice_repartition_line_ids.filtered(
                            lambda x: x.repartition_type == 'tax')
                        creditacc = 0
                        debitacc = 0
                        creditref = 0
                        debitref = 0
                        currency = payment.move_id.currency_id.id
                        payamt = payment.amount
                        for rec in payment.move_id.line_ids:
                            if rec.debit == 0:
                                creditacc = rec.account_id.id
                                creditref = rec.name
                            if rec.credit == 0:
                                debitacc = rec.account_id.id
                                debitref = rec.name
                        payment.move_id.line_ids.unlink()
                        tds_amt_inc = payment.amount - (payment.tds_amt + payment.sales_tds_amt)
                        vals = []
                        excluding_debit = payment.amount + payment.tds_amt + payment.sales_tds_amt
                        vals.append({'name': debitref,
                                     'amount_currency': payment.amount,
                                     'debit': excluding_debit,
                                     'credit': 0,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': debitacc,
                                     'currency_id': currency,
                                     # 'move_id': payment.move_id.id
                                     })
                        vals.append({'name': creditref,
                                     'amount_currency': tds_amt_inc,
                                     'debit': 0,
                                     'credit': payment.amount,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': creditacc,
                                     'currency_id': currency,
                                     # 'move_id': payment.move_id.id
                                     })
                        vals.append({'name': _('Income Tax Withhold'),
                                     'amount_currency': payment.tds_amt,
                                     'debit': 0,
                                     'credit': payment.tds_amt,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': tax_repartition_lines.id and tax_repartition_lines.account_id.id,
                                     'currency_id': currency,
                                     # 'move_id': payment.move_id.id
                                     })
                        vals.append({'name': _('Sale Tax Withhold'),
                                     'amount_currency': payment.sales_tds_amt,
                                     'debit': 0,
                                     'credit': payment.sales_tds_amt,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': sales_tax_repartition_lines.id and sales_tax_repartition_lines.account_id.id,
                                     'currency_id': currency,
                                     # 'move_id': payment.move_id.id
                                     })
                        lines = [(0, 0, line_move) for line_move in vals]
                        payment.move_id.write({'line_ids': lines})
                        payment.move_id.write({'currency_id': currency})
                        payment.move_id.action_post()

            if payment.tds_type in ['excluding', 'including'] and payment.sales_tds_type in ['excluding',
                                                                                             'including'] and (
                    payment.tds_tax_id and payment.tds_amt) or (
                    payment.sales_tds_tax_id and payment.sales_tds_amt) and payment.bill_type == 'bill':
                if payment.payment_type == 'inbound' and payment.partner_type == 'customer':
                    if payment.tds_type == 'including' or payment.sales_tds_type == 'including':
                        payment.move_id.button_draft()
                        tax_repartition_lines = payment.tds_tax_id.invoice_repartition_line_ids.filtered(
                            lambda x: x.repartition_type == 'tax')
                        sales_tax_repartition_lines = payment.sales_tds_tax_id.invoice_repartition_line_ids.filtered(
                            lambda x: x.repartition_type == 'tax')
                        creditacc = 0
                        debitacc = 0
                        creditref = 0
                        debitref = 0
                        currency = payment.move_id.currency_id.id
                        payamt = payment.amount
                        for rec in payment.move_id.line_ids:
                            if rec.debit == 0:
                                creditacc = rec.account_id.id
                                creditref = rec.name
                            if rec.credit == 0:
                                debitacc = rec.account_id.id
                                debitref = rec.name
                        payment.move_id.line_ids.unlink()
                        tds_amt_inc = payment.amount - (payment.tds_amt + payment.sales_tds_amt)
                        vals = []
                        vals.append({'name': creditref,
                                     'amount_currency': payment.amount,
                                     'debit': 0,
                                     'credit': payment.amount,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': creditacc,
                                     'currency_id': currency,
                                     # 'move_id': payment.move_id.id
                                     })
                        vals.append({'name': debitref,
                                     'amount_currency': tds_amt_inc,
                                     'debit': tds_amt_inc,
                                     'credit': 0,
                                     'date_maturity': payment.date,
                                     'partner_id': payment.partner_id.id,
                                     'account_id': debitacc,
                                     'currency_id': currency,
                                     # 'move_id': payment.move_id.id
                                     })
                        if payment.tds_amt:
                            vals.append({'name': _('Income Tax Withhold'),
                                         'amount_currency': payment.tds_amt,
                                         'debit': payment.tds_amt,
                                         'credit': 0,
                                         'date_maturity': payment.date,
                                         'partner_id': payment.partner_id.id,
                                         'account_id': tax_repartition_lines.id and tax_repartition_lines.account_id.id,
                                         'currency_id': currency,
                                         # 'move_id': payment.move_id.id
                                         })
                        if payment.sales_tds_amt:
                            vals.append({'name': _('Sale Tax Withhold'),
                                         'amount_currency': payment.sales_tds_amt,
                                         'debit': payment.sales_tds_amt,
                                         'credit': 0,
                                         'date_maturity': payment.date,
                                         'partner_id': payment.partner_id.id,
                                         'account_id': sales_tax_repartition_lines.id and sales_tax_repartition_lines.account_id.id,
                                         'currency_id': currency,
                                         # 'move_id': payment.move_id.id
                                         })
                        lines = [(0, 0, line_move) for line_move in vals]
                        payment.move_id.write({'line_ids': lines})
                        payment.move_id.write({'currency_id': currency})
                        payment.move_id.action_post()

            # payment.amount = payamt
            move_lines = self.env['account.move.line']
            invoice_ids = payment.reconcile_invoice_ids.filtered(lambda x: x.reconcile).mapped('invoice_id')
            invoice_move = invoice_ids.mapped('line_ids').filtered(
                lambda r: not r.reconciled and r.account_id.internal_type in ('payable', 'receivable'))
            payment_move = payment.invoice_line_ids.filtered(
                lambda r: not r.reconciled and r.account_id.internal_type in ('payable', 'receivable'))
            move_lines |= (invoice_move + payment_move)
            if move_lines:
                move_lines.reconcile()

        return res

    def _synchronize_from_moves(self, changed_fields):
        ''' Update the account.payment regarding its related account.move.
        Also, check both models are still consistent.
        :param changed_fields: A set containing all modified fields on account.move.
        '''
        if self._context.get('skip_account_move_synchronization'):
            return

        for pay in self.with_context(skip_account_move_synchronization=True):

            # After the migration to 14.0, the journal entry could be shared between the account.payment and the
            # account.bank.statement.line. In that case, the synchronization will only be made with the statement line.
            if pay.move_id.statement_line_id:
                continue

            move = pay.move_id
            move_vals_to_write = {}
            payment_vals_to_write = {}

            if 'journal_id' in changed_fields:
                if pay.journal_id.type not in ('bank', 'cash'):
                    raise UserError(_("A payment must always belongs to a bank or cash journal."))

            if 'line_ids' in changed_fields:
                all_lines = move.line_ids
                liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

                if len(liquidity_lines) != 1 or len(counterpart_lines) != 1:
                    if self.sales_tds_type == 'default':
                        raise UserError(_(
                            "The journal entry %s reached an invalid state relative to its payment.\n"
                            "To be consistent, the journal entry must always contains:\n"
                            "- one journal item involving the outstanding payment/receipts account.\n"
                            "- one journal item involving a receivable/payable account.\n"
                            "- optional journal items, all sharing the same account.\n\n"
                        ) % move.display_name)

                if any(line.currency_id != all_lines[0].currency_id for line in all_lines):
                    raise UserError(_(
                        "The journal entry %s reached an invalid state relative to its payment.\n"
                        "To be consistent, the journal items must share the same currency."
                    ) % move.display_name)

                if any(line.partner_id != all_lines[0].partner_id for line in all_lines):
                    raise UserError(_(
                        "The journal entry %s reached an invalid state relative to its payment.\n"
                        "To be consistent, the journal items must share the same partner."
                    ) % move.display_name)

                if counterpart_lines.account_id.user_type_id.type == 'receivable':
                    partner_type = 'customer'
                else:
                    partner_type = 'supplier'

                liquidity_amount = liquidity_lines.amount_currency

                move_vals_to_write.update({
                    'currency_id': liquidity_lines.currency_id.id,
                    'partner_id': liquidity_lines.partner_id.id,
                })
                payment_vals_to_write.update({
                    'amount': abs(liquidity_amount),
                    'payment_type': 'inbound' if liquidity_amount > 0.0 else 'outbound',
                    'partner_type': partner_type,
                    'currency_id': liquidity_lines.currency_id.id,
                    'destination_account_id': counterpart_lines.account_id.id,
                    'partner_id': liquidity_lines.partner_id.id,
                })

            move.write(move._cleanup_write_orm_values(move, move_vals_to_write))
            pay.write(move._cleanup_write_orm_values(pay, payment_vals_to_write))


class AccountPaymentReconcile(models.Model):
    _name = 'account.payment.reconcile'

    def _check_full_deduction(self):
        if self.invoice_id:
            payment_ids = [payment['account_payment_id'] for payment in
                           self.invoice_id._get_reconciled_info_JSON_values()]
            if payment_ids:
                payments = self.env['account.payment'].browse(payment_ids)
                return any([True if payment.tds_amt or payment.sales_tds_amt else False for payment in payments])
            else:
                return False

    payment_id = fields.Many2one('account.payment')
    reconcile = fields.Boolean(string="Select")
    invoice_id = fields.Many2one('account.move', required=True)
    currency_id = fields.Many2one('res.currency')
    amount_total = fields.Monetary(string='Total')
    amount_untaxed = fields.Monetary(string='Untaxed Amount')
    amount_tax = fields.Monetary(string='Taxes Amount')
    already_paid = fields.Float("Amount Paid")
    amount_residual = fields.Monetary('Amount Due')
    full_wht_deduction = fields.Boolean('Full DED. WHT')
    is_editable_deduction = fields.Boolean(default=lambda self: self._check_full_deduction())
    amount_paid = fields.Monetary(string="Payment Amount")
    it_wht_amount = fields.Monetary(string="IT WHT Amount", compute='_compute_wht_amount', store=True, readonly=True)
    st_wht_amount = fields.Monetary(string="ST WHT Amount", compute='_compute_wht_amount', store=True, readonly=True)

    # @api.constrains('amount_paid')
    # def _check_amount_paid(self):
    #     for line in self.filtered(lambda x: x.reconcile):
    #         if line.amount_paid > line.amount_residual:
    #             raise UserError('Payment amount should be less than or equal to amount due')

    @api.depends('amount_paid', 'payment_id.tds_tax_id', 'payment_id.sales_tds_tax_id', 'full_wht_deduction')
    def _compute_wht_amount(self):
        for line in self:
            # if self._context.get('active_model', False) == 'account.move':
            #     move = self.env['account.move'].browse(self._context.get('active_id', []))
            #     wht_id = move.partner_id.wht_id
            #     income_tax_id = move.partner_id.income_tax_id
            # else:
            wht_id = line.payment_id.sales_tds_tax_id
            income_tax_id = line.payment_id.tds_tax_id
            if line.full_wht_deduction:
                line.it_wht_amount = line.amount_total * income_tax_id.amount / 100
                line.st_wht_amount = line.amount_tax * wht_id.amount / 100
            else:
                line.it_wht_amount = line.amount_paid * income_tax_id.amount / 100
                payment_per = line.amount_paid / line.amount_total * 100 if line.amount_total else 0.0
                tot_sales_tax = line.amount_tax * wht_id.amount / 100
                line.st_wht_amount = tot_sales_tax * payment_per / 100
            # tax_to_per = (line.amount_tax / 100.0) / 100.0 * line.payment_id.sales_tds_tax_id.amount
            # final = payment_per * tax_to_per
            # line.st_wht_amount = final


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    sales_tds_type = fields.Selection([('default', 'Payment Without WHT'), ('including', 'Payment Including WHT'),
                                       ('excluding', 'Payment Excluding With WHT')], default="default",
                                      string="Sales Tax Withhold Type")
    sales_tds_tax_id = fields.Many2one('account.tax', string='Sales Tax Withhold Percentage')
    sales_tds_amt = fields.Monetary(string='Sales Tax Withhold Amount', compute='compute_sales_tds_amnt')
    tds_type = fields.Selection([('default', 'Payment Without WHT'), ('including', 'Payment Including WHT'),
                                 ('excluding', 'Payment Excluding With WHT')], default="default",
                                string="Income Tax Withhold Type")
    tds_tax_id = fields.Many2one('account.tax', string='Incomte Tax Withhold Percentage')
    tds_amt = fields.Monetary(string='Income Tax Withhold Amount', compute='compute_tds_amnt')
    reconcile_invoice_ids = fields.Many2many('account.payment.reconcile', string="Invoices", copy=False)

    @api.depends('sales_tds_type', 'sales_tds_tax_id', 'amount')
    def compute_sales_tds_amnt(self):
        for payment in self:
            wht_id = payment.sales_tds_tax_id
            payment.sales_tds_amt = 0.0
            if payment.sales_tds_type in ('including', 'excluding') and payment.sales_tds_tax_id and payment.amount:
                applicable = True
                if payment.partner_id and payment.partner_id.tds_threshold_check:
                    applicable = True
                if applicable and payment.sales_tds_type in ['excluding', 'including'] and payment.amount:
                    if not payment.reconcile_invoice_ids or len(payment.reconcile_invoice_ids.filtered(lambda x: x.reconcile)) == 0:
                        amount = payment.sales_tds_tax_id.amount
                        payment.sales_tds_amt = (payment.amount * amount / 100)
                    else:
                        for line in payment.reconcile_invoice_ids.filtered(lambda x: x.reconcile):
                            if line.full_wht_deduction:
                                line.st_wht_amount = line.amount_tax * wht_id.amount / 100
                            else:
                                payment_per = line.amount_paid / line.amount_total * 100 if line.amount_total else 0.0
                                tot_sales_tax = line.amount_tax * wht_id.amount / 100
                                line.st_wht_amount = tot_sales_tax * payment_per / 100
                        payment.sales_tds_amt = sum(payment.reconcile_invoice_ids.filtered(lambda x: x.reconcile).mapped('st_wht_amount'))

    @api.onchange('reconcile_invoice_ids')
    def _onchnage_reconcile_invoice_ids(self):
        self.amount = sum(self.reconcile_invoice_ids.filtered(lambda x: x.reconcile).mapped('amount_paid'))

    @api.depends('tds_type', 'tds_tax_id', 'amount')
    def compute_tds_amnt(self):
        for payment in self:
            income_tax_id = payment.tds_tax_id
            payment.tds_amt = 0.0
            if payment.tds_type in ('including', 'excluding') and payment.tds_tax_id and payment.amount:
                applicable = True
                if payment.partner_id and payment.partner_id.tds_threshold_check:
                    applicable = True
                if applicable and payment.tds_type == 'including':

                    if not payment.reconcile_invoice_ids or len(payment.reconcile_invoice_ids.filtered(lambda x: x.reconcile)) == 0:
                        tds_amount = payment.tds_tax_id.amount
                        payment.tds_amt = (payment.amount * tds_amount / 100)
                    else:
                        for line in payment.reconcile_invoice_ids.filtered(lambda x: x.reconcile):
                            if line.full_wht_deduction:
                                line.it_wht_amount = line.amount_total * income_tax_id.amount / 100
                            else:
                                line.it_wht_amount = line.amount_paid * income_tax_id.amount / 100
                        payment.tds_amt = sum(payment.reconcile_invoice_ids.filtered(lambda x: x.reconcile).mapped('it_wht_amount'))

    @api.model
    def default_get(self, fields):
        res = super(AccountPaymentRegister, self).default_get(fields)
        moves = self.env['account.move'].browse(self._context.get('active_ids', []))
        res.update({'reconcile_invoice_ids': [(0, 0, {'invoice_id': move.id, 'already_paid': sum(
            [payment['amount'] for payment in move._get_reconciled_info_JSON_values()]),
                                                      'amount_residual': move.amount_residual,
                                                      'amount_untaxed': move.amount_untaxed,
                                                      'amount_tax': move.amount_tax, 'currency_id': move.currency_id.id,
                                                      'amount_total': move.amount_total, }) for move in moves],
                    'sales_tds_tax_id': moves.partner_id.wht_id.id, 'tds_tax_id': moves.partner_id.income_tax_id.id})
        return res

    def _create_payment_vals_from_wizard(self):
        # OVERRIDE
        payment_vals = super(AccountPaymentRegister, self)._create_payment_vals_from_wizard()
        payment_vals.update({
            'sales_tds_type': self.sales_tds_type,
            'sales_tds_tax_id': self.sales_tds_tax_id.id,
            'tds_type': self.tds_type,
            'tds_tax_id': self.tds_tax_id.id,
            'reconcile_invoice_ids': self.reconcile_invoice_ids,
        })
        return payment_vals
