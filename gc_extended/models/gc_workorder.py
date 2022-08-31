# -*- coding: utf-8 -*-
from odoo import api, fields, models


class GcWorkorder(models.Model):
    _name = 'gc.workorder'
    _description = 'Green Clothing Workorder'

    name = fields.Char(string='Workorder Number', required=True)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    workorder_id = fields.Many2one('gc.workorder', string='Workorder Number')
    product_brand_id = fields.Many2one('common.product.brand.ept', string="Product Brand",
                                       help='Select a brand for this product.')

    def _action_confirm(self):
        res = super(SaleOrder, self)._action_confirm()
        if self.workorder_id:
            self.picking_ids.write({'workorder_id': self.workorder_id.id})
        return res

    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals['workorder_id'] = self.workorder_id.id
        return invoice_vals


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    workorder_id = fields.Many2one('gc.workorder', string='Workorder Number')


class AccountMove(models.Model):
    _inherit = 'account.move'

    workorder_id = fields.Many2one('gc.workorder', string='Workorder Number')


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    workorder_id = fields.Many2one('gc.workorder', string='Workorder Number')

    def _prepare_account_move_line(self, move=False):
        res = super()._prepare_account_move_line(move)
        res.update({'workorder_id': self.workorder_id.id})
        return res


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    workorder_id = fields.Many2one('gc.workorder', string='Workorder Number')
