from .models.tigerbeetle_client import get_client, query_filter


def sync_tigerbeetle_accounts(env):
    """ Bootstrap cd.account.account with every account that already exists
    in Tigerbeetle, so the local cache isn't empty for a cluster that
    predates this module.
    """
    client = get_client(env)
    accounts = client.query_accounts(query_filter(limit=8190))

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
