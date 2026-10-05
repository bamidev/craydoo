from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAccountInvoiceDraft(TransactionCase):
    """ Only covers what doesn't require a live Tigerbeetle cluster -
    `action_post`'s happy path (actually creating transfers) needs one and
    isn't exercised here.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contact = cls.env['cd.contact.person'].create({'name': 'Jane Doe'})

    def test_create_auto_creates_invoice(self):
        draft = self.env['cd.account.invoice.draft'].create({'debtor': self.contact.contact_info.id})
        self.assertTrue(draft.invoice_id)
        self.assertEqual(draft.invoice_id.debtor, self.contact.contact_info)

    def test_create_with_explicit_invoice(self):
        invoice = self.env['cd.account.invoice'].create({'debtor': self.contact.contact_info.id})
        draft = self.env['cd.account.invoice.draft'].create({'invoice_id': invoice.id})
        self.assertEqual(draft.invoice_id, invoice)
        self.assertEqual(draft.debtor, self.contact.contact_info)

    def test_action_post_requires_accounts(self):
        draft = self.env['cd.account.invoice.draft'].create({'debtor': self.contact.contact_info.id})
        with self.assertRaises(UserError):
            draft.action_post()

    def test_action_post_raises_if_already_locked(self):
        draft = self.env['cd.account.invoice.draft'].create({'debtor': self.contact.contact_info.id})
        draft.invoice_id.locked = True
        with self.assertRaises(UserError):
            draft.action_post()
