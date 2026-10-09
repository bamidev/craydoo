from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestContactPerson(TransactionCase):

    def test_create_flattens_into_contact_info(self):
        person = self.env['cd.contact.person'].create({
            'name': 'John Doe',
            'city': 'Rotterdam',
        })
        self.assertTrue(person.contact_info_id)
        self.assertEqual(person.contact_info_id.name, 'John Doe')
        self.assertEqual(person.contact_info_id.city, 'Rotterdam')

    def test_create_with_explicit_contact_info(self):
        info = self.env['cd.contact.info'].create({'name': 'Existing Info'})
        person = self.env['cd.contact.person'].create({'contact_info_id': info.id})
        self.assertEqual(person.contact_info_id, info)
        self.assertEqual(person.name, 'Existing Info')

    def test_editing_person_writes_through_to_contact_info(self):
        person = self.env['cd.contact.person'].create({'name': 'Jane Roe'})
        person.city = 'Eindhoven'
        self.assertEqual(person.contact_info_id.city, 'Eindhoven')

    def test_cannot_link_to_locked_contact_info(self):
        info = self.env['cd.contact.info'].create({'name': 'Locked Info', 'locked': True})
        with self.assertRaises(ValidationError):
            self.env['cd.contact.person'].create({'contact_info_id': info.id})

    def test_function_is_specific_to_person(self):
        person = self.env['cd.contact.person'].create({
            'name': 'Jane Roe', 'function': 'Engineer',
        })
        self.assertEqual(person.function, 'Engineer')

    def test_display_name_combines_salutation_first_infix_last(self):
        person = self.env['cd.contact.person'].create({
            'salutation': 'mr', 'first_name': 'Jan', 'infix': 'van der', 'name': 'Berg',
        })
        self.assertEqual(person.display_name, 'Mr. Jan van der Berg')

    def test_display_name_without_infix(self):
        person = self.env['cd.contact.person'].create({'first_name': 'Jane', 'name': 'Doe'})
        self.assertEqual(person.display_name, 'Jane Doe')

    def test_requires_first_or_last_name(self):
        with self.assertRaises(ValidationError):
            self.env['cd.contact.person'].create({})
