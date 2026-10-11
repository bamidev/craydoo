from odoo import api, fields, models
from odoo.tools.date_utils import all_timezones


def _tz_get(self):
    return [(tz, tz) for tz in all_timezones]


class ContactInfo(models.Model):
    """ Raw contact information.

    `cd.contact.person` and `cd.contact.company` are the editable,
    user-facing records; each of them points to one `cd.contact.info` row
    that actually carries the data.
    """
    _name = 'cd.contact.info'
    _description = 'Contact Information'
    _inherit = ['cd.contact.address_mixin']
    _order = 'name'
    _rec_name = 'display_name'

    name = fields.Char(index=True, copy=True)
    display_name = fields.Char(compute='_compute_display_name', store=True)
    active = fields.Boolean(default=True)

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

    tz = fields.Selection(_tz_get, string='Timezone')

    company_id = fields.Many2one('res.company', string='Company')
