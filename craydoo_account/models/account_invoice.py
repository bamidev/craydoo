from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..fields import PartitionedMany2one, UInteger
from ..partition import PARTITIONED_TABLES, ensure_year_partitions


class AccountInvoice(models.Model):
    """ An invoice
    """
    _name = 'cd.account.invoice'
    _description = 'Invoice'
    _inherit = ['cd.account.locked_mixin', 'mail.thread']
    _order = 'date desc, name desc'

    name = fields.Char(required=True, copy=False, default='/')
    active = fields.Boolean(default=True)
    locked = fields.Boolean(default=False, copy=False, index=True)

    billing_address_id = fields.Many2one(
        'cd.account.address', required=True, readonly=True, copy=False, ondelete='restrict',
        string="Billing Address")
    language_id = fields.Many2one('res.lang')

    date = fields.Date(required=True, default=lambda self: fields.Date.context_today(self))
    due_date = fields.Date()
    currency_id = fields.Many2one(
        'res.currency', required=True, default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company)

    invoice_line_ids = fields.One2many('cd.account.invoice.line', 'invoice_id', copy=True)
    transfer_id = fields.Many2one('cd.account.transfer', copy=False, index=True, readonly=True)
    transfer_ids = fields.Many2many('cd.account.transfer', related='transfer_id.linked_ids')

    amount_untaxed = UInteger(compute='_compute_amounts', store=True)
    amount_tax = UInteger(compute='_compute_amounts', store=True)
    amount_total = UInteger(compute='_compute_amounts', store=True)
    amount_untaxed_currency = fields.Monetary(
        compute='_compute_amount_currency', currency_field='currency_id')
    amount_tax_currency = fields.Monetary(
        compute='_compute_amount_currency', currency_field='currency_id')
    amount_total_currency = fields.Monetary(
        compute='_compute_amount_currency', currency_field='currency_id')

    @api.depends('amount_untaxed', 'amount_tax', 'amount_total', 'currency_id')
    def _compute_amount_currency(self):
        for inv in self:
            factor = 10 ** inv.currency_id.decimal_places if inv.currency_id else 1
            inv.amount_untaxed_currency = inv.amount_untaxed / factor
            inv.amount_tax_currency = inv.amount_tax / factor
            inv.amount_total_currency = inv.amount_total / factor

    @api.depends('invoice_line_ids.amount_revenue', 'invoice_line_ids.amount_tax')
    def _compute_amounts(self):
        for inv in self:
            inv.amount_untaxed = sum(inv.invoice_line_ids.mapped('amount_revenue'))
            inv.amount_tax = sum(inv.invoice_line_ids.mapped('amount_tax'))
            inv.amount_total = inv.amount_untaxed + inv.amount_tax

    def write(self, vals):
        if vals.get('active') is False:
            locked_invoices = self.filtered('locked')
            if locked_invoices:
                raise UserError(_("Only unlocked invoices can be archived."))
        return super().write(vals)

    def _tax_breakdown(self):
        """ `{tax: amount}` for every tax used on this invoice's lines,
        amount aggregated across all lines it applies to. Calls
        `tax._compute_amount` directly rather than `compute_all`, since
        `compute_all` only returns a summed total across every tax in a
        recordset, not each one's own amount.
        """
        self.ensure_one()
        totals = {}
        for line in self.invoice_line_ids:
            base = line.amount_unit * line.quantity
            for tax in line.tax_ids:
                totals[tax] = totals.get(tax, 0) + tax._compute_amount(base, line.quantity)
        return totals

    @api.model
    def _cron_ensure_partitions(self):
        """ Keep the forward end of every partitioned table's range
        supplied with partitions, so there's always one ready for next
        year's invoices.
        """
        for tablename, date_column in PARTITIONED_TABLES:
            ensure_year_partitions(self.env.cr, tablename)


class AccountInvoiceLine(models.Model):
    """ Its table, `cd_account_invoice_line`, is natively range-partitioned
    by `date` (see `craydoo_account.partition`), mirroring
    `cd.account.invoice`'s own partitioning so a line always lives in the
    same partition generation as its invoice. Because of that,
    `cd_account_invoice`'s primary key is the composite `(id, date)` rather
    than plain `id` (Postgres requires partitioned tables' unique
    constraints to cover the partition column), so `invoice_id` uses
    `PartitionedMany2one` and the real foreign key is the composite
    `_invoice_fkey` below instead of the single-column one Many2one would
    otherwise add.
    """
    _name = 'cd.account.invoice.line'
    _description = 'Invoice Line'
    _inherit = ['cd.account.locked_mixin']

    invoice_id = PartitionedMany2one('cd.account.invoice', required=True, ondelete='cascade')
    date = fields.Date(related='invoice_id.date', store=True, readonly=True, required=True, precompute=True)
    sequence = fields.Integer(default=10)
    name = fields.Char()
    quantity = fields.Integer(default=1)
    amount_unit = UInteger(required=True, default=0)
    tax_ids = fields.Many2many('cd.account.tax')
    currency_id = fields.Many2one(related='invoice_id.currency_id')

    locked = fields.Boolean(related='invoice_id.locked', store=True)

    amount_revenue = UInteger(compute='_compute_amounts')
    amount_tax = UInteger(compute='_compute_amounts')
    amount_total = UInteger(compute='_compute_amounts')
    amount_unit_currency = fields.Monetary(
        compute='_compute_amount_currency', inverse='_inverse_amount_unit_currency',
        currency_field='currency_id')
    amount_revenue_currency = fields.Monetary(
        compute='_compute_amount_currency', currency_field='currency_id')
    amount_tax_currency = fields.Monetary(
        compute='_compute_amount_currency', currency_field='currency_id')
    amount_total_currency = fields.Monetary(
        compute='_compute_amount_currency', currency_field='currency_id')

    _invoice_fkey = models.Constraint(
        'FOREIGN KEY (invoice_id, date) REFERENCES cd_account_invoice (id, date) ON DELETE CASCADE')

    @api.depends('amount_unit', 'amount_revenue', 'amount_tax', 'amount_total', 'currency_id')
    def _compute_amount_currency(self):
        for line in self:
            factor = 10 ** line.currency_id.decimal_places if line.currency_id else 1
            line.amount_unit_currency = line.amount_unit / factor
            line.amount_revenue_currency = line.amount_revenue / factor
            line.amount_tax_currency = line.amount_tax / factor
            line.amount_total_currency = line.amount_total / factor

    @api.depends('quantity', 'amount_unit', 'tax_ids')
    def _compute_amounts(self):
        for line in self:
            _amount, tax_amount, total_amount = line.tax_ids.compute_all(
                line.amount_unit, quantity=line.quantity)
            line.amount_total = total_amount
            line.amount_tax = tax_amount
            line.amount_revenue = total_amount - tax_amount

    def get_default_account_id(self):
        """ The account this line's revenue should post to - hook point,
        overridden by `craydoo_account_product` to resolve it from the
        line's product once that module is installed. No such default
        exists at this level, so this is always empty here, leaving the
        caller (`cd.account.invoice.draft._revenue_legs`) to fall back to
        the invoice's manually configured `credit_account_id`.
        """
        self.ensure_one()
        return self.env['cd.account.account']

    def _inverse_amount_unit_currency(self):
        for line in self:
            factor = 10 ** line.currency_id.decimal_places if line.currency_id else 1
            line.amount_unit = round(line.amount_unit_currency * factor)
