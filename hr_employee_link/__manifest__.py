# -*- coding: utf-8 -*-
{
    'name': 'HR Employee Link (Procure_to_pay)',
    'version': '19.0.1.0.0',
    'category': 'HR',
    'summary': 'Allow linking Users to Employees (UI enhancement for FootGearH P2P)',
    'author': 'FootGearH',
    'depends': ['base', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_users_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
