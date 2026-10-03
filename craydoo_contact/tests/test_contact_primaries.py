from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestContactPrimaries(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.info = cls.env['cd.contact.info'].create({'name': 'Jane Doe'})

    def test_setting_two_primaries_at_create_keeps_the_last_one(self):
        first = self.env['cd.contact.email'].create({
            'contact_info': self.info.id, 'address': 'first@example.com', 'is_primary': True,
        })
        second = self.env['cd.contact.email'].create({
            'contact_info': self.info.id, 'address': 'second@example.com', 'is_primary': True,
        })
        self.assertFalse(first.is_primary)
        self.assertTrue(second.is_primary)

    def test_promoting_one_demotes_the_previous_primary(self):
        first = self.env['cd.contact.email'].create({
            'contact_info': self.info.id, 'address': 'first@example.com', 'is_primary': True,
        })
        second = self.env['cd.contact.email'].create({
            'contact_info': self.info.id, 'address': 'second@example.com',
        })
        second.is_primary = True
        self.assertFalse(first.is_primary)
        self.assertTrue(second.is_primary)

    def test_primaries_are_scoped_per_contact_info(self):
        other_info = self.env['cd.contact.info'].create({'name': 'John Roe'})
        mine = self.env['cd.contact.phone'].create({
            'contact_info': self.info.id, 'number': '1', 'is_primary': True,
        })
        others = self.env['cd.contact.phone'].create({
            'contact_info': other_info.id, 'number': '2', 'is_primary': True,
        })
        self.assertTrue(mine.is_primary)
        self.assertTrue(others.is_primary)
