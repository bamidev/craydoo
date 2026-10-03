from odoo import _, models
from odoo.exceptions import UserError


class ContactLockedMixin(models.AbstractModel):
    """ Shared immutability behaviour for records that can be `locked`.

    Inheriting models define their own `locked` field - a stored Boolean on
    the authoritative record (`cd.contact.info`), or a related field sourced
    from it on dependents (`cd.contact.email/phone/website`). Either way,
    once `locked` is true the record can no longer be written to or
    unlinked, unless the `craydoo_allow_locked_write` context flag is set.
    """
    _name = 'cd.contact.locked_mixin'
    _description = 'Contact Locked Mixin'

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
