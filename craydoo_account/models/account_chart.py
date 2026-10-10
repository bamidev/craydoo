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


class AccountChartAccount(models.Model):
    """ One account definition within a `cd.account.chart` - the portable
    subset of `cd.account.account`'s fields (code/name); `ledger_id` only
    gets assigned once an entry is actually applied.
    """
    _name = 'cd.account.chart.account'
    _description = 'Chart of Accounts Entry'
    _order = 'code'

    chart_id = fields.Many2one('cd.account.chart', required=True, ondelete='cascade')
    code = fields.Char(required=True, size=8)
    name = fields.Char(required=True, translate=True)

    _code_unique_per_chart = models.Constraint(
        'UNIQUE(chart_id, code)', 'An account code can only appear once per chart.')
