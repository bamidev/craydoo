from odoo import _, api, fields, models
from odoo.exceptions import UserError

INVOICE_FIELD_NAMES = [
    'name', 'debtor_id', 'language', 'date', 'due_date', 'currency_id',
    'company_id', 'invoice_line_ids',
]


class AccountInvoiceDraft(models.Model):
    """ Thin wrapper around `cd.account.invoice`, same shape as
    `cd.contact.mixin`/`cd.contact.info`: this is where an invoice is built
    up and configured with the accounts to post to, while the underlying
    `cd.account.invoice` holds the real (eventually locked) data.
    """
    _name = 'cd.account.invoice.draft'
    _description = 'Invoice Draft'

    invoice_id = fields.Many2one('cd.account.invoice', required=True, ondelete='cascade', copy=False)

    name = fields.Char(related='invoice_id.name', readonly=False, store=True)
    debtor_id = fields.Many2one(related='invoice_id.debtor_id', readonly=False)
    language = fields.Selection(related='invoice_id.language', readonly=False)
    date = fields.Date(related='invoice_id.date', readonly=False)
    due_date = fields.Date(related='invoice_id.due_date', readonly=False)
    currency_id = fields.Many2one(related='invoice_id.currency_id', readonly=False)
    company_id = fields.Many2one(related='invoice_id.company_id', readonly=False)
    invoice_line_ids = fields.One2many(related='invoice_id.invoice_line_ids', readonly=False)
    amount_untaxed = fields.Monetary(related='invoice_id.amount_untaxed', currency_field='currency_id')
    amount_tax = fields.Monetary(related='invoice_id.amount_tax', currency_field='currency_id')
    amount_total = fields.Monetary(related='invoice_id.amount_total', currency_field='currency_id')
    locked = fields.Boolean(related='invoice_id.locked')

    debit_account_id = fields.Many2one(
        'cd.account.account', default=lambda self: self._default_account('default_debit_account_id'))
    credit_account_id = fields.Many2one(
        'cd.account.account', default=lambda self: self._default_account('default_credit_account_id'))

    @api.model
    def _default_account(self, field):
        account = self.env.company[field]
        if account:
            return account
        param = self.env['ir.config_parameter'].sudo().get_int(f'craydoo_account.{field}', 0)
        return self.env['cd.account.account'].browse(param)

    @api.model
    def _default_credit_account(self):
        return self._default_account('default_credit_account_id')

    @api.model
    def _default_debit_account(self):
        return self._default_account('default_debit_account_id')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('invoice_id'):
                invoice_vals = {f: vals[f] for f in INVOICE_FIELD_NAMES if f in vals}
                vals['invoice_id'] = self.env['cd.account.invoice'].create(invoice_vals).id
        return super().create(vals_list)

    def action_post(self):
        for draft in self:
            if draft.invoice_id.locked:
                raise UserError(_("This invoice is already posted."))

            debit_account = draft.debit_account_id
            credit_account = draft.credit_account_id
            if not debit_account or not credit_account:
                raise UserError(_(
                    "No debit/credit account configured for this invoice, its "
                    "company, or the Accounting settings."))
            if debit_account.ledger_id != credit_account.ledger_id:
                raise UserError(_("The debit and credit accounts must belong to the same ledger."))
            ledger = debit_account.ledger_id

            invoice = draft.invoice_id
            invoice.debtor_id = invoice.debtor_id.create_locked_copy()
            if invoice.name == '/':
                invoice.name = self.env['ir.sequence'].next_by_code('cd.account.invoice') or '/'

            transfer = self.env['cd.account.transfer'].create({
                'ledger_id': ledger.id,
                'type': 'invoice',
                'amount': round(invoice.amount_total * 10 ** invoice.currency_id.decimal_places),
                'debit_account_id': debit_account.id,
                'credit_account_id': credit_account.id,
            })
            invoice.transfer_id = transfer.id
            invoice.date = transfer.date

            invoice.locked = True
