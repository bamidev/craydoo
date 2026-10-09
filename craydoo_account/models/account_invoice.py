from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..partition import PARTITIONED_TABLES, ensure_year_partitions


class AccountInvoice(models.Model):
    """ Its table, `cd_account_invoice`, is natively range-partitioned by
    `date` (see `craydoo_account.partition`) - `date` is therefore
    required, so every row always has a partition to land in.
    """
    _name = 'cd.account.invoice'
    _description = 'Invoice'
    _inherit = ['cd.account.locked_mixin', 'mail.thread']
    _order = 'date desc, name desc'

    name = fields.Char(required=True, copy=False, default='/')
    active = fields.Boolean(default=True)
    locked = fields.Boolean(default=False, copy=False, index=True)

    debtor_id = fields.Many2one('cd.contact.info', required=True, string="Billed to")
    language = fields.Selection(lambda self: self.env['res.lang'].get_installed())

    date = fields.Date(required=True, default=lambda self: fields.Date.context_today(self))
    due_date = fields.Date()
    currency_id = fields.Many2one(
        'res.currency', required=True, default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company)

    invoice_line_ids = fields.One2many('cd.account.invoice.line', 'invoice_id', copy=True)
    transfer_id = fields.Many2one('cd.account.transfer', copy=False, index=True, readonly=True)

    amount_untaxed = fields.Monetary(compute='_compute_amounts', store=True, currency_field='currency_id')
    amount_tax = fields.Monetary(compute='_compute_amounts', store=True, currency_field='currency_id')
    amount_total = fields.Monetary(compute='_compute_amounts', store=True, currency_field='currency_id')

    @api.depends('invoice_line_ids.price_subtotal', 'invoice_line_ids.price_tax')
    def _compute_amounts(self):
        for inv in self:
            inv.amount_untaxed = sum(inv.invoice_line_ids.mapped('price_subtotal'))
            inv.amount_tax = sum(inv.invoice_line_ids.mapped('price_tax'))
            inv.amount_total = inv.amount_untaxed + inv.amount_tax

    def write(self, vals):
        if vals.get('active') is False:
            locked_invoices = self.filtered('locked')
            if locked_invoices:
                raise UserError(_("Only unlocked invoices can be archived."))
        return super().write(vals)

    @api.model
    def _cron_ensure_partitions(self):
        """ Keep the forward end of every partitioned table's range
        supplied with partitions, so there's always one ready for next
        year's invoices. Called monthly by an ir.cron.
        """
        for tablename, date_column in PARTITIONED_TABLES:
            ensure_year_partitions(self.env.cr, tablename, date_column)
