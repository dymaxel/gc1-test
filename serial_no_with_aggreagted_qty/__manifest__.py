{
    'name': 'Serial number in Sale Order, Purchase Order, Invoice, Picking',
    'version': '14.0.0.0',
    'author': 'Jawaid Iqbal',
    'summary': '',
    'description': """""",
    'category': 'Base',
    'website': 'https://dymaxel.com/',
    'license': 'AGPL-3',

    'depends': ['sale_management', 'account', 'purchase'],

    'data': [
        'views/sale_order_views.xml',
        'report/sale_order_report.xml',
    ],

    'qweb': [],
    'images': ['static/description/Banner.png'],

    'installable': True,
    'application': True,
    'auto_install': False,
}