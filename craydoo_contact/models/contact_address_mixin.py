from odoo import fields, models


class ContactAddressMixin(models.AbstractModel):
    """ Shared postal-address fields - used by `cd.contact.info`, and by
    `cd.account.address` in craydoo_account (a frozen snapshot of the
    subset of a contact's details relevant to invoicing), so the two stay
    structurally identical.
    """
    _name = 'cd.contact.address_mixin'
    _description = 'Address Mixin'

    name = fields.Char()
    street = fields.Char()
    house = fields.Char()
    address_extra = fields.Char()
    city = fields.Char()
    zip = fields.Char(string='ZIP')
    state_id = fields.Many2one(
        'res.country.state', ondelete='restrict',
        domain="[('country_id', '=?', country_id)]",
    )
    country_id = fields.Many2one('res.country', ondelete='restrict')
