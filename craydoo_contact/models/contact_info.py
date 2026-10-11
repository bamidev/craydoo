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
    _rec_name = 'display_name'

    name = fields.Char(index=True, copy=True)
    display_name = fields.Char(compute='_compute_display_name', store=True)
    active = fields.Boolean(default=True)
    locked = fields.Boolean(default=False, copy=False, index=True)
    locked_copy_id = fields.Many2one('cd.contact.info', copy=False)
    source_id = fields.Many2one('cd.contact.info', readonly=True, index=True, copy=False)

    email_ids = fields.One2many('cd.contact.email', 'contact_info_id', string='Emails')
    phone_ids = fields.One2many('cd.contact.phone', 'contact_info_id', string='Phone Numbers')
    website_ids = fields.One2many('cd.contact.website', 'contact_info_id', string='Websites')
    language_ids = fields.One2many('cd.contact.language', 'contact_info_id', string='Languages')
    main_email = fields.Char(
        compute='_compute_main_email', inverse='_inverse_main_email', string='Email')
    main_phone = fields.Char(
        compute='_compute_main_phone', inverse='_inverse_main_phone', string='Phone')
    primary_language_id = fields.Many2one(
        'res.lang', compute='_compute_primary_language_id', inverse='_inverse_primary_language_id',
        string='Language')

    @api.depends('name')
    def _compute_display_name(self):
        for info in self:
            info.display_name = info.name

    @api.depends('email_ids.address', 'email_ids.is_primary')
    def _compute_main_email(self):
        for info in self:
            email = info.email_ids.filtered('is_primary')[:1] or info.email_ids[:1]
            info.main_email = email.address

    def _inverse_main_email(self):
        if not self.main_email:
            return

        for info in self:
            email = info.email_ids.filtered('is_primary')[:1] or info.email_ids[:1]
            if email:
                email.address = info.main_email
            else:
                self.env['cd.contact.email'].create({
                    'contact_info_id': info.id, 'address': info.main_email, 'is_primary': True,
                })

    @api.depends('phone_ids.number', 'phone_ids.is_primary')
    def _compute_main_phone(self):
        for info in self:
            phone = info.phone_ids.filtered('is_primary')[:1] or info.phone_ids[:1]
            info.main_phone = phone.number

    def _inverse_main_phone(self):
        if not self.main_phone:
            return

        for info in self:
            phone = info.phone_ids.filtered('is_primary')[:1] or info.phone_ids[:1]
            if phone:
                phone.number = info.main_phone
            else:
                self.env['cd.contact.phone'].create({
                    'contact_info_id': info.id, 'number': info.main_phone, 'is_primary': True,
                })

    @api.depends('language_ids.language_id', 'language_ids.is_primary')
    def _compute_primary_language_id(self):
        for info in self:
            language = info.language_ids.filtered('is_primary')[:1] or info.language_ids[:1]
            info.primary_language_id = language.language_id

    def _inverse_primary_language_id(self):
        if not self.primary_language_id:
            return

        for info in self:
            language = info.language_ids.filtered('is_primary')[:1] or info.language_ids[:1]
            if language:
                language.language_id = info.primary_language_id
            else:
                self.env['cd.contact.language'].create({
                    'contact_info_id': info.id, 'language_id': info.primary_language_id.id,
                    'is_primary': True,
                })

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

    tz = fields.Selection(_tz_get, string='Timezone')

    company_id = fields.Many2one('res.company', string='Company')

    def write(self, vals):
        res = super().write(vals)
        if set(vals) - {'locked', 'locked_copy_id'}:
            for info in self:
                if info.locked_copy_id:
                    info.locked_copy_id = False
        return res

    def create_locked_copy(self):
        self.ensure_one()
        if self.locked:
            return self
        if not self.locked_copy_id:
            self.locked_copy_id = self.copy({'locked': True, 'source_id': self.id})
        return self.locked_copy_id
