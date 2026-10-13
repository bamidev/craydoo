from odoo import fields, models

LOCATION_USAGES = [
    ('internal', 'Internal'),
    ('customer', 'Customer'),
    ('supplier', 'Supplier'),
]


class StockLocation(models.Model):
    _name = 'cd.stock.location'
    _description = 'Stock Location'

    name = fields.Char(required=True)
    usage = fields.Selection(LOCATION_USAGES, required=True, default='internal')
    warehouse_id = fields.Many2one('cd.stock.warehouse')
