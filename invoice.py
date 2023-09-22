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
        #cls._check_modify_exclude.add('move')
        cls._transitions |= set((('posted', 'draft'),))
        cls._buttons['draft']['invisible'] = ~Eval('allow_draft', False)
        cls._buttons['draft']['depends'] += tuple(['allow_draft'])

    def get_allow_draft(self, name):
        if self.state not in {'posted', 'cancelled', 'validated'}:
            return False
        elif self.state == 'posted':
            lines_to_pay = [l for l in self.lines_to_pay
                if not l.reconciliation]
            # Invoice allready paid or partial paid, could not be possible
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
            if (not invoice.allow_draft
                    or (invoice.state in ('validated', 'cancelled')
                        and invoice.number is None)):
                to_draft.append(invoice)
                continue

            if invoice.state == 'canceled':
                invoice.additional_moves += tuple(
                    [invoice.move, invoice.cnacel_move])
                to_save.append(invoice)
                continue

            if invoice.state == 'validated':
                to_save.append(invoice)
                continue

            lines_to_pay = [l for l in invoice.lines_to_pay
                if not l.reconciliation]
            extra_lines = [l for l in invoice.move.lines
                if not l.account.reconcile]

            compensation_move = Move.create_compensation_move(
                lines_to_pay + extra_lines, origin=invoice)
            moves.append(compensation_move)

            invoice.additional_moves += tuple(
                [invoice.move, compensation_move])
            invoice.move = None
            to_save.append(invoice)

        if moves:
            Move.post(moves)

        # Only make the special steps for the invoices that came from 'posted'
        # state or 'validated', 'canceled' with number, so the invoice have one
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

        if to_save:
            cls._clean_payments(to_save)
