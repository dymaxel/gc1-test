# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    use_purchase_terms = fields.Boolean(
        string='Default Terms & Conditions',
        config_parameter='purchase.use_purchase_terms')
    purchase_terms = fields.Text(related='company_id.purchase_terms', string="Terms & Conditions", readonly=False)
