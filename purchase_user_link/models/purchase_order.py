# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError


_logger = logging.getLogger(__name__)

APPROVAL_LIMIT_VND = 20_000_000.0
APPROVER_GROUP = 'purchase.group_purchase_manager'


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    approver_id = fields.Many2one(
        'res.users',
        string='Approver',
        copy=False,
        tracking=True,
    )
    approval_date = fields.Datetime(
        string='Approval Date',
        copy=False,
        readonly=True,
        tracking=True,
    )
    rejection_reason = fields.Text(
        string='Rejection Reason',
        copy=False,
    )
    amount_total_vnd = fields.Monetary(
        string='Total Amount (VND)',
        compute='_compute_amount_total_vnd',
        currency_field='company_currency_id',
    )
    is_above_limit = fields.Boolean(
        string='Above Approval Limit',
        compute='_compute_is_above_limit',
    )

    def _get_vnd_currency(self):
        vnd = self.env.ref('base.VND', raise_if_not_found=False)
        if not vnd:
            vnd = self.env['res.currency'].search([('name', '=', 'VND')], limit=1)
        if not vnd:
            vnd = self.env['res.currency'].search([('symbol', 'in', ['₫', 'đ'])], limit=1)
        return vnd

    def _get_amount_total_vnd(self):
        self.ensure_one()

        if self.currency_id and self.currency_id.name == 'VND':
            return self.amount_total

        vnd = self._get_vnd_currency()
        if not vnd:
            raise UserError(_('VND currency was not found. Please activate or create the VND currency.'))

        if not self.currency_id:
            raise UserError(_('This purchase order has no currency.'))

        conversion_date = (
            fields.Date.to_date(self.date_order)
            if self.date_order
            else fields.Date.context_today(self)
        )
        return self.currency_id._convert(
            self.amount_total,
            vnd,
            self.company_id,
            conversion_date,
        )

    def _requires_vnd_approval(self):
        self.ensure_one()
        amount_vnd = self._get_amount_total_vnd()
        _logger.warning(
            '[PO_APPROVAL_FIX] running: po=%s amount_total=%s currency=%s amount_vnd=%s limit=%s',
            self.name, self.amount_total, self.currency_id.name, amount_vnd, APPROVAL_LIMIT_VND,
        )
        return amount_vnd > APPROVAL_LIMIT_VND

    @api.depends('amount_total', 'currency_id', 'company_id', 'date_order')
    def _compute_amount_total_vnd(self):
        for order in self:
            try:
                order.amount_total_vnd = order._get_amount_total_vnd()
            except Exception:
                order.amount_total_vnd = 0.0

    @api.depends('amount_total_vnd')
    def _compute_is_above_limit(self):
        for order in self:
            order.is_above_limit = order.amount_total_vnd > APPROVAL_LIMIT_VND

    def _check_po_approval_rights(self):
        if not self.env.user.has_group(APPROVER_GROUP):
            raise AccessError(_('Only an authorized manager can approve or reject this purchase order.'))

    def button_confirm(self):
        _logger.warning('[PO_APPROVAL_FIX] custom button_confirm called for ids=%s', self.ids)

        for order in self:
            if order.state not in ('draft', 'sent'):
                continue

            error_msg = order._confirmation_error_message()
            if error_msg:
                raise UserError(error_msg)

            order.order_line._validate_analytic_distribution()
            order._add_supplier_to_product()

            if order._requires_vnd_approval():
                order.write({
                    'state': 'to approve',
                    'approval_date': False,
                    'rejection_reason': False,
                })
                order.message_post(body=_(
                    'Purchase order sent for approval because the total amount is above 20,000,000 VND.'
                ))
                return True

        return super().button_confirm()

    def button_approve(self, force=False):
        approval_orders = self.filtered(lambda order: order._requires_vnd_approval())

        if approval_orders:
            approval_orders._check_po_approval_rights()

        for order in approval_orders:
            if order.approver_id and order.approver_id != self.env.user:
                raise UserError(_(
                    'This purchase order is assigned to %(approver)s for approval.',
                    approver=order.approver_id.display_name,
                ))

        result = super().button_approve(force=force)

        approval_date = fields.Datetime.now()
        for order in approval_orders.filtered(lambda record: record.state == 'purchase'):
            order.write({
                'approver_id': self.env.user.id,
                'approval_date': approval_date,
            })
            order.message_post(body=_(
                'Purchase order approved by %(user)s.',
                user=self.env.user.display_name,
            ))

        return result

    def button_reject(self):
        self.ensure_one()

        if self.state != 'to approve':
            raise UserError(_('Only purchase orders waiting for approval can be rejected.'))

        if not self._requires_vnd_approval():
            raise UserError(_('Only purchase orders above 20,000,000 VND can be rejected through this approval flow.'))

        self._check_po_approval_rights()

        if not self.rejection_reason:
            raise UserError(_('Please enter a rejection reason before rejecting this order.'))

        self.write({
            'state': 'cancel',
            'approver_id': self.env.user.id,
            'approval_date': False,
        })
        self.message_post(body=_(
            'Purchase order rejected by %(user)s. Reason: %(reason)s',
            user=self.env.user.display_name,
            reason=self.rejection_reason,
        ))
        return True
