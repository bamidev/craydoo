from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAccountInvoiceLine(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contact = cls.env['cd.contact.person'].create({'name': 'Jane Doe'})
        cls.invoice = cls.env['cd.account.invoice'].create({
            'debtor': cls.contact.contact_info.id,
        })
        cls.tax = cls.env['cd.account.tax'].create({
            'name': '20%', 'amount_type': 'percent', 'amount': 20.0,
        })

    def test_amounts_without_tax(self):
        line = self.env['cd.account.invoice.line'].create({
            'invoice': self.invoice.id, 'quantity': 3, 'price_unit': 50.0,
        })
        self.assertAlmostEqual(line.price_subtotal, 150.0)
        self.assertAlmostEqual(line.price_tax, 0.0)
        self.assertAlmostEqual(line.price_total, 150.0)

    def test_amounts_with_tax(self):
        line = self.env['cd.account.invoice.line'].create({
            'invoice': self.invoice.id, 'quantity': 1, 'price_unit': 100.0,
            'taxes': [(6, 0, [self.tax.id])],
        })
        self.assertAlmostEqual(line.price_subtotal, 100.0)
        self.assertAlmostEqual(line.price_tax, 20.0)
        self.assertAlmostEqual(line.price_total, 120.0)
