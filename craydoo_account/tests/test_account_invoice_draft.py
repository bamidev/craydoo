from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAccountInvoiceDraft(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contact = cls.env['cd.contact.person'].create({'name': 'Jane Doe'})
        cls.ledger = cls.env['cd.account.ledger'].create({'name': 'Test Ledger'})
        cls.debit_account = cls.env['cd.account.account'].create({
            'name': 'Debtors', 'code': '1100', 'ledger_id': cls.ledger.id,
        })
        cls.credit_account = cls.env['cd.account.account'].create({
            'name': 'Sales', 'code': '8000', 'ledger_id': cls.ledger.id,
        })

    def test_create_auto_creates_invoice(self):
        draft = self.env['cd.account.invoice.draft'].create({'debtor_id': self.contact.contact_info_id.id})
        self.assertTrue(draft.invoice_id)
        self.assertEqual(draft.invoice_id.debtor_id, self.contact.contact_info_id)

    def test_create_with_explicit_invoice(self):
        invoice = self.env['cd.account.invoice'].create({'debtor_id': self.contact.contact_info_id.id})
        draft = self.env['cd.account.invoice.draft'].create({'invoice_id': invoice.id})
        self.assertEqual(draft.invoice_id, invoice)
        self.assertEqual(draft.debtor_id, self.contact.contact_info_id)

    def test_action_post_requires_accounts(self):
        draft = self.env['cd.account.invoice.draft'].create({'debtor_id': self.contact.contact_info_id.id})
        with self.assertRaises(UserError):
            draft.action_post()

    def test_action_post_raises_if_already_locked(self):
        draft = self.env['cd.account.invoice.draft'].create({'debtor_id': self.contact.contact_info_id.id})
        draft.invoice_id.locked = True
        with self.assertRaises(UserError):
            draft.action_post()

    def test_action_post_creates_transfer(self):
        draft = self.env['cd.account.invoice.draft'].create({
            'debtor_id': self.contact.contact_info_id.id,
            'debit_account_id': self.debit_account.id,
            'credit_account_id': self.credit_account.id,
            'invoice_line_ids': [Command.create({'name': 'Line', 'price_unit': 10.0})],
        })
        draft.action_post()

        invoice = draft.invoice_id
        self.assertTrue(invoice.locked)
        transfer = invoice.transfer_id
        self.assertTrue(transfer)
        self.assertEqual(transfer.debit_account_id, self.debit_account)
        self.assertEqual(transfer.credit_account_id, self.credit_account)
        self.assertEqual(
            transfer.amount, round(invoice.amount_total * 10 ** invoice.currency_id.decimal_places))

        with self.assertRaises(UserError):
            transfer.write({'amount': 1})
        with self.assertRaises(UserError):
            transfer.unlink()

    def test_action_post_splits_tax_across_allocations(self):
        vat_account = self.env['cd.account.account'].create({
            'name': 'VAT Payable', 'code': '2200', 'ledger_id': self.ledger.id,
        })
        tax = self.env['cd.account.tax'].create({
            'name': '21%', 'amount_type': 'percent', 'amount': 21.0,
            'invoice_line_ids': [Command.create({'account_id': vat_account.id, 'percentage': 100.0})],
        })
        draft = self.env['cd.account.invoice.draft'].create({
            'debtor_id': self.contact.contact_info_id.id,
            'debit_account_id': self.debit_account.id,
            'credit_account_id': self.credit_account.id,
            'invoice_line_ids': [Command.create({
                'name': 'Line', 'price_unit': 100.0, 'tax_ids': [Command.link(tax.id)],
            })],
        })
        draft.action_post()

        invoice = draft.invoice_id
        revenue_transfer = invoice.transfer_id
        self.assertEqual(revenue_transfer.debit_account_id, self.debit_account)
        self.assertEqual(revenue_transfer.credit_account_id, self.credit_account)
        self.assertEqual(revenue_transfer.amount, 10000)

        self.assertFalse(revenue_transfer.is_linked)
        tax_transfer = revenue_transfer.linked_ids
        self.assertTrue(tax_transfer)
        self.assertTrue(tax_transfer.is_linked)
        self.assertEqual(tax_transfer.debit_account_id, self.debit_account)
        self.assertEqual(tax_transfer.credit_account_id, vat_account)
        self.assertEqual(tax_transfer.amount, 2100)

        self.assertIn(tax_transfer, revenue_transfer.linked_ids)
        self.assertIn(revenue_transfer, tax_transfer.linked_ids)

    def test_action_post_requires_tax_allocation(self):
        tax = self.env['cd.account.tax'].create({
            'name': '21% unconfigured', 'amount_type': 'percent', 'amount': 21.0,
        })
        draft = self.env['cd.account.invoice.draft'].create({
            'debtor_id': self.contact.contact_info_id.id,
            'debit_account_id': self.debit_account.id,
            'credit_account_id': self.credit_account.id,
            'invoice_line_ids': [Command.create({
                'name': 'Line', 'price_unit': 100.0, 'tax_ids': [Command.link(tax.id)],
            })],
        })
        with self.assertRaises(UserError):
            draft.action_post()
