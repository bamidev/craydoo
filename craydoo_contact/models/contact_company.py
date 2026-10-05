from odoo import fields, models


class ContactCompany(models.Model):
    _name = 'cd.contact.company'
    _description = 'Company'
    _inherit = ['cd.contact.mixin']
    _order = 'name'

    name = fields.Char(required=True)
    vat_id = fields.Char(string='Tax ID')
