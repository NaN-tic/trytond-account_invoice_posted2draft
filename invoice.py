# This file is part account_invoice_posted2draft module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pyson import Eval
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.i18n import gettext
from trytond.exceptions import UserError


class Invoice(metaclass=PoolMeta):
    __name__ = 'account.invoice'

    @classmethod
    def __setup__(cls):
        super(Invoice, cls).__setup__()
        cls._check_modify_exclude.add('move')
        cls._transitions |= set((('posted', 'draft'),))
        cls._buttons.update({
                'draft': {
                    'invisible': (Eval('state').in_(['draft', 'paid'])
                        | ((Eval('state') == 'cancelled') & Eval('cancel_move'))),
                    },
                })

    @classmethod
    def draft(cls, invoices):
        pool = Pool()
        Move = pool.get('account.move')
        JournalPeriod = pool.get('account.journal.period')

        moves = []
        for invoice in invoices:
            if invoice.move:
                # check period is closed
                if invoice.move.period.state == 'close':
                    raise UserError(gettext(
                        'account_invoice_posted2draft.msg_draft_closed_period',
                            invoice=invoice.rec_name,
                            period=invoice.move.period.rec_name,
                            ))
                # check period and journal is closed
                journal_periods = JournalPeriod.search([
                        ('journal', '=', invoice.move.journal.id),
                        ('period', '=', invoice.move.period.id),
                        ], limit=1)
                if journal_periods:
                    journal_period, = journal_periods
                    if journal_period.state == 'close':
                        raise UserError(gettext(
                            'account_invoice_posted2draft.'
                                'msg_modify_closed_journal_period',
                                invoice=invoice.rec_name,
                                journal_period=journal_period.rec_name))
                moves.append(invoice.move)
        if moves:
            with Transaction().set_context(draft_invoices=True):
                Move.write(moves, {'state': 'draft'})
        cls.write(invoices, {
            'invoice_report_format': None,
            'invoice_report_cache': None,
            })
        with Transaction().set_context(draft_invoices=True):
            return super(Invoice, cls).draft(invoices)

    @classmethod
    def credit(cls, invoices, refund=False):
        with Transaction().set_context(cancel_from_credit=True):
            return super().credit(invoices, refund)

    @classmethod
    def cancel(cls, invoices):
        if not Transaction().context.get('cancel_from_credit', False):
            for invoice in invoices:
                if invoice.type == 'out' and invoice.number:
                    raise UserError(
                        gettext('account_invoice_posted2draft.'
                            'msg_cancel_invoice_with_number',
                            invoice=invoice.rec_name))
        return super(Invoice, cls).cancel(invoices)


class Move(metaclass=PoolMeta):
    __name__ = 'account.move'

    @classmethod
    def check_modify(cls, *args, **kwargs):
        if Transaction().context.get('draft_invoices', False):
            return
        return super(Move, cls).check_modify(*args, **kwargs)
