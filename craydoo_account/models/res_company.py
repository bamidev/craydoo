from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    account_ledger = fields.Many2one('cd.account.ledger')
    default_debit_account = fields.Many2one(
        'cd.account.account', domain="[('ledger', '=', account_ledger)]")
    default_credit_account = fields.Many2one(
        'cd.account.account', domain="[('ledger', '=', account_ledger)]")
