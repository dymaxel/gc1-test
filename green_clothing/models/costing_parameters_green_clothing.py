
from odoo import api, fields, models


class CostingParametersGreenClothing(models.Model):
    _name = "costing.parameters.green.clothing"

    name = fields.Char(string="Name")
    consumption = fields.Float(string="Consumption")
    price = fields.Float(string="Price")

    costing_sheet_id = fields.Many2one('costing.sheet.green.clothing', string="id")
