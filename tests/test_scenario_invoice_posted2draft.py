import unittest
from decimal import Decimal

from proteus import Model
from trytond.modules.account.exceptions import CancelWarning
from trytond.modules.account.tests.tools import (create_chart,
                                                 create_fiscalyear,
                                                 get_accounts)
from trytond.modules.account_invoice.tests.tools import (
    create_payment_term, set_fiscalyear_invoice_sequences)
from trytond.modules.company.tests.tools import create_company, get_company
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules


class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):

        # Install account_invoice_posted2draft
        activate_modules('account_invoice_posted2draft')

        # Create company
        _ = create_company()
        company = get_company()

        # Create fiscal year
        fiscalyear = set_fiscalyear_invoice_sequences(
            create_fiscalyear(company))
        fiscalyear.click('create_period')

        # Create chart of accounts
        _ = create_chart(company)
        accounts = get_accounts(company)
        receivable = accounts['receivable']
        revenue = accounts['revenue']
        expense = accounts['expense']

        # Create party
        Party = Model.get('party.party')
        party = Party(name='Party')
        party.save()

        # Create account category
        ProductCategory = Model.get('product.category')
        account_category = ProductCategory(name="Account Category")
        account_category.accounting = True
        account_category.account_expense = expense
        account_category.account_revenue = revenue
        account_category.save()

        # Create product
        ProductUom = Model.get('product.uom')
        unit, = ProductUom.find([('name', '=', 'Unit')])
        ProductTemplate = Model.get('product.template')
        template = ProductTemplate()
        template.name = 'product'
        template.default_uom = unit
        template.type = 'service'
        template.list_price = Decimal('40')
        template.account_category = account_category
        product, = template.products
        product.cost_price = Decimal('25')
        template.save()
        product, = template.products

        # Create payment term
        payment_term = create_payment_term()
        payment_term.save()

        # Create invoice
        Invoice = Model.get('account.invoice')
        invoice = Invoice()
        invoice.party = party
        invoice.payment_term = payment_term
        line = invoice.lines.new()
        line.product = product
        line.quantity = 5
        line.unit_price = Decimal('40')
        self.assertEqual(invoice.untaxed_amount, Decimal('200.00'))
        invoice.click('post')
        self.assertEqual(invoice.number, '1')
        receivable.reload()
        self.assertEqual(receivable.debit, Decimal('200.00'))

        # Move it back to draft
        invoice.click('draft')
        self.assertEqual(invoice.number, '1')
        invoice.invoice_report_cache
        receivable.reload()
        self.assertEqual(receivable.debit, Decimal('200.00'))
        self.assertEqual(receivable.credit, Decimal('200.00'))

        # Invoices can not be set to draft if period is closed
        invoice.click('post')
        invoice.move.period.click('close')

        with self.assertRaises(CancelWarning):
            invoice.click('draft')
