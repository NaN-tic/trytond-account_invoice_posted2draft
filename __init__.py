# This file is part account_invoice_posted2draft module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from . import invoice
from . import commission
from . import payment


def register():
    Pool.register(
        invoice.Invoice,
        invoice.Move,
        module='account_invoice_posted2draft', type_='model')
    Pool.register(
        payment.Invoice,
        depends=['account_payment'],
        module='account_invoice_posted2draft', type_='model')
    Pool.register(
        commission.Invoice,
        depends=['commission'],
        module='account_invoice_posted2draft', type_='model')
