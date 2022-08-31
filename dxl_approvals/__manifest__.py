# -*- coding: utf-8 -*-

{
    "name": "DXL Approvals",
    "version": "14.0.3",
    "category": "Purchase Management",
    "depends": ["purchase_stock", "sale", "account"],
    "data": [
        'security/purchase_security.xml',
        'views/res_company_view.xml',
        'views/purchase_view.xml',
        'views/sale_order_view.xml',
        'views/account_payment_view.xml',
    ],
    "installable": True,
    "application": False,
}
