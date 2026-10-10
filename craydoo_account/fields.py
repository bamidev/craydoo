from odoo import fields
from odoo.tools import sql

UBIGINTEGER_MAX = (1 << 63) - 1


class UBigInteger(fields.Integer):
    """ Non-negative integer stored as a native Postgres `bigint` (`int8`).
    `bigint` itself is signed 64-bit, and Postgres has no native unsigned
    integer type at all, so this only ever uses the non-negative half of
    that range - 0 to 2**63-1 (63 bits of magnitude, not 64) - via a CHECK
    constraint.
    """
    _column_type = ('int8', 'bigint')

    def update_db_column(self, model, column):
        super().update_db_column(model, column)
        cr = model.env.cr
        conname = f'{model._table}_{self.name}_ubiginteger'
        definition = f'CHECK ({self.name} BETWEEN 0 AND {UBIGINTEGER_MAX})'
        current_definition = sql.constraint_definition(cr, model._table, conname)
        if current_definition == definition:
            return
        if current_definition:
            sql.drop_constraint(cr, model._table, conname)
        model.pool.post_constraint(
            cr, lambda cr: sql.add_constraint(cr, model._table, conname, definition), conname)


class BigInteger(fields.Integer):
    """ Signed 64-bit integer, stored as a native Postgres `bigint` (`int8`)
    instead of the usual 32-bit `integer` - for values that need the full
    64-bit signed range and can legitimately go negative (e.g. a running
    account balance), unlike `UBigInteger`. No CHECK constraint needed:
    `bigint`'s native range already *is* the signed 64-bit range.
    """
    _column_type = ('int8', 'bigint')


class PartitionedMany2one(fields.Many2one):
    """ Like Many2one, but the comodel's table is range-partitioned, so its
    primary key is a composite `(id, <partition column>)` rather than
    Odoo's usual plain `id` - a single-column `FOREIGN KEY (self)
    REFERENCES comodel(id)` is therefore impossible to create (Postgres
    requires a unique constraint on a partitioned table to cover its
    partition column). This skips the foreign key Many2one would otherwise
    add automatically; the real (composite) one must be declared by hand as
    a `models.Constraint` on this field's model.
    """
    def update_db_foreign_key(self, model, column):
        pass
