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
        cls._buttons['draft']['invisible'] = (
            Eval('state').in_(['draft', 'paid']) | (
                (Eval('state') == 'cancelled') & Eval('cancel_move')))

    @classmethod
    def draft(cls, invoices):
        pool = Pool()
        Move = pool.get('account.move')
        MoveLine = pool.get('account.move.line')
        Reconcile = pool.get('account.move.reconciliation')
        JournalPeriod = pool.get('account.journal.period')

        moves = []
        payment_lines = []
        reconciliation_to_delete = set()
        for invoice in invoices:
            invoice_moves = []
            if invoice.move:
                invoice_moves.append(invoice.move)
            invoice_moves += list(invoice.additional_moves)
            move_lines = [l for move in invoice_moves for l in move.lines]
            for move in invoice_moves:
                for line in move.lines:
                    if line.reconciliation:
                        line_reconciles = MoveLine.search([
                                ('reconciliation', '=', line.reconciliation.id)
                                ])
                        if set(line_reconciles) - set(move_lines) == set():
                            reconciliation_to_delete.add(line.reconciliation)
                # check period is closed
                if move.period.state == 'close':
                    raise UserError(gettext(
                        'account_invoice_posted2draft.msg_draft_closed_period',
                            invoice=invoice.rec_name,
                            period=move.period.rec_name,
                            ))
                # check period and journal is closed
                journal_periods = JournalPeriod.search([
                        ('journal', '=', move.journal.id),
                        ('period', '=', move.period.id),
                        ], limit=1)
                if journal_periods:
                    journal_period, = journal_periods
                    if journal_period.state == 'close':
                        raise UserError(gettext(
                            'account_invoice_posted2draft.'
                                'msg_modify_closed_journal_period',
                                invoice=invoice.rec_name,
                                journal_period=journal_period.rec_name))
                moves.append(move)
            if invoice.payment_lines:
                for payment_line in invoice.payment_lines:
                    if payment_line.move and payment_line.move.lines:
                        for lines in payment_line.move.lines:
                            payment_lines.append(lines)

        if reconciliation_to_delete:
            Reconcile.delete(reconciliation_to_delete)
        if moves:
            with Transaction().set_context(draft_invoices=True):
                Move.write(moves, {'state': 'draft'})
                # If the payment lines dont have a reconciliation, then the field
                # invoice_payment will be fill up, and when we try to draft an
                # invoice it will give us an error
                if payment_lines:
                    MoveLine.write(payment_lines, {'invoice_payment':None})
        cls.write(invoices, {
            'invoice_report_format': None,
            'invoice_report_cache': None,
            })
        with Transaction().set_context(draft_invoices=True):
            return super(Invoice, cls).draft(invoices)

    @classmethod
    def credit(cls, invoices, refund=False, **values):
        with Transaction().set_context(cancel_from_credit=True):
            return super().credit(invoices, refund, **values)


class Move(metaclass=PoolMeta):
    __name__ = 'account.move'

    @classmethod
    def check_modify(cls, *args, **kwargs):
        if Transaction().context.get('draft_invoices', False):
            return
        return super(Move, cls).check_modify(*args, **kwargs)
