from odoo import api, fields, models


class ContactPhone(models.Model):
    _name = 'cd.contact.phone'
    _description = 'Phone Number'
    _inherit = ['cd.contact.primaries_mixin', 'cd.contact.locked_mixin']
    _rec_name = 'number'
    _order = 'is_primary desc, id'

    contact_info_id = fields.Many2one('cd.contact.info', required=True, ondelete='cascade')
    number = fields.Char(required=True)
    type = fields.Selection(
        [
            ('phone', 'Phone'),
            ('mobile', 'Mobile'),
            ('fax', 'Fax'),
        ],
        required=True, default='phone',
    )
    locked = fields.Boolean(related='contact_info_id.locked', store=True)

    @api.constrains('number')
    def _check_number(self):
        for phone in self:
            if phone.number:
                phone._phone_format(fname='number', raise_exception=True)
