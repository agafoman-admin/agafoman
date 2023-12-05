{
    'name': "AGAF Purchase",
    'summary': """ AGAF Purchase""",
    'description': """AGAF Purchase""",
    'version': '16.0.0.0',
    'author': 'Pragmatic TechSoft Pvt Ltd.',
    'website': "www.pragtech.co.in",
    'category': 'Purchase',
    'depends': ['base', 'purchase','project'],


    'data': [
        'security/ir.model.access.csv',
        'views/menu.xml',
        'views/purchase_order.xml',
        'wizards/vendor_comparison.xml'
    ],
    'assets': {'web.assets_backend':
               ['AGAF_Purchase/static/src/js/action_manager.js',
                ],
                },
 
    'installable': True,
    'auto_install': False,
}
