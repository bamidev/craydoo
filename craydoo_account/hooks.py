from .partition import PARTITIONED_TABLES, create_partitioned_table, ensure_year_partitions


def pre_init_hook(env):
    """ Pre-create the partitioned tables of this module before `_auto_init`
    gets to them, and populate their initial set of year partitions, so
    installation doesn't trip over "no partition of relation found for
    row" the first time an invoice gets created.
    """
    for tablename, date_column in PARTITIONED_TABLES:
        create_partitioned_table(env.cr, tablename, date_column)
        ensure_year_partitions(env.cr, tablename)
