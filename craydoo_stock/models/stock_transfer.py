from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockTransfer(models.Model):
    """ One movement of a specific quantity of a product from one
    location to another. Immutable once created - a transfer is a
    historical fact, not something to revise after execution.
    """
    _name = 'cd.stock.transfer'
    _description = 'Stock Transfer'
    _order = 'id'

    name = fields.Char(
        required=True, readonly=True, copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('cd.stock.transfer'))
    date = fields.Date(required=True, readonly=True, default=fields.Date.context_today)
    product_id = fields.Many2one('cd.product.variant', required=True, readonly=True)
    quantity = fields.Integer(required=True, readonly=True)
    location_id = fields.Many2one(
        'cd.stock.location', required=True, readonly=True, ondelete='restrict')
    location_dest_id = fields.Many2one(
        'cd.stock.location', required=True, readonly=True, ondelete='restrict')
    group_id = fields.Many2one(
        'cd.stock.transfer.group', readonly=True, ondelete='restrict')

    def _bump_quantity(self, location_id, delta):
        """ `sudo()` - regular users can only read `cd.stock.quantity`,
        but still need to be able to create transfers, which bumps it.
        """
        self.ensure_one()
        Quantity = self.env['cd.stock.quantity'].sudo()
        quantity = Quantity.search([
            ('product_id', '=', self.product_id.id), ('location_id', '=', location_id),
        ])
        if not quantity:
            quantity = Quantity.create({
                'product_id': self.product_id.id, 'location_id': location_id, 'quantity': 0,
            })
        quantity.quantity += delta

    @api.model_create_multi
    def create(self, vals_list):
        transfers = super().create(vals_list)
        for transfer in transfers:
            transfer._bump_quantity(transfer.location_id.id, -transfer.quantity)
            transfer._bump_quantity(transfer.location_dest_id.id, transfer.quantity)
        return transfers

    def unlink(self):
        raise UserError(_("Stock history cannot be deleted."))

    def write(self, vals):
        raise UserError(_("Stock history cannot be changed."))


class StockTransferGroup(models.Model):
    """ Links several `cd.stock.transfer`s together as belonging to one
    warehouse operation - e.g. every transfer generated from validating
    one `cd.stock.picking.order`.
    """
    _name = 'cd.stock.transfer.group'
    _description = 'Stock Transfer Group'

    transfer_ids = fields.One2many('cd.stock.transfer', 'group_id')
