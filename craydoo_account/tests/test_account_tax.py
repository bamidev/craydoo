from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAccountTax(TransactionCase):

    def test_percent_tax_excluded(self):
        tax = self.env['cd.account.tax'].create({
            'name': '15%', 'amount_type': 'percent', 'amount': 15.0,
        })
        res = tax.compute_all(100.0, quantity=2.0)
        self.assertAlmostEqual(res['total_excluded'], 200.0)
        self.assertAlmostEqual(res['total_included'], 230.0)

    def test_percent_tax_included(self):
        tax = self.env['cd.account.tax'].create({
            'name': '15% incl', 'amount_type': 'percent', 'amount': 15.0,
            'price_include': True,
        })
        res = tax.compute_all(115.0)
        self.assertAlmostEqual(res['total_excluded'], 100.0)
        self.assertAlmostEqual(res['total_included'], 115.0)

    def test_fixed_tax(self):
        tax = self.env['cd.account.tax'].create({
            'name': 'Eco fee', 'amount_type': 'fixed', 'amount': 5.0,
        })
        res = tax.compute_all(50.0, quantity=3.0)
        self.assertAlmostEqual(res['total_excluded'], 150.0)
        self.assertAlmostEqual(res['total_included'], 165.0)

    def test_invoice_allocation_lines_are_separate_from_refund_lines(self):
        tax = self.env['cd.account.tax'].create({'name': '21%', 'amount': 21.0})
        tag = self.env['cd.account.tax.tag'].create({'name': 'Box 1'})
        ledger = self.env['cd.account.ledger'].create({'name': 'Test Ledger'})
        account = self.env['cd.account.account'].create({
            'name': 'VAT', 'code': '1500', 'ledger_id': ledger.id,
        })
        line = self.env['cd.account.tax.allocation.line'].create({
            'invoice_tax_id': tax.id, 'account_id': account.id, 'tag_ids': [(6, 0, [tag.id])],
            'percentage': 100.0,
        })
        self.assertIn(line, tax.invoice_line_ids)
        self.assertNotIn(line, tax.refund_line_ids)
