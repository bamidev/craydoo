from datetime import date

from odoo.tools import SQL, sql as odoo_sql
from odoo.tools.sql import table_exists


def _existing_tables_craydoo(cr, tablenames):
    """ Monkeypatch for `odoo.tools.sql.existing_tables`.

    Postgres represents a native range-partitioned table's parent shell
    (what `create_partitioned_table` below creates) with `relkind = 'p'`,
    a kind the stock query doesn't match - it only matches `'r'` (ordinary
    tables), `'v'` (views) and `'m'` (materialized views). Since
    `table_exists`, and in turn `_auto_init`, build on `existing_tables`,
    an already-created partitioned table is invisible to them: `_auto_init`
    concludes the table doesn't exist yet and issues its own `CREATE TABLE`,
    which fails with "relation already exists". Widening the match to also
    include `'p'` is the only change made here; the query is otherwise
    identical to the original.
    """
    cr.execute(SQL("""
        SELECT c.relname
          FROM pg_class c
         WHERE c.relname IN %s
           AND c.relkind IN ('r', 'v', 'm', 'p')
           AND c.relnamespace = current_schema::regnamespace
    """, tuple(tablenames)))
    return [row[0] for row in cr.fetchall()]


odoo_sql.existing_tables = _existing_tables_craydoo

# (table, partition key column) pairs for every table in this module that's
# natively range-partitioned by Postgres. Each table's parent shell is
# pre-created by `pre_init_hook` (before `_auto_init` gets to it), and kept
# supplied with partitions going forward by `_cron_ensure_partitions`.
PARTITIONED_TABLES = [
    ('cd_account_invoice', 'date'),
    ('cd_account_invoice_line', 'date'),
]

YEARS_BEHIND = 5
YEARS_AHEAD = 2


def create_partitioned_table(cr, tablename, date_column):
    """ Pre-create `tablename` as a range-partitioned shell - just `id` and
    the partition key column - before `_auto_init` gets to it. `_auto_init`
    only runs its own (ordinary, non-partitioned) `CREATE TABLE` when the
    table doesn't exist yet, and otherwise just ALTERs in the rest of the
    model's columns, so pre-creating the table this way is all it takes for
    Odoo to end up managing a partitioned table instead of an ordinary one.

    Note Postgres requires every unique/primary key index on a partitioned
    table to include the partition column, so the primary key here is
    `(id, date_column)` rather than Odoo's usual plain `id`.
    """
    if table_exists(cr, tablename):
        return
    cr.execute(SQL(
        "CREATE TABLE %s (id SERIAL NOT NULL, %s DATE NOT NULL, PRIMARY KEY (id, %s)) "
        "PARTITION BY RANGE (%s)",
        SQL.identifier(tablename), SQL.identifier(date_column),
        SQL.identifier(date_column), SQL.identifier(date_column),
    ))


def ensure_year_partitions(cr, tablename, date_column, years_behind=YEARS_BEHIND, years_ahead=YEARS_AHEAD):
    """ Idempotently create one partition per calendar year, from
    `years_behind` years ago through `years_ahead` years from now, so
    there's always a partition ready for a backdated or future-dated row.
    Safe to call repeatedly - at install time, and from a recurring cron
    that keeps extending the forward end of the range.
    """
    this_year = date.today().year
    for year in range(this_year - years_behind, this_year + years_ahead + 1):
        partition = f'{tablename}_y{year}'
        if table_exists(cr, partition):
            continue
        cr.execute(SQL(
            "CREATE TABLE %s PARTITION OF %s FOR VALUES FROM (%s) TO (%s)",
            SQL.identifier(partition), SQL.identifier(tablename),
            date(year, 1, 1), date(year + 1, 1, 1),
        ))
