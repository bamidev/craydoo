from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    account_transfer_convert_immediately = fields.Boolean(
        string="Convert foreign-currency transfers immediately",
        config_parameter='craydoo_account.transfer_convert_immediately')
