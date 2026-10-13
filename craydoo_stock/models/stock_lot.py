from odoo import fields, models


class StockLot(models.Model):
    _name = 'cd.stock.lot'
    _description = 'Stock Lot'

    name = fields.Char(required=True)
    product_id = fields.Many2one('cd.product.variant', required=True)

    _unique = models.Constraint(
        'UNIQUE (product_id, name)', 'This lot already exists for this product.')
