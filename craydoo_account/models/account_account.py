from odoo import fields, models


class AccountAccount(models.Model):
    """ An accounting account.

    Creatable and `active` is freely writable, but `ledger_id`/`code` can't
    be changed once set (both are `readonly`). Deleting one is only
    blocked once a transfer actually references it - see
    `debit_account_id`/`credit_account_id`'s `ondelete` on
    `cd.account.transfer`.
    """
    _name = 'cd.account.account'
    _description = 'Account'
    _rec_name = 'name'

    active = fields.Boolean(default=True)
    name = fields.Char(required=True, translate=True)

    code = fields.Char(required=True, readonly=True, size=8)
    ledger_id = fields.Many2one('cd.account.ledger', required=True, readonly=True)
