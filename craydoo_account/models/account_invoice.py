from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountInvoice(models.Model):
    _name = 'cd.account.invoice'
    _description = 'Invoice'
    _inherit = ['cd.account.tigerbeetle.mixin']
    _order = 'invoice_date desc, name desc'

    name = fields.Char(required=True, copy=False, default='/')
    active = fields.Boolean(default=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
    ], required=True, default='draft', copy=False)

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

    @api.depends('tigerbeetle_ref', 'state')
    def _compute_locked(self):
        super()._compute_locked()
        for inv in self:
            if inv.state != 'draft':
                inv.locked = True

    def write(self, vals):
        if vals.get('active') is False:
            non_draft = self.filtered(lambda inv: inv.state != 'draft')
            if non_draft:
                raise UserError(_("Only draft invoices can be archived."))
        return super().write(vals)

    def action_post(self):
        for inv in self:
            if inv.state != 'draft':
                continue
            inv.debtor = inv.debtor.create_locked_copy()
            if inv.name == '/':
                inv.name = self.env['ir.sequence'].next_by_code('cd.account.invoice') or '/'
            inv.state = 'posted'
