from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.mail import email_normalize


class ContactEmail(models.Model):
    _name = 'cd.contact.email'
    _description = 'Email Address'
    _inherit = ['cd.contact.primaries_mixin', 'cd.contact.locked_mixin']
    _rec_name = 'address'
    _order = 'is_primary desc, id'

    contact_info_id = fields.Many2one('cd.contact.info', required=True, ondelete='cascade')
    address = fields.Char(required=True)
    locked = fields.Boolean(related='contact_info_id.locked', store=True)

    @api.constrains('address')
    def _check_address(self):
        for email in self:
            if email.address and not email_normalize(email.address):
                raise ValidationError(_("%s is not a valid email address.", email.address))
