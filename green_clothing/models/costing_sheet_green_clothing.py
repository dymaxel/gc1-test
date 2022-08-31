from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class CostingSheetGreenClothing(models.Model):
    _name = "costing.sheet.green.clothing"
    _description = "Costing Sheet Green Clothing"
    _rec_name = "item_id"

    name = fields.Char(string="Sequence", readonly=True, required=True, copy=False, default='New')

    item_id = fields.Many2one('product.template', string="Item & Style")
    customer_id = fields.Many2one("res.partner", "Buyer/Customer", required=True)

    order_qty = fields.Float(string="Order Qty")
    season = fields.Char(string="Season")
    size_range = fields.Char(string="Size Range")
    wash_color = fields.Char(string="Wash Color")
    fabric_details = fields.Char(string="Fabric Details")
    pocketing_details = fields.Char(string="Pocketing details")
    fabric_qty = fields.Char(string="Fabric Qty")
    commission = fields.Float(string="Commission %")
    profit = fields.Float(string="Profit %")
    rejection = fields.Float(string="Rejection %")
    exchange_rate = fields.Float(string="Exchange Rate")

    sub_total = fields.Float(string="Sub Total")
    trim_details_total = fields.Float(string="Trims Total", related='trims_total')
    fabric_details_total = fields.Float(string="Fabric Total", related='fabric_total')
    parameters_total = fields.Float(string="Parameters Total")
    rejection_total = fields.Float(string="Rejection Total")
    sheet_total = fields.Float(string="Total")
    profit_total = fields.Float(string="Profit Total")
    grand_total = fields.Float(string="Grand Total")
    c_total = fields.Float(string="C %")
    price_per_piece = fields.Float(string="Price Per Piece")
    purchase_order_count = fields.Integer(string="PO Count", compute="get_total_po_no")
    trims_total = fields.Float(string="Sub Total")
    fabric_total = fields.Float(string="Sub Total")

    order_date = fields.Date(string="Order Date")
    shipment_date = fields.Date(string="Shipment Date")
    customer_po_number = fields.Char(string="Customer PO Number")

    state = fields.Selection([('draft', 'Draft'),
                              ('approval', 'To Be Approval'),
                              ('approve', 'Approved')], string='State', default="draft")

    cs_parameter_line_ids = fields.One2many('costing.sheet.parameter.lines', 'cs_parameter_green_clothing_id',
                                            string="Costing Sheet Lines")
    cs_trims_line_ids = fields.One2many('costing.sheet.trims.lines', 'cs_trims_green_clothing_id',
                                        string="Costing Sheet Lines")
    cs_fabric_line_ids = fields.One2many('costing.sheet.fabric.lines', 'cs_fabric_total_id',
                                         string="Costing Sheet Fabric Lines")
    costing_sheet_green_clothing_lines = fields.Many2one('costing.parameters.green.clothing', string="id")

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env["ir.sequence"].next_by_code("green_clothing.cs_green_clothing") or _('New')
        self.env['account.analytic.account'].create({'name': vals['name'], 'partner_id': vals['customer_id']})
        return super(CostingSheetGreenClothing, self).create(vals)

    def write(self, vals):
        if any(state == 'approve' for state in set(self.mapped('state'))):
            raise UserError(_("You can't edit in approved state"))
        else:
            return super().write(vals)

    @api.onchange('item_id')
    def create_lines(self):
        self.cs_parameter_line_ids = [(5, 0, 0)]
        grin = self.env['costing.parameters.green.clothing'].search([])
        list = []
        for parameter_line in grin:
            list.append((0, 0, {
                'costing_par': parameter_line.id,
            }))
        self.cs_parameter_line_ids = list

    @api.onchange('cs_parameter_line_ids', 'rejection', 'profit', 'commission', 'exchange_rate', 'trim_details_total',
                  'fabric_details_total')
    def get_total_price(self):
        total = 0.0
        for rec in self.cs_parameter_line_ids:
            if rec:
                total += rec.total
            self.parameters_total = total

            sub_total = self.parameters_total + self.trim_details_total + self.fabric_details_total
            self.sub_total = sub_total

            rejection_value = (sub_total * self.rejection) / 100
            self.rejection_total = rejection_value
            s_t_value = rejection_value + sub_total
            self.sheet_total = s_t_value

            profit_value = (s_t_value / 100) * self.profit
            self.profit_total = profit_value
            grand_value = profit_value + s_t_value
            self.grand_total = grand_value

            c_t_total = (grand_value / 100) * self.commission
            self.c_total = c_t_total

            g_c_total = grand_value + c_t_total
            if self.exchange_rate > 0:
                self.price_per_piece = g_c_total / self.exchange_rate

    @api.onchange('cs_trims_line_ids')
    def get_trims_price_total(self):
        total = 0.0
        for rec in self.cs_trims_line_ids:
            if rec:
                total += rec.unit_price
            self.trims_total = total

    @api.onchange('cs_fabric_line_ids')
    def get_fabric_price_total(self):
        total = 0.0
        for rec in self.cs_fabric_line_ids:
            if rec:
                total += rec.total
            self.fabric_total = total

    def submit_btn(self):
        self.state = 'approval'

    def approve_btn(self):
        self.state = 'approve'

    def create_quotation_btn(self):
        for rec in self:
            green_clothing_purchase_order = self.env['purchase.order'].create({
                'green_clothing_name': self.name,
                'partner_id': self.customer_id.id,
            })
            purchase_lines_trims = []
            for lines in rec.cs_trims_line_ids:
                purchase_lines_trims.append((0, 0, {
                    'name': lines.trims.name,
                    # 'product_template_id': lines.trims.product_tmpl_id.id,
                    'product_id': lines.trims.id,
                    'product_qty': lines.po_quantity,
                    'product_uom': lines.trims.uom_id.id,
                    'cs_price': lines.unit_price,
                    'price_unit': lines.unit_price,
                    'date_planned': fields.Datetime.now(),
                    'order_id': green_clothing_purchase_order.id,
                }))
            green_clothing_purchase_order.write({'order_line': purchase_lines_trims})

            purchase_lines_fabric = []
            for lines in rec.cs_fabric_line_ids:
                purchase_lines_fabric.append((0, 0, {
                    'name': lines.fabric_items.name,
                    # 'product_template_id': lines.fabric_items.product_tmpl_id.id,
                    'product_id': lines.fabric_items.id,
                    'product_qty': lines.po_quantity,
                    'product_uom': lines.fabric_items.uom_id.id,
                    'cs_price': lines.price,
                    'price_unit': lines.price,
                    'date_planned': fields.Datetime.now(),
                    'price_subtotal': lines.total,
                    'order_id': green_clothing_purchase_order.id,
                }))
            green_clothing_purchase_order.write({'order_line': purchase_lines_fabric})

    def action_purchase_order(self):
        self.ensure_one()
        return {
            'name': _('Purchase Order'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'purchase.order',
            'context': {'create': False},
            'domain': [('green_clothing_name', '=', self.name)],
        }

    def get_total_po_no(self):
        for rec in self:
            rec.purchase_order_count = self.env['purchase.order'].search_count(
                [('green_clothing_name', '=', self.name)])


class CostingSheetParameterLines(models.Model):
    _name = "costing.sheet.parameter.lines"
    _description = "Costing Sheet Parameter Lines"

    costing_par = fields.Many2one('costing.parameters.green.clothing', string="Costing Parameter")
    consumption = fields.Float(string="Consumption")
    price = fields.Float(string="Price")
    total = fields.Float(string="Total")

    cs_parameter_green_clothing_id = fields.Many2one('costing.sheet.green.clothing', string="id")

    @api.onchange('consumption', 'price')
    def _calculate_values(self):
        if self.consumption and self.price:
            self.total = self.consumption * self.price


class CostingSheetTrimsLines(models.Model):
    _name = "costing.sheet.trims.lines"
    _description = "Costing Sheet Trims Lines"

    trims = fields.Many2one('product.product', string="Trims")
    po_quantity = fields.Float(string="PO Quantity",
                               groups='green_clothing.group_green_clothing_costing_sheet_cs_customization')
    consumption = fields.Float(string="Consumption",
                               groups='green_clothing.group_green_clothing_costing_sheet_cs_customization')
    unit_price = fields.Float(string="Unit Price")

    cs_trims_green_clothing_id = fields.Many2one('costing.sheet.green.clothing', string="id")

    @api.onchange('consumption', 'cs_trims_green_clothing_id')
    def _calculate_po_quantity_trims(self):
        if self.consumption and self.cs_trims_green_clothing_id:
            required = self.consumption * self.cs_trims_green_clothing_id.order_qty
            rejection_qty = (required / 100) * self.cs_trims_green_clothing_id.rejection
            self.po_quantity = required + rejection_qty


class CostingSheetFabricLines(models.Model):
    _name = "costing.sheet.fabric.lines"
    _description = "Costing Sheet Fabric Lines"

    fabric_items = fields.Many2one('product.product', string="Fabric Items")
    po_quantity = fields.Float(string="PO Quantity",
                               groups='green_clothing.group_green_clothing_costing_sheet_cs_customization')
    consumption = fields.Float(string="Consumption")
    price = fields.Float(string="Price")
    total = fields.Float(string="Total")

    cs_fabric_total_id = fields.Many2one('costing.sheet.green.clothing', string="id")

    @api.onchange('consumption', 'cs_fabric_total_id')
    def _calculate_po_quantity_fabric(self):
        if self.consumption and self.cs_fabric_total_id:
            required = self.consumption * self.cs_fabric_total_id.order_qty
            rejection_qty = (required / 100) * self.cs_fabric_total_id.rejection
            self.po_quantity = required + rejection_qty

    @api.onchange('fabric_items')
    def _get_consumption(self):
        if self.fabric_items:
            consumption = self.env["product.consumption.line"].search([('product_name', '=', self.fabric_items.id)],
                                                                      limit=1)
            self.consumption = consumption.consumption
            self.price = self.fabric_items.list_price

    @api.onchange('consumption', 'price')
    def _calculate_values(self):
        if self.consumption and self.price:
            self.total = self.consumption * self.price
