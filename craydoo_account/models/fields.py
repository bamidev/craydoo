from odoo import fields


class BigInteger(fields.Integer):
    """ 64-bit integer, for Tigerbeetle ids: plain `fields.Integer` maps to a
    32-bit Postgres column, too small to hold one.
    """
    column_type = ('int8', 'bigint')
