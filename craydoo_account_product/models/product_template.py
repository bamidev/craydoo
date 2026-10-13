from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'cd.product.template'

    income_account_id = fields.Many2one('cd.account.account')
    expense_account_id = fields.Many2one('cd.account.account')
