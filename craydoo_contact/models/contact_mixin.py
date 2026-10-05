from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

INFO_FIELD_NAMES = [
    'name', 'emails', 'phones', 'websites', 'street', 'house', 'address_extra',
    'city', 'zip', 'state', 'country', 'tz', 'company_id',
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

    contact_info = fields.Many2one(
        'cd.contact.info', string='Contact Information',
        required=True, ondelete='restrict', copy=False, readonly=True,
    )

    name = fields.Char(related='contact_info.name', readonly=False, store=True)
    display_name = fields.Char(compute='_compute_display_name', store=True)
    main_email = fields.Char(related='contact_info.main_email', readonly=False)
    main_phone = fields.Char(related='contact_info.main_phone', readonly=False)
    emails = fields.One2many(related='contact_info.emails', readonly=False)
    phones = fields.One2many(related='contact_info.phones', readonly=False)
    websites = fields.One2many(related='contact_info.websites', readonly=False)
    street = fields.Char(related='contact_info.street', readonly=False)
    house = fields.Char(related='contact_info.house', readonly=False)
    address_extra = fields.Char(related='contact_info.address_extra', readonly=False, string="Apt/Suite/Unit/Other")
    city = fields.Char(related='contact_info.city', readonly=False)
    zip = fields.Char(related='contact_info.zip', readonly=False)
    state = fields.Many2one(related='contact_info.state', readonly=False)
    country = fields.Many2one(related='contact_info.country', readonly=False)
    tz = fields.Selection(related='contact_info.tz', readonly=False)
    company_id = fields.Many2one(related='contact_info.company_id', readonly=False)

    @api.depends('name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.name

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('contact_info'):
                info_vals = {f: vals[f] for f in INFO_FIELD_NAMES if f in vals}
                vals['contact_info'] = self.env['cd.contact.info'].create(info_vals).id
        return super().create(vals_list)

    @api.constrains('contact_info')
    def _check_contact_info_unlocked(self):
        for rec in self:
            if rec.contact_info.locked:
                raise ValidationError(_(
                    "%(contact)s is locked and can no longer be linked to %(record)s.",
                    contact=rec.contact_info.display_name, record=rec.display_name,
                ))
