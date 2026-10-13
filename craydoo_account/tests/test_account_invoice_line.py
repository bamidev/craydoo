from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAccountInvoiceLine(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        address = cls.env['cd.account.address'].create({'name': 'Jane Doe'})
        cls.invoice = cls.env['cd.account.invoice'].create({'billing_address_id': address.id})
        cls.tax = cls.env['cd.account.tax'].create({
            'name': '20%', 'amount_type': 'percent', 'amount': 20.0, 'price_include': True,
        })

    def test_amounts_without_tax(self):
        line = self.env['cd.account.invoice.line'].create({
            'invoice_id': self.invoice.id, 'quantity': 3, 'amount_unit_currency': 50.0,
        })
        self.assertAlmostEqual(line.amount_revenue_currency, 150.0)
        self.assertAlmostEqual(line.amount_tax_currency, 0.0)
        self.assertAlmostEqual(line.amount_total_currency, 150.0)

    def test_amounts_with_tax(self):
        # `price_include` - the tax's amount is already part of the
        # configured price, so `amount_total` stays at 100 and
        # `amount_revenue` is what's left after carving the tax out of it.
        line = self.env['cd.account.invoice.line'].create({
            'invoice_id': self.invoice.id, 'quantity': 1, 'amount_unit_currency': 100.0,
            'tax_ids': [(6, 0, [self.tax.id])],
        })
        self.assertAlmostEqual(line.amount_total_currency, 100.0)
        self.assertAlmostEqual(line.amount_tax_currency, 20.0)
        self.assertAlmostEqual(line.amount_revenue_currency, 80.0)
