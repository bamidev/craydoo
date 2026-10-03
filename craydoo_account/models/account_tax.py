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
        if self.price_include:
            return base_amount - base_amount / (1 + self.amount / 100.0)
        return base_amount * self.amount / 100.0

    def compute_all(self, price_unit, quantity=1.0):
        """ Apply every tax in self to `price_unit * quantity`, mirroring a
        trimmed version of Odoo's own `account.tax.compute_all`: no
        compounding between taxes, no rounding methods, just a flat
        included/excluded split per tax.
        """
        base = price_unit * quantity
        included_total = 0.0
        excluded_total = 0.0
        taxes_data = []
        for tax in self:
            tax_amount = tax._compute_amount(base, quantity)
            if tax.price_include:
                included_total += tax_amount
            else:
                excluded_total += tax_amount
            taxes_data.append({'id': tax.id, 'name': tax.name, 'amount': tax_amount})

        total_excluded = base - included_total
        total_included = total_excluded + included_total + excluded_total
        return {
            'total_excluded': total_excluded,
            'total_included': total_included,
            'taxes': taxes_data,
        }
