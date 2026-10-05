from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestContactInfo(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.info = cls.env['cd.contact.info'].create({})

    def test_unlocked_record_is_editable(self):
        self.info.write({'city': 'Rotterdam'})
        self.assertEqual(self.info.city, 'Rotterdam')

    def test_locked_record_cannot_be_written(self):
        self.info.locked = True
        with self.assertRaises(UserError):
            self.info.write({'city': 'Amsterdam'})

    def test_locked_record_cannot_be_unlinked(self):
        self.info.locked = True
        with self.assertRaises(UserError):
            self.info.unlink()

    def test_locked_record_cannot_be_unlocked(self):
        self.info.locked = True
        with self.assertRaises(UserError):
            self.info.locked = False

    def test_locked_write_allowed_with_context_flag(self):
        self.info.locked = True
        self.info.with_context(craydoo_allow_locked_write=True).write({'city': 'Utrecht'})
        self.assertEqual(self.info.city, 'Utrecht')

    def test_unlocked_record_can_be_unlinked(self):
        info = self.env['cd.contact.info'].create({})
        info.unlink()

    def test_phones_one2many(self):
        self.env['cd.contact.phone'].create({
            'contact_info': self.info.id, 'number': '+31612345678', 'type': 'mobile',
        })
        self.assertEqual(len(self.info.phones), 1)
        self.assertEqual(self.info.phones.number, '+31612345678')

    def test_locking_contact_info_locks_its_phones(self):
        phone = self.env['cd.contact.phone'].create({
            'contact_info': self.info.id, 'number': '+31612345678',
        })
        self.info.locked = True
        self.assertTrue(phone.locked)
        with self.assertRaises(UserError):
            phone.write({'number': '+31600000000'})
