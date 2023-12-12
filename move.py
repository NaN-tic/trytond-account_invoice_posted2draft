# This file is part account_invoice_posted2draft module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction


class Move(metaclass=PoolMeta):
    __name__ = 'account.move'

    @classmethod
    def check_modify(cls, *args, **kwargs):
        # As now the moves related to an invoice are not delete when 'draft'
        # the invoice, is needed to modify some restricted fields when the
        # move is in post state
        if Transaction().context.get('invoice_posted2draft', False):
            return
        return super().check_modify(*args, **kwargs)

    @classmethod
    def delete(cls, moves):
        # When invoice is set to 'draft', try to delete the move's associated
        # in 'move' and 'additional_move' fields. If these moves are posted
        # they cannot be deleted but keep them as history
        if Transaction().context.get('invoice_posted2draft', False):
            return
        super().delete(moves)


class Line(metaclass=PoolMeta):
    __name__ = 'account.move.line'

    @classmethod
    def check_modify(cls, lines, modified_fields=None):
        # As now the moves related to an invoice are not delete when 'draft'
        # the invoice, is needed to modify some restricted fields when the
        # move is in post state
        if Transaction().context.get('invoice_posted2draft', False):
            return
        return super().check_modify(lines, modified_fields)
