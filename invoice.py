# This file is part account_invoice_posted2draft module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import Workflow, ModelView
from trytond.pyson import Eval
from trytond.pool import Pool, PoolMeta

__all__ = ['Invoice']
__metaclass__ = PoolMeta


class Invoice:
    __name__ = 'account.invoice'

    @classmethod
    def __setup__(cls):
        super(Invoice, cls).__setup__()
        cls._check_modify_exclude.append('move')
        cls._transitions |= set((('posted', 'draft'),))
        cls._buttons.update({
                'draft': {
                    'invisible': (Eval('state').in_(['draft', 'paid'])
                    | ((Eval('state') == 'cancel') & Eval('cancel_move'))),
                    },
                })
        cls._error_messages.update({
                'cancel_invoice_with_number': ('You cannot cancel an invoice '
                    'with number.'),
                })

    @classmethod
    @ModelView.button
    @Workflow.transition('draft')
    def draft(cls, invoices):
        pool = Pool()
        Move = pool.get('account.move')
        try:
            Payment = pool.get('account.payment')
        except KeyError:
            Payment = None
        moves = []
        lines = []
        for invoice in invoices:
            if invoice.move:
                moves.append(invoice.move)
                lines.extend([l.id for l in invoice.move.lines])
        if moves:
            Move.draft(moves)
        if Payment:
            payments = Payment.search([
                    ('line', 'in', lines),
                    ('state', '=', 'failed'),
                    ])
            if payments:
                Payment.write(payments, {'line': None})
        cls.write(invoices, {
            'invoice_report_format': None,
            'invoice_report_cache': None,
            })
        return super(Invoice, cls).draft(invoices)

    @classmethod
    @Workflow.transition('cancel')
    def cancel(cls, invoices):
        for invoice in invoices:
            if (invoice.type in ('out_invoice', 'out_credit_note') and
                    invoice.number):
                cls.raise_user_error('cancel_invoice_with_number')

        return super(Invoice, cls).cancel(invoices)
