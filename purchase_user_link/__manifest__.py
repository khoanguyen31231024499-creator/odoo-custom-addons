# -*- coding: utf-8 -*-
{
    'name': 'Purchase User Constraint (Procure_to_pay)',
    'version': '19.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Ensure Purchase users have linked Employee (FootGearH P2P constraint)',
    'author': 'FootGearH',
    'depends': ['base', 'hr', 'purchase', 'hr_employee_link'],
    'data': [
        'security/purchase_roles.xml',
        'security/ir.model.access.csv',
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
