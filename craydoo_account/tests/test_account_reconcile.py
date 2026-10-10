from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAccountReconcile(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ledger = cls.env['cd.account.ledger'].create({'name': 'Test Ledger'})
        cls.receivable = cls.env['cd.account.account'].create({
            'name': 'Receivable', 'code': '1100', 'ledger_id': ledger.id, 'allow_reconciles': True,
        })
        cls.revenue = cls.env['cd.account.account'].create({
            'name': 'Revenue', 'code': '8000', 'ledger_id': ledger.id,
        })
        cls.bank = cls.env['cd.account.account'].create({
            'name': 'Bank', 'code': '1000', 'ledger_id': ledger.id,
        })
        cls.ledger = ledger

    def _post(self, debit_account, credit_account, amount):
        return self.env['cd.account.transfer'].create({
            'date': '2020-01-01', 'ledger_id': self.ledger.id, 'type': 'invoice', 'amount': amount,
            'debit_account_id': debit_account.id, 'credit_account_id': credit_account.id,
        })

    def test_part_requires_allow_reconciles(self):
        invoice = self._post(self.receivable, self.revenue, 1000)
        payment = self._post(self.bank, self.receivable, 1000)
        with self.assertRaises(ValidationError):
            self.env['cd.account.reconcile.part'].create({
                'account_id': self.revenue.id, 'debit_transfer_id': invoice.id,
                'credit_transfer_id': payment.id, 'amount': 1000,
            })

    def test_part_requires_matching_debit_side(self):
        invoice = self._post(self.receivable, self.revenue, 1000)
        other_invoice = self._post(self.receivable, self.revenue, 500)
        with self.assertRaises(ValidationError):
            self.env['cd.account.reconcile.part'].create({
                'account_id': self.receivable.id, 'debit_transfer_id': other_invoice.id,
                'credit_transfer_id': invoice.id, 'amount': 500,
            })

    def test_residual_amount_updates_on_both_sides(self):
        invoice = self._post(self.receivable, self.revenue, 1000)
        payment = self._post(self.bank, self.receivable, 1000)
        self.assertEqual(invoice.residual_amount, 1000)
        self.assertEqual(payment.residual_amount, 1000)

        self.env['cd.account.reconcile.part'].create({
            'account_id': self.receivable.id, 'debit_transfer_id': invoice.id,
            'credit_transfer_id': payment.id, 'amount': 1000,
        })
        self.assertEqual(invoice.residual_amount, 0)
        self.assertEqual(payment.residual_amount, 0)

    def test_wizard_fully_settles_and_groups_into_reconcile(self):
        invoice = self._post(self.receivable, self.revenue, 1000)
        payment = self._post(self.bank, self.receivable, 1000)

        wizard = self.env['cd.account.reconcile.wizard'].create({
            'account_id': self.receivable.id,
            'debit_transfer_id': invoice.id,
            'credit_transfer_id': payment.id,
            'amount': 1000,
        })
        wizard.action_reconcile()

        self.assertEqual(invoice.residual_amount, 0)
        self.assertEqual(payment.residual_amount, 0)

        reconciles = self.env['cd.account.reconcile'].search([])
        self.assertEqual(len(reconciles), 1)
        self.assertEqual(len(reconciles.part_ids), 1)
        self.assertEqual(reconciles.part_ids.debit_transfer_id, invoice)
        self.assertEqual(reconciles.part_ids.credit_transfer_id, payment)

    def test_wizard_partial_match_does_not_create_reconcile(self):
        invoice = self._post(self.receivable, self.revenue, 1000)
        payment = self._post(self.bank, self.receivable, 600)

        wizard = self.env['cd.account.reconcile.wizard'].create({
            'account_id': self.receivable.id,
            'debit_transfer_id': invoice.id,
            'credit_transfer_id': payment.id,
            'amount': 600,
        })
        wizard.action_reconcile()

        self.assertEqual(invoice.residual_amount, 400)
        self.assertEqual(payment.residual_amount, 0)
        self.assertFalse(self.env['cd.account.reconcile'].search([]))

    def test_wizard_rejects_amount_above_residual(self):
        invoice = self._post(self.receivable, self.revenue, 1000)
        payment = self._post(self.bank, self.receivable, 600)

        wizard = self.env['cd.account.reconcile.wizard'].create({
            'account_id': self.receivable.id,
            'debit_transfer_id': invoice.id,
            'credit_transfer_id': payment.id,
            'amount': 601,
        })
        with self.assertRaises(UserError):
            wizard.action_reconcile()
