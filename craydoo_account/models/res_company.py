from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    account_ledger_id = fields.Many2one('cd.account.ledger')
    default_debit_account_id = fields.Many2one(
        'cd.account.account', domain="[('ledger_id', '=', account_ledger_id)]")
    default_credit_account_id = fields.Many2one(
        'cd.account.account', domain="[('ledger_id', '=', account_ledger_id)]")
