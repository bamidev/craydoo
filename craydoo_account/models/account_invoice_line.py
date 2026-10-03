from odoo import api, fields, models


class AccountInvoiceLine(models.Model):
    _name = 'cd.account.invoice.line'
    _description = 'Invoice Line'
    _inherit = ['cd.account.tigerbeetle.mixin']

    invoice = fields.Many2one('cd.account.invoice', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char()
    quantity = fields.Float(default=1.0)
    price_unit = fields.Float(required=True, default=0.0)
    taxes = fields.Many2many('cd.account.tax')
    currency = fields.Many2one(related='invoice.currency')

    price_subtotal = fields.Monetary(compute='_compute_amounts', store=True, currency_field='currency')
    price_tax = fields.Monetary(compute='_compute_amounts', store=True, currency_field='currency')
    price_total = fields.Monetary(compute='_compute_amounts', store=True, currency_field='currency')

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
