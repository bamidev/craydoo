from odoo import _
from odoo.exceptions import UserError

try:
    import tigerbeetle as tb
except ImportError:
    tb = None

_client = None


def get_client(env):
    """ Process-wide Tigerbeetle client, built lazily from ir.config_parameter
    so a missing/unconfigured cluster doesn't break module load.
    """
    global _client
    if _client is None:
        if tb is None:
            raise RuntimeError("The 'tigerbeetle' python package is not installed.")
        get_param = env['ir.config_parameter'].sudo().get_param
        cluster_id = int(get_param('craydoo_account.tigerbeetle_cluster_id', '0'))
        addresses = get_param('craydoo_account.tigerbeetle_addresses', '3000')
        _client = tb.ClientSync(cluster_id=cluster_id, replica_addresses=addresses)
    return _client


def new_id():
    """ A fresh Tigerbeetle id, masked down to 64 bits so it fits in our
    `TigerbeetleId` columns - ids in this project are assumed to always be
    small enough for this truncation to be safe.
    """
    return tb.id() & 0xFFFFFFFFFFFFFFFF


def query_filter(limit, **overrides):
    """ A `tigerbeetle.QueryFilter` matching anything (every field is 0,
    the TB wildcard), with `limit` and any of its fields overridden - every
    field is a required positional/keyword arg on QueryFilter, so this
    saves repeating all the zeroes at every call site.
    """
    kwargs = {
        'user_data_128': 0, 'user_data_64': 0, 'user_data_32': 0,
        'ledger': 0, 'code': 0, 'timestamp_min': 0, 'timestamp_max': 0,
        'limit': limit, 'flags': tb.QueryFilterFlags(0),
    }
    kwargs.update(overrides)
    return tb.QueryFilter(**kwargs)


def create_linked_transfers(env, transfers):
    """ Create a batch of Tigerbeetle transfers as one atomic LINKED chain -
    either all of them land or none do. `transfers` is a list of dicts of
    `tigerbeetle.Transfer` kwargs (without `id`/`flags`, which this fills
    in); returns the generated ids, in the same order.
    """
    client = get_client(env)
    ids = [new_id() for _ in transfers]
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
