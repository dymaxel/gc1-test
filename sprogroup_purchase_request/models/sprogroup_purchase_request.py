# -*- coding: utf-8 -*-
# Copyright 2016 Eficent Business and IT Consulting Services S.L.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, fields, models, SUPERUSER_ID
from odoo.tools.translate import _
from odoo.addons import decimal_precision as dp
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError

_STATES = [
    ('draft', 'Draft'),
    ('to_approve', 'To be approved'),
    ('leader_approved', 'HOD Approved'),
    ('manager_approved', 'Procurement Approved'),
    ('rejected', 'Rejected'),
    ('done', 'Done')
]


class SprogroupPurchaseRequest(models.Model):
    _name = 'sprogroup.purchase.request'
    _description = 'Sprogroup Purchase Request'
    _inherit = ['mail.thread']
    _rec_name = 'code'

    @api.model
    def _get_default_requested_by(self):
        return self.env['res.users'].browse(self.env.uid)

    @api.model
    def _get_default_name(self):
        return self.env['ir.sequence'].next_by_code('sprogroup.purchase.request')

    name = fields.Char('Request Name', size=32, required=True, track_visibility='onchange')
    code = fields.Char('Code', size=32, required=True, default=_get_default_name, track_visibility='onchange',
                       copy=False)
    date_start = fields.Date('Creation date', help="Date when the user initiated the request.",
                             default=fields.Date.context_today, track_visibility='onchange')
    end_start = fields.Date('Valid Until', default=fields.Date.context_today, track_visibility='onchange')

    rejected_date = fields.Datetime('Rejected Date', track_visibility='onchange')
    hod_approval_date = fields.Datetime('HOD Approval', track_visibility='onchange')
    procure_approval_date = fields.Datetime('Procurement Approval', track_visibility='onchange')
    requested_by = fields.Many2one('res.users', 'Requested by', required=True, track_visibility='onchange',
                                   default=_get_default_requested_by)
    assigned_to = fields.Many2one('res.users', 'Approver', required=True, track_visibility='onchange')
    description = fields.Text('Description')

    line_ids = fields.One2many('sprogroup.purchase.request.line', 'request_id', 'Products to Purchase', readonly=False,
                               copy=True, track_visibility='onchange')
    state = fields.Selection(selection=_STATES, string='Status', index=True, track_visibility='onchange', required=True,
                             copy=False, default='draft')
    po_count = fields.Integer(compute='_cumpute_po_count')

    rejected_note = fields.Text(string="Rejected Note")
    reason = fields.Char('Reason')
    segment = fields.Many2one('account.analytic.group', string='Segment')
    status = fields.Many2one('account.analytic.group', string='Dimension Status')
    region = fields.Many2one('account.analytic.group', string='Region')
    city = fields.Many2one('account.analytic.group', string='City')
    loading_points = fields.Many2one('account.analytic.group', string='Loading Points')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    trip_no = fields.Char(string='Trip Number')

    @api.constrains('fd_lines')
    def check_fd_lines(self):
        for pr in self:
            if len(pr.fd_lines) > 1:
                raise ValidationError(_('Please add only one financial dimension line.'))
            if not pr.fd_lines:
                raise ValidationError(_('Please add financial dimension'))

    def _cumpute_po_count(self):
        for request in self:
            request.po_count = self.env['purchase.order'].search_count(
                [('sprogroup_purchase_request_id', '=', request.id)])

    def action_open_purchase(self):
        return {
            'name': _('Purchase Order'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'purchase.order',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('sprogroup_purchase_request_id', 'in', self.ids)],
        }

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        if default is None:
            default = {}
        if not default.get('name'):
            default.update(name=_('%s (copy)') % (self.name))
        return super(SprogroupPurchaseRequest, self).copy(default)

    @api.onchange('state')
    def onchange_state(self):
        assigned_to = None
        if self.state:
            if (self.requested_by.id == False):
                self.assigned_to = None
                return

            employee = self.env['hr.employee'].search([('work_email', '=', self.requested_by.email)])
            if (len(employee) > 0):
                if (employee[0].department_id and employee[0].department_id.manager_id):
                    assigned_to = employee[0].department_id.manager_id.user_id

        self.assigned_to = assigned_to

    # @api.one
    @api.depends('requested_by')
    def _compute_department(self):
        if (self.requested_by.id == False):
            self.department_id = None
            return

        employee = self.env['hr.employee'].search([('work_email', '=', self.requested_by.email)])
        if (len(employee) > 0):
            self.department_id = employee[0].department_id.id
        else:
            self.department_id = None

    department_id = fields.Many2one('hr.department', string='Department', compute='_compute_department', store=True, )

    # @api.one
    @api.depends('state')
    def _compute_can_leader_approved(self):
        current_user_id = self.env.uid
        if (self.state == 'to_approve' and current_user_id == self.assigned_to.id):
            self.can_leader_approved = True
        else:
            self.can_leader_approved = False

    can_leader_approved = fields.Boolean(string='Can Leader approved', compute='_compute_can_leader_approved')

    # @api.one
    @api.depends('state')
    def _compute_can_manager_approved(self):
        current_user = self.env['res.users'].browse(self.env.uid)

        if (self.state == 'leader_approved' and current_user.has_group(
                'sprogroup_purchase_request.group_sprogroup_purchase_request_manager')):
            self.can_manager_approved = True
        else:
            self.can_manager_approved = False

    can_manager_approved = fields.Boolean(string='Can Manager approved', compute='_compute_can_manager_approved')

    # @api.one
    @api.depends('state')
    def _compute_can_reject(self):
        self.can_reject = (self.can_leader_approved or self.can_manager_approved)

    can_reject = fields.Boolean(string='Can reject', compute='_compute_can_reject')

    # @api.multi
    @api.depends('state')
    def _compute_is_editable(self):
        for rec in self:
            if rec.state in ('to_approve', 'leader_approved', 'manager_approved', 'rejected', 'done'):
                rec.is_editable = False
            else:
                rec.is_editable = True

    is_editable = fields.Boolean(string="Is editable",
                                 compute="_compute_is_editable",
                                 readonly=True)

    @api.model
    def create(self, vals):
        request = super(SprogroupPurchaseRequest, self).create(vals)
        if vals.get('assigned_to'):
            request.message_subscribe(partner_ids=[request.assigned_to.partner_id.id])
        return request

    # @api.multi
    def write(self, vals):
        res = super(SprogroupPurchaseRequest, self).write(vals)
        for request in self:
            if vals.get('assigned_to'):
                self.message_subscribe(partner_ids=[request.assigned_to.partner_id.id])
        return res

    def button_draft(self):
        self.mapped('line_ids').do_uncancel()
        return self.write({'state': 'draft'})

    def button_to_approve(self):
        return self.write({'state': 'to_approve'})

    def button_leader_approved(self):
        self.hod_approval_date = fields.Datetime.today()
        return self.write({'state': 'leader_approved'})

    def button_manager_approved(self):
        self.procure_approval_date = fields.Datetime.today()
        users = self.requested_by + self.assigned_to
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
        message = _("<p>Purchase Request has been approved <a href=%s >%s</a></p>") % (base_url, self.code)
        for user in users:
            mail_values = {
                'subject': _('Approval Required'),
                'body_html': message,
                'author_id': self.env.user.partner_id.id,
                'email_from': self.env.company.email or self.env.user.email_formatted,
                'email_to': user.email_formatted,
            }
            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.send()
        users.notify_info(message, title="Notification")
        return self.write({'state': 'manager_approved'})

    def button_rejected(self):
        view_id = self.env.ref('sprogroup_purchase_request.wizard_pur_reason_form').id
        return {
            'name': _('Reject Reason'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'create.pur.wizard.reason',
            'target': 'new',
            'res_id': False,
            'context': {
                'default_issue_id_fleet': self.id,
            },
            'views': [[view_id, 'form']],
        }

    def button_done(self):
        return self.write({'state': 'done'})

    def check_auto_reject(self):
        """When all lines are cancelled the purchase request should be
        auto-rejected."""
        for pr in self:
            if not pr.line_ids.filtered(lambda l: l.cancelled is False):
                pr.write({'state': 'rejected'})

    def make_purchase_quotation(self):
        view_id = self.env.ref('purchase.purchase_order_form')

        # vals = {
        #     'partner_id': partner.id,
        #     'picking_type_id': self.rule_id.picking_type_id.id,
        #     'company_id': self.company_id.id,
        #     'currency_id': partner.property_purchase_currency_id.id or self.env.user.company_id.currency_id.id,
        #     'dest_address_id': self.partner_dest_id.id,
        #     'origin': self.origin,
        #     'payment_term_id': partner.property_supplier_payment_term_id.id,
        #     'date_order': purchase_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
        #     'fiscal_position_id': fpos,
        #     'group_id': group
        # }

        order_line = []
        financial_line = []
        for line in self.line_ids:
            product = line.product_id
            fpos = self.env['account.fiscal.position']
            if self.env.uid == SUPERUSER_ID:
                company_id = self.env.user.company_id.id
                taxes_id = fpos.map_tax(
                    line.product_id.supplier_taxes_id.filtered(lambda r: r.company_id.id == company_id))
            else:
                taxes_id = fpos.map_tax(line.product_id.supplier_taxes_id)

            product_line = (0, 0, {'product_id': line.product_id.id,
                                   'state': 'draft',
                                   'sprogroup_purchase_request_line_id': line.id,
                                   'product_uom': line.product_id.uom_po_id.id,
                                   'price_unit': line.price_unit,
                                   'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                   # 'taxes_id' : ((6,0,[taxes_id.id])),
                                   'product_qty': line.product_qty,
                                   'name': line.name
                                   })
            order_line.append(product_line)

        # vals = {
        #     'order_line' : order_line
        # }
        #
        # po = self.env['purchase.order'].create(vals)

        return {
            'name': _('New Quotation'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'views': [(view_id.id, 'form')],
            'context': {
                'default_order_line': order_line,
                'default_fd_lines': financial_line,
                'default_sprogroup_purchase_request_id': self.id,
                'default_state': 'draft',
                'default_origin': self.code,
                'default_trip_no': self.trip_no,
            }
        }


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    sprogroup_purchase_request_id = fields.Many2one('sprogroup.purchase.request', 'Purchase Request ID',
                                                    track_visibility='onchange', readonly=True)
    trip_no = fields.Char(string='Trip Number')

    def _prepare_invoice(self):
        res = super(PurchaseOrder, self)._prepare_invoice()
        res['trip_no'] = self.trip_no
        return res

    @api.constrains('sprogroup_purchase_request_id')
    def _check_duplidate_vendor_rfq(self):
        if self.sprogroup_purchase_request_id and self.search_count(
                [('sprogroup_purchase_request_id', '=', self.sprogroup_purchase_request_id.id),
                 ('partner_id', '=', self.partner_id.id)]) > 1:
            raise UserError(_('You cannot create more than one RFQ for the same vendor.'))

    @api.model
    def create(self, vals):
        rec = super(PurchaseOrder, self).create(vals)
        if rec.sprogroup_purchase_request_id:
            purchase_message = _(
                "PO created from Purchase Request: <a href=# data-oe-model=sprogroup.purchase.request data-oe-id=%d>%s</a>.") % (
                                   rec.sprogroup_purchase_request_id.id,
                                   rec.sprogroup_purchase_request_id.name + '-' + rec.sprogroup_purchase_request_id.code)
            # rec.message_post(body=_('Statement %s - %s confirmed, items were created.') % (rec.sprogroup_purchase_request_id.name, rec.sprogroup_purchase_request_id.code,))
            rec.message_post(body=purchase_message)
            request_message = _("PO Created : <a href=# data-oe-model=purchase.order data-oe-id=%d>%s</a>") % (
                rec.id, rec.name)
            rec.sprogroup_purchase_request_id.message_post(body=request_message)

        return rec

    def button_confirm(self):
        for rec in self.filtered(lambda x: x.sprogroup_purchase_request_id):
            for line in rec.order_line:
                confirmed_lines = self.env['purchase.order.line'].search(
                    [('sprogroup_purchase_request_line_id', '=', line.sprogroup_purchase_request_line_id.id),
                     ('state', '=', 'purchase')])
                confirmed_qty = sum(confirmed_lines.mapped('product_qty'))
                if line.sprogroup_purchase_request_line_id.product_qty < (confirmed_qty + line.product_qty):
                    raise UserError(_('You have already confirmed the purchase order with PR Qty'))
        return super(PurchaseOrder, self).button_confirm()

    # def button_confirm(self):
    #     res = super(PurchaseOrder, self).button_confirm()
    #     for rec in self:
    #         if rec.sprogroup_purchase_request_id:
    #             po = self.env['purchase.order'].search([('sprogroup_purchase_request_id', '=', rec.sprogroup_purchase_request_id.id)])
    #             for purchase in po:
    #                 if purchase.id != rec.id:
    #                     purchase.state = 'cancel'
    #     return res


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    sprogroup_purchase_request_line_id = fields.Many2one('sprogroup.purchase.request.line', string="Request Line")

    @api.constrains('product_qty', 'product_uom')
    def _onchange_quantity(self):
        for line in self.filtered(lambda x: x.sprogroup_purchase_request_line_id):
            request_line = line.sprogroup_purchase_request_line_id
            confirmed_line = self.search(
                [('sprogroup_purchase_request_line_id', '=', request_line.id), ('state', '=', 'purchase')])
            remaining_qty = line.product_qty + sum(confirmed_line.mapped('product_qty'))
            if (request_line.product_qty < line.product_qty) or (request_line.product_qty < remaining_qty):
                raise ValidationError(_('RFQ quantity cannot be more than PR Qty'))

    @api.onchange('price_unit', 'product_qty')
    def onchange_price_unit_qty(self):
        if self.product_qty < 0:
            raise UserError(_('You cannot enter negative quantity.'))
        if self.price_unit < 0:
            raise UserError(_('You cannot enter negative price unit.'))


class SprogroupPurchaseRequestLine(models.Model):
    _name = "sprogroup.purchase.request.line"
    _description = "Sprogroup Purchase Request Line"
    _inherit = ['mail.thread']

    # @api.multi
    @api.depends('product_id', 'name', 'product_uom_id', 'product_qty',
                 'date_required', 'specifications')
    # @api.multi
    def _compute_supplier_id(self):
        for rec in self:
            if rec.product_id:
                if rec.product_id.seller_ids:
                    rec.supplier_id = rec.product_id.seller_ids[0].name

    product_id = fields.Many2one(
        'product.product', 'Product',
        domain=[('purchase_ok', '=', True)], required=True,
        track_visibility='onchange')
    name = fields.Char('Description', size=256,
                       track_visibility='onchange')
    product_uom_id = fields.Many2one('uom.uom', 'Product Unit of Measure',
                                     track_visibility='onchange')
    price_unit = fields.Float(string='Unit Price', required=True, digits='Product Price')
    product_qty = fields.Float(string='Quantity', track_visibility='onchange',
                               digits=dp.get_precision('Product Unit of Measure'))
    request_id = fields.Many2one('sprogroup.purchase.request',
                                 'Purchase Request',
                                 ondelete='cascade', readonly=True)
    company_id = fields.Many2one('res.company',
                                 string='Company',
                                 store=True, readonly=True)

    requested_by = fields.Many2one('res.users',
                                   related='request_id.requested_by',
                                   string='Requested by',
                                   store=True, readonly=True)
    assigned_to = fields.Many2one('res.users',
                                  related='request_id.assigned_to',
                                  string='Assigned to',
                                  store=True, readonly=True)
    date_start = fields.Date(related='request_id.date_start',
                             string='Request Date', readonly=True,
                             store=True)
    end_start = fields.Date(related='request_id.end_start',
                            string='End Date', readonly=True,
                            store=True)
    description = fields.Text(related='request_id.description',
                              string='Description', readonly=True,
                              store=True)
    date_required = fields.Date(string='Request Date', required=True,
                                track_visibility='onchange',
                                default=fields.Date.context_today)

    specifications = fields.Text(string='Specifications')
    request_state = fields.Selection(string='Request state',
                                     readonly=True,
                                     related='request_id.state',
                                     selection=_STATES,
                                     store=True)
    supplier_id = fields.Many2one('res.partner',
                                  string='Preferred supplier',
                                  compute="_compute_supplier_id")

    cancelled = fields.Boolean(
        string="Cancelled", readonly=True, default=False, copy=False)

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            name = self.product_id.name
            if self.product_id.code:
                name = '[%s] %s' % (name, self.product_id.code)
            if self.product_id.description_purchase:
                name += '\n' + self.product_id.description_purchase
            self.product_uom_id = self.product_id.uom_id.id
            self.product_qty = 1
            self.name = name

    @api.onchange('price_unit', 'product_qty')
    def onchange_price_unit_qty(self):
        if self.product_qty < 0:
            raise UserError(_('You cannot enter negative quantity.'))
        if self.price_unit < 0:
            raise UserError(_('You cannot enter negative price unit.'))

    # @api.multi
    def do_cancel(self):
        """Actions to perform when cancelling a purchase request line."""
        self.write({'cancelled': True})

    # @api.multi
    def do_uncancel(self):
        """Actions to perform when uncancelling a purchase request line."""
        self.write({'cancelled': False})

    def _compute_is_editable(self):
        for rec in self:
            if rec.request_id.state in ('to_approve', 'leader_approved', 'manager_approved', 'rejected',
                                        'done'):
                rec.is_editable = False
            else:
                rec.is_editable = True

    is_editable = fields.Boolean(string='Is editable',
                                 compute="_compute_is_editable",
                                 readonly=True)

    # @api.multi
    def write(self, vals):
        res = super(SprogroupPurchaseRequestLine, self).write(vals)
        if vals.get('cancelled'):
            requests = self.mapped('request_id')
            requests.check_auto_reject()
        return res


class StockPicking(models.Model):
    _inherit = "stock.picking"
    back_reason = fields.Char("Backorder Reason")
    return_remark = fields.Char("Return Remarks")


class StockBackorderConfirmationcustom(models.TransientModel):
    _inherit = 'stock.backorder.confirmation'

    reason = fields.Char("Reason", required=True)

    # def process(self):complete comment jawaid 20/4/2022
    #     pickings_to_do = self.env['stock.picking']
    #     pickings_not_to_do = self.env['stock.picking']
    #     for line in self.backorder_confirmation_line_ids:
    #         if line.to_backorder is True:
    #             pickings_to_do |= line.picking_id
    #         else:
    #             pickings_not_to_do |= line.picking_id
    #
    #     for pick_id in pickings_not_to_do:
    #         moves_to_log = {}
    #         for move in pick_id.move_lines:
    #             if float_compare(move.product_uom_qty,
    #                              move.quantity_done,
    #                              precision_rounding=move.product_uom.rounding) > 0:
    #                 moves_to_log[move] = (move.quantity_done, move.product_uom_qty)
    #         pick_id._log_less_quantities_than_expected(moves_to_log)
    #
    #     pickings_to_validate = self.env.context.get('button_validate_picking_ids')
    #     if pickings_to_validate:
    #         pickings_to_validate = self.env['stock.picking'].browse(pickings_to_validate).with_context(
    #             skip_backorder=True)
    #         pickings_to_validate.back_reason = self.reason
    #
    #         if pickings_not_to_do:
    #             pickings_to_validate = pickings_to_validate.with_context(
    #                 picking_ids_not_to_backorder=pickings_not_to_do.ids)
    #         return pickings_to_validate.button_validate()
    #     return True


class AccountMove(models.Model):
    _inherit = "account.move"

    trip_no = fields.Char(string='Trip Number')


class AccountPayment(models.Model):
    _inherit = "account.payment"

    trip_no = fields.Char(string='Trip Number')


class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    sprogroup_purchase_request_id = fields.Many2one('sprogroup.purchase.request', string='Purchase Request',
                                                    readonly=True)
    price_unit = fields.Integer(string='Unit Price', readonly=True)

    def _select(self):
        return super(PurchaseReport, self)._select() + ", po.sprogroup_purchase_request_id, l.price_unit"
