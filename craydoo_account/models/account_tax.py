from math import floor

from odoo import fields, models


class AccountTax(models.Model):
    _name = 'cd.account.tax'
    _description = 'Tax'
    _inherit = ['cd.account.tax.allocation']
    _order = 'sequence, id'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    amount_type = fields.Selection([
        ('percent', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ], required=True, default='percent')
    amount = fields.Float(required=True, default=0.0)
    type_tax_use = fields.Selection([
        ('sale', 'Sales'),
        ('purchase', 'Purchases'),
        ('none', 'None'),
    ], required=True, default='sale')
    price_include = fields.Boolean(string='Included in Price', default=False)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    def _compute_amount(self, base_amount, quantity=1.0):
        self.ensure_one()
        if self.amount_type == 'fixed':
            return self.amount * quantity
        return floor(base_amount * self.amount / 100.0)

    def compute_all(self, price_unit, quantity=1.0):
        """ Apply every tax in self to `price_unit * quantity`, mirroring a
        trimmed version of Odoo's own `account.tax.compute_all`: no
        compounding between taxes, just a flat sum of each tax's own
        amount against the untouched base.

        Returns `(amount, tax_amount, total_amount)`:
        - `amount`: `price_unit * quantity`, untouched by tax.
        - `tax_amount`: every tax's own amount, summed.
        - `total_amount`: `amount` plus whatever tax isn't already
          included in it - an excluded tax adds to the total; an
          included one doesn't, since it's already part of `amount`.
        """
        amount = price_unit * quantity
        tax_amount = 0
        excluded_amount = 0
        for tax in self:
            this_tax_amount = tax._compute_amount(amount, quantity)
            tax_amount += this_tax_amount
            if not tax.price_include:
                excluded_amount += this_tax_amount
        total_amount = amount + excluded_amount
        return amount, tax_amount, total_amount
