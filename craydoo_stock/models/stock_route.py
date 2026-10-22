from odoo import fields, models


class StockRoute(models.Model):
    """A step or list of steps that can be used to transfer stock."""
    _name = 'cd.stock.route'

    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        index=True
    )
    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(required=True, default=0)

    step_ids = fields.Many2one('stock.route')


class StockRouteStep(models.Model):
    """A step in a stock.route."""
    _name = 'cd.stock.route.step'

    active = fields.Boolean(default=True)
    company_id = fields.Many2one(related='route_id.company_id')
    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(required=True, default=0)

    action = fields.Selection([('pull', 'Pull'), ('push', 'Push')], default='pull', required=True)
    route_id = fields.Many2one('stock.route', required=True, readonly=True)
