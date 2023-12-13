# This file is part account_invoice_posted2draft module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool, PoolMeta

__all__ = ['Invoice']


class Invoice(metaclass=PoolMeta):
    __name__ = 'account.invoice'

    @classmethod
    def draft(cls, invoices):
        Payment = Pool().get('account.payment')

        lines = []
        for invoice in invoices:
            if invoice.move:
                lines.extend([l.id for l in invoice.move.lines])
        if lines:
            payments = Payment.search([
                    ('line', 'in', lines),
                    ('state', '=', 'failed'),
                    ])
            if payments:
                Payment.write(payments, {'line': None})

        return super(Invoice, cls).draft(invoices)
