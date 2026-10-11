from odoo import fields, models


class ContactWebsite(models.Model):
    _name = 'cd.contact.website'
    _description = 'Website'
    _inherit = ['cd.contact.primaries_mixin']
    _rec_name = 'url'
    _order = 'is_primary desc, id'

    contact_info_id = fields.Many2one('cd.contact.info', required=True, ondelete='cascade')
    url = fields.Char(required=True)
    type = fields.Selection(
        [
            ('website', 'Website'),
            ('social', 'Social Media'),
        ],
        required=True, default='website',
    )
