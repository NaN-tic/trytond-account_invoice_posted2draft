# This file is part account_invoice_posted2draft module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool, PoolMeta
from trytond.i18n import gettext
from trytond.exceptions import UserError


class Invoice(metaclass=PoolMeta):
    __name__ = 'account.invoice'

    @classmethod
    def draft(cls, invoices):
        pool = Pool()
        Payment = pool.get('account.payment')

        for invoice in invoices:
            moves = []
            if invoice.move:
                moves.append(invoice.move)
            if invoice.additional_moves:
                moves.extend(invoice.additional_moves)

            if moves:
                lines = [l.id for m in moves for l in m.lines]
                if lines:
                    payments = Payment.search([
                            ('line', 'in', lines),
                            ('state', '!=', 'failed'),
                            ])
                    if payments:
                        raise UserError(gettext('account_invoice_posted2draft'
                                '.msg_invoice_in_payment',
                                invoice=invoice.rec_name,
                                payments=", ".join([p.id for p in payments])))
        return super().draft(invoices)
