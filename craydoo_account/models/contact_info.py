from odoo import models

ADDRESS_FIELD_NAMES = ['street', 'house', 'address_extra', 'city', 'zip', 'state_id', 'country_id']


class ContactInfo(models.Model):
    _inherit = 'cd.contact.info'

    def get_address(self):
        """ Find-or-create the `cd.account.address` matching this contact's
        current details, interning it so repeated calls with the same
        values share one row.
        """
        self.ensure_one()
        vals = {
            field: self[field].id if self._fields[field].type == 'many2one' else self[field]
            for field in ADDRESS_FIELD_NAMES
        }
        # `display_name`, not `name` - e.g. a person's `name` is just their
        # last name, while `display_name` is the full "Mr. John van Doe"
        # composed from salutation/first_name/infix/name.
        vals['name'] = self.display_name
        Address = self.env['cd.account.address'].sudo()
        address = Address.search([(field, '=', value) for field, value in vals.items()], limit=1)
        return address or Address.create({**vals, 'source_id': self.id})
