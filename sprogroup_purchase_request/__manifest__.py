# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Purchase Request',
    'version': '14.0.3',
    'category': 'Purchases',
    'author':'tung.tung11191@gmail.com',
    'description': """
Use Purchase Request module for requesting product.
    """,
    'summary': 'Create purchase request',
    'website': 'http://sprogroup.com',
    'images': ['static/description/icon.jpg'],
    'data': [
        'security/sprogroup_purchase_request_security.xml',
        'security/ir.model.access.csv',
        'data/sprogroup_purchase_request_data.xml',
        'views/sprogroup_purchase_request_view.xml',
        'wizard/pur_reason_wizard.xml',
    ],
    'depends': ['mail', 'purchase', 'hr', 'purchase_stock'],
    'installable': True,
    'application': True,
    'sequence': 105,
    'license': 'AGPL-3',
}
