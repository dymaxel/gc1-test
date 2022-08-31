from odoo import api, fields, models, _


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    green_clothing_name = fields.Char(string="Green Clothing Sequence", readonly=True, copy=False,)

    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        for lines in self.order_line:
            if lines.price_unit and lines.cs_price:
                if lines.price_unit != lines.cs_price:
                    mail_template = self.env.ref('green_clothing.approval_cs_price_email_template')
                    mail_template.send_mail(self.id, force_send=True)
                    self.write({'state': 'to approve'})
                    return res
        return res


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    cs_price = fields.Float(string="CS Price", readonly=True, copy=False,
                            groups='green_clothing.group_green_clothing_costing_sheet_cs_customization')

    last_purchase_price = fields.Float(string="Last Purchase Price", copy=False)
    last_vendor_name = fields.Many2one('res.partner', string="Last Vendor Name", copy=False)

    @api.onchange('product_id')
    def onchange_product_id(self):
        super(PurchaseOrderLine, self).onchange_product_id()
        for record in self:
            line_ids = []
            if record.product_id:
                purchase_lines = self.env['purchase.order.line'].sudo().search([('product_id', '=', record.product_id.id),
                                                                                ('order_id.state', 'in', ('purchase', 'done'))])
                if purchase_lines:
                    for lines in purchase_lines:
                        line_ids.append(lines.id)
            final_list = sorted(line_ids, key=int, reverse=True)
            if len(final_list) >= 1:
                last_price = self.env['purchase.order.line'].sudo().browse(final_list[0])
                record.last_vendor_name = last_price.order_id.partner_id
                record.last_purchase_price = last_price.price_unit
