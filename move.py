# This file is part account_invoice_posted2draft module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction


class Move(metaclass=PoolMeta):
    __name__ = 'account.move'

    def get_allow_draft(self, name):
        Invoice = Pool().get('account.invoice')
        Move = Pool().get('account.move')

        result = super().get_allow_draft(name)

        if self.origin and isinstance(self.origin, (Invoice, Move)):
            return True
        return result
