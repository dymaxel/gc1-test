{
    "name": "Generic Security Restriction",
    "version": "14.0.1",
    "author": "Center of Research and Development",
    "website": "https://crnd.pro",
    "license": 'OPL-1',
    "summary": """
        Hide Menu / Restrict Menu /
        Hide Field On The View / Make Field Readonly /
        Hide Stat Button / Change Parameters of M2o Fields:
        ('no_open', 'no_create', 'no_quick_create', 'no_create_edit')
    """,
    'category': 'Technical Settings',
    'depends': [
        'base',
        'web',
        'sale',
        'account',
        'purchase',
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/ir_ui_menu_view.xml',
        'views/res_groups_view.xml',
        'views/res_users_view.xml',
        'views/ir_model_view.xml',
        'views/all_model_views.xml',
    ],
    'demo': [],
    'images': ['static/description/banner.gif'],
    'installable': True,
    'auto_install': False,
    'application': False,
    'price': 15.0,
    'currency': 'EUR',
}
