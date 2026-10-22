from odoo import _, fields, models
from odoo.tools import SQL


class StockQuantity(models.Model):
    """ The on-hand quantity of a product at a location right now - bumped
    incrementally by `cd.stock.transfer.create` as transfers happen.
    """
    _name = 'cd.stock.quantity'
    _description = 'Stock Quantity'

    product_id = fields.Many2one('cd.product.variant', required=True, readonly=True, index=True)
    location_id = fields.Many2one(
        'cd.stock.location', required=True, readonly=True, ondelete='restrict', index=True)
    quantity = fields.Integer(required=True, readonly=True, default=0)

    _unique = models.Constraint(
        'UNIQUE (product_id, location_id)', 'Only one quantity record per product and location.')

    def action_recompute_quantity(self):
        """ Recomputes `quantity` from scratch off `cd.stock.transfer` (net
        incoming minus outgoing, summed in a single query rather than in
        Python) - a repair action for whenever it's suspected to have
        drifted from reality. Any correction gets logged on the product
        variant, since a mismatch here means something went wrong
        elsewhere.
        """
        transfer_table = self.env['cd.stock.transfer']._table
        for quantity in self:
            self.env.cr.execute(SQL(
                """
                SELECT
                    COALESCE(SUM(quantity) FILTER (WHERE location_dest_id = %s), 0)
                    - COALESCE(SUM(quantity) FILTER (WHERE location_id = %s), 0)
                FROM %s
                WHERE product_id = %s AND (location_id = %s OR location_dest_id = %s)
                """,
                quantity.location_id.id, quantity.location_id.id, SQL.identifier(transfer_table),
                quantity.product_id.id, quantity.location_id.id, quantity.location_id.id,
            ))
            recomputed = self.env.cr.fetchone()[0]
            if recomputed != quantity.quantity:
                quantity.product_id.message_post(body=_(
                    "Stock quantity at %(location)s corrected from %(old)s to %(new)s.",
                    location=quantity.location_id.name, old=quantity.quantity, new=recomputed))
                quantity.sudo().quantity = recomputed
