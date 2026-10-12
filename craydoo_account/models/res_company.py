from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    account_ledger_id = fields.Many2one(
        'cd.account.ledger',
        default=lambda self: self.env.ref('craydoo_account.account_ledger_main', raise_if_not_found=False))
    default_debit_account_id = fields.Many2one(
        'cd.account.account', domain="[('ledger_id', '=', account_ledger_id)]")
    default_credit_account_id = fields.Many2one(
        'cd.account.account', domain="[('ledger_id', '=', account_ledger_id)]")
