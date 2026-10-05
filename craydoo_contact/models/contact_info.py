from odoo import api, fields, models
from odoo.tools.date_utils import all_timezones


def _tz_get(self):
    return [(tz, tz) for tz in all_timezones]


class ContactInfo(models.Model):
    """ Raw contact information.

    `cd.contact.person` and `cd.contact.company` are the editable,
    user-facing records; each of them points to one `cd.contact.info` row
    that actually carries the data. A `cd.contact.info` record becomes
    immutable once `locked` is set, which craydoo_account relies on to
    freeze the contact details that were in effect when an invoice was
    posted.
    """
    _name = 'cd.contact.info'
    _description = 'Contact Information'
    _inherit = ['cd.contact.locked_mixin']
    _order = 'name'

    name = fields.Char(index=True, copy=True)
    active = fields.Boolean(default=True)
    locked = fields.Boolean(default=False, copy=False, index=True)
    locked_copy = fields.Many2one('cd.contact.info', copy=False)

    emails = fields.One2many('cd.contact.email', 'contact_info', string='Emails')
    phones = fields.One2many('cd.contact.phone', 'contact_info', string='Phone Numbers')
    websites = fields.One2many('cd.contact.website', 'contact_info', string='Websites')
    main_email = fields.Char(
        compute='_compute_main_email', inverse='_inverse_main_email', string='Email')
    main_phone = fields.Char(
        compute='_compute_main_phone', inverse='_inverse_main_phone', string='Phone')

    @api.depends('emails.address', 'emails.is_primary')
    def _compute_main_email(self):
        for info in self:
            email = info.emails.filtered('is_primary')[:1] or info.emails[:1]
            info.main_email = email.address

    def _inverse_main_email(self):
        for info in self:
            email = info.emails.filtered('is_primary')[:1] or info.emails[:1]
            if email:
                email.address = info.main_email
            else:
                self.env['cd.contact.email'].create({
                    'contact_info': info.id, 'address': info.main_email, 'is_primary': True,
                })

    @api.depends('phones.number', 'phones.is_primary')
    def _compute_main_phone(self):
        for info in self:
            phone = info.phones.filtered('is_primary')[:1] or info.phones[:1]
            info.main_phone = phone.number

    def _inverse_main_phone(self):
        for info in self:
            phone = info.phones.filtered('is_primary')[:1] or info.phones[:1]
            if phone:
                phone.number = info.main_phone
            else:
                self.env['cd.contact.phone'].create({
                    'contact_info': info.id, 'number': info.main_phone, 'is_primary': True,
                })

    street = fields.Char()
    house = fields.Char()
    address_extra = fields.Char()
    city = fields.Char()
    zip = fields.Char(string='ZIP')
    state = fields.Many2one(
        'res.country.state', ondelete='restrict',
        domain="[('country_id', '=?', country)]",
    )
    country = fields.Many2one('res.country', ondelete='restrict')

    tz = fields.Selection(_tz_get, string='Timezone')

    company_id = fields.Many2one('res.company', string='Company')

    def write(self, vals):
        res = super().write(vals)
        if set(vals) - {'locked', 'locked_copy'}:
            for info in self:
                if info.locked_copy:
                    info.locked_copy = False
        return res

    def create_locked_copy(self):
        self.ensure_one()
        if self.locked:
            return self
        if not self.locked_copy:
            self.locked_copy = self.copy({'locked': True})
        return self.locked_copy
