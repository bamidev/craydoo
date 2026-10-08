from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    company_account_ledger = fields.Many2one(related='company_id.account_ledger', readonly=False)
    company_default_debit_account = fields.Many2one(
        related='company_id.default_debit_account', readonly=False)
    company_default_credit_account = fields.Many2one(
        related='company_id.default_credit_account', readonly=False)

    fallback_ledger_id = fields.Many2one(
        'cd.account.ledger', config_parameter='craydoo_account.default_ledger')
    fallback_debit_account_id = fields.Many2one(
        'cd.account.account', config_parameter='craydoo_account.default_debit_account')
    fallback_credit_account_id = fields.Many2one(
        'cd.account.account', config_parameter='craydoo_account.default_credit_account')
