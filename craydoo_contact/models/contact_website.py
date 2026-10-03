from odoo import fields, models


class ContactWebsite(models.Model):
    _name = 'cd.contact.website'
    _description = 'Website'
    _inherit = ['cd.contact.locked_mixin']
    _rec_name = 'url'

    contact_info = fields.Many2one('cd.contact.info', required=True, ondelete='cascade')
    url = fields.Char(required=True)
    type = fields.Selection(
        [
            ('website', 'Website'),
            ('social', 'Social Media'),
        ],
        required=True, default='website',
    )
    locked = fields.Boolean(related='contact_info.locked', store=True)
