# -*- coding: utf-8 -*-
# Copyright (c) 2015-Present TidyWay Software Solution. (<https://tidyway.in/>)

from odoo import models, api, fields
from datetime import date, time, datetime


class BatchHistory(models.Model):
    _name = 'batch.history'
    _description = 'Batch History'

    product_id = fields.Many2one('product.product', readonly=True)
    qty = fields.Integer('Barcode Labels Qty', readonly=True)
    print_date = fields.Datetime('Print Date', default = datetime.now(), readonly=True)
    batch_no = fields.Char('Batch No', readonly=True)
    user_id = fields.Many2one('res.users', readonly=True, default=lambda self: self.env.user)

class ResUsers(models.Model):
    _inherit = 'res.users'

    pricelist_id = fields.Many2one('product.pricelist', string='Default Pricelist')
