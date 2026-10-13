from odoo import api, fields, models


class ProductVariant(models.Model):
    _name = 'cd.product.variant'
    _inherit = ['mail.thread']
    _description = 'Product Variant'

    name = fields.Char(required=True)
    barcode = fields.Char()
    template_id = fields.Many2one('cd.product.template', required=True, ondelete='cascade')
    variant_image = fields.Image()
    image = fields.Image(compute='_compute_image')

    _unique_barcode = models.Constraint('UNIQUE (barcode)', 'This barcode is already in use.')

    @api.depends('variant_image', 'template_id.image')
    def _compute_image(self):
        for variant in self:
            variant.image = variant.variant_image or variant.template_id.image
