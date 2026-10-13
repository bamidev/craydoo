from odoo import _, api, fields, models


class ProductTemplateEnableTrackingWizard(models.TransientModel):
    """ Shown instead of directly flipping a `cd.product.template` tracking
    flag when the product already has `cd.stock.transfer`s - enabling the
    flag on a product with history would be meaningless, so this offers a
    copy of the product to enable it on instead.
    """
    _name = 'cd.product.template.enable.tracking.wizard'
    _description = 'Enable Product Tracking'

    template_id = fields.Many2one('cd.product.template', required=True)
    field_name = fields.Char(required=True)
    message = fields.Char(compute='_compute_message')

    @api.depends('template_id')
    def _compute_message(self):
        for wizard in self:
            wizard.message = _(
                "%(product)s already has stock transfers, so this tracking setting can't "
                "be enabled on it directly. Create a copy of the product to enable it there "
                "instead?", product=wizard.template_id.name)

    def action_create_copy(self):
        self.ensure_one()
        copy = self.template_id.copy({self.field_name: True})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'cd.product.template',
            'view_mode': 'form',
            'res_id': copy.id,
        }
