from odoo import fields, models


class AccountLedger(models.Model):
    """ Local registry of Tigerbeetle ledger numbers. Tigerbeetle has no
    "list ledgers" API - a ledger is just a u32 tag on accounts/transfers -
    so unlike `cd.account.account`/`cd.account.transfer` this is a normal,
    Postgres-backed model: configure your ledgers here once, then look them
    up by `number` wherever a raw Tigerbeetle ledger integer needs a name.
    """
    _name = 'cd.account.ledger'
    _description = 'Ledger'
    _order = 'number'

    name = fields.Char(required=True)
    number = fields.Integer(required=True)
