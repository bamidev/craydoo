from odoo import fields, models


class ContactCompany(models.Model):
    _name = 'cd.contact.company'
    _description = 'Company'
    _inherit = ['cd.contact.mixin']
    _order = 'name'

    vat_id = fields.Char(string='Tax ID')
