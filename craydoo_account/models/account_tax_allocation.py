from odoo import fields, models


class AccountTaxAllocation(models.AbstractModel):
    _name = 'cd.account.tax.allocation'
    _description = 'Tax Allocation'

    invoice_lines = fields.One2many('cd.account.tax.allocation.line', 'invoice_tax')
    refund_lines = fields.One2many('cd.account.tax.allocation.line', 'refund_tax')
