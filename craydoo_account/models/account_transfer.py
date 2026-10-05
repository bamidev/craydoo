from odoo import fields, models

from .fields import TigerbeetleId
from .tigerbeetle_client import get_client, query_filter


class AccountTransfer(models.Model):
    """ A Tigerbeetle transfer, viewed live - no local copy. The record's
    own `id` *is* the Tigerbeetle transfer id, same reasoning as
    `cd.account.account`.

    Only searching by id, or with no filter at all (page through
    everything), is supported - see `cd.account.account` for why.
    """
    _name = 'cd.account.transfer'
    _description = 'Tigerbeetle Transfer'
    _inherit = ['cd.account.tigerbeetle.record']
    _rec_name = 'id'

    ledger = fields.Many2one('cd.account.ledger', readonly=True)
    code = fields.Integer(readonly=True)
    flags = fields.Integer(readonly=True)
    amount = TigerbeetleId(readonly=True)
    debit_account = fields.Many2one('cd.account.account', readonly=True)
    credit_account = fields.Many2one('cd.account.account', readonly=True)

    def _tb_fetch(self, ids):
        if not ids:
            return {}
        transfers = get_client(self.env).lookup_transfers(list(ids))
        ledgers = {
            l.number: l for l in self.env['cd.account.ledger'].search(
                [('number', 'in', [t.ledger for t in transfers])])
        }
        data = {}
        for t in transfers:
            ledger = ledgers.get(t.ledger)
            data[t.id] = {
                'ledger': (ledger.id, ledger.display_name) if ledger else False,
                'code': t.code,
                'flags': int(t.flags),
                'amount': t.amount,
                'debit_account': (t.debit_account_id, str(t.debit_account_id)) if t.debit_account_id else False,
                'credit_account': (t.credit_account_id, str(t.credit_account_id)) if t.credit_account_id else False,
            }
        return data

    def _tb_search_ids(self, domain):
        client = get_client(self.env)
        ids = self._tb_ids_from_domain(domain)
        if ids is not None:
            return [t.id for t in client.lookup_transfers(ids)]
        if domain:
            raise NotImplementedError(
                "cd.account.transfer only supports searching by id; browse a "
                "specific id instead of filtering.")
        return [t.id for t in client.query_transfers(query_filter(limit=8190))]
