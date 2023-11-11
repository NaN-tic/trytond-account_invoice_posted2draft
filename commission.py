# This file is part account_invoice_posted2draft module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool, PoolMeta
from trytond.tools import grouped_slice


class Invoice(metaclass=PoolMeta):
    __name__ = 'account.invoice'

    def get_allow_draft(self, name):
        pool = Pool()
        Commission = pool.get('commission')

        result = super().get_allow_draft(name)

        invoiced = Commission.search([
                ('origin.invoice', '=', self.id, 'account.invoice.line'),
                ('invoice_line', '!=', None),
                ])
        if invoiced:
            result = False
        return result

    @classmethod
    def draft(cls, invoices):
        pool = Pool()
        Commission = pool.get('commission')

        to_delete = []
        for sub_invoices in grouped_slice(invoices):
            ids = [i.id for i in sub_invoices]
            to_delete = Commission.search([
                    ('origin.invoice', 'in', ids, 'account.invoice.line'),
                    ('invoice_line', '=', None),
                    ])
            if to_delete:
                to_delete_origin = Commission.search([
                        ('origin.id', 'in',
                            [x.id for x in to_delete], 'commission'),
                        ('invoice_line', '=', None),
                        ])
                if to_delete_origin:
                    to_delete += to_delete_origin
            Commission.delete(to_delete)
        return super(Invoice, cls).draft(invoices)
