from odoo import fields
from odoo.tools import sql

UINT128_MAX = (1 << 128) - 1


class UInt128(fields.Integer):
    """ Unsigned 128-bit integer, for Tigerbeetle ids: plain `fields.Integer`
    maps to a 32-bit Postgres column, and even `bigint` only covers 64 bits
    signed - neither can hold a Tigerbeetle id, which is a u128. Postgres has
    no native 128-bit integer type, so this is stored as an unbounded
    `numeric` column with a CHECK constraint restricting it to the uint128
    range.
    """
    _column_type = ('numeric', 'numeric')

    def update_db_column(self, model, column):
        super().update_db_column(model, column)
        cr = model.env.cr
        conname = f'{model._table}_{self.name}_uint128'
        definition = f'CHECK ({self.name} BETWEEN 0 AND {UINT128_MAX})'
        current_definition = sql.constraint_definition(cr, model._table, conname)
        if current_definition == definition:
            return
        if current_definition:
            sql.drop_constraint(cr, model._table, conname)
        model.pool.post_constraint(
            cr, lambda cr: sql.add_constraint(cr, model._table, conname, definition), conname)


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
