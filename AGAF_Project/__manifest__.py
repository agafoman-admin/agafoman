{
    'name': "AGAF Project",
    'summary': """ AGAF Project""",
    'description': """AGAF Project""",
    'version': '16.0.0.0',
    'author': 'Pragmatic TechSoft Pvt Ltd.',
    'website': "www.pragtech.co.in",
    'category': 'Project',
    'depends': ['base','project','hr','sale','stock','AGAF_sales','fleet'],
    'data': [
        'data/groups.xml',
        'security/ir.model.access.csv',
        'data/rule.xml',
        'data/sequence.xml',
        'report/picking.xml',
        'report/mrs_template.xml',
        'report/mrs_report.xml',
        'report/mts_template.xml',
        'report/mts_report.xml',
        'report/consolidation_template.xml',
        'report/consolidate_report.xml',
        'views/project.xml',
        'views/mrs.xml',
        'views/mvs.xml',
        'views/reject_reason.xml',
        'views/stock_location.xml',
        'views/consolidate.xml',
        'views/purchase_order.xml',
        'views/task.xml',
    ],
 
    'installable': True,
    'auto_install': False,
}
