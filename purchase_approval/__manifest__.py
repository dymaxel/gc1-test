# -*- coding: utf-8 -*-

{
    "name": "Purchase Approval",
    "version": "14.0.3",
    "category": "Purchase Management",
    "depends": ["purchase_stock"],
    "data": [
        'security/purchase_security.xml',
        'views/res_company_view.xml',
        'views/purchase_view.xml',
    ],
    "installable": True,
    "application": False,
}
