from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAccountInvoice(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contact = cls.env['cd.contact.person'].create({'name': 'Jane Doe'})

    def test_amount_total_computed_from_lines(self):
        tax = self.env['cd.account.tax'].create({
            'name': '10%', 'amount_type': 'percent', 'amount': 10.0,
        })
        invoice = self.env['cd.account.invoice'].create({
            'debtor_id': self.contact.contact_info_id.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Consulting', 'quantity': 2, 'price_unit': 100.0,
                'tax_ids': [(6, 0, [tax.id])],
            })],
        })
        self.assertAlmostEqual(invoice.amount_untaxed, 200.0)
        self.assertAlmostEqual(invoice.amount_tax, 20.0)
        self.assertAlmostEqual(invoice.amount_total, 220.0)

    def test_locked_invoice_cannot_be_written(self):
        invoice = self.env['cd.account.invoice'].create({'debtor_id': self.contact.contact_info_id.id})
        invoice.locked = True
        with self.assertRaises(UserError):
            invoice.write({'date': '2026-01-01'})

    def test_locked_write_allowed_with_context_flag(self):
        invoice = self.env['cd.account.invoice'].create({'debtor_id': self.contact.contact_info_id.id})
        invoice.locked = True
        invoice.with_context(craydoo_allow_locked_write=True).write({'date': '2026-01-01'})
        self.assertEqual(str(invoice.date), '2026-01-01')

    def test_only_unlocked_invoices_can_be_archived(self):
        invoice = self.env['cd.account.invoice'].create({'debtor_id': self.contact.contact_info_id.id})
        invoice.locked = True
        with self.assertRaises(UserError):
            invoice.active = False

    def test_unlocked_invoice_can_be_archived(self):
        invoice = self.env['cd.account.invoice'].create({'debtor_id': self.contact.contact_info_id.id})
        invoice.active = False
        self.assertFalse(invoice.active)
