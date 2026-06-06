# -*- coding: utf-8 -*-
"""
stock_picking.py
Lắng nghe sự kiện trên các giao dịch kho để kích hoạt Event-driven RFQ.

Các điểm lắng nghe:
  1. stock.picking.button_validate()   → Xử lý phiếu xuất kho (DO)
  2. sale.order.action_confirm()       → Xác nhận đơn bán hàng
  3. pos.order.action_pos_order_paid() → Thanh toán đơn POS
"""

import logging
from odoo import models

_logger = logging.getLogger(__name__)


# =============================================================================
# 1. TRIGGER TỪ STOCK PICKING (Phiếu xuất kho)
# =============================================================================

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        """
        Override xác nhận phiếu kho. Thực hiện super() TRƯỚC,
        sau đó trigger kiểm tra tồn kho của các sản phẩm storable.
        """
        result = super().button_validate()

        # Tối ưu: Lọc trực tiếp các move xuất kho và sản phẩm là hàng lưu kho ('product')
        outgoing_moves = self.mapped('move_ids').filtered(
            lambda m: m.picking_id.picking_type_code == 'outgoing' and m.product_id.type == 'consu'
        )
        outgoing_product_ids = outgoing_moves.mapped('product_id').ids

        if outgoing_product_ids:
            # Lấy danh sách tên phiếu (VD: WH/OUT/00015)
            source_names = ", ".join(self.mapped('name'))
            
            _logger.info(
                "Stock Picking validated: trigger RFQ check cho %d sản phẩm từ %s",
                len(outgoing_product_ids),
                source_names
            )
            self.env['stock.warehouse.orderpoint']._trigger_instant_rfq_for_products(
                list(outgoing_product_ids),
                trigger_source=source_names
            )

        return result


# =============================================================================
# 2. TRIGGER TỪ SALE ORDER (Đơn bán hàng)
# =============================================================================

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """
        Override xác nhận đơn bán hàng.
        Khi Sales Order được confirm, nhu cầu xuất kho phát sinh →
        kiểm tra ngay tồn kho khả dụng và tạo RFQ nếu cần.
        """
        _logger.info("DEBUG action_confirm called on sale.order IDs: %s", self.ids)
        
        result = super().action_confirm()

        product_ids = self.mapped('order_line.product_id').filtered(
            lambda p: p.type == 'consu'
        ).ids

        if product_ids:
            # Lấy danh sách mã SO (VD: SO0019)
            source_names = ", ".join(self.mapped('name'))
            
            _logger.info(
                "Sale Order confirmed: trigger RFQ check cho %d sản phẩm từ %s",
                len(product_ids),
                source_names
            )
            self.env['stock.warehouse.orderpoint']._trigger_instant_rfq_for_products(
                list(product_ids),
                trigger_source=source_names
            )

        return result


# =============================================================================
# 3. TRIGGER TỪ POS ORDER (Đơn hàng POS)
# =============================================================================

class PosOrder(models.Model):
    _inherit = 'pos.order'

    def action_pos_order_paid(self):
        """
        Override sự kiện thanh toán POS.
        Đơn POS paid đồng nghĩa hàng được xuất → kiểm tra tồn kho.
        """
        result = super().action_pos_order_paid()

        product_ids = self.mapped('lines.product_id').filtered(
            lambda p: p.type == 'consu'
        ).ids

        if product_ids:
            # Lấy danh sách mã đơn POS
            source_names = ", ".join(self.mapped('name'))
            
            _logger.info(
                "POS Order paid: trigger RFQ check cho %d sản phẩm từ %s",
                len(product_ids),
                source_names
            )
            self.env['stock.warehouse.orderpoint']._trigger_instant_rfq_for_products(
                list(product_ids),
                trigger_source=source_names
            )

        return result