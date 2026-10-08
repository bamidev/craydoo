from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..fields import UInt128
from .tigerbeetle_client import create_account


IMMUTABLE_FIELDS = [
    'tigerbeetle_id', 'code', 'flags', 'ledger'
]


class AccountAccount(models.Model):
    """ An accounting account.
    Any 

    Creatable and `active` is freely writable (a purely local annotation,
    never sent to Tigerbeetle), but `tigerbeetle_id`/`ledger`/`code`/`flags`
    can't be changed once set, and records can't be deleted - Tigerbeetle
    has no "update"/"delete account" API at all.
    """
    _name = 'cd.account.account'
    _description = 'Tigerbeetle Account'
    _rec_name = 'name'

    active = fields.Boolean(default=True)
    tigerbeetle_id = UInt128(required=True, index=True, readonly=True, copy=False)
    name = fields.Char(required=True, translate=True)

    code = fields.Integer(required=True, readonly=True)
    flags = fields.Integer(required=True, readonly=True, default=0)
    ledger = fields.Many2one('cd.account.ledger', required=True, readonly=True)

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

        #def write(self, vals):
        #immutable = set(vals) & set(IMMUTABLE_FIELDS)
        #if immutable:
        #    labels = ', '.join(self._fields[f].string for f in immutable)
        #    raise UserError(_("%(fields)s can't be changed once set.", fields=labels))
        #return super().write(vals)

    def unlink(self):
        raise UserError(_("Tigerbeetle accounts can't be deleted."))
