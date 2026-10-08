from odoo import api, fields, models

from ..fields import PartitionedMany2one, UInt128


class AccountInvoiceLine(models.Model):
    """ Its table, `cd_account_invoice_line`, is natively range-partitioned
    by `date` (see `craydoo_account.partition`), mirroring
    `cd.account.invoice`'s own partitioning so a line always lives in the
    same partition generation as its invoice. Because of that,
    `cd_account_invoice`'s primary key is the composite `(id, date)` rather
    than plain `id` (Postgres requires partitioned tables' unique
    constraints to cover the partition column), so `invoice` uses
    `PartitionedMany2one` and the real foreign key is the composite
    `_invoice_fkey` below instead of the single-column one Many2one would
    otherwise add.
    """
    _name = 'cd.account.invoice.line'
    _description = 'Invoice Line'
    _inherit = ['cd.account.locked_mixin']

    invoice = PartitionedMany2one('cd.account.invoice', required=True, ondelete='cascade')
    date = fields.Date(related='invoice.date', store=True, readonly=True, required=True, precompute=True)
    sequence = fields.Integer(default=10)
    name = fields.Char()
    quantity = fields.Float(default=1.0)
    price_unit = fields.Float(required=True, default=0.0)
    taxes = fields.Many2many('cd.account.tax')
    currency = fields.Many2one(related='invoice.currency')

    locked = fields.Boolean(related='invoice.locked', store=True)
    tigerbeetle_id = UInt128(copy=False, index=True, readonly=True)

    price_subtotal = fields.Monetary(compute='_compute_amounts', store=True, currency_field='currency')
    price_tax = fields.Monetary(compute='_compute_amounts', store=True, currency_field='currency')
    price_total = fields.Monetary(compute='_compute_amounts', store=True, currency_field='currency')

    _invoice_fkey = models.Constraint(
        'FOREIGN KEY (invoice, date) REFERENCES cd_account_invoice (id, date) ON DELETE CASCADE')

    @api.depends('quantity', 'price_unit', 'taxes')
    def _compute_amounts(self):
        for line in self:
            if line.taxes:
                res = line.taxes.compute_all(line.price_unit, quantity=line.quantity)
                line.price_subtotal = res['total_excluded']
                line.price_total = res['total_included']
            else:
                line.price_subtotal = line.quantity * line.price_unit
                line.price_total = line.price_subtotal
            line.price_tax = line.price_total - line.price_subtotal
