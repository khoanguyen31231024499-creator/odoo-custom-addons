# -*- coding: utf-8 -*-
"""
stock_warehouse_orderpoint.py

Auto RFQ from Reordering Rules.

Bản chỉnh cho môi trường Odoo hiện hành:
- Đã FIX lỗi cộng dồn số lượng sai logic khi gộp đơn RFQ.
- Đã FIX lỗi mất dấu Source/Origin khi gộp nhiều luồng sự kiện vào chung 1 RFQ.
- Cron đọc đúng qty_forecast/qty_on_hand từ Reordering Rule.
- Không dùng field qty_multiple nếu Odoo không có.
- Bỏ qua notification Purchase Manager để tránh lỗi res.groups.users.
"""

import logging
import math
from datetime import timedelta

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    trigger_mode_custom = fields.Selection(
        selection=[
            ('auto_instant', 'Tức thì (Event-driven)'),
            ('scheduled', 'Theo lịch (Scheduled)'),
        ],
        string='Chế độ kích hoạt',
        default='scheduled',
        required=True,
        help=(
            "auto_instant: Hệ thống kiểm tra và tạo RFQ ngay khi có giao dịch "
            "làm thay đổi tồn kho như xác nhận Sales/POS hoặc xuất kho.\n"
            "scheduled: Chỉ chạy theo tác vụ định kỳ."
        ),
    )

    def _get_qty_available_custom(self):
        self.ensure_one()

        # Qty on hand thực tế
        qty_on_hand = self.product_id.with_context(
            location=self.location_id.id
        ).qty_available

        # Tính outgoing: stock moves đã confirmed, chưa done
        outgoing_moves = self.env['stock.move'].search([
            ('product_id', '=', self.product_id.id),
            ('location_id', 'child_of', self.location_id.id),
            ('state', 'not in', ['done', 'cancel']),
            ('picking_id.picking_type_id.code', '=', 'outgoing'),
        ])
        qty_outgoing = sum(
            m.product_uom_qty for m in outgoing_moves
        )

        qty_available = qty_on_hand - qty_outgoing

        _logger.info(
            "AUTO RFQ DEBUG | Product=%s | OnHand=%s | Outgoing=%s | Available=%s | Min=%s",
            self.product_id.display_name,
            qty_on_hand,
            qty_outgoing,
            qty_available,
            self.product_min_qty,
        )
        _logger.info(
            "DEBUG moves: %s",
            [(m.id, m.state, m.product_uom_qty) for m in outgoing_moves]
        ) 
        return qty_available

    def _get_best_supplier(self):
        self.ensure_one()

        suppliers = self.env['product.supplierinfo'].search([
            ('product_tmpl_id', '=', self.product_id.product_tmpl_id.id),
            ('partner_id.active', '=', True),
        ], order='sequence asc, delay asc', limit=1)

        if not suppliers:
            _logger.warning(
                "AUTO RFQ SKIP | Product=%s | Không tìm thấy vendor/supplierinfo.",
                self.product_id.display_name,
            )
            return False

        _logger.info(
            "AUTO RFQ DEBUG | Product=%s | Supplier=%s | sequence=%s | delay=%s",
            self.product_id.display_name,
            suppliers.partner_id.display_name,
            suppliers.sequence,
            suppliers.delay,
        )
        return suppliers.partner_id

    def _compute_order_qty(self, qty_available):
        self.ensure_one()

        qty_order = self.product_max_qty - qty_available
        if qty_order <= 0:
            return 0.0

        qty_multiple = getattr(self, 'qty_multiple', 0.0)
        if qty_multiple and qty_multiple > 0:
            qty_order = math.ceil(qty_order / qty_multiple) * qty_multiple

        return qty_order

    def _find_or_create_draft_rfq(self, supplier_partner, trigger_source=''):
        self.ensure_one()

        PurchaseOrder = self.env['purchase.order'].sudo()

        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('warehouse_id', '=', self.warehouse_id.id),
            ('warehouse_id.company_id', '=', self.company_id.id),
        ], limit=1)

        domain = [
            ('partner_id', '=', supplier_partner.id),
            ('state', '=', 'draft'),
            ('company_id', '=', self.company_id.id),
        ]

        if picking_type:
            domain.append(('picking_type_id', '=', picking_type.id))

        existing_rfq = PurchaseOrder.search(domain, limit=1, order='id desc')

        if existing_rfq:
            _logger.info(
                "AUTO RFQ | Gộp vào RFQ hiện có: %s | Supplier=%s",
                existing_rfq.name,
                supplier_partner.display_name,
            )
            
            # --- BẮT ĐẦU FIX LỖI MẤT DẤU ORIGIN ---
            if trigger_source:
                current_origin = existing_rfq.origin or ''
                if trigger_source not in current_origin:
                    existing_rfq.origin = f"{current_origin}, {trigger_source}" if current_origin else trigger_source
                
                # Cập nhật thêm trường custom nếu có khai báo
                if 'origin_trigger_custom' in PurchaseOrder._fields:
                    current_custom = existing_rfq.origin_trigger_custom or ''
                    if trigger_source not in current_custom:
                        existing_rfq.origin_trigger_custom = f"{current_custom}, {trigger_source}" if current_custom else trigger_source
            # --- KẾT THÚC FIX LỖI ---

            return existing_rfq, False

        # Nếu không có RFQ nháp, tiến hành tạo mới
        rfq_vals = {
            'partner_id': supplier_partner.id,
            'company_id': self.company_id.id,
            'currency_id': (
                supplier_partner.property_purchase_currency_id.id
                or self.company_id.currency_id.id
            ),
            'date_order': fields.Datetime.now(),
        }

        if trigger_source:
            rfq_vals['origin'] = trigger_source

        if 'origin_trigger_custom' in PurchaseOrder._fields:
            rfq_vals['origin_trigger_custom'] = trigger_source or _('Auto-generated by Reordering Rule')

        if 'is_auto_generated' in PurchaseOrder._fields:
            rfq_vals['is_auto_generated'] = True

        if picking_type:
            rfq_vals['picking_type_id'] = picking_type.id

        rfq = PurchaseOrder.create(rfq_vals)

        _logger.info(
            "AUTO RFQ | Tạo RFQ mới: %s | Supplier=%s",
            rfq.name,
            supplier_partner.display_name,
        )
        return rfq, True

    def _add_or_update_rfq_line(self, rfq, qty_order):
        self.ensure_one()

        PurchaseOrderLine = self.env['purchase.order.line'].sudo()

        existing_line = PurchaseOrderLine.search([
            ('order_id', '=', rfq.id),
            ('product_id', '=', self.product_id.id),
        ], limit=1)

        if existing_line:
            # --- BẮT ĐẦU FIX LỖI CỘNG DỒN ---
            if qty_order > existing_line.product_qty:
                _logger.info(
                    "AUTO RFQ | Cập nhật dòng RFQ=%s | Product=%s | Từ %s lên %s",
                    rfq.name,
                    self.product_id.display_name,
                    existing_line.product_qty,
                    qty_order,
                )
                existing_line.write({'product_qty': qty_order})
            else:
                _logger.info(
                    "AUTO RFQ | Bỏ qua cập nhật RFQ=%s | Product=%s | Nhu cầu %s đã được đáp ứng bởi %s trong đơn nháp",
                    rfq.name,
                    self.product_id.display_name,
                    qty_order,
                    existing_line.product_qty,
                )
            # --- KẾT THÚC FIX LỖI ---
            return existing_line

        supplier_info = self.env['product.supplierinfo'].search([
            ('product_tmpl_id', '=', self.product_id.product_tmpl_id.id),
            ('partner_id', '=', rfq.partner_id.id),
        ], order='sequence asc, delay asc', limit=1)

        price_unit = supplier_info.price if supplier_info else 0.0
        lead_time = supplier_info.delay if supplier_info else 0
        date_planned = fields.Datetime.now() + timedelta(days=lead_time or 0)

        line_vals = {
            'order_id': rfq.id,
            'product_id': self.product_id.id,
            'product_qty': qty_order,
            'price_unit': price_unit,
            'date_planned': date_planned,
            'name': self.product_id.display_name,
        }

        # Tương thích nếu Odoo của máy có tên field UoM khác.
        if 'product_uom' in PurchaseOrderLine._fields and self.product_uom:
            line_vals['product_uom'] = self.product_uom.id
        elif 'product_uom_id' in PurchaseOrderLine._fields and self.product_uom:
            line_vals['product_uom_id'] = self.product_uom.id

        new_line = PurchaseOrderLine.create(line_vals)

        _logger.info(
            "AUTO RFQ | Thêm dòng mới | RFQ=%s | Product=%s | Qty=%s | Price=%s",
            rfq.name,
            self.product_id.display_name,
            qty_order,
            price_unit,
        )
        return new_line

    def _notify_purchase_manager(self, rfq, is_new):
        """
        Tạm bỏ notification để tránh crash cron trên Odoo version hiện tại.
        """
        self.ensure_one()

        _logger.info(
            "AUTO RFQ NOTIFY SKIP | RFQ=%s | is_new=%s | Product=%s",
            rfq.name,
            is_new,
            self.product_id.display_name,
        )
        return True

    def _process_auto_rfq(self, trigger_source=''):
        self.ensure_one()

        qty_available = self._get_qty_available_custom()

        if qty_available > self.product_min_qty:
            _logger.info(
                "AUTO RFQ SKIP | Product=%s | Available=%s > Min=%s",
                self.product_id.display_name,
                qty_available,
                self.product_min_qty,
            )
            return False

        _logger.info(
            "AUTO RFQ | DƯỚI MỨC TỒN KHO | Product=%s | Available=%s <= Min=%s",
            self.product_id.display_name,
            qty_available,
            self.product_min_qty,
        )

        supplier = self._get_best_supplier()
        if not supplier:
            return False

        qty_order = self._compute_order_qty(qty_available)
        if qty_order <= 0:
            _logger.info(
                "AUTO RFQ SKIP | Product=%s | Qty to order=%s <= 0 | Max=%s | Available=%s",
                self.product_id.display_name,
                qty_order,
                self.product_max_qty,
                qty_available,
            )
            return False

        _logger.info(
            "AUTO RFQ | Product=%s | Qty to order=%s",
            self.product_id.display_name,
            qty_order,
        )

        # Truyền trigger_source vào hàm tạo/gộp RFQ
        rfq, is_new = self._find_or_create_draft_rfq(supplier, trigger_source=trigger_source)
        self._add_or_update_rfq_line(rfq, qty_order)
        self._notify_purchase_manager(rfq, is_new)

        return rfq

    @api.model
    def _run_scheduled_rfq(self):
        _logger.info("=== BẮT ĐẦU: Scheduled RFQ Check ===")

        orderpoints = self.search([
            ('trigger_mode_custom', '=', 'scheduled'),
            ('active', '=', True),
        ])

        _logger.info("Tìm thấy %d orderpoint cần kiểm tra.", len(orderpoints))

        processed_count = 0
        error_count = 0

        for op in orderpoints:
            try:
                with self.env.cr.savepoint():
                    # Đánh dấu nguồn là Cron Job
                    result = op._process_auto_rfq(trigger_source='Scheduled Cron')
                    if result:
                        processed_count += 1
            except Exception as e:
                _logger.exception(
                    "AUTO RFQ ERROR | OP=%s | Product=%s | Error=%s",
                    op.id,
                    op.product_id.display_name,
                    str(e),
                )
                error_count += 1

        _logger.info(
            "=== KẾT THÚC: Scheduled RFQ Check | Xử lý: %d | Lỗi: %d ===",
            processed_count,
            error_count,
        )

    @api.model
    def _trigger_instant_rfq_for_products(self, product_ids, trigger_source='Event Trigger'):
        if not product_ids:
            return

        _logger.info(
            "=== EVENT-DRIVEN RFQ: Kiểm tra %d sản phẩm (Nguồn: %s) ===",
            len(product_ids), trigger_source
        )

        orderpoints = self.search([
            ('product_id', 'in', list(product_ids)),
            ('trigger_mode_custom', '=', 'auto_instant'),
            ('active', '=', True),
        ])

        for op in orderpoints:
            try:
                with self.env.cr.savepoint():
                    # Truyền thẳng nguồn kích hoạt để ghi nhận vào RFQ
                    op._process_auto_rfq(trigger_source=trigger_source)
            except Exception as e:
                _logger.exception(
                    "AUTO RFQ ERROR | Event-driven | OP=%s | Product=%s | Error=%s",
                    op.id,
                    op.product_id.display_name,
                    str(e),
                )