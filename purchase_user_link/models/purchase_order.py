# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


APPROVAL_LIMIT = 20000000.0

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    approver_id = fields.Many2one(
        'res.users',
        string='Approver',
        tracking=True,
        help='Manager assigned to approve this purchase order.',
    )
    approval_date = fields.Datetime(
        string='Approval Date',
        copy=False,
        readonly=True,
        tracking=True,
        help='Timestamp when the order is approved by the manager.',
    )
    rejection_reason = fields.Text(
        string='Rejection Reason',
        copy=False,
        help='Reason entered by the manager when rejecting the order.',
    )
    is_above_limit = fields.Boolean(
        string='Above Approval Limit',
        compute='_compute_is_above_limit',
        store=True,
        help='True when the total amount is at or above the approval threshold.',
    )

    @api.depends('amount_total')
    def _compute_is_above_limit(self):
        for order in self:
            order.is_above_limit = order.amount_total >= APPROVAL_LIMIT

    def button_confirm(self):
        for order in self:
            if order.state not in ('draft', 'sent'):
                continue

            error_msg = order._confirmation_error_message()
            if error_msg:
                raise UserError(error_msg)

            order.order_line._validate_analytic_distribution()
            order._add_supplier_to_product()

            if order.is_above_limit:
                order.write({'state': 'to approve'})
                order.message_post(body=_(
                    'Purchase order sent for approval because the total amount exceeds the approval limit.'
                ))
                continue

            if order._approval_allowed():
                order.button_approve()
            else:
                order.write({'state': 'to approve'})
        return True

    def button_approve(self, force=False):
        for order in self:
            if order.approver_id and order.approver_id != self.env.user:
                raise UserError(_(
                    'This purchase order is assigned to %(approver)s for approval.',
                    approver=order.approver_id.display_name,
                ))

            if order.approver_id and not self.env.user.has_group('purchase.group_purchase_manager'):
                raise UserError(_('Only a Purchase Manager can approve this order.'))

        result = super().button_approve(force=force)

        approval_date = fields.Datetime.now()
        for order in self.filtered(lambda record: record.state == 'purchase'):
            values = {
                'approval_date': approval_date,
            }
            if not order.approver_id:
                values['approver_id'] = self.env.user.id
            order.write(values)
            order.message_post(body=_(
                'Purchase order approved by %(user)s.',
                user=self.env.user.display_name,
            ))
        return result

    def button_reject(self):
        self.ensure_one()

        if not self.env.user.has_group('purchase.group_purchase_manager'):
            raise UserError(_('Only a Purchase Manager can reject this order.'))
        if not self.rejection_reason:
            raise UserError(_('Please enter a rejection reason before rejecting this order.'))

        self.write({
            'state': 'cancel',
            'approver_id': self.env.user.id,
        })
        self.message_post(body=_(
            'Purchase order rejected by %(user)s. Reason: %(reason)s',
            user=self.env.user.display_name,
            reason=self.rejection_reason,
        ))
        return True