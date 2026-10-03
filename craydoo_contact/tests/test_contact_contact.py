from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestContactContact(TransactionCase):

    def test_create_flattens_into_contact_info(self):
        contact = self.env['cd.contact.contact'].create({
            'name': 'John Doe',
            'city': 'Rotterdam',
        })
        self.assertTrue(contact.contact_info)
        self.assertEqual(contact.contact_info.name, 'John Doe')
        self.assertEqual(contact.contact_info.city, 'Rotterdam')

    def test_create_with_explicit_contact_info(self):
        info = self.env['cd.contact.info'].create({'name': 'Existing Info'})
        contact = self.env['cd.contact.contact'].create({'contact_info': info.id})
        self.assertEqual(contact.contact_info, info)
        self.assertEqual(contact.name, 'Existing Info')

    def test_editing_contact_writes_through_to_contact_info(self):
        contact = self.env['cd.contact.contact'].create({'name': 'Jane Roe'})
        contact.city = 'Eindhoven'
        self.assertEqual(contact.contact_info.city, 'Eindhoven')

    def test_cannot_link_to_locked_contact_info(self):
        info = self.env['cd.contact.info'].create({'name': 'Locked Info', 'locked': True})
        with self.assertRaises(ValidationError):
            self.env['cd.contact.contact'].create({'contact_info': info.id})

    def test_function_is_specific_to_contact(self):
        contact = self.env['cd.contact.contact'].create({
            'name': 'Jane Roe', 'function': 'Engineer',
        })
        self.assertEqual(contact.function, 'Engineer')
