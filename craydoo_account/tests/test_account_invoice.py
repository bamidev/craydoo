from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAccountInvoice(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.address = cls.env['cd.account.address'].create({'name': 'Jane Doe'})

    def test_amount_total_computed_from_lines(self):
        # `price_include` - the tax's amount is already part of the
        # configured price, so the invoice's `amount_total` stays at 200
        # and `amount_untaxed` is what's left after carving the tax out.
        tax = self.env['cd.account.tax'].create({
            'name': '10%', 'amount_type': 'percent', 'amount': 10.0, 'price_include': True,
        })
        invoice = self.env['cd.account.invoice'].create({
            'billing_address_id': self.address.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Consulting', 'quantity': 2, 'amount_unit_currency': 100.0,
                'tax_ids': [(6, 0, [tax.id])],
            })],
        })
        self.assertAlmostEqual(invoice.amount_untaxed_currency, 180.0)
        self.assertAlmostEqual(invoice.amount_tax_currency, 20.0)
        self.assertAlmostEqual(invoice.amount_total_currency, 200.0)

    def test_locked_invoice_cannot_be_written(self):
        invoice = self.env['cd.account.invoice'].create({'billing_address_id': self.address.id})
        invoice.locked = True
        with self.assertRaises(UserError):
            invoice.write({'date': '2026-01-01'})

    def test_locked_write_allowed_with_context_flag(self):
        invoice = self.env['cd.account.invoice'].create({'billing_address_id': self.address.id})
        invoice.locked = True
        invoice.with_context(craydoo_allow_locked_write=True).write({'date': '2026-01-01'})
        self.assertEqual(str(invoice.date), '2026-01-01')

    def test_only_unlocked_invoices_can_be_archived(self):
        invoice = self.env['cd.account.invoice'].create({'billing_address_id': self.address.id})
        invoice.locked = True
        with self.assertRaises(UserError):
            invoice.active = False

    def test_unlocked_invoice_can_be_archived(self):
        invoice = self.env['cd.account.invoice'].create({'billing_address_id': self.address.id})
        invoice.active = False
        self.assertFalse(invoice.active)
