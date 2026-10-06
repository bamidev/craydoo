from .models.tigerbeetle_client import QUERY_PAGE_LIMIT, get_client, query_filter
from .partition import PARTITIONED_TABLES, create_partitioned_table, ensure_year_partitions


def pre_init_hook(env):
    """ Pre-create the partitioned tables of this module before `_auto_init`
    gets to them, and populate their initial set of year partitions, so
    installation doesn't trip over "no partition of relation found for
    row" the first time an invoice gets created.
    """
    for tablename, date_column in PARTITIONED_TABLES:
        create_partitioned_table(env.cr, tablename, date_column)
        ensure_year_partitions(env.cr, tablename, date_column)


def post_init_hook(env):
    sync_tigerbeetle_accounts(env)
    create_default_ledger_and_accounts(env)


def sync_tigerbeetle_accounts(env):
    """ Bootstrap cd.account.account with every account that already exists
    in Tigerbeetle, so the local cache isn't empty for a cluster that
    predates this module.
    """
    client = get_client(env)
    accounts = []
    timestamp_min = 1
    while True:
        page = client.query_accounts(query_filter(timestamp_min=timestamp_min))
        accounts.extend(page)
        if len(page) < QUERY_PAGE_LIMIT:
            break
        timestamp_min = page[-1].timestamp + 1

    existing_ids = set(env['cd.account.account'].search([]).mapped('tigerbeetle_id'))
    ledgers = {ledger.number: ledger for ledger in env['cd.account.ledger'].search([])}

    vals_list = []
    for account in accounts:
        if account.id in existing_ids:
            continue
        ledger = ledgers.get(account.ledger)
        if not ledger:
            ledger = env['cd.account.ledger'].create({
                'number': account.ledger, 'name': f'Ledger {account.ledger}',
            })
            ledgers[account.ledger] = ledger
        vals_list.append({
            'tigerbeetle_id': account.id, 'ledger': ledger.id, 'code': account.code,
            'flags': int(account.flags),
        })

    if vals_list:
        env['cd.account.account'].with_context(cd_account_sync=True).create(vals_list)


def create_default_ledger_and_accounts(env):
    """ If, even after `sync_tigerbeetle_accounts`, no ledger is known
    locally (a fresh Tigerbeetle cluster with nothing to sync), set up a
    default ledger and a default debit/credit account pair, and point the
    `craydoo_account.default_*` config parameters (the Accounting settings'
    global fallback, read by `AccountInvoiceDraft._default_account`) at
    them, so invoicing works out of the box instead of erroring out with
    "no debit/credit account configured".
    """
    if env['cd.account.ledger'].search_count([]):
        return

    ledger = env['cd.account.ledger'].create({'number': 1, 'name': 'Main Ledger'})
    debit_account = env['cd.account.account'].create({'ledger': ledger.id, 'code': 1})
    credit_account = env['cd.account.account'].create({'ledger': ledger.id, 'code': 2})

    icp = env['ir.config_parameter'].sudo()
    icp.set_param('craydoo_account.default_ledger', ledger.id)
    icp.set_param('craydoo_account.default_debit_account', debit_account.id)
    icp.set_param('craydoo_account.default_credit_account', credit_account.id)
