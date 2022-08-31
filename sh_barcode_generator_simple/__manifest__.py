# -*- coding: utf-8 -*-
{
    'name': 'Product Barcode Generator Simple',

    'author' : 'Softhealer Technologies',
    
    'website': 'https://www.softhealer.com',
    
    'version': '13.0.1.3',
    
    'category': 'Sales',
    
    'summary': 'Generates Barcode For Product.',
    
    'description': """Generates Barcode For Product.""",
    
    'depends': ['product'],
    
    'images': ['static/description/background.png', ],
        
    'data': [
        'security/barcode_generator_group.xml',
        'security/ir.model.access.csv',
        'views/product_barcode_generator.xml',
        'views/product_view.xml',
    ],
    
#     'external_dependencies' : {
#         "python" : ["barcode"],
#     },
             
    'installable': True,
    
    'auto_install': False,
    
    'application': True,
    
    "price": 12,
    
    "currency": "EUR"        
}
