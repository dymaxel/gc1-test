{
    'name': "GC Extended",
    'description': "GC Extended",
    'author': 'Dymaxel Systems',
    'category': 'Account',
    'version': '14.0.2',
    'application': True,
    'depends': ['account', 'purchase', 'sale', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/products_template_view.xml',
        'views/gc_workorder_view.xml',
    ],
}
