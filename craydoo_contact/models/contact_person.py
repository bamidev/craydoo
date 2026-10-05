from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ContactPerson(models.Model):
    _name = 'cd.contact.person'
    _description = 'Person'
    _inherit = ['cd.contact.mixin']
    _order = 'name, first_name'

    function = fields.Char(string='Job Position')

    salutation = fields.Selection([
        ('mr', 'Mr.'),
        ('mrs', 'Mrs.'),
        ('ms', 'Ms.'),
        ('mx', 'Mx.'),
        ('dr', 'Dr.'),
    ])
    first_name = fields.Char()
    prefix = fields.Char()

    @api.depends('salutation', 'first_name', 'prefix', 'name')
    def _compute_display_name(self):
        salutations = dict(self._fields['salutation'].selection)
        for person in self:
            parts = [
                salutations.get(person.salutation), person.first_name,
                person.prefix, person.name,
            ]
            person.display_name = ' '.join(p for p in parts if p)

    @api.constrains('first_name', 'name')
    def _check_first_or_last_name(self):
        for person in self:
            if not (person.first_name or person.name):
                raise ValidationError(_("Set at least a first or last name."))
