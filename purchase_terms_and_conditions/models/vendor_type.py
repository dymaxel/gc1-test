# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class VendorType(models.Model):
    _name = 'vendor.type'
    _description = 'Vendor Type'

    name = fields.Char('Name', required=True)
    notes = fields.Text('Terms and Conditions')
