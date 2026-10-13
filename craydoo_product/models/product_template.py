from odoo import fields, models


class ProductTemplate(models.Model):
    _name = 'cd.product.template'
    _inherit = ['mail.thread']
    _description = 'Product Template'

    name = fields.Char(required=True)
    image = fields.Image()
    category_id = fields.Many2one('cd.product.category', required=True)
    attributes = fields.Properties(
        definition_record='category_id', definition_record_field='attributes_definition')
    variant_ids = fields.One2many('cd.product.variant', 'template_id')
