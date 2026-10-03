from odoo import api, fields, models


class ContactPrimariesMixin(models.AbstractModel):
    """ Shared behaviour for records where at most one sibling (grouped by
    `_primary_group_field`) can have `is_primary` set at a time.
    """
    _name = 'cd.contact.primaries_mixin'
    _description = 'Contact Primaries Mixin'

    _primary_group_field = 'contact_info'

    is_primary = fields.Boolean(required=True, default=False)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.filtered('is_primary')._reset_other_primaries()
        return records

    def write(self, vals):
        res = super().write(vals)
        if vals.get('is_primary'):
            self.filtered('is_primary')._reset_other_primaries()
        return res

    def _reset_other_primaries(self):
        for rec in self:
            group = rec[self._primary_group_field]
            others = self.search([
                (self._primary_group_field, '=', group.id),
                ('id', '!=', rec.id),
                ('is_primary', '=', True),
            ])
            others.write({'is_primary': False})
