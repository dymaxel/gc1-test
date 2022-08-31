# -*- coding: utf-8 -*-
# Copyright (c) 2015-Present TidyWay Software Solution. (<https://tidyway.in/>)

from odoo import models, fields, api, _
from reportlab.graphics import barcode
from base64 import b64encode

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    life_days = fields.Integer('Product Life(Days)', copy=False)

class TRReportBarcodeLabels(models.AbstractModel):
    _name = 'report.td_zebra_barcode_labels.report_product_tdzebrabarcode'
    _description = 'report_product_tdzebrabarcode'

    @api.model
    def _get_report_values(self, docids, data=None):
        browse_record_list = []
        product_obj = self.env["product.product"]
        config = self.env.ref('td_zebra_barcode_labels.default_tdzebrabarcode_configuration')
        if not config:
            raise Warning(_(" Please configure barcode data from "
                            "configuration menu"))
        for rec in data['form']['product_ids']:
            for loop in range(0, int(rec['qty'])):
                browse_record_list.append((product_obj.browse(int(rec['product_id']))))
        return {
            'doc_ids': browse_record_list,
            'docs': docids,
            'product_name': data['form']['product_name'],
            'product_variant': data['form']['product_variant'],
            'price_display': data['form']['price_display'],
            'pricelist_id': data['form']['pricelist_id'],
            'product_code': data['form']['product_code'],
            'liquidation' : data['form']['liquidation'],
            'batch_no': data['form']['batch_no'],
            'is_company' : config.is_company,
            'get_barcode_string': self._get_barcode_string,
            'data': data,
            'get_lines': self._get_lines,
            'config': config
            }

#     @api.model
#     def _get_barcode_string(self, barcode_value, data):
#         barcode_str = barcode.createBarcodeDrawing(
#                             data['barcode_type'],
#                             value=barcode_value,
#                             format='png',
#                             width=int(data['barcode_height']),
#                             height=int(data['barcode_width']),
#                             humanReadable=data['humanreadable']
#                             )
#         encoded_string = b64encode(barcode_str.asString('png'))
#         barcode_str = "<img style='width:" + str(data['display_width']) + "px;height:" + str(data['display_height']) + "px'src='data:image/png;base64,{0}'>".format(encoded_string)
#         return barcode_str or ''

    @api.model
    def _get_barcode_string(self, barcode_value, data):
        barcode_str = barcode.createBarcodeDrawing(
                            data['barcode_type'],
                            value=barcode_value,
                            format='png',
                            width=int(data['barcode_height']),
                            height=int(data['barcode_width']),
                            humanReadable=data['humanreadable']
                            )
        encoded_string = b64encode(barcode_str.asString('png')).decode("utf-8")
        barcode_str = "<img style='width:" + str(data['display_width']) + "px;height:" + str(data['display_height']) + "px'src='data:image/png;base64,{0}'>".format(encoded_string)
        return barcode_str or ''


    @api.model
    def _get_symbol(self, product):
        symbol = ''
        if product.company_id:
            symbol = product.company_id.currency_id.symbol
        else:
            symbol = self.env.user.company_id.currency_id.symbol
        return symbol

    # @api.model
    # def _divided_blank_update(self, total_quantities):
    #     """
    #     Process
    #         -add a blank dictionaries
    #     """
    #     lists = []
    #     needs_to_add = total_quantities % 1
    #     if needs_to_add == 1:
    #         lists.append({'name_1': ' '})
    #         lists.append({'name_2': ' '})
    #     if needs_to_add == 2:
    #         lists.append({'name_2': ' '})
    #     return lists

    @api.model
    def _get_lines(self, form):
        prod_obj = self.env['product.product']
        result = []
        dict_data = {}
        data_append = False
        price_display = form.get('price_display')
        pricelist_id = self.env['product.pricelist'].browse(form.get('pricelist_id'))
        tax_included = form.get('tax_included')
        barcode_font_size = form.get('barcode_font_size')
        tax_round = form.get('tax_round')
        currency_position = form.get('currency_position', 'before') or 'before'
        total_value = 0
        column_type = int(form.get('column_type'))
        batch_sequence = form.get('batch_sequence')
        lines = form and form.get('product_ids', []) or []
        total_quantities = sum([int(x['qty']) for x in lines])
        user = self.env.user
        for l in lines:
            p = prod_obj.sudo().browse(l['product_id'])
            for c in range(0, int(l['qty'])):
                value = total_value % column_type
                data_append = False
                symbol = self._get_symbol(p)
                product_price = 0.0
                if price_display:
                    price_value = p.lst_price
                    if pricelist_id:
                        price_value = pricelist_id.get_product_price(p, 1.0, False)
                    product_price = price_value
                    tax_value = product_price * sum(p.taxes_id.mapped('amount')) / 100.0
                    if not tax_included and p.taxes_id:
                        price_value = price_value + tax_value
                    if tax_included and p.taxes_id:
                        tax_value = price_value * sum(p.taxes_id.mapped('amount'))/(100+p.taxes_id.amount)
                        product_price = product_price - tax_value
                    list_price = symbol+' '+str(price_value)
                    if currency_position == 'after':
                        list_price = 'RP ' + str(round(product_price, 2)) + ' + ST ' + str(round(tax_value, 2)) +' = '+ str(round(price_value, 2))+' '+symbol
                    dict_data.update({'list_price'+'_'+str(value): list_price})
                barcode_value = p[str(form['barcode_field'])]
                variant = ", ".join([v.name for v in p.product_template_attribute_value_ids])
                attribute_string = variant and "%s" % (variant) or ''
                dict_data.update({
                   'name'+'_'+str(value): p.name or '',
                   'code'+'_'+str(value): barcode_value,
                   'variants'+'_'+str(value): attribute_string or '',
                   'default_code'+'_'+str(value): p.default_code or '',
                   'barcode_font_size':  barcode_font_size,
                   'liquidation'+'_'+str(value): 'Best Before : '+ l['product_expiry'] or '',
                   'batch_no'+'_'+str(value): 'Batch No : '+ batch_sequence or '',
                  })
                total_value += 1
                if total_value % column_type == 0:
                    result.append(dict_data)
                    data_append = True
                    dict_data = {}
        if not data_append:
            result.append(dict_data)
        return [x for x in result if x]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
