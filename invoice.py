# This file is part account_invoice_posted2draft module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool, PoolMeta
from trytond.model import fields
from trytond.pyson import Eval
from trytond.transaction import Transaction
from trytond.i18n import gettext
from trytond.exceptions import UserError


class Invoice(metaclass=PoolMeta):
    __name__ = 'account.invoice'

    allow_draft = fields.Function(
        fields.Boolean("Allow Draft Invoice"), 'get_allow_draft')

    @classmethod
    def __setup__(cls):
        super(Invoice, cls).__setup__()
        cls._transitions |= set((('posted', 'draft'),))
        cls._buttons['draft']['invisible'] = ~Eval('allow_draft', False)
        cls._buttons['draft']['depends'] += tuple(['allow_draft'])

    def get_allow_draft(self, name):
        # when IN invoice is validate from scratch, the move is in 'draft'
        # state, so in this case could be draft in a "normal" way
        if (self.state == 'validated' and self.move
                and self.move.state != 'draft'):
            return False
        elif self.state == 'cancelled' and self.number is not None:
            return False
        elif self.state in {'paid', 'draft'}:
            return False
        elif self.state == 'posted':
            lines_to_pay = [l for l in self.lines_to_pay
                if not l.reconciliation]
            # Invoice already paid or partial paid, should not be possible
            # to change state to draft.
            if (not lines_to_pay
                    or self.amount_to_pay != self.total_amount):
                return False
        return True

    @classmethod
    def draft(cls, invoices):
        pool = Pool()
        Move = pool.get('account.move')
        MoveLine = pool.get('account.move.line')
        JournalPeriod = pool.get('account.journal.period')
        Warning = pool.get('res.user.warning')

        moves = []
        move_lines = []
        to_draft = []
        to_save = []
        for invoice in invoices:
            if not invoice.allow_draft:
                continue

            move = invoice.move
            if move:
                if move.state == 'draft':
                    to_draft.append(invoice)
                else:
                    to_save.append(invoice)
                    cancel_move = move.cancel(reversal=True)
                    Move.post([cancel_move])
                    moves.extend((invoice.move, cancel_move))
                    invoice.move = None
            else:
                to_draft.append(invoice)
            if invoice.cancel_move:
                moves.append(invoice.cancel_move)
                invoice.cancel_move = None
            invoice.additional_moves += tuple(moves)

        # Only make the special steps for the invoices that came from 'posted'
        # state or 'validated', 'cancelled' with number, so the invoice have one
        # or more move associated.
        # The other possible invoices follow the standard workflow.
        if to_draft:
            super().draft(to_draft)
        if to_save:
            cls.save(to_save)
            with Transaction().set_context(invoice_posted2draft=True):
                super().draft(to_save)

        for invoice in to_save:
            to_reconcile = []
            for move in invoice.additional_moves:
                for line in move.lines:
                    if (not line.reconciliation
                            and line.account == invoice.account):
                        to_reconcile.append(line)
            if to_reconcile:
                MoveLine.reconcile(to_reconcile)

        # Remove links to lines which actually do not pay the invoice
        if to_save:
            cls._clean_payments(to_save)
