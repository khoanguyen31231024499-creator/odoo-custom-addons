# -*- coding: utf-8 -*-
# Part of FootGearH - Procure to Pay
# Purchase User Link Constraint

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.constrains('groups_id', 'employee_id')
    def _check_purchase_user_has_employee(self):
        """
        Check: Users in purchase groups must have an Employee assigned.
        """
        purchase_user_group = self.env.ref('purchase.group_purchase_user', raise_if_not_found=False)
        purchase_manager_group = self.env.ref('purchase.group_purchase_manager', raise_if_not_found=False)

        for user in self:
            is_purchase_user = purchase_user_group and purchase_user_group in user.groups_id
            is_purchase_manager = purchase_manager_group and purchase_manager_group in user.groups_id

            if (is_purchase_user or is_purchase_manager) and not user.employee_id:
                raise ValidationError(
                    _("User '%s' belongs to Purchase group but has no linked Employee. Please assign an employee to this user.") % user.name
                )
