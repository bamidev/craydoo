from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .fields import TigerbeetleId
from .tigerbeetle_client import create_account


class AccountAccount(models.Model):
    """ A Tigerbeetle account. Identity fields (tigerbeetle_id/ledger/code)
    are stored locally in Postgres - they never change after creation in
    Tigerbeetle anyway, so caching them means listing/searching/archiving
    doesn't need a live Tigerbeetle connection.

    Creatable and `active` is freely writable (a purely local annotation,
    never sent to Tigerbeetle), but `tigerbeetle_id`/`ledger`/`code`/`flags`
    can't be changed once set, and records can't be deleted - Tigerbeetle
    has no "update"/"delete account" API at all.
    """
    _name = 'cd.account.account'
    _description = 'Tigerbeetle Account'
    _rec_name = 'tigerbeetle_id'

    tigerbeetle_id = TigerbeetleId(required=True, index=True, readonly=True, copy=False)
    ledger = fields.Many2one('cd.account.ledger', required=True, readonly=True)
    code = fields.Integer(readonly=True)
    flags = fields.Integer(readonly=True)
    active = fields.Boolean(default=True)

    _tigerbeetle_id_unique = models.Constraint(
        'UNIQUE(tigerbeetle_id)', 'A Tigerbeetle account can only be cached once.')

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get('cd_account_sync'):
            for vals in vals_list:
                ledger = self.env['cd.account.ledger'].browse(vals.get('ledger'))
                if not ledger:
                    raise UserError(_("A ledger is required to create a Tigerbeetle account."))
                vals['tigerbeetle_id'] = create_account(
                    self.env, ledger=ledger.number, code=vals.get('code', 0))
        return super().create(vals_list)

    def write(self, vals):
        if set(vals) - {'active'}:
            raise UserError(_("Only 'active' can be changed on a Tigerbeetle account."))
        return super().write(vals)

    def unlink(self):
        raise UserError(_("Tigerbeetle accounts can't be deleted."))
