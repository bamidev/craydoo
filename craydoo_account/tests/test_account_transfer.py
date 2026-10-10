from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAccountTransfer(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ledger = cls.env['cd.account.ledger'].create({'name': 'Test Ledger'})
        cls.account_a, cls.account_b, cls.account_c = cls.env['cd.account.account'].create([
            {'name': 'A', 'code': '1', 'ledger_id': ledger.id},
            {'name': 'B', 'code': '2', 'ledger_id': ledger.id},
            {'name': 'C', 'code': '3', 'ledger_id': ledger.id},
        ])
        cls.ledger = ledger

    def _post(self, debit_account, credit_account, amount, date):
        return self.env['cd.account.transfer'].create({
            'date': date, 'ledger_id': self.ledger.id, 'code': 1, 'amount': amount,
            'debit_account_id': debit_account.id, 'credit_account_id': credit_account.id,
        })

    def _balance(self, account, year):
        return self.env['cd.account.fiscal.year.account.balance'].search([
            ('account_id', '=', account.id), ('fiscal_year_id.year', '=', year),
        ])

    def test_totals_stay_correct_across_several_transfers(self):
        # All within the same (safely past, never "current") fiscal year.
        self._post(self.account_a, self.account_b, 100, '2020-01-10')
        self._post(self.account_b, self.account_c, 50, '2020-02-10')
        self._post(self.account_a, self.account_c, 30, '2020-03-10')

        balance_a = self._balance(self.account_a, 2020)
        balance_b = self._balance(self.account_b, 2020)
        balance_c = self._balance(self.account_c, 2020)

        self.assertEqual(balance_a.debit_total, 130)
        self.assertEqual(balance_a.credit_total, 0)
        self.assertEqual(balance_a.closing_debit, 130)
        self.assertEqual(balance_a.closing_credit, 0)
        self.assertEqual(balance_a.closing_balance, -130)

        self.assertEqual(balance_b.debit_total, 50)
        self.assertEqual(balance_b.credit_total, 100)
        self.assertEqual(balance_b.closing_balance, 50)

        self.assertEqual(balance_c.debit_total, 0)
        self.assertEqual(balance_c.credit_total, 80)
        self.assertEqual(balance_c.closing_balance, 80)

        # cd.account.account totals sum/filter across its fiscal year balances.
        self.assertEqual(self.account_a.debit_total, 130)
        self.assertEqual(self.account_a.credit_total, 0)
        self.assertEqual(self.account_a.debit_year_total, 0)  # 2020 isn't the current year
        self.assertEqual(self.account_a.credit_year_total, 0)

    def test_opening_balance_carries_forward_to_next_year(self):
        self._post(self.account_a, self.account_b, 100, '2020-06-01')
        self._post(self.account_a, self.account_b, 40, '2021-01-15')

        balance_2020 = self._balance(self.account_a, 2020)
        balance_2021 = self._balance(self.account_a, 2021)

        self.assertEqual(balance_2020.closing_debit, 100)
        self.assertEqual(balance_2020.closing_credit, 0)
        self.assertEqual(balance_2020.closing_balance, -100)

        # 2021 opens with exactly what 2020 closed with.
        self.assertEqual(balance_2021.opening_debit, 100)
        self.assertEqual(balance_2021.opening_credit, 0)
        self.assertEqual(balance_2021.opening_balance, -100)

        # Plus its own year's activity on top.
        self.assertEqual(balance_2021.debit_total, 40)
        self.assertEqual(balance_2021.closing_debit, 140)
        self.assertEqual(balance_2021.closing_balance, -140)

    def test_transfer_is_immutable(self):
        transfer = self._post(self.account_a, self.account_b, 10, '2020-01-01')
        with self.assertRaises(UserError):
            transfer.write({'amount': 1})
        with self.assertRaises(UserError):
            transfer.unlink()
