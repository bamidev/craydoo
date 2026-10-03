from odoo import fields, models


class ContactContact(models.Model):
    _name = 'cd.contact.contact'
    _description = 'Contact'
    _inherit = ['cd.contact.mixin']
    _order = 'name'

    function = fields.Char(string='Job Position')
