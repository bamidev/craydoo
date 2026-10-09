from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestContactCompany(TransactionCase):

    def test_create_flattens_into_contact_info(self):
        company = self.env['cd.contact.company'].create({
            'name': 'Acme Corp', 'city': 'Breda',
        })
        self.assertTrue(company.contact_info_id)
        self.assertEqual(company.contact_info_id.name, 'Acme Corp')

    def test_cannot_link_to_locked_contact_info(self):
        info = self.env['cd.contact.info'].create({'name': 'Locked Co', 'locked': True})
        with self.assertRaises(ValidationError):
            self.env['cd.contact.company'].create({'contact_info_id': info.id})

    def test_vat_id_is_specific_to_company(self):
        company = self.env['cd.contact.company'].create({
            'name': 'Acme Corp', 'vat_id': 'NL123456789B01',
        })
        self.assertEqual(company.vat_id, 'NL123456789B01')
