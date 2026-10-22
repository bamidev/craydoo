from odoo import _, fields, models
from odoo.exceptions import UserError

ORDER_STATES = [
    ('draft', 'Draft'),
    ('done', 'Done'),
]


class StockPickingOrder(models.Model):
    """ A document describing which products need to move where - mutable
    while in `draft`. Validating it creates the actual `cd.stock.transfer`s
    (one per line), grouped into a single new `cd.stock.transfer.group`.
    """
    _name = 'cd.stock.picking.order'
    _description = 'Picking Order'

    name = fields.Char(
        required=True, readonly=True, copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('cd.stock.picking.order'))
    state = fields.Selection(ORDER_STATES, required=True, readonly=True, default='draft')
    order_line_ids = fields.One2many('cd.stock.picking.order.line', 'order_id')

    def action_validate(self):
        for order in self:
            if order.state == 'done':
                raise UserError(_("This picking order is already validated."))
            if not order.order_line_ids:
                raise UserError(_("Add at least one line before validating."))

            group = self.env['cd.stock.transfer.group'].create({})
            for line in order.order_line_ids:
                self.env['cd.stock.transfer'].create({
                    'date': fields.Date.context_today(self),
                    'product_id': line.product_id.id,
                    'quantity': line.quantity,
                    'location_id': line.location_id.id,
                    'location_dest_id': line.location_dest_id.id,
                    'group_id': group.id,
                })

            order.group_id = group.id
            order.state = 'done'


class StockPickingOrderLine(models.Model):
    _name = 'cd.stock.picking.order.line'
    _description = 'Picking Order Line'

    order_id = fields.Many2one('cd.stock.picking.order', required=True, ondelete='cascade')
    product_id = fields.Many2one('cd.product.variant', required=True)
    quantity = fields.Integer(required=True)
    location_id = fields.Many2one('cd.stock.location', required=True)
    location_dest_id = fields.Many2one('cd.stock.location', required=True)
    plan_id = fields.Many2one('cd.stock.transfer.plan', readonly=True, copy=False)
