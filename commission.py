# This file is part account_invoice_posted2draft module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool, PoolMeta
from trytond.tools import grouped_slice
from trytond.transaction import Transaction
from sql.operators import Concat


class Invoice(metaclass=PoolMeta):
    __name__ = 'account.invoice'

    @classmethod
    def get_allow_draft(cls, invoices, name):
        pool = Pool()
        Commission = pool.get('commission')
        Line = pool.get('account.invoice.line')

        res = super().get_allow_draft(invoices, name)

        line = Line.__table__()
        commission = Commission.__table__()

        invoice_ids = [i.id for i in invoices]
        query = line.join(commission,
            condition=commission.origin == Concat('account.invoice.line,', line.id)
            ).select(line.invoice, where=line.invoice.in_(invoice_ids))

        cursor = Transaction().connection.cursor()
        cursor.execute(*query)
        for record in cursor.fetchall():
            res[record[0]] = False

        return res

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
