from odoo import fields, models


class AccountChart(models.Model):
    """ A reusable set of account definitions (e.g. a country's standard
    chart of accounts), shipped by an l10n module and applied onto real
    `cd.account.account` records by a wizard. Portable data only - no
    ledger/company wiring here, since which ledger a chart gets applied to
    is chosen when it's actually applied, not baked into the chart itself.
    """
    _name = 'cd.account.chart'
    _description = 'Chart of Accounts'

    name = fields.Char(required=True, translate=True)
    account_ids = fields.One2many('cd.account.chart.account', 'chart_id')

    default_debit_account_id = fields.Many2one(
        'cd.account.chart.account', domain="[('chart_id', '=', id)]")
    default_credit_account_id = fields.Many2one(
        'cd.account.chart.account', domain="[('chart_id', '=', id)]")
