from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockTransfer(models.Model):
    """ One movement of a specific quantity of a product from one
    location to another. Immutable once created - a transfer is a
    historical administrative fact, not something to revise after
    execution.
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
    location_src_id = fields.Many2one(
        'cd.stock.location', required=True, readonly=True, ondelete='restrict')
    location_dest_id = fields.Many2one(
        'cd.stock.location', required=True, readonly=True, ondelete='restrict')
    plan_id = fields.Many2one(
        'cd.stock.transfer.plan', readonly=True, ondelete='restrict')
    serial_id = fields.Many2one('cd.stock.serial', readonly=True, ondelete='restrict')
    lot_id = fields.Many2one('cd.stock.lot', readonly=True, ondelete='restrict')

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

    def _check_tracking(self, vals):
        """ Enforces `cd.product.template.track_by_serial`/`track_by_lot`:
        a transfer of a tracked product must actually carry the matching
        serial/lot - and a serial, by definition, covers exactly one unit.
        """
        product = self.env['cd.product.variant'].browse(vals.get('product_id'))
        template = product.template_id
        if template.track_by_serial:
            if not vals.get('serial_id'):
                raise UserError(_(
                    "%(product)s is tracked by serial number - set one.", product=product.name))
            if vals.get('quantity') != 1:
                raise UserError(_(
                    "%(product)s is tracked by serial number - quantity must be 1.",
                    product=product.name))
        if template.track_by_lot and not vals.get('lot_id'):
            raise UserError(_(
                "%(product)s is tracked by lot - set one.", product=product.name))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._check_tracking(vals)
        transfers = super().create(vals_list)
        for transfer in transfers:
            transfer._bump_quantity(transfer.location_id.id, -transfer.quantity)
            transfer._bump_quantity(transfer.location_dest_id.id, transfer.quantity)
        return transfers

    def unlink(self):
        raise UserError(_("Stock history cannot be deleted."))

    def write(self, vals):
        raise UserError(_("Stock history cannot be changed."))


class StockTransferPlan(models.Model):
    """ The plan of one or several stock transfers.
    """
    _name = 'cd.stock.transfer.plan'
    _description = 'Stock Transfer Plan'

    product_id = fields.Many2one('cd.product.variant', required=True, readonly=True)
    demand = fields.Integer(required=True)
    transfer_ids = fields.One2many('cd.stock.transfer', 'group_id')

