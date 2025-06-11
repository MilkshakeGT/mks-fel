{
    'name': 'FEL Guatemala (Digifact)',
    'version': '1.0',
    'summary': 'Integración con Digifact FEL para Guatemala',
    'depends': ['account','point_of_sale'],
    'data': [
         #'views/account_move_views.xml',
         'views/account_move_views_.xml',
         #'views/report_invoice_fel_v17.xml',
         'views/report_invoice_fel_v18.xml',
         #'views/report_invoice_fel_pos.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
