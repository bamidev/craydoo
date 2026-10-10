from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ..fields import UInteger


class AccountReconcile(models.Model):
    _name = 'cd.account.reconcile'
    _description = 'Reconcile'

    part_ids = fields.Many2many('cd.account.reconcile.part')


class AccountReconcilePart(models.Model):
    _name = 'cd.account.reconcile.part'
    _description = 'Reconcile Part'

    account_id = fields.Many2one('cd.account.account', required=True, readonly=True)
    debit_transfer_id = fields.Many2one('cd.account.transfer', required=True, readonly=True)
    credit_transfer_id = fields.Many2one('cd.account.transfer', required=True, readonly=True)
    amount = UInteger(required=True, readonly=True)

    @api.constrains('account_id', 'debit_transfer_id', 'credit_transfer_id')
    def _check_accounts(self):
        for rec in self:
            if not rec.account_id.allow_reconciles:
                raise ValidationError(_("%(account)s doesn't allow reconciliation.", account=rec.account_id.name))
            if rec.debit_transfer_id.debit_account_id != rec.account_id:
                raise ValidationError(_(
                    "The debit transfer must debit %(account)s.", account=rec.account_id.name))
            if rec.credit_transfer_id.credit_account_id != rec.account_id:
                raise ValidationError(_(
                    "The credit transfer must credit %(account)s.", account=rec.account_id.name))
