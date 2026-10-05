from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountInvoice(models.Model):
    _name = 'cd.account.invoice'
    _description = 'Invoice'
    _inherit = ['cd.account.locked_mixin', 'mail.thread']
    _order = 'invoice_date desc, name desc'

    name = fields.Char(required=True, copy=False, default='/')
    active = fields.Boolean(default=True)
    locked = fields.Boolean(default=False, copy=False, index=True)

    debtor = fields.Many2one('cd.contact.info', required=True)
    language = fields.Selection(lambda self: self.env['res.lang'].get_installed())

    invoice_date = fields.Date()
    due_date = fields.Date()
    currency = fields.Many2one(
        'res.currency', required=True, default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company)

    invoice_lines = fields.One2many('cd.account.invoice.line', 'invoice', copy=True)

    amount_untaxed = fields.Monetary(compute='_compute_amounts', store=True, currency_field='currency')
    amount_tax = fields.Monetary(compute='_compute_amounts', store=True, currency_field='currency')
    amount_total = fields.Monetary(compute='_compute_amounts', store=True, currency_field='currency')

    @api.depends('invoice_lines.price_subtotal', 'invoice_lines.price_tax')
    def _compute_amounts(self):
        for inv in self:
            inv.amount_untaxed = sum(inv.invoice_lines.mapped('price_subtotal'))
            inv.amount_tax = sum(inv.invoice_lines.mapped('price_tax'))
            inv.amount_total = inv.amount_untaxed + inv.amount_tax

    def write(self, vals):
        if vals.get('active') is False:
            locked_invoices = self.filtered('locked')
            if locked_invoices:
                raise UserError(_("Only unlocked invoices can be archived."))
        return super().write(vals)
