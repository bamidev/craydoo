from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestContactInfo(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.info = cls.env['cd.contact.info'].create({})

    def test_record_is_editable(self):
        self.info.write({'city': 'Rotterdam'})
        self.assertEqual(self.info.city, 'Rotterdam')

    def test_phones_one2many(self):
        self.env['cd.contact.phone'].create({
            'contact_info_id': self.info.id, 'number': '+31612345678', 'type': 'mobile',
        })
        self.assertEqual(len(self.info.phone_ids), 1)
        self.assertEqual(self.info.phone_ids.number, '+31612345678')
