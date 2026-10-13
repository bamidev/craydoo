from odoo import fields, models


class StockWarehouse(models.Model):
    _name = 'cd.stock.warehouse'
    _description = 'Warehouse'

    name = fields.Char(required=True)
    location_ids = fields.One2many('cd.stock.location', 'warehouse_id')
