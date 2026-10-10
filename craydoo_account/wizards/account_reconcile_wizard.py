from odoo import Command, _, fields, models
from odoo.exceptions import UserError


class AccountReconcileWizard(models.TransientModel):
    """ Matches one open debit transfer against one open credit transfer on
    `account_id`, for `amount` (at most the smaller of the two's
    `residual_amount`). If that fully settles both sides, every
    `cd.account.reconcile.part` that ever referenced either transfer is
    grouped into one `cd.account.reconcile`.
    """
    _name = 'cd.account.reconcile.wizard'
    _description = 'Reconcile'

    account_id = fields.Many2one(
        'cd.account.account', required=True, domain=[('allow_reconciles', '=', True)])
    debit_transfer_id = fields.Many2one(
        'cd.account.transfer', required=True,
        domain="[('debit_account_id', '=', account_id), ('residual_amount', '!=', 0)]")
    credit_transfer_id = fields.Many2one(
        'cd.account.transfer', required=True,
        domain="[('credit_account_id', '=', account_id), ('residual_amount', '!=', 0)]")
    amount = fields.Integer(required=True)

    def action_reconcile(self):
        self.ensure_one()
        debit, credit = self.debit_transfer_id, self.credit_transfer_id
        if self.amount <= 0:
            raise UserError(_("The amount to reconcile must be positive."))
        if self.amount > debit.residual_amount or self.amount > credit.residual_amount:
            raise UserError(_("Can't reconcile more than either transfer's residual amount."))

        self.env['cd.account.reconcile.part'].create({
            'account_id': self.account_id.id,
            'debit_transfer_id': debit.id,
            'credit_transfer_id': credit.id,
            'amount': self.amount,
        })

        if debit.residual_amount == 0 and credit.residual_amount == 0:
            parts = self.env['cd.account.reconcile.part'].search([
                '|', ('debit_transfer_id', '=', debit.id), ('credit_transfer_id', '=', credit.id),
            ])
            self.env['cd.account.reconcile'].create({'part_ids': [Command.set(parts.ids)]})

        return {'type': 'ir.actions.act_window_close'}
