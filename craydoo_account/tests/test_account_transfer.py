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

    def _post(self, debit_account, credit_account, amount):
        return self.env['cd.account.transfer'].create({
            'ledger_id': self.ledger.id, 'code': 1, 'amount': amount,
            'debit_account_id': debit_account.id, 'credit_account_id': credit_account.id,
        })

    def test_totals_stay_correct_across_several_transfers(self):
        # A --100--> B: A is debited (-100), B is credited (+100).
        transfer1 = self._post(self.account_a, self.account_b, 100)
        self.assertEqual(transfer1.debit_account_total, -100)
        self.assertEqual(transfer1.credit_account_total, 100)

        # B --50--> C: B was last credited to 100, now debited.
        transfer2 = self._post(self.account_b, self.account_c, 50)
        self.assertEqual(transfer2.debit_account_total, 50)
        self.assertEqual(transfer2.credit_account_total, 50)

        # A --30--> C: A was last debited to -100; C was last credited to 50.
        transfer3 = self._post(self.account_a, self.account_c, 30)
        self.assertEqual(transfer3.debit_account_total, -130)
        self.assertEqual(transfer3.credit_account_total, 80)

        # Earlier transfers keep their own snapshot - nothing retroactively changes.
        self.assertEqual(transfer1.debit_account_total, -100)
        self.assertEqual(transfer1.credit_account_total, 100)
        self.assertEqual(transfer2.debit_account_total, 50)
        self.assertEqual(transfer2.credit_account_total, 50)

        # cd.account.account.total reflects each account's latest transfer,
        # and can be negative (A has only ever been debited).
        self.assertEqual(self.account_a.total, -130)
        self.assertEqual(self.account_b.total, 50)
        self.assertEqual(self.account_c.total, 80)
