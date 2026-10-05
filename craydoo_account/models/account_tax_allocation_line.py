from odoo import fields, models

from .fields import TigerbeetleId


class AccountTaxAllocationLine(models.Model):
    _name = 'cd.account.tax.allocation.line'
    _description = 'Tax Allocation Line'
    _order = 'sequence, id'

    invoice_tax = fields.Many2one('cd.account.tax', ondelete='cascade')
    refund_tax = fields.Many2one('cd.account.tax', ondelete='cascade')
    sequence = fields.Integer(default=10)
    account_id = TigerbeetleId()
    tags = fields.Many2many('cd.account.tax.tag', string='Tax Tags')
    percentage = fields.Float(required=True, default=100.0)
