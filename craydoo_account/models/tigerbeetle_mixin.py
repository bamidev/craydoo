from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .fields import BigInteger


class TigerbeetleLockedMixin(models.AbstractModel):
    """ Shared locking behaviour for records written through to Tigerbeetle.

    Once `tigerbeetle_ref` is set, the record is frozen: only `base.group_system`
    may still write to it, and deleting it requires going through
    `action_unlink_confirmed` (wired to a confirm dialog in the view) instead
    of a plain unlink.
    """
    _name = 'cd.account.tigerbeetle.mixin'
    _description = 'Tigerbeetle Locked Record Mixin'

    tigerbeetle_ref = BigInteger(copy=False, index=True, readonly=True)
    locked = fields.Boolean(compute='_compute_locked', store=True)

    @api.depends('tigerbeetle_ref')
    def _compute_locked(self):
        for rec in self:
            rec.locked = bool(rec.tigerbeetle_ref)

    def _check_locked_access(self):
        locked = self.filtered('locked')
        if locked and not self.env.user.has_group('base.group_system'):
            raise UserError(_(
                "The following records are locked and can only be changed by "
                "administrators: %s", ', '.join(locked.mapped('display_name')),
            ))

    def write(self, vals):
        if set(vals) - {'tigerbeetle_ref'}:
            self._check_locked_access()
        return super().write(vals)

    def unlink(self):
        self._check_locked_access()
        locked = self.filtered('locked')
        if locked and not self.env.context.get('craydoo_confirm_delete_locked'):
            raise UserError(_(
                "The following records are locked. Use the Delete button on "
                "the form to confirm this action: %s", ', '.join(locked.mapped('display_name')),
            ))
        return super().unlink()

    def action_unlink_confirmed(self):
        self.with_context(craydoo_confirm_delete_locked=True).unlink()
