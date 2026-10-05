from odoo import fields, models

from .fields import TigerbeetleId
from .tigerbeetle_client import get_client, query_filter


class AccountAccount(models.Model):
    """ A Tigerbeetle account, viewed live - no local copy. The record's own
    `id` *is* the Tigerbeetle account id (there's no Postgres sequence to
    hand out a different one), so any TigerbeetleId field elsewhere that stores
    a Tigerbeetle account id can be browsed directly:
    `env['cd.account.account'].browse(some_account_id)`.

    Only searching by id, or with no filter at all (page through everything),
    is supported - Tigerbeetle's `query_accounts` has no free-text search,
    only equality on ledger/code/user_data and a timestamp range, none of
    which a generic Odoo search box produces today.
    """
    _name = 'cd.account.account'
    _description = 'Tigerbeetle Account'
    _inherit = ['cd.account.tigerbeetle.record']
    _rec_name = 'id'

    ledger = fields.Many2one('cd.account.ledger', readonly=True)
    code = fields.Integer(readonly=True)
    flags = fields.Integer(readonly=True)
    debits_pending = TigerbeetleId(readonly=True)
    debits_posted = TigerbeetleId(readonly=True)
    credits_pending = TigerbeetleId(readonly=True)
    credits_posted = TigerbeetleId(readonly=True)

    def _tb_fetch(self, ids):
        if not ids:
            return {}
        accounts = get_client(self.env).lookup_accounts(list(ids))
        ledgers = {
            l.number: l for l in self.env['cd.account.ledger'].search(
                [('number', 'in', [a.ledger for a in accounts])])
        }
        data = {}
        for a in accounts:
            ledger = ledgers.get(a.ledger)
            data[a.id] = {
                'ledger': (ledger.id, ledger.display_name) if ledger else False,
                'code': a.code,
                'flags': int(a.flags),
                'debits_pending': a.debits_pending,
                'debits_posted': a.debits_posted,
                'credits_pending': a.credits_pending,
                'credits_posted': a.credits_posted,
            }
        return data

    def _tb_search_ids(self, domain):
        client = get_client(self.env)
        ids = self._tb_ids_from_domain(domain)
        if ids is not None:
            return [a.id for a in client.lookup_accounts(ids)]
        if domain:
            raise NotImplementedError(
                "cd.account.account only supports searching by id; browse a "
                "specific id instead of filtering.")
        return [a.id for a in client.query_accounts(query_filter(limit=8190))]
