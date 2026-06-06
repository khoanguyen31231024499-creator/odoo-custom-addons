# -*- coding: utf-8 -*-
# Part of FootGearH - Procure to Pay
# HR Employee Link Enhancement

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    role = fields.Selection(
        selection=[('group_user', 'Nhân viên'), ('group_system', 'Quản lý')],
        compute='_compute_role',
        readonly=False,
        string='Role',
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        domain="[('user_id', '=', False)]",
        help='Link this user account to a specific employee record.',
    )


