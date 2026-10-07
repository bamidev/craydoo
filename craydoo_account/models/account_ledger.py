from odoo import fields, models


class AccountLedger(models.Model):
    """ Local registry of Tigerbeetle ledger numbers."""
    _name = 'cd.account.ledger'
    _description = 'Ledger'
    _order = 'number'

    name = fields.Char(required=True)
    number = fields.Integer(required=True)
