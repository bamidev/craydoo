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
        draft = self.env['cd.account.invoice.draft'].create({
            'billing_contact_id': self.contact.contact_info_id.id,
        })
        self.assertTrue(draft.invoice_id)

    def test_create_with_explicit_invoice(self):
        address = self.env['cd.account.address'].create({'name': 'Jane Doe'})
        invoice = self.env['cd.account.invoice'].create({'billing_address_id': address.id})
        draft = self.env['cd.account.invoice.draft'].create({
            'invoice_id': invoice.id, 'billing_contact_id': self.contact.contact_info_id.id,
        })
        self.assertEqual(draft.invoice_id, invoice)
        self.assertEqual(draft.billing_contact_id, self.contact.contact_info_id)

    def test_action_post_requires_accounts(self):
        draft = self.env['cd.account.invoice.draft'].create({
            'billing_contact_id': self.contact.contact_info_id.id,
        })
        with self.assertRaises(UserError):
            draft.action_post()

    def test_action_post_raises_if_already_locked(self):
        draft = self.env['cd.account.invoice.draft'].create({
            'billing_contact_id': self.contact.contact_info_id.id,
        })
        draft.invoice_id.locked = True
        with self.assertRaises(UserError):
            draft.action_post()

    def test_action_post_creates_transfer(self):
        draft = self.env['cd.account.invoice.draft'].create({
            'billing_contact_id': self.contact.contact_info_id.id,
            'debit_account_id': self.debit_account.id,
            'credit_account_id': self.credit_account.id,
            'invoice_line_ids': [Command.create({'name': 'Line', 'price_unit': 10.0})],
        })
        invoice = draft.invoice_id
        draft.action_post()

        self.assertFalse(draft.exists())
        self.assertTrue(invoice.locked)
        self.assertEqual(
            invoice.billing_address_id.name, self.contact.contact_info_id.display_name)
        transfer = invoice.transfer_id
        self.assertTrue(transfer)
        self.assertEqual(transfer.debit_account_id, self.debit_account)
        self.assertEqual(transfer.credit_account_id, self.credit_account)
        self.assertEqual(
            transfer.posted_id.amount,
            round(invoice.amount_total * 10 ** invoice.currency_id.decimal_places))

        with self.assertRaises(UserError):
            transfer.write({'date': '2020-01-02'})
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
            'billing_contact_id': self.contact.contact_info_id.id,
            'debit_account_id': self.debit_account.id,
            'credit_account_id': self.credit_account.id,
            'invoice_line_ids': [Command.create({
                'name': 'Line', 'price_unit': 100.0, 'tax_ids': [Command.link(tax.id)],
            })],
        })
        invoice = draft.invoice_id
        draft.action_post()

        # transfer_id is the *last* linked transfer - here, the tax leg.
        tax_transfer = invoice.transfer_id
        self.assertTrue(tax_transfer.backward_link_id)
        self.assertEqual(tax_transfer.debit_account_id, self.debit_account)
        self.assertEqual(tax_transfer.credit_account_id, vat_account)
        self.assertEqual(tax_transfer.posted_id.amount, 2100)

        # transfer_ids (transfer_id.linked_ids) finds the rest of the chain.
        self.assertEqual(invoice.transfer_ids, tax_transfer.linked_ids)
        revenue_transfer = invoice.transfer_ids
        self.assertFalse(revenue_transfer.backward_link_id)
        self.assertEqual(revenue_transfer.debit_account_id, self.debit_account)
        self.assertEqual(revenue_transfer.credit_account_id, self.credit_account)
        self.assertEqual(revenue_transfer.posted_id.amount, 10000)

    def test_action_post_requires_tax_allocation(self):
        tax = self.env['cd.account.tax'].create({
            'name': '21% unconfigured', 'amount_type': 'percent', 'amount': 21.0,
        })
        draft = self.env['cd.account.invoice.draft'].create({
            'billing_contact_id': self.contact.contact_info_id.id,
            'debit_account_id': self.debit_account.id,
            'credit_account_id': self.credit_account.id,
            'invoice_line_ids': [Command.create({
                'name': 'Line', 'price_unit': 100.0, 'tax_ids': [Command.link(tax.id)],
            })],
        })
        with self.assertRaises(UserError):
            draft.action_post()
