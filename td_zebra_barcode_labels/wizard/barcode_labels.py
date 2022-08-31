# -*- coding: utf-8 -*-
# Copyright (c) 2015-Present TidyWay Software Solution. (<https://tidyway.in/>)

from odoo import models, fields, api, _
from odoo.exceptions import Warning
from reportlab.graphics import barcode
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError
import pytz
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT


class tdzebrabarcodeProductLines(models.TransientModel):
    _name = "tdzebrabarcode.product.lines"
    _description = 'Barcode Labels Lines'

    product_id = fields.Many2one(
         'product.product',
         string='Product',
         required=True
         )
    qty = fields.Integer(
         'Barcode Labels Qty',
         default=1,
         required=True
         )
    wizard_id = fields.Many2one(
        'tdzebrabarcode.labels',
        string='Wizard'
        )
    product_expiry = fields.Datetime('Product Expiry')

    @api.onchange('product_expiry')
    def onchnage_(self):
        for line in self:
            if line.product_expiry and line.product_expiry < fields.Datetime.now():
                raise UserError(_('Invalid expiry date !'))

    def get_client_time(self, local_date):
        from datetime import datetime
        if not local_date:
            return ''
        date = local_date.strftime('%Y-%m-%d %H:%M:%S')
        if date:
            user_tz = self.env.user.tz or self.env.context.get('tz') or 'UTC'
            local = pytz.timezone(user_tz)
            date = datetime.strftime(pytz.utc.localize(datetime.strptime(date, DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),"%b-%d-%y %H:%M:%S")
        return date

    @api.onchange('product_id')
    def onchange_product_id(self):
        for line in self:
            if line.product_id and line.product_id.life_days > 0:
                line.product_expiry = datetime.today() + timedelta(days=line.product_id.life_days)
            else:
                line.product_expiry = False


class tdzebrabarcodeLabels(models.TransientModel):
    _name = "tdzebrabarcode.labels"
    _description = 'Barcode Labels'

    def get_zebra_date(self):
        user_tz = self.env.user.tz or self.env.context.get('tz') or 'UTC'
        local = pytz.timezone(user_tz)
        date = datetime.strftime(pytz.utc.localize(datetime.strptime(fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S'), DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),"%m-%d%y%H%M")
        return date

    @api.model
    def default_get(self, fields):
        product_get_ids = []
        if self._context.get('active_model') == 'product.product':
            record_ids = self._context.get('active_ids', []) or []
            products = self.env['product.product'].browse(record_ids)
            product_get_ids = [(0, 0, {
                                     'product_id': product.id,
                                     'qty': 1.0
                                     }) for product in products]
        elif self._context.get('active_model') == 'product.template':
            record_ids = self._context.get('active_ids', []) or []
            templates = self.env['product.template'].browse(record_ids)
            product_get_ids = []
            for template in templates:
                product_get_ids += [(0, 0, {
                             'product_id': product.id,
                             'qty': 1.0
                             }) for product in template.product_variant_ids]
        elif self._context.get('active_model') == 'purchase.order':
            record_ids = self._context.get('active_ids', []) or []
            purchase_recs = self.env['purchase.order'].browse(record_ids)
            product_get_ids = []
            for purchase in purchase_recs:
                for line in purchase.order_line:
                    if line.product_id and line.product_id.type != 'service':
                        product_get_ids += [(0, 0, {
                                 'product_id': line.product_id.id,
                                 'qty': int(abs(line.product_qty)) or 1.0
                                 })]
        elif self._context.get('active_model') == 'stock.picking':
            record_ids = self._context.get('active_ids', []) or []
            picking_recs = self.env['stock.picking'].browse(record_ids)
            product_get_ids = []
            for picking in picking_recs:
                for line in picking.move_lines:
                    if line.product_id and line.product_id.type != 'service':
                        product_get_ids += [(0, 0, {
                                 'product_id': line.product_id.id,
                                 'qty': int(abs(line.product_qty)) or 1.0
                                 })]
        elif self._context.get('active_model') == 'stock.quant':
            record_ids = self._context.get('active_ids', []) or []
            quant_ids = self.env['stock.quant'].browse(record_ids)
            product_get_ids = []
            for quant in quant_ids:
                if quant.product_id and quant.product_id.type != 'service':
                    product_get_ids += [(0, 0, {
                        'product_id': quant.product_id.id,
                        'qty': int(abs(quant.quantity)) or 0.0
                    })]
#         elif self._context.get('active_model') == 'mrp.production':
#             record_ids = self._context.get('active_ids', []) or []
#             mrp_recs = self.env['mrp.production'].browse(record_ids)
#             product_get_ids = []
#             for mrp in mrp_recs:
#                 for line in mrp.finished_move_line_ids:
#                     if line.product_id and line.product_id.type != 'service':
#                         product_get_ids += [(0, 0, {
#                                  'product_id': line.product_id.id,
#                                  'qty': int(abs(line.qty_done)) or 1.0
#                                  })]

        view_id = self.env['ir.ui.view'].search([('name', '=', 'report_product_tdzebrabarcode')])
        if not view_id.arch:
            raise Warning('Someone has deleted the reference '
                          'view of report, Please Update the module!')
        return {
                'product_get_ids': product_get_ids,
                'pricelist_id': self.env.user.pricelist_id and self.env.user.pricelist_id.id or False
                }

    product_get_ids = fields.One2many(
          'tdzebrabarcode.product.lines',
          'wizard_id',
          string='Products'
          )
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')

    @api.onchange('product_get_ids')
    def onchange_product_get_ids(self):
        return {'domain': {'pricelist_id': [('id', '=', self.env.user.pricelist_id.id)]}}

    def print_report(self):
        batch_no = self.env['ir.sequence'].next_by_code('batch.history.report')
        history = []
        for line in self.product_get_ids:
            history.append({
              'batch_no': batch_no,
              'product_id': line.product_id.id,
              'qty': line.qty,
              'print_date': fields.Datetime.now(),
            })
        self.env['batch.history'].create(history)
        if not self.env.user.has_group('td_zebra_barcode_labels.group_zbarcode_labels'):
            raise Warning(_("You have not enough rights to access this "
                            "document.\n Please contact administrator to access "
                            "this document."))
        if not self.product_get_ids:
            raise Warning(_(""" There is no product lines to print."""))
        config_rec = self.env['tdzebrabarcode.configuration'].search([], limit=1)
        if not config_rec:
            raise Warning(_(" Please configure barcode data from "
                            "configuration menu"))
        datas = {
                 'ids': [x.product_id.id for x in self.product_get_ids],
                 'form': {
                    'barcode_height': config_rec.barcode_height or 300,
                    'barcode_width': config_rec.barcode_width or 1500,
                    'barcode_type': config_rec.barcode_type or 'EAN13',
                    'barcode_field': config_rec.barcode_field or '',
                    'display_width': config_rec.display_width,
                    'display_height': config_rec.display_height,
                    'liquidation_size' : config_rec.liquidation_size,
                    'column_type': config_rec.column_type,
                    'humanreadable': config_rec.humanreadable,
                    'barcode_font_size': config_rec.barcode_font_size,
                    'product_name': config_rec.product_name,
                    'liquidation' : config_rec.liquidation,
                    'batch_no': config_rec.batch_no,
                    'batch_sequence': self.get_zebra_date(),
                    'batch_size': config_rec.batch_size,
                    'product_variant': config_rec.product_variant,
                    'price_display': config_rec.price_display,
                    'pricelist_id': self.pricelist_id.id,
                    'tax_included': config_rec.tax_included,
                    'tax_round': config_rec.tax_round,
                    'product_code': config_rec.product_code or '',
                    'currency_position': config_rec.currency_position or 'after',
                    'currency': config_rec.currency and config_rec.currency.id or '',
                    'symbol': config_rec.currency and config_rec.currency.symbol or '',
                    'product_ids': [{
                         'product_id': line.product_id.id,
                         'qty': line.qty,
                         'product_expiry': line.get_client_time(line.product_expiry),
                         } for line in self.product_get_ids]
                      }
                 }
        browse_pro = self.env['product.product'].browse([x.product_id.id for x in self.product_get_ids])
        for product in browse_pro:
            barcode_value = product[config_rec.barcode_field]
            if not barcode_value:
                raise Warning(_('Please define barcode for %s!' % (product['name'])))
            try:
                barcode.createBarcodeDrawing(
                            config_rec.barcode_type,
                            value=barcode_value,
                            format='png',
                            width=int(config_rec.barcode_height),
                            height=int(config_rec.barcode_width),
                            humanReadable=config_rec.humanreadable or False
                            )
            except:
                raise Warning('Select valid barcode type according barcode '
                              'field value or check value in field!')
        action = self.env.ref('td_zebra_barcode_labels.td_zebra_barcode_labels_11cm').report_action(self, data=datas)
        action.update({'close_on_report_download': True})
        return action

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
