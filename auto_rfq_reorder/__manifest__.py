# -*- coding: utf-8 -*-
{
    'name': 'Auto RFQ from Reordering Rules',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Purchase',
    'summary': 'Tự động tạo RFQ nháp khi tồn kho xuống dưới mức tối thiểu',
    'description': """
Auto RFQ Reorder Module
=======================
Module tự động tạo Yêu cầu báo giá (RFQ) khi sản phẩm xuống dưới mức tồn kho tối thiểu.

Tính năng chính:
- Trigger tức thì khi xác nhận Sales/POS Order hoặc xuất kho
- Trigger theo lịch (cuối ngày)
- Gộp đơn thông minh theo nhà cung cấp
- Ưu tiên nhà cung cấp theo thứ tự và thời gian giao hàng
- Thông báo tự động cho Purchase Manager
    """,
    'author': 'Custom Development',
    'depends': [
        'stock',
        'purchase',
        'purchase_stock',
        'sale',
        'point_of_sale',
        'sale_stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/stock_warehouse_orderpoint_views.xml',
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
