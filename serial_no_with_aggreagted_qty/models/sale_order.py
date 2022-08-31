from odoo import api, fields, models
from datetime import date


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    total_product_qty = fields.Integer(compute="_compute_total_product_qty", help="total Quantity")

    @api.depends('order_line')
    def _compute_total_product_qty(self):
        for record in self:
            if record.order_line:
                for line in record.order_line:
                    record.total_product_qty += line.product_uom_qty
            else:
                record.total_product_qty = 0


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    sl_no = fields.Integer(string='Sr#', compute='_compute_serial_number', store=True)

    @api.depends('sequence', 'order_id')
    def _compute_serial_number(self):
        for order_line in self:
            if not order_line.sl_no:
                serial_no = 1
                for line in order_line.mapped('order_id').order_line.filtered(lambda sol: sol.product_id):
                    line.sl_no = serial_no
                    serial_no += 1


class AccountMove(models.Model):
    _inherit = 'account.move'

    total_product_qty = fields.Integer(compute="_compute_total_product_qty", help="total Quantity")
    amount_in_words = fields.Char(compute='_compute_amount_in_words')

    @api.depends('currency_id', 'amount_total')
    def _compute_amount_in_words(self):
        amount_in_pkr = round(
            self.currency_id._convert(self.amount_total, self.env.ref('base.PKR'), self.env.company, date.today()))
        self.amount_in_words = '{} {:,}'.format(self.env.ref('base.PKR').symbol, amount_in_pkr)

    @api.depends('invoice_line_ids')
    def _compute_total_product_qty(self):
        for record in self:
            if record.invoice_line_ids:
                for line in record.invoice_line_ids:
                    record.total_product_qty += line.quantity
            else:
                record.total_product_qty = 0


class AccountInvoice(models.Model):
    _inherit = "account.move.line"

    sl_no = fields.Integer(string='Sr#', compute='_compute_serial_number', store=True)

    @api.depends('sequence', 'move_id')
    def _compute_serial_number(self):
        for order_line in self:
            if not order_line.sl_no:
                serial_no = 1
                for line in order_line.mapped('move_id').invoice_line_ids.filtered(lambda aml: aml.product_id):
                    line.sl_no = serial_no
                    serial_no += 1


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    total_product_qty = fields.Integer(compute="_compute_total_product_qty", help="total Quantity")

    @api.depends('order_line')
    def _compute_total_product_qty(self):
        for record in self:
            if record.order_line:
                for line in record.order_line:
                    record.total_product_qty += line.product_qty
            else:
                record.total_product_qty = 0


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    sl_no = fields.Integer(string='Sr#', compute='_compute_serial_number', store=True)

    @api.depends('sequence', 'order_id')
    def _compute_serial_number(self):
        for order_line in self:
            if not order_line.sl_no:
                serial_no = 1
                for line in order_line.mapped('order_id').order_line.filtered(lambda pol: pol.product_id):
                    line.sl_no = serial_no
                    serial_no += 1


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    total_product_qty = fields.Integer(compute="_compute_total_product_qty", help="total Quantity")

    @api.depends('move_ids_without_package')
    def _compute_total_product_qty(self):
        for record in self:
            if record.move_ids_without_package:
                for line in record.move_ids_without_package:
                    record.total_product_qty += line.product_uom_qty
            else:
                record.total_product_qty = 0


class StockMove(models.Model):
    _inherit = "stock.move"

    sl_no = fields.Integer(string='Sr#', compute='_compute_serial_number', store=True)

    @api.depends('sequence', 'picking_id')
    def _compute_serial_number(self):
        for move in self:
            if not move.sl_no:
                serial_no = 1
                for line in move.mapped('picking_id').move_ids_without_package.filtered(lambda m: m.product_id):
                    line.sl_no = serial_no
                    serial_no += 1
