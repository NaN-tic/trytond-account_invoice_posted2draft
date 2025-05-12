# This file is part account_invoice_posted2draft module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool, PoolMeta
from trytond.model import fields
from itertools import groupby
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
        super().__setup__()
        cls._transitions |= set((('posted', 'draft'),))
        cls._buttons['draft']['invisible'] = ~Eval('allow_draft', False)
        cls._buttons['draft']['depends'] += tuple(['allow_draft'])
        cls._check_modify_exclude.update(['validated_by', 'posted_by'])

    @classmethod
    def get_allow_draft(cls, invoices, name):
        res = dict((x.id, False) for x in invoices)

        for invoice in invoices:
            if invoice.state in {'paid', 'draft'}:
                continue
            elif (invoice.state == 'posted' and (invoice.payment_lines
                        or invoice.reconciliation_lines)):
                continue
            res[invoice.id] = True
        return res

    @classmethod
    def draft(cls, invoices):
        pool = Pool()
        Move = pool.get('account.move')
        Reconciliation = pool.get('account.move.reconciliation')

        for invoice in invoices:
            if not invoice.allow_draft:
                continue

            # Before delete all the moves related with the invoice ensure that
            # all of them, if are reconcilied, are reconciliated themself, not
            # with an "external" move.
            moves = [x for x in ([invoice.move, invoice.cancel_move]
                + list(invoice.additional_moves)) if x is not None]
            if not moves:
                continue
            lines = [x for move in moves for line in move.lines
                if line.reconciliation is not None
                for x in line.reconciliation.lines]
            lines = list(set(lines))
            lines.sort(key=lambda line: line.reconciliation.id)
            grouped_reconciliations = {
                reconciliation: list({line.move for line in group})
                for reconciliation, group in groupby(lines,
                    key=lambda line: line.reconciliation)
                }
            for _, reconciliation_moves in grouped_reconciliations.items():
                if not set(reconciliation_moves).issubset(set(moves)):
                    raise UserError(gettext(
                        'account_invoice_posted2draft.msg_not_allowed_to_draft',
                        invoice=invoice.number))
            Reconciliation.delete(grouped_reconciliations.keys())
            with Transaction().set_context(invoice_posted2draft=True):
                if Move._buttons.get('draft', None):
                    Move.draft(moves)
                Move.delete(moves)
        with Transaction().set_context(invoice_posted2draft=True):
            super().draft(invoices)
        cls.write(invoices, {
            'invoice_report_format': None,
            'invoice_report_cache': None,
            'invoice_report_cache_id': None,
            })
