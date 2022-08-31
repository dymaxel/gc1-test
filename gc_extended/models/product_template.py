from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    product_consumption_ids = fields.One2many('product.consumption.line', 'consumption_ids',
                                              string="Product Consumption ids", copy=False)
    size_ids = fields.Many2many('product.size')


class ProductTemplateLine(models.Model):
    _name = "product.consumption.line"

    consumption_ids = fields.Many2one('product.template')
    product_name = fields.Many2one('product.product', string="Product")
    consumption = fields.Float(string="Consumption")
