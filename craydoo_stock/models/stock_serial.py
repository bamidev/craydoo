from odoo import fields, models


class StockSerial(models.Model):
    _name = 'cd.stock.serial'
    _description = 'Stock Serial Number'
    _rec_name = 'serial'

    serial = fields.Char(required=True)
    product_id = fields.Many2one('cd.product.variant', required=True)

    _unique = models.Constraint(
        'UNIQUE (product_id, serial)', 'This serial number already exists for this product.')
