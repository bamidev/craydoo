from odoo import fields, models


class AccountInvoiceLine(models.Model):
    _inherit = 'cd.account.invoice.line'

    product_id = fields.Many2one('cd.product.variant')

    def _get_default_account_id(self):
        """ Resolves the account from the line's product template, falling
        back to its category - the same product-then-category fallback
        chain vanilla Odoo uses - before giving up to `super()`'s
        "nothing at this level" default. `cd.product.variant` has no
        account of its own - only the template/category do.
        """
        self.ensure_one()
        if not self.product_id:
            return super()._get_default_account_id()
        template = self.product_id.template_id
        return (
            template.income_account_id
            or template.category_id.income_account_id
            or super()._get_default_account_id()
        )
