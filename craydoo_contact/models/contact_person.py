from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ContactPerson(models.Model):
    _name = 'cd.contact.person'
    _description = 'Person'
    _inherit = ['cd.contact.mixin']
    _order = 'name, first_name'

    first_name = fields.Char()
    function = fields.Char(string='Job Position')
    infix = fields.Char()
    salutation = fields.Selection([
        ('mr', 'Mr.'),
        ('mrs', 'Mrs.'),
        ('ms', 'Ms.'),
        ('mx', 'Mx.'),
        ('dr', 'Dr.'),
    ])

    @api.depends('salutation', 'first_name', 'infix', 'name')
    def _compute_display_name(self):
        salutations = dict(self._fields['salutation'].selection)
        for person in self:
            parts = [
                salutations.get(person.salutation), person.first_name,
                person.infix, person.name,
            ]
            person.contact_info.display_name = ' '.join(p for p in parts if p)
            person.display_name = person.contact_info.display_name

    @api.constrains('first_name', 'name')
    def _check_first_or_last_name(self):
        for person in self:
            if not (person.first_name or person.name):
                raise ValidationError(_("Set at least a first or last name."))
