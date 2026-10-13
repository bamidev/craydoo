from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = 'cd.product.category'

    income_account_id = fields.Many2one('cd.account.account')
    expense_account_id = fields.Many2one('cd.account.account')
