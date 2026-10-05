from odoo import models


class TigerbeetleRecord(models.AbstractModel):
    """ Base for Odoo models whose rows live in Tigerbeetle, not Postgres:
    `cd.account.transfer` (`cd.account.account` is cached locally instead,
    see there for why). No table is created
    (`_auto = False`); `_search`/`read` go straight to the Tigerbeetle client
    via the two hooks concrete models implement: `_tb_search_ids` and
    `_tb_fetch`. These records are only ever produced by posting the
    accounting documents that write to Tigerbeetle directly, so
    create/write/unlink aren't supported here.

    `_tb_fetch` must return values already shaped the way `read()` expects:
    a Many2one field's value is `(id, display_name)` or `False`, not a bare
    id - each concrete model knows its own field types, so it does that
    formatting itself rather than this generic base guessing at it.
    """
    _name = 'cd.account.tigerbeetle.record'
    _description = 'Tigerbeetle-Backed Record'
    _auto = False

    def _tb_fetch(self, ids):
        """ Return {id: {field_name: value}} for the given ids. """
        raise NotImplementedError

    def _tb_search_ids(self, domain):
        """ Return the full list of matching ids for a domain. Tigerbeetle
        has no general-purpose table scan, so only a handful of domain
        shapes are supported (id equality/in, and whatever
        `query_accounts`/`query_transfers` can filter on); anything else
        should raise NotImplementedError.
        """
        raise NotImplementedError

    @staticmethod
    def _tb_ids_from_domain(domain):
        """ Return a list of ids if `domain` is exactly one `('id', '=', x)`
        or `('id', 'in', xs)` leaf, else None.
        """
        if len(domain) != 1:
            return None
        leaf = domain[0]
        if not (isinstance(leaf, (list, tuple)) and len(leaf) == 3):
            return None
        field, operator, value = leaf
        if field != 'id':
            return None
        if operator == '=':
            return [value]
        if operator == 'in':
            return list(value)
        return None

    def _search(self, domain, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        ids = self._tb_search_ids(domain)
        if offset:
            ids = ids[offset:]
        if limit:
            ids = ids[:limit]
        if count:
            return len(ids)
        return ids

    def read(self, fields=None, load='_classic_read'):
        field_names = fields or [f for f in self._fields if f != 'id']
        data = self._tb_fetch(self.ids)
        return [
            {'id': rec_id, **{f: data.get(rec_id, {}).get(f, False) for f in field_names}}
            for rec_id in self.ids
        ]

    def create(self, vals_list):
        raise NotImplementedError("Tigerbeetle records can't be created from Odoo directly.")

    def write(self, vals):
        raise NotImplementedError("Tigerbeetle records are immutable from Odoo.")

    def unlink(self):
        raise NotImplementedError("Tigerbeetle records can't be deleted from Odoo.")
