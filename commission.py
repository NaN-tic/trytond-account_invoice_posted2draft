# This file is part account_invoice_posted2draft module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool, PoolMeta
from trytond.tools import grouped_slice

__all__ = ['Invoice']


class Invoice(metaclass=PoolMeta):
    __name__ = 'account.invoice'

    @classmethod
    def draft(cls, invoices):
        Commission = Pool().get('commission')

        for sub_invoices in grouped_slice(invoices):
            ids = [i.id for i in sub_invoices]
            commissions = Commission.search([
                    ('origin.invoice', 'in', ids, 'account.invoice.line'),
                    ])
            if commissions:
                commissions_origin = Commission.search([
                        ('origin.id', 'in', [c.id for c in commissions], 'commission'),
                        ])
                if commissions_origin:
                    commissions += commissions_origin
            Commission.delete(commissions)

        return super(Invoice, cls).draft(invoices)
