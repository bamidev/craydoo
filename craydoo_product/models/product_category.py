from odoo import fields, models


class ProductCategory(models.Model):
    _name = 'cd.product.category'
    _description = 'Product Category'

    name = fields.Char(required=True)
    attributes_definition = fields.PropertiesDefinition()
