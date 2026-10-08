from odoo import fields, models


class AccountChartAccount(models.Model):
    """ One account definition within a `cd.account.chart` - the portable
    subset of `cd.account.account`'s fields (code/name/flags); `ledger` and
    `tigerbeetle_id` only get assigned once an entry is actually applied.
    """
    _name = 'cd.account.chart.account'
    _description = 'Chart of Accounts Entry'
    _order = 'code'

    chart_id = fields.Many2one('cd.account.chart', required=True, ondelete='cascade')
    code = fields.Integer(required=True)
    name = fields.Char(required=True, translate=True)

    _code_unique_per_chart = models.Constraint(
        'UNIQUE(chart_id, code)', 'An account code can only appear once per chart.')
