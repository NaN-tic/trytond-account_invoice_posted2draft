# This file is part account_invoice_posted2draft module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import PoolMeta


class Invoice(metaclass=PoolMeta):
    __name__ = 'account.invoice'

    def get_allow_cancel(self, name):
        allow_cancel = super().get_allow_cancel(name)
        # not allow cancel invoices in case has number and not move
        if self.number and not self.move:
            return False
        return allow_cancel

    @classmethod
    def cancel(cls, invoices):
        # check allow_cancel invoices
        to_cancel = [invoice for invoice in invoices if invoice.allow_cancel]
        super().cancel(to_cancel)
