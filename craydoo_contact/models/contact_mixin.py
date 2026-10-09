from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

INFO_FIELD_NAMES = [
    'name', 'email_ids', 'phone_ids', 'website_ids', 'street', 'house', 'address_extra',
    'city', 'zip', 'state_id', 'country_id', 'tz', 'company_id',
]


class ContactMixin(models.AbstractModel):
    """ Shared behaviour for `cd.contact.person` and `cd.contact.company`:
    both are thin, freely-editable wrappers around one `cd.contact.info`
    record.
    """
    _name = 'cd.contact.mixin'
    _description = 'Contact Mixin'
    _inherit = ['mail.thread']
    _rec_name = 'display_name'

    contact_info_id = fields.Many2one(
        'cd.contact.info', string='Contact Information',
        required=True, ondelete='restrict', copy=False, readonly=True,
    )

    display_name = fields.Char(compute='_compute_display_name')
    name = fields.Char(related='contact_info_id.name', readonly=False)
    main_email = fields.Char(related='contact_info_id.main_email', readonly=False)
    main_phone = fields.Char(related='contact_info_id.main_phone', readonly=False)
    email_ids = fields.One2many(related='contact_info_id.email_ids', readonly=False)
    phone_ids = fields.One2many(related='contact_info_id.phone_ids', readonly=False)
    website_ids = fields.One2many(related='contact_info_id.website_ids', readonly=False)
    street = fields.Char(related='contact_info_id.street', readonly=False)
    house = fields.Char(related='contact_info_id.house', readonly=False)
    address_extra = fields.Char(
        related='contact_info_id.address_extra', readonly=False, string="Apt/Suite/Unit/Other")
    city = fields.Char(related='contact_info_id.city', readonly=False)
    zip = fields.Char(related='contact_info_id.zip', readonly=False)
    state_id = fields.Many2one(related='contact_info_id.state_id', readonly=False)
    country_id = fields.Many2one(related='contact_info_id.country_id', readonly=False)
    tz = fields.Selection(related='contact_info_id.tz', readonly=False)
    company_id = fields.Many2one(related='contact_info_id.company_id', readonly=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('contact_info_id'):
                info_vals = {f: vals[f] for f in INFO_FIELD_NAMES if f in vals}
                vals['contact_info_id'] = self.env['cd.contact.info'].create(info_vals).id
        return super().create(vals_list)

    @api.depends('name')
    def _compute_display_name(self):
        for this in self:
            this.display_name = this.contact_info_id.display_name

    @api.constrains('contact_info_id')
    def _check_contact_info_unlocked(self):
        for rec in self:
            if rec.contact_info_id.locked:
                raise ValidationError(_(
                    "%(contact)s is locked and can no longer be linked to %(record)s.",
                    contact=rec.contact_info_id.display_name, record=rec.display_name,
                ))
