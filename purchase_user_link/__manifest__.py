# -*- coding: utf-8 -*-
{
    'name': 'PO Approval Fix',
    'version': '19.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Force PO approval when total amount is above 20,000,000 VND',
    'author': 'FootGearH',
    'license': 'LGPL-3',
    'depends': ['purchase'],
    'data': [
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
