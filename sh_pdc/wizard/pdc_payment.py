# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Attachment(models.Model):
    _inherit = 'ir.attachment'

    pdc_id = fields.Many2one('pdc.wizard')


class PDC_wizard(models.Model):
    _name = "pdc.wizard"
    _description = "PDC Wizard"

    is_invisible_done = fields.Boolean(compute='_compute_done_visible')

    @api.depends('due_date')
    def _compute_done_visible(self):
        if self.due_date:
            if self.due_date > datetime.date.today():
                self.is_invisible_done = True
            else:
                self.is_invisible_done = False
        else:
            self.is_invisible_done = False

    def open_attachments(self):
        [action] = self.env.ref('base.action_attachment').read()
        ids = self.env['ir.attachment'].search([('pdc_id', '=', self.id)])
        id_list = []
        for pdc_id in ids:
            id_list.append(pdc_id.id)
        action['domain'] = [('id', 'in', id_list)]
        return action

    def open_journal_items(self):
        [action] = self.env.ref('account.action_account_moves_all').read()
        ids = self.env['account.move.line'].search([('pdc_id', '=', self.id)])
        id_list = []
        for pdc_id in ids:
            id_list.append(pdc_id.id)
        action['domain'] = [('id', 'in', id_list)]
        return action

    def open_journal_entry(self):
        [action] = self.env.ref('sh_pdc.sh_pdc_action_move_journal_line').read()
        ids = self.env['account.move'].search([('pdc_id', '=', self.id)])
        id_list = []
        for pdc_id in ids:
            id_list.append(pdc_id.id)
        action['domain'] = [('id', 'in', id_list)]
        return action

    @api.model
    def default_get(self, fields):
        rec = super(PDC_wizard, self).default_get(fields)
        active_ids = self._context.get('active_ids')
        active_model = self._context.get('active_model')

        # Check for selected invoices ids
        if not active_ids or active_model != 'account.move':
            return rec

        invoices = self.env['account.move'].browse(active_ids)

        if invoices:
            invoice = invoices[0]

            if invoice.move_type in ('out_invoice', 'out_refund'):
                rec.update({'payment_type': 'receive_money'})

            elif invoice.move_type in ('in_invoice', 'in_refund'):
                rec.update({'payment_type': 'send_money'})

            amls = invoices.line_ids.filtered(lambda inv: inv.account_internal_type in ('receivable', 'payable'))

            rec.update({'source_amount': abs(sum(amls.mapped('amount_residual')))})

            rec.update({'source_currency_id': amls.mapped('currency_id').id})

            if amls.currency_id.id == self.env.company.currency_id.id:

                rec.update({'source_amount_currency': rec['source_amount']})

            else:

                rec.update({'source_amount_currency': abs(sum(amls.mapped('amount_residual_currency')))})

            rec.update({'partner_id': invoice.partner_id.id, 'payment_amount': invoice.amount_residual,
                        'invoice_id': invoice.id, 'due_date': invoice.invoice_date_due, 'memo': invoice.name,
                        'currency_id': invoice.currency_id.id})

        return rec

    name = fields.Char("Name", default='New', readonly=1)
    payment_type = fields.Selection([('receive_money', 'Receive Money'), ('send_money', 'Send Money')],
                                    string="Payment Type", default='receive_money')
    partner_id = fields.Many2one('res.partner', string="Partner", required=True)
    payment_amount = fields.Monetary("Payment Amount")
    currency_id = fields.Many2one('res.currency', string="Currency", default=lambda self: self.env.company.currency_id)
    reference = fields.Char("Cheque Reference")
    journal_id = fields.Many2one('account.journal', string="Payment Journal", domain=[('type', '=', 'bank')],
                                 required=1)
    payment_date = fields.Date("Payment Date", default=fields.Date.today(), required=1)
    due_date = fields.Date("Due Date", required=1)
    memo = fields.Char("Memo")
    agent = fields.Char("Agent")
    bank_id = fields.Many2one('res.bank', string="Bank")
    invoice_id = fields.Many2one('account.move', string="Invoice/Bill")
    state = fields.Selection(
        [('draft', 'Draft'), ('registered', 'Registered'), ('returned', 'Returned'), ('deposited', 'Deposited'),
         ('bounced', 'Bounced'), ('done', 'Done'), ('cancel', 'Cancelled')], string="State", default='draft')

    attachment_ids = fields.One2many('ir.attachment', 'pdc_id', string="Attachments")
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
    reconcile_invoice_ids = fields.One2many('account.payment.reconcile', 'pdc_id', string="Invoices", copy=False)

    source_currency_id = fields.Many2one('res.currency', string='Source Currency', copy=False,
                                         help="The payment's currency.")
    company_currency_id = fields.Many2one('res.currency', string="Company Currency",
                                          default=lambda self: self.env.company.currency_id.id)
    source_amount = fields.Monetary(string="Amount to Pay (company currency)", copy=False,
                                    currency_field='company_currency_id')
    source_amount_currency = fields.Monetary(string="Amount to Pay (foreign currency)", copy=False,
                                             currency_field='source_currency_id')

    @api.onchange('currency_id')
    def _onchange_currency_id(self):
        for wizard in self:
            amount_payment_currency = wizard.env.company.currency_id._convert(wizard.source_amount, wizard.currency_id,
                                                                              wizard.env.company, wizard.payment_date)
            wizard.payment_amount = amount_payment_currency

    # @api.depends('source_amount', 'source_amount_currency', 'source_currency_id', 'currency_id', 'payment_date')
    # def _compute_amount(self):
    #     for wizard in self:
    #         if wizard.source_currency_id == wizard.currency_id:
    #             # Same currency.
    #             wizard.payment_amount = wizard.source_amount_currency
    #         elif wizard.currency_id == wizard.env.company.currency_id:
    #             # Payment expressed on the company's currency.
    #             wizard.payment_amount = wizard.source_amount
    #         else:
    #             # Foreign currency on payment different than the one set on the journal entries.
    #             amount_payment_currency = wizard.env.company.currency_id._convert(wizard.source_amount,
    #                                                                               wizard.currency_id,
    #                                                                               wizard.env.company,
    #                                                                               wizard.payment_date)
    #             wizard.payment_amount = amount_payment_currency

    # def _compute_from_lines(self):
    #
    #     for wizard in self:
    #
    #         print(wizard.partner_id.name)
    #         amls = self.env['account.move.line'].search(
    #             [('move_id.state', '=', 'posted'), ('account_internal_type', 'in', ('receivable', 'payable')),
    #              ('partner_id', '=', wizard.partner_id.id)])
    #
    #         print(amls)
    #         print(amls.mapped('partner_id.name'))
    #         wizard.source_amount = abs(sum(amls.mapped('amount_residual')))
    #
    #         wizard.source_currency_id = amls.mapped('currency_id').id
    #
    #         if amls.currency_id.id == self.env.company.currency_id.id:
    #
    #             wizard.source_amount_currency = wizard.source_amount
    #
    #         else:
    #
    #             wizard.source_amount_currency = abs(sum(amls.mapped('amount_residual_currency')))

    @api.onchange('reconcile_invoice_ids')
    def _onchnage_reconcile_invoice_ids(self):
        self.payment_amount = sum(self.reconcile_invoice_ids.filtered(lambda x: x.reconcile).mapped('amount_paid'))

    @api.onchange('partner_id', 'payment_type', 'partner_type')
    def _onchange_partner_id(self):
        if not self.partner_id:
            return
        partner_id = self.partner_id
        self.reconcile_invoice_ids = [(5,)]
        move_type = {'send_money': 'in_invoice', 'receive_money': 'out_invoice'}
        moves = self.env['account.move'].sudo().search(
            [('partner_id', '=', self.partner_id.id), ('state', '=', 'posted'),
             ('payment_state', 'not in', ['paid', 'reversed']), ('move_type', '=', move_type[self.payment_type]),
             ('company_id', '=', self.env.company.id)])
        vals = []
        for move in moves:
            vals.append((0, 0, {
                'pdc_id': self.id,
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

    @api.depends('sales_tds_type', 'sales_tds_tax_id', 'payment_amount')
    def compute_sales_tds_amnt(self):
        for payment in self:
            wht_id = payment.sales_tds_tax_id
            payment.sales_tds_amt = 0.0
            if payment.sales_tds_type in (
                    'including', 'excluding') and payment.sales_tds_tax_id and payment.payment_amount:
                applicable = True
                if payment.partner_id and payment.partner_id.tds_threshold_check:
                    applicable = payment.check_turnover(self.partner_id.id, self.sales_tds_tax_id.payment_excess,
                                                        payment.amount)
                    # applicable = Truejawaid 24/6/2022
                if applicable and payment.sales_tds_type in ['excluding', 'including'] and payment.payment_amount:
                    if not payment.reconcile_invoice_ids or len(
                            payment.reconcile_invoice_ids.filtered(lambda x: x.reconcile)) == 0:
                        amount = payment.sales_tds_tax_id.amount
                        payment.sales_tds_amt = (payment.payment_amount * amount / 100)
                    else:
                        for line in payment.reconcile_invoice_ids.filtered(lambda x: x.reconcile):
                            if line.full_wht_deduction:
                                line.st_wht_amount = line.amount_tax * wht_id.amount / 100
                            else:
                                payment_per = line.amount_paid / line.amount_total * 100 if line.amount_total else 0.0
                                tot_sales_tax = line.amount_tax * wht_id.amount / 100
                                line.st_wht_amount = tot_sales_tax * payment_per / 100
                        payment.sales_tds_amt = sum(
                            payment.reconcile_invoice_ids.filtered(lambda x: x.reconcile).mapped('st_wht_amount'))

    @api.depends('tds_type', 'tds_tax_id', 'payment_amount')
    def compute_tds_amnt(self):
        for payment in self:
            income_tax_id = payment.tds_tax_id
            payment.tds_amt = 0.0
            if payment.tds_type in ('including', 'excluding') and payment.tds_tax_id and payment.payment_amount:
                applicable = True
                if payment.partner_id and payment.partner_id.tds_threshold_check:
                    applicable = payment.check_turnover(self.partner_id.id, self.tds_tax_id.payment_excess,
                                                        payment.payment_amount)
                    # applicable = Truejawaid 24/6/2022
                if applicable and payment.tds_type == 'including':

                    if not payment.reconcile_invoice_ids or len(
                            payment.reconcile_invoice_ids.filtered(lambda x: x.reconcile)) == 0:
                        tds_amount = payment.tds_tax_id.amount
                        payment.tds_amt = (payment.payment_amount * tds_amount / 100)
                    else:
                        for line in payment.reconcile_invoice_ids.filtered(lambda x: x.reconcile):
                            if line.full_wht_deduction:
                                line.it_wht_amount = line.amount_total * income_tax_id.amount / 100
                            else:
                                line.it_wht_amount = line.amount_paid * income_tax_id.amount / 100
                        payment.tds_amt = sum(
                            payment.reconcile_invoice_ids.filtered(lambda x: x.reconcile).mapped('it_wht_amount'))

    # Register pdc payment
    def button_register(self):
        self.write({'state': 'registered'})
        self.action_deposited()
        if self.invoice_id:
            self.invoice_id.payment_state = 'in_payment'

    #
    def action_register(self):
        self.check_payment_amount()
        self.write({'state': 'registered'})

    def check_payment_amount(self):
        if self.payment_amount <= 0.0:
            raise UserError("Amount must be greater than zero!")

    def check_pdc_account(self):
        if self.payment_type == 'receive_money':
            if not self.env.company.pdc_customer:
                raise UserError("Please Set PDC payment account for Customer !")
            else:
                return self.env.company.pdc_customer.id

        else:
            if not self.env.company.pdc_vendor:
                raise UserError("Please Set PDC payment account for Supplier !")
            else:
                return self.env.company.pdc_vendor.id

    def get_partner_account(self):
        if self.payment_type == 'receive_money':
            return self.partner_id.property_account_receivable_id.id
        else:
            return self.partner_id.property_account_payable_id.id

    def action_returned(self):
        self.check_payment_amount()
        self.write({'state': 'returned'})

    def get_credit_move_line(self, account):
        return {
            'pdc_id': self.id,
            'partner_id': self.partner_id.id,
            'account_id': account,
            'credit': self.payment_amount,
            'ref': self.memo,
            'date': self.payment_date,
            'date_maturity': self.due_date,
        }

    def get_debit_move_line(self, account):
        return {
            'pdc_id': self.id,
            'partner_id': self.partner_id.id,
            'account_id': account,
            'debit': self.payment_amount,
            'ref': self.memo,
            'date': self.payment_date,
            'date_maturity': self.due_date,
        }

    def get_move_vals(self, debit_line, credit_line):
        return {
            'pdc_id': self.id,
            'date': self.payment_date,
            'journal_id': self.journal_id.id,
            'partner_id': self.partner_id.id,
            'ref': self.memo,
            'line_ids': [(0, 0, debit_line),
                         (0, 0, credit_line)]
        }

    def action_deposited(self):
        move = self.env['account.move']

        self.check_payment_amount()  # amount must be positive
        pdc_account = self.check_pdc_account()
        partner_account = self.get_partner_account()

        # Create Journal Item
        if self.payment_type == 'receive_money':
            move_line_vals_debit = self.get_debit_move_line(pdc_account)
            move_line_vals_credit = self.get_credit_move_line(partner_account)
        else:
            move_line_vals_debit = self.get_debit_move_line(partner_account)
            move_line_vals_credit = self.get_credit_move_line(pdc_account)

        # create move and post it
        move_vals = self.get_move_vals(move_line_vals_debit, move_line_vals_credit)
        tax_repartition_lines = self.tds_tax_id.invoice_repartition_line_ids.filtered(
            lambda x: x.repartition_type == 'tax')
        sales_tax_repartition_lines = self.sales_tds_tax_id.invoice_repartition_line_ids.filtered(
            lambda x: x.repartition_type == 'tax')

        income_tax_vals = {
            'name': _('Income Tax Withhold'),
            'date_maturity': self.due_date,
            'partner_id': self.partner_id.id,
            'account_id': tax_repartition_lines.id and tax_repartition_lines.account_id.id,
            'pdc_id': self.id,
        }

        sales_tax_vals = {
            'name': _('Salse Tax Withhold'),
            'date_maturity': self.due_date,
            'partner_id': self.partner_id.id,
            'account_id': sales_tax_repartition_lines.id and sales_tax_repartition_lines.account_id.id,
            'pdc_id': self.id,
        }

        if self.payment_type == 'send_money':

            debit = 0

            if self.tds_amt and self.tds_type == 'including' and self.sales_tds_type != 'including':

                credit = self.tds_amt

                for rec in move_vals.get('line_ids'):
                    if 'credit' in rec[2]:
                        rec[2]['credit'] = rec[2]['credit'] - credit

                income_tax_vals.update({'credit': credit, 'debit': debit})

                move_vals['line_ids'].append((0, 0, income_tax_vals))

            if self.sales_tds_amt and self.sales_tds_type == 'including' and self.tds_type != 'including':

                credit = self.sales_tds_amt

                for rec in move_vals.get('line_ids'):
                    if 'credit' in rec[2]:
                        rec[2]['credit'] = rec[2]['credit'] - credit

                sales_tax_vals.update({'credit': credit, 'debit': debit})

                move_vals['line_ids'].append((0, 0, sales_tax_vals))

            if self.tds_amt and self.sales_tds_amt and self.sales_tds_type == 'including' and self.tds_type == 'including':

                credit = self.sales_tds_amt + self.tds_amt

                for rec in move_vals.get('line_ids'):
                    if 'credit' in rec[2]:
                        rec[2]['credit'] = rec[2]['credit'] - credit

                income_tax_vals.update({'credit': self.tds_amt, 'debit': debit})

                move_vals['line_ids'].append((0, 0, income_tax_vals))

                sales_tax_vals.update({'credit': self.sales_tds_amt, 'debit': debit})

                move_vals['line_ids'].append((0, 0, sales_tax_vals))

        if self.payment_type == 'receive_money':

            credit = 0

            if self.tds_amt and self.tds_type == 'including' and self.sales_tds_type != 'including':

                debit = self.tds_amt

                for rec in move_vals.get('line_ids'):
                    if 'debit' in rec[2]:
                        rec[2]['debit'] = rec[2]['debit'] - debit

                income_tax_vals.update({'credit': credit, 'debit': debit})

                move_vals['line_ids'].append((0, 0, income_tax_vals))

            if self.sales_tds_amt and self.sales_tds_type == 'including' and self.tds_type != 'including':

                debit = self.sales_tds_amt

                for rec in move_vals.get('line_ids'):
                    if 'debit' in rec[2]:
                        rec[2]['debit'] = rec[2]['debit'] - debit

                sales_tax_vals.update({'credit': credit, 'debit': debit})

                move_vals['line_ids'].append((0, 0, sales_tax_vals))

            if self.tds_amt and self.sales_tds_amt and self.sales_tds_type == 'including' and self.tds_type == 'including':

                debit = self.sales_tds_amt + self.tds_amt

                for rec in move_vals.get('line_ids'):
                    if 'debit' in rec[2]:
                        rec[2]['debit'] = rec[2]['debit'] - debit

                income_tax_vals.update({'credit': credit, 'debit': self.tds_amt})

                move_vals['line_ids'].append((0, 0, income_tax_vals))

                sales_tax_vals.update({'credit': credit, 'debit': self.sales_tds_amt})

                move_vals['line_ids'].append((0, 0, sales_tax_vals))

        move_id = move.create(move_vals)
        move_id.action_post()
        self.write({'state': 'deposited'})

    def action_bounced(self):
        move = self.env['account.move']

        self.check_payment_amount()  # amount must be positive
        pdc_account = self.check_pdc_account()
        partner_account = self.get_partner_account()

        # Create Journal Item
        if self.payment_type == 'receive_money':
            move_line_vals_debit = self.get_debit_move_line(partner_account)
            move_line_vals_credit = self.get_credit_move_line(pdc_account)
        else:
            move_line_vals_debit = self.get_debit_move_line(pdc_account)
            move_line_vals_credit = self.get_credit_move_line(partner_account)

        if self.memo:
            move_line_vals_debit.update({'name': 'PDC Payment :' + self.memo})
            move_line_vals_credit.update({'name': 'PDC Payment :' + self.memo})
        else:
            move_line_vals_debit.update({'name': 'PDC Payment'})
            move_line_vals_credit.update({'name': 'PDC Payment'})
        # create move and post it
        move_vals = self.get_move_vals(move_line_vals_debit, move_line_vals_credit)
        move_id = move.create(move_vals)
        move_id.action_post()

        self.write({'state': 'bounced'})

    def action_done(self):
        move = self.env['account.move']

        self.check_payment_amount()  # amount must be positive
        pdc_account = self.check_pdc_account()
        bank_account = self.journal_id.default_account_id.id

        # Create Journal Item
        if self.payment_type == 'receive_money':
            move_line_vals_debit = self.get_debit_move_line(bank_account)
            move_line_vals_credit = self.get_credit_move_line(pdc_account)
        else:
            move_line_vals_debit = self.get_debit_move_line(pdc_account)
            move_line_vals_credit = self.get_credit_move_line(bank_account)

        if self.memo:
            move_line_vals_debit.update({'name': 'PDC Payment :' + self.memo})
            move_line_vals_credit.update({'name': 'PDC Payment :' + self.memo})
        else:
            move_line_vals_debit.update({'name': 'PDC Payment'})
            move_line_vals_credit.update({'name': 'PDC Payment'})

        # create move and post it
        move_vals = self.get_move_vals(move_line_vals_debit, move_line_vals_credit)
        move_vals['date'] = self.due_date

        tax_amount = 0.0

        if self.tds_amt and self.tds_type == 'including' and self.sales_tds_type != 'including':
            tax_amount = self.tds_amt

        if self.sales_tds_amt and self.sales_tds_type == 'including' and self.tds_type != 'including':
            tax_amount = self.sales_tds_amt

        if self.tds_amt and self.sales_tds_amt and self.sales_tds_type == 'including' and self.tds_type == 'including':
            tax_amount = self.sales_tds_amt + self.tds_amt

        for rec in move_vals.get('line_ids'):
            if 'credit' in rec[2]:
                rec[2]['credit'] = rec[2]['credit'] - tax_amount

            if 'debit' in rec[2]:
                rec[2]['debit'] = rec[2]['debit'] - tax_amount

        move_id = move.create(move_vals)
        move_id.action_post()
        if self.invoice_id:
            self.invoice_id.sudo().write({'amount_residual_signed': 0.0, 'amount_residual': 0.0})
            self.invoice_id._compute_amount()
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    @api.model
    def create(self, vals):
        if vals.get('payment_type') == 'receive_money':
            vals['name'] = self.env['ir.sequence'].next_by_code('pdc.payment.customer')
        elif vals.get('payment_type') == 'send_money':
            vals['name'] = self.env['ir.sequence'].next_by_code('pdc.payment.vendor')

        return super(PDC_wizard, self).create(vals)


class AccountPaymentReconcile(models.Model):
    _inherit = 'account.payment.reconcile'

    pdc_id = fields.Many2one('pdc.wizard')
