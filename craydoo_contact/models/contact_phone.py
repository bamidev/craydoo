from odoo import fields, models


class ContactPhone(models.Model):
    _name = 'cd.contact.phone'
    _description = 'Phone Number'
    _inherit = ['cd.contact.primaries_mixin', 'cd.contact.locked_mixin']
    _rec_name = 'number'
    _order = 'is_primary desc, id'

    contact_info = fields.Many2one('cd.contact.info', required=True, ondelete='cascade')
    number = fields.Char(required=True)
    type = fields.Selection(
        [
            ('phone', 'Phone'),
            ('mobile', 'Mobile'),
            ('fax', 'Fax'),
        ],
        required=True, default='phone',
    )
    locked = fields.Boolean(related='contact_info.locked', store=True)
