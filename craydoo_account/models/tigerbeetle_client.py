from odoo import _
from odoo.exceptions import UserError

try:
    import tigerbeetle as tb
except ImportError:
    tb = None

_client = None

QUERY_PAGE_LIMIT = 1000


def get_client(env):
    """ Process-wide Tigerbeetle client, built lazily from ir.config_parameter
    so a missing/unconfigured cluster doesn't break module load.
    """
    global _client
    if _client is None:
        if tb is None:
            raise RuntimeError("The 'tigerbeetle' python package is not installed.")
        icp = env['ir.config_parameter'].sudo()
        cluster_id = icp.get_int('craydoo_account.tigerbeetle_cluster_id', 0)
        addresses = icp.get_str('craydoo_account.tigerbeetle_addresses', '3000')
        _client = tb.ClientSync(cluster_id=cluster_id, replica_addresses=addresses)
    return _client


def query_filter(limit=QUERY_PAGE_LIMIT, **overrides):
    """ A `tigerbeetle.QueryFilter` matching anything (every field is 0,
    the TB wildcard), with `limit` (defaulting to `QUERY_PAGE_LIMIT`, well
    under the cluster's own batch-size ceiling) and any of its fields
    overridden - every field is a required positional/keyword arg on
    QueryFilter, so this saves repeating all the zeroes at every call site.
    """
    kwargs = {
        'user_data_128': 0, 'user_data_64': 0, 'user_data_32': 0,
        'ledger': 0, 'code': 0, 'timestamp_min': 0, 'timestamp_max': 0,
        'limit': limit, 'flags': tb.QueryFilterFlags(0),
    }
    kwargs.update(overrides)
    return tb.QueryFilter(**kwargs)


def create_account(env, *, ledger, code, flags=0, user_data_32=0):
    """ Create a single Tigerbeetle account and return its id, raising
    UserError if Tigerbeetle refuses it.
    """
    client = get_client(env)
    account_id = tb.id()
    account = tb.Account(
        id=account_id, ledger=ledger, code=code, flags=tb.AccountFlags(flags),
        user_data_32=user_data_32,
    )
    for result in client.create_accounts([account]):
        if result.status != tb.CreateAccountStatus.CREATED:
            raise UserError(_("Tigerbeetle refused the account: %s", result.status.name))
    return account_id


def create_linked_transfers(env, transfers):
    """ Create a batch of Tigerbeetle transfers as one atomic LINKED chain -
    either all of them land or none do. `transfers` is a list of dicts of
    `tigerbeetle.Transfer` kwargs (without `id`/`flags`, which this fills
    in); returns the generated ids, in the same order.
    """
    client = get_client(env)
    ids = [tb.id() for _ in transfers]
    last = len(transfers) - 1
    objects = [
        tb.Transfer(
            id=ids[i],
            flags=tb.TransferFlags.LINKED if i < last else tb.TransferFlags(0),
            **kwargs,
        )
        for i, kwargs in enumerate(transfers)
    ]
    for result in client.create_transfers(objects):
        if result.status != tb.CreateTransferStatus.CREATED:
            raise UserError(_("Tigerbeetle refused the transfer: %s", result.status.name))
    return ids
