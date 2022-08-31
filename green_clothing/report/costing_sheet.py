# -*- coding:utf-8 -*-

from odoo import api, models, _


class CostingSheetView(models.AbstractModel):
    _name = 'report.green_clothing.costing_sheet_view'
    _description = "Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['costing.sheet.green.clothing'].browse(docids)

        # Getting current company
        company = self.env.company

        # Getting current user
        user = self.env.user

        def get_date_format(date):
            if date:
                return date.strftime('%d-%b-%Y')

        return {
            'doc_ids': docids,
            'doc_model': 'costing.sheet.woven',
            'docs': docs,
            'company': company,
            'user': user,
            'get_date_format': get_date_format,
        }
