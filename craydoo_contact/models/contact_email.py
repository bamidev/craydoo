from odoo import fields, models


class ContactEmail(models.Model):
    _name = 'cd.contact.email'
    _description = 'Email Address'
    _inherit = ['cd.contact.primaries_mixin', 'cd.contact.locked_mixin']
    _rec_name = 'address'
    _order = 'is_primary desc, id'

    contact_info = fields.Many2one('cd.contact.info', required=True, ondelete='cascade')
    address = fields.Char(required=True)
    locked = fields.Boolean(related='contact_info.locked', store=True)
