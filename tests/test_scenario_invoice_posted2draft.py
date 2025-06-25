import unittest
from decimal import Decimal

from proteus import Model
from trytond.model.modelstorage import DomainValidationError
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
        activate_modules(['account_invoice_posted2draft', 'account_es'])


        # Create company
        _ = create_company()
        company = get_company()

        # allow cancel invoices
        company.cancel_invoice_out = True
        company.save()

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
        invoice1 = Invoice()
        invoice1.party = party
        invoice1.payment_term = payment_term
        line = invoice1.lines.new()
        line.product = product
        line.quantity = 5
        line.unit_price = Decimal('40')
        self.assertEqual(invoice1.untaxed_amount, Decimal('200.00'))
        invoice1.click('post')
        self.assertEqual(invoice1.number, '1')
        receivable.reload()
        self.assertEqual(receivable.debit, Decimal('200.00'))

        # Move it back to draft
        invoice1.click('draft')
        self.assertEqual(invoice1.number, '1')
        invoice1.invoice_report_cache
        receivable.reload()
        self.assertEqual(receivable.debit, Decimal('0'))
        self.assertEqual(receivable.credit, Decimal('0'))

        # Create invoice with reprograming payment date
        invoice2 = Invoice()
        invoice2.party = party
        invoice2.payment_term = payment_term
        line = invoice2.lines.new()
        line.product = product
        line.quantity = 5
        line.unit_price = Decimal('40')
        self.assertEqual(invoice2.untaxed_amount, Decimal('200.00'))
        invoice2.click('post')
        self.assertEqual(invoice2.number, '2')
        receivable.reload()
        self.assertEqual(receivable.debit, Decimal('200.00'))

        #Reschedule line
        reschedule = invoice2.click('reschedule_lines_to_pay')
        reschedule_lines, = reschedule.actions
        self.assertEqual(reschedule_lines.form.total_amount, Decimal('200.00'))
        reschedule_lines.form.start_date = invoice2.move.period.end_date
        reschedule_lines.form.frequency ='monthly'
        reschedule_lines.form.number = 2
        reschedule_lines.execute('preview')
        reschedule_lines.execute('reschedule')

        invoice2.reload()
        self.assertEqual(invoice2.state, 'posted')
        self.assertEqual(len(invoice2.lines_to_pay), Decimal('4'))
        self.assertEqual(len([l for l in invoice2.lines_to_pay if not l.reconciliation]), Decimal('2'))
        self.assertEqual(invoice2.amount_to_pay, Decimal('200.00'))
        self.assertEqual(len(invoice2.additional_moves), Decimal('1'))

        # Move it back to draft
        invoice2.click('draft')
        self.assertEqual(invoice2.number, '2')
        invoice2.invoice_report_cache
        self.assertEqual(invoice2.move, None)
        self.assertEqual(invoice2.additional_moves, [])
        receivable.reload()
        self.assertEqual(receivable.debit, Decimal('0'))
        self.assertEqual(receivable.credit, Decimal('0'))

        # Create invoice and not allow cancel in case has number
        invoice3 = Invoice()
        invoice3.party = party
        invoice3.payment_term = payment_term
        line = invoice3.lines.new()
        line.product = product
        line.quantity = 5
        line.unit_price = Decimal('40')
        self.assertEqual(invoice3.untaxed_amount, Decimal('200.00'))
        invoice3.click('post')
        self.assertEqual(invoice3.number, '3')
        self.assertEqual(invoice3.allow_draft, True)
        invoice3.click('draft')
        self.assertEqual(invoice3.number, '3')
        self.assertEqual(invoice3.move, None)
        self.assertEqual(invoice3.state, 'draft')
        self.assertEqual(invoice3.allow_draft, False)
        self.assertEqual(invoice3.allow_cancel, False)
        invoice3.click('cancel')
        # invoice state, keep in draft state
        self.assertEqual(invoice3.state, 'draft')
        invoice3.click('post')
        self.assertEqual(invoice3.state, 'posted')
        self.assertEqual(invoice3.allow_cancel, True)
        invoice3.click('cancel')
        self.assertEqual(invoice3.state, 'cancelled')
        self.assertNotEqual(invoice3.move, None)
        self.assertNotEqual(invoice3.cancel_move, None)

        # Invoices can not be set to draft if period is closed
        invoice1.click('post')
        invoice2.click('post')
        invoice1.move.period.click('close')

        with self.assertRaises(DomainValidationError):
            invoice1.click('draft')
