from odoo import models


class ProductTemplate(models.Model):
    _inherit = 'cd.product.template'

    def _action_open_enable_tracking_wizard(self, field_name):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'cd.product.template.enable.tracking.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_template_id': self.id,
                'default_field_name': field_name,
            },
        }

    def _stock_has_transfers(self):
        self.ensure_one()
        return bool(self.env['cd.stock.transfer'].search_count([
            ('product_id', 'in', self.variant_ids.ids),
        ]))

    def action_enable_track_by_serial(self):
        self.ensure_one()
        if self._stock_has_transfers():
            return self._action_open_enable_tracking_wizard('track_by_serial')
        self.track_by_serial = True
