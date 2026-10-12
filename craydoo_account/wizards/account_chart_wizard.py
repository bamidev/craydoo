from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountChartWizard(models.TransientModel):
    """ Instantiates a `cd.account.chart` template as real, ledger-bound
    `cd.account.account` records (the chart itself only carries portable
    code/name data - which ledger they belong to is chosen here, at apply
    time), then wires the resulting debit/credit accounts up as the
    company's sales defaults.

    Applying onto a ledger that already has accounts is allowed, but asks
    for confirmation first (`view_account_chart_wizard_confirm`), since
    it's rarely intentional.
    """
    _name = 'cd.account.chart.wizard'
    _description = 'Apply Chart of Accounts'

    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company)
    chart_id = fields.Many2one('cd.account.chart', required=True)
    ledger_id = fields.Many2one(
        'cd.account.ledger', required=True, default=lambda self: self.env.company.account_ledger_id)

    def action_apply(self):
        self.ensure_one()
        entries = self.chart_id.account_ids
        if not entries:
            raise UserError(_("This chart of accounts has no accounts to create."))
        if not self.env.context.get('force_apply') and self.env['cd.account.account'].search_count(
                [('ledger_id', '=', self.ledger_id.id)]):
            return {
                'type': 'ir.actions.act_window',
                'name': _("Confirm"),
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'view_id': self.env.ref('craydoo_account.view_account_chart_wizard_confirm').id,
                'target': 'new',
            }

        existing_by_code = {
            account.code: account
            for account in self.env['cd.account.account'].search([('ledger_id', '=', self.ledger_id.id)])
        }

        account_by_entry_id = {}
        to_create = []
        for entry in entries:
            existing = existing_by_code.get(entry.code)
            if existing:
                account_by_entry_id[entry.id] = existing.id
            else:
                to_create.append(entry)

        if to_create:
            accounts = self.env['cd.account.account'].create([{
                'ledger_id': self.ledger_id.id,
                'code': entry.code,
                'name': entry.name,
                'allow_reconciles': entry.allow_reconciles,
            } for entry in to_create])
            account_by_entry_id.update(zip([entry.id for entry in to_create], accounts.ids))

        self.company_id.account_ledger_id = self.ledger_id
        chart = self.chart_id
        if chart.default_debit_account_id:
            self.company_id.default_debit_account_id = account_by_entry_id[
                chart.default_debit_account_id.id]
        if chart.default_credit_account_id:
            self.company_id.default_credit_account_id = account_by_entry_id[
                chart.default_credit_account_id.id]

        return {
            'type': 'ir.actions.act_window',
            'name': _("Accounts"),
            'res_model': 'cd.account.account',
            'view_mode': 'list,form',
            'domain': [('id', 'in', list(account_by_entry_id.values()))],
        }
