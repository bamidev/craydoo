from odoo import _, models
from odoo.exceptions import UserError


class AccountLockedMixin(models.AbstractModel):
    """ Shared immutability behaviour for records that can be `locked`:
    inheriting models define their own `locked` field (stored, or related to
    a parent record's); once true, write/unlink raise unless the
    `craydoo_allow_locked_write` context flag is set.
    """
    _name = 'cd.account.locked_mixin'
    _description = 'Account Locked Mixin'

    def _check_locked(self):
        if self.env.context.get('craydoo_allow_locked_write'):
            return
        locked = self.filtered('locked')
        if locked:
            raise UserError(_(
                "The following records are locked and cannot be changed: %s",
                ', '.join(locked.mapped('display_name')),
            ))

    def write(self, vals):
        if set(vals) - {'locked'} or vals.get('locked') is False:
            self._check_locked()
        return super().write(vals)

    def unlink(self):
        self._check_locked()
        return super().unlink()
