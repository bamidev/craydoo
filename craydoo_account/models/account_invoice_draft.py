from odoo import _, api, fields, models
from odoo.exceptions import UserError

INVOICE_FIELD_NAMES = [
    'name', 'language_id', 'date', 'due_date', 'currency_id',
    'company_id', 'invoice_line_ids',
]


class AccountInvoiceDraft(models.Model):
    """ Thin wrapper around `cd.account.invoice`, same shape as
    `cd.contact.mixin`/`cd.contact.info`: this is where an invoice is built
    up and configured with the accounts to post to, while the underlying
    `cd.account.invoice` holds the real (eventually locked) data.
    """
    _name = 'cd.account.invoice.draft'
    _inherits = {'cd.account.invoice': 'invoice_id'}
    _description = 'Invoice Draft'

    invoice_id = fields.Many2one('cd.account.invoice', required=True, ondelete='cascade', copy=False)
    billing_contact_id = fields.Many2one('cd.contact.info', required=True, string="Billed to")

    debit_account_id = fields.Many2one(
        'cd.account.account', default=lambda self: self._default_account('default_receivable_account_id'))
    credit_account_id = fields.Many2one(
        'cd.account.account', default=lambda self: self._default_account('default_income_account_id'))

    @api.model
    def _default_account(self, field):
        account = self.env.company[field]
        if account:
            return account
        param = self.env['ir.config_parameter'].sudo().get_int(f'craydoo_account.{field}', 0)
        return self.env['cd.account.account'].browse(param)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('invoice_id'):
                invoice_vals = {f: vals[f] for f in INVOICE_FIELD_NAMES if f in vals}
                contact = self.env['cd.contact.info'].browse(vals.get('billing_contact_id'))
                invoice_vals['billing_address_id'] = contact.get_address().id
                invoice_vals.setdefault('language_id', contact.primary_language_id.id)
                vals['invoice_id'] = self.env['cd.account.invoice'].create(invoice_vals).id
        return super().create(vals_list)

    def _tax_legs(self, invoice):
        """ `(account, amount)` pairs (amount in minor currency units) for
        every tax used on `invoice`, split across that tax's configured
        `cd.account.tax.allocation.line`s by `percentage`. The last
        allocation line of each tax absorbs that tax's own rounding, so
        the legs for one tax always sum to exactly that tax's amount.
        """
        legs = []
        for tax, amount in invoice._tax_breakdown().items():
            if not amount:
                continue
            allocations = tax.invoice_line_ids
            if not allocations:
                raise UserError(_(
                    "%(tax)s has no configured account allocation - set up where "
                    "its amount should post before invoicing with it.", tax=tax.name))

            tax_amount = amount
            allocated = 0
            for i, allocation in enumerate(allocations):
                if not allocation.account_id:
                    raise UserError(_(
                        "One of %(tax)s's allocations has no destination account.", tax=tax.name))
                if i == len(allocations) - 1:
                    portion = tax_amount - allocated
                else:
                    portion = round(tax_amount * allocation.percentage / 100.0)
                allocated += portion
                legs.append((allocation.account_id, portion))
        return legs

    def _revenue_legs(self, invoice, revenue_amount, fallback_account):
        """ `(account, amount)` pairs (amount in minor currency units) for
        `invoice`'s pre-tax revenue (`revenue_amount`), split across its
        lines by the account each one resolves via
        `cd.account.invoice.line.get_default_account_id` (falling back
        to `fallback_account` when a line doesn't resolve one), then
        grouped - so e.g. two lines resolving to the same account end up
        as one leg, not two. The last line absorbs whatever's left of
        `revenue_amount` after the others, so the legs always sum to
        exactly `revenue_amount` (a line's own `amount_revenue` can drift
        from that by a cent or two, since tax is rounded per-tax for
        `_tax_legs` but per-line there).
        """
        lines = invoice.invoice_line_ids
        totals = {}
        allocated = 0
        for i, line in enumerate(lines):
            account = line.get_default_account_id() or fallback_account
            if not account:
                raise UserError(_(
                    "%(line)s has no account configured to post to.", line=line.name))
            if i == len(lines) - 1:
                portion = revenue_amount - allocated
            else:
                portion = line.amount_revenue
            allocated += portion
            totals[account] = totals.get(account, 0) + portion
        return list(totals.items())

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
            ledger = debit_account.ledger_id

            invoice = draft.invoice_id
            invoice.billing_address_id = draft.billing_contact_id.get_address()
            if invoice.name == '/':
                invoice.name = self.env['ir.sequence'].next_by_code('cd.account.invoice') or '/'

            tax_legs = self._tax_legs(invoice)
            revenue_amount = invoice.amount_total - sum(amount for _account, amount in tax_legs)
            revenue_legs = self._revenue_legs(invoice, revenue_amount, credit_account)

            legs = revenue_legs + tax_legs
            for account, _amount in legs:
                if account.ledger_id != ledger:
                    raise UserError(_(
                        "%(account)s doesn't belong to the same ledger as %(debit_account)s.",
                        account=account.name, debit_account=debit_account.name))

            last_transfer = None
            for account, amount in legs:
                transfer_draft = self.env['cd.account.transfer.draft'].create({
                    'date': fields.Date.context_today(self),
                    'ledger_id': ledger.id,
                    'type': 'invoice',
                    'amount': amount,
                    'currency_id': invoice.currency_id.id,
                    'debit_account_id': debit_account.id,
                    'credit_account_id': account.id,
                    'backward_link_id': last_transfer.id if last_transfer else False,
                    'billing_contact_id': draft.billing_contact_id.id,
                })
                last_transfer = transfer_draft.action_post()

            invoice.transfer_id = last_transfer.id
            invoice.date = last_transfer.date

            invoice.locked = True
            draft.unlink()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'cd.account.invoice',
            'view_mode': 'form',
            'res_id': invoice.id,
        }
