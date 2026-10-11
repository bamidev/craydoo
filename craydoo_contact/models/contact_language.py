from odoo import fields, models


class ContactLanguage(models.Model):
    _name = 'cd.contact.language'
    _description = 'Language'
    _inherit = ['cd.contact.primaries_mixin', 'cd.contact.locked_mixin']
    _rec_name = 'language_id'
    _order = 'is_primary desc, id'

    contact_info_id = fields.Many2one('cd.contact.info', required=True, ondelete='cascade')
    language_id = fields.Many2one('res.lang', required=True)
    locked = fields.Boolean(related='contact_info_id.locked', store=True)
