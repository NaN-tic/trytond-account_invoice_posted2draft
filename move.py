# This file is part account_invoice_posted2draft module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction


class Move(metaclass=PoolMeta):
    __name__ = 'account.move'

    @classmethod
    def check_modify(cls, *args, **kwargs):
        if Transaction().context.get('invoice_posted2draft', False):
            return
        return super().check_modify(*args, **kwargs)

    @classmethod
    def delete(cls, moves):
        if Transaction().context.get('invoice_posted2draft', False):
            return
        super().delete(moves)

    @classmethod
    def create_compensation_move(cls, lines, origin=None, journal=None):
        """
        Create a compensation move from move lines.
        And add the origin if is setted.
        If origini is setted and it is an invoice, for example, the
        journal is not needed becasue is taken the invoice.

        """
        pool = Pool()
        MoveLine = pool.get('account.move.line')
        Period = pool.get('account.period')
        Date = pool.get('ir.date')

        if not lines:
            return None

        company_id = (origin.company.id if hasattr(origin, 'company')
            else Transaction().context.get('company'))
        with Transaction().set_context(company=company_id):
            date = Date.today()
        period_id = Period.find(company_id, date=date)
        if not period_id:
            raise UserError(gettext(
                    'account_invoice_posted2draft.msg_draft_closed_period',
                    period=Period(period_id).rec_name,
                    ))
        if not journal:
            journal = origin.journal if hasattr(origin, 'journal') else None

        move = cls()
        move.journal = journal
        move.period = period_id
        move.date = date
        move.origin = origin
        move.company = company_id
        move.save()

        default = {
            'move': move,
            'debit': lambda data: data['credit'],
            'credit': lambda data: data['debit'],
            'amount_second_currency': (
                lambda data: data['amount_second_currency'] * -1
                if data['amount_second_currency']
                else data['amount_second_currency']),
            'tax_lines.amount': lambda data: data['amount'] * -1,
            'origin': (
                lambda data: 'account.move.line,%s' % data['id']),
            'analytic_lines.debit': lambda data: data['credit'],
            'analytic_lines.credit': lambda data: data['debit'],
            'bank_account': None,
            'payment_type': None,
            }
        move_lines = MoveLine.copy(lines, default=default)

        return move


class Line(metaclass=PoolMeta):
    __name__ = 'account.move.line'

    @classmethod
    def check_modify(cls, lines, modified_fields=None):
        if Transaction().context.get('invoice_posted2draft', False):
            return
        return super().check_modify(lines, modified_fields)
