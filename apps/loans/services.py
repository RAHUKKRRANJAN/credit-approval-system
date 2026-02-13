"""
Loan service layer.

Contains credit score calculation, eligibility checking,
and loan creation logic. This is the core business logic
of the credit approval system.
"""

import logging
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from dateutil.relativedelta import relativedelta

from django.db import transaction
from django.db.models import Sum

from apps.core.exceptions import CustomerNotFoundError
from apps.core.utils import calculate_emi
from apps.customers.models import Customer
from apps.loans.models import Loan

logger = logging.getLogger(__name__)


class CreditScoreService:
    """
    Service for calculating customer credit scores.

    Credit score is computed out of 100 based on 5 factors
    from historical loan data.
    """

    # Weight distribution for credit score components (total = 100)
    WEIGHT_ON_TIME_PAYMENT = 30
    WEIGHT_NUM_LOANS = 20
    WEIGHT_CURRENT_YEAR_ACTIVITY = 20
    WEIGHT_LOAN_VOLUME = 30

    @classmethod
    def calculate(cls, customer: Customer) -> int:
        """
        Calculate credit score for a customer (0-100).

        Factors:
            i.   Past loans paid on time
            ii.  Number of loans taken in past
            iii. Loan activity in current year
            iv.  Loan approved volume vs approved limit
            v.   If total current loans > approved_limit → score = 0

        Args:
            customer: The Customer instance.

        Returns:
            Credit score as integer (0-100).
        """
        loans = Loan.objects.filter(customer=customer)

        # No loan history → baseline credit score
        if not loans.exists():
            return 50

        total_loans = loans.count()
        active_loans = loans.filter(is_active=True)

        # Factor v: If total current loan amount > approved_limit → score = 0
        total_current_loan_amount = active_loans.aggregate(
            total=Sum('loan_amount')
        )['total'] or Decimal('0')

        if total_current_loan_amount > customer.approved_limit:
            logger.info(
                "Customer %d: current loans (%s) > approved_limit (%d) → score=0",
                customer.pk,
                total_current_loan_amount,
                customer.approved_limit,
            )
            return 0

        # Factor i: Past loans paid on time
        totals = loans.aggregate(
            total_tenure=Sum('tenure'),
            total_on_time=Sum('emis_paid_on_time'),
        )
        total_emis_due = totals['total_tenure'] or 0
        total_emis_on_time = totals['total_on_time'] or 0

        if total_emis_due > 0:
            on_time_ratio = total_emis_on_time / total_emis_due
        else:
            on_time_ratio = 0.0

        score_on_time = on_time_ratio * cls.WEIGHT_ON_TIME_PAYMENT

        # Factor ii: Number of loans taken
        # Fewer loans = better score. Penalize for too many loans.
        if total_loans <= 2:
            loan_count_ratio = 1.0
        elif total_loans <= 5:
            loan_count_ratio = 0.7
        elif total_loans <= 10:
            loan_count_ratio = 0.4
        else:
            loan_count_ratio = 0.1

        score_num_loans = loan_count_ratio * cls.WEIGHT_NUM_LOANS

        # Factor iii: Loan activity in current year
        current_year = date.today().year
        current_year_loans = loans.filter(start_date__year=current_year).count()

        if current_year_loans == 0:
            activity_ratio = 1.0  # No new loans this year = stable
        elif current_year_loans <= 2:
            activity_ratio = 0.7
        elif current_year_loans <= 4:
            activity_ratio = 0.4
        else:
            activity_ratio = 0.1  # Too many loans this year = risky

        score_activity = activity_ratio * cls.WEIGHT_CURRENT_YEAR_ACTIVITY

        # Factor iv: Loan approved volume
        total_loan_volume = loans.aggregate(
            total=Sum('loan_amount')
        )['total'] or Decimal('0')

        if customer.approved_limit > 0:
            volume_ratio = float(total_loan_volume) / float(customer.approved_limit)
            # Lower volume ratio = better score
            if volume_ratio <= 0.25:
                volume_score_ratio = 1.0
            elif volume_ratio <= 0.5:
                volume_score_ratio = 0.7
            elif volume_ratio <= 0.75:
                volume_score_ratio = 0.4
            elif volume_ratio <= 1.0:
                volume_score_ratio = 0.2
            else:
                volume_score_ratio = 0.0
        else:
            volume_score_ratio = 0.0

        score_volume = volume_score_ratio * cls.WEIGHT_LOAN_VOLUME

        # Final score
        total_score = round(
            score_on_time + score_num_loans + score_activity + score_volume
        )

        # Clamp between 0 and 100
        total_score = max(0, min(100, total_score))

        logger.info(
            "Customer %d credit score: %d "
            "(on_time=%.1f, num_loans=%.1f, activity=%.1f, volume=%.1f)",
            customer.pk,
            total_score,
            score_on_time,
            score_num_loans,
            score_activity,
            score_volume,
        )

        return total_score


class EligibilityService:
    """
    Service for checking loan eligibility based on credit score
    and income constraints.
    """

    @classmethod
    def check(
        cls,
        customer: Customer,
        loan_amount: Decimal,
        interest_rate: Decimal,
        tenure: int,
    ) -> dict:
        """
        Check loan eligibility for a customer.

        Steps:
            1. Calculate credit score
            2. Check loan_amount vs approved_limit
            3. Check EMI > 50% salary rule
            4. Apply slab-based approval logic
            5. Correct interest rate if needed
            6. Calculate monthly installment

        Args:
            customer: The Customer instance (should be locked via select_for_update).
            loan_amount: Requested loan amount.
            interest_rate: Requested annual interest rate (%).
            tenure: Requested tenure in months.

        Returns:
            Dict with approval status, rates, and EMI details.
        """
        loan_amount = Decimal(str(loan_amount))
        interest_rate = Decimal(str(interest_rate))

        # Step 1: Calculate credit score
        credit_score = CreditScoreService.calculate(customer)

        # Step 2: Check loan_amount vs approved_limit
        if loan_amount > customer.approved_limit:
            logger.info(
                "Customer %d: loan_amount (%s) > approved_limit (%d) → rejected",
                customer.pk,
                loan_amount,
                customer.approved_limit,
            )
            new_emi = calculate_emi(loan_amount, interest_rate, tenure)
            return cls._build_response(
                customer_id=customer.pk,
                approval=False,
                interest_rate=interest_rate,
                corrected_interest_rate=interest_rate,
                tenure=tenure,
                monthly_installment=new_emi,
            )

        # Step 3: Check if current EMIs > 50% of monthly salary
        current_emi_total = Loan.objects.filter(
            customer=customer,
            is_active=True,
        ).aggregate(total=Sum('monthly_installment'))['total'] or Decimal('0')

        monthly_salary = Decimal(str(customer.monthly_salary))
        emi_limit = monthly_salary * Decimal('0.5')

        # Also check if adding new EMI would breach 50% limit
        new_emi = calculate_emi(loan_amount, interest_rate, tenure)

        if current_emi_total >= emi_limit:
            logger.info(
                "Customer %d: current EMIs (%s) >= 50%% salary (%s) → rejected",
                customer.pk,
                current_emi_total,
                emi_limit,
            )
            return cls._build_response(
                customer_id=customer.pk,
                approval=False,
                interest_rate=interest_rate,
                corrected_interest_rate=interest_rate,
                tenure=tenure,
                monthly_installment=new_emi,
            )

        # Step 4 & 5: Apply slab logic and correct interest rate
        approval = False
        corrected_interest_rate = interest_rate

        if credit_score > 50:
            # Any interest rate is fine
            approval = True

        elif 30 < credit_score <= 50:
            if interest_rate > Decimal('12'):
                approval = True
            else:
                corrected_interest_rate = Decimal('12.00')
                approval = True

        elif 10 < credit_score <= 30:
            if interest_rate > Decimal('16'):
                approval = True
            else:
                corrected_interest_rate = Decimal('16.00')
                approval = True

        else:
            # credit_score <= 10 → reject
            approval = False

        # Step 6: Calculate EMI with corrected rate
        final_emi = calculate_emi(loan_amount, corrected_interest_rate, tenure)

        # Additional check: would the new EMI push total EMIs > 50% of salary?
        if approval and (current_emi_total + final_emi) > emi_limit:
            logger.info(
                "Customer %d: adding new EMI (%s) would push total (%s) "
                "> 50%% salary (%s) → rejected",
                customer.pk,
                final_emi,
                current_emi_total + final_emi,
                emi_limit,
            )
            approval = False

        return cls._build_response(
            customer_id=customer.pk,
            approval=approval,
            interest_rate=interest_rate,
            corrected_interest_rate=corrected_interest_rate,
            tenure=tenure,
            monthly_installment=final_emi,
        )

    @staticmethod
    def _build_response(
        customer_id: int,
        approval: bool,
        interest_rate: Decimal,
        corrected_interest_rate: Decimal,
        tenure: int,
        monthly_installment: Decimal,
    ) -> dict:
        """Build a standardized eligibility response dict."""
        return {
            'customer_id': customer_id,
            'approval': approval,
            'interest_rate': interest_rate,
            'corrected_interest_rate': corrected_interest_rate,
            'tenure': tenure,
            'monthly_installment': monthly_installment,
        }


class LoanService:
    """Service for loan creation and retrieval operations."""

    @classmethod
    @transaction.atomic
    def create_loan(
        cls,
        customer_id: int,
        loan_amount: Decimal,
        interest_rate: Decimal,
        tenure: int,
    ) -> dict:
        """
        Create a new loan after checking eligibility.

        Uses select_for_update() BEFORE eligibility check to prevent
        TOCTOU race conditions in concurrent loan approvals.

        Args:
            customer_id: Customer's primary key.
            loan_amount: Requested loan amount.
            interest_rate: Requested annual interest rate (%).
            tenure: Requested tenure in months.

        Returns:
            Dict with loan creation result.
        """
        loan_amount = Decimal(str(loan_amount))
        interest_rate = Decimal(str(interest_rate))

        # Step 1: Lock the customer row FIRST to prevent race conditions
        try:
            customer = Customer.objects.select_for_update().get(pk=customer_id)
        except Customer.DoesNotExist:
            raise CustomerNotFoundError(
                detail=f"Customer with ID {customer_id} not found."
            )

        # Step 2: Check eligibility with the locked customer
        eligibility = EligibilityService.check(
            customer=customer,
            loan_amount=loan_amount,
            interest_rate=interest_rate,
            tenure=tenure,
        )

        if not eligibility['approval']:
            return {
                'loan_id': None,
                'customer_id': customer_id,
                'loan_approved': False,
                'message': cls._get_rejection_message(customer),
                'monthly_installment': None,
            }

        # Use corrected interest rate for the loan
        final_rate = eligibility['corrected_interest_rate']
        monthly_installment = eligibility['monthly_installment']

        # Get today's date for start_date
        today = date.today()
        end_date = today + relativedelta(months=tenure)

        # Create the loan
        loan = Loan.objects.create(
            customer=customer,
            loan_amount=loan_amount,
            tenure=tenure,
            interest_rate=final_rate,
            monthly_installment=monthly_installment,
            emis_paid_on_time=0,
            start_date=today,
            end_date=end_date,
            is_active=True,
        )

        # Update customer's current_debt (customer is already locked)
        customer.current_debt += loan_amount
        customer.save(update_fields=['current_debt'])

        logger.info(
            "Loan #%d created for customer %d: amount=%s, rate=%s%%, "
            "tenure=%d, emi=%s",
            loan.pk,
            customer_id,
            loan_amount,
            final_rate,
            tenure,
            monthly_installment,
        )

        return {
            'loan_id': loan.pk,
            'customer_id': customer_id,
            'loan_approved': True,
            'message': 'Loan approved successfully.',
            'monthly_installment': monthly_installment,
        }

    @staticmethod
    def _get_rejection_message(customer: Customer) -> str:
        """Generate a descriptive rejection message."""
        current_emi = Loan.objects.filter(
            customer=customer,
            is_active=True,
        ).aggregate(total=Sum('monthly_installment'))['total'] or Decimal('0')

        emi_limit = Decimal(str(customer.monthly_salary)) * Decimal('0.5')
        credit_score = CreditScoreService.calculate(customer)

        reasons = []
        if credit_score <= 10:
            reasons.append(
                f'Credit score too low ({credit_score}/100).'
            )
        if current_emi >= emi_limit:
            reasons.append(
                'Current EMIs exceed 50% of monthly income.'
            )

        return ' '.join(reasons) if reasons else 'Loan not approved based on eligibility criteria.'

    @staticmethod
    def get_loan(loan_id: int) -> Optional[Loan]:
        """
        Retrieve a single loan by ID.

        Args:
            loan_id: The loan's primary key.

        Returns:
            Loan instance or None.
        """
        try:
            return Loan.objects.select_related('customer').get(pk=loan_id)
        except Loan.DoesNotExist:
            return None

    @staticmethod
    def get_customer_loans(customer_id: int) -> list:
        """
        Retrieve all loans for a given customer.

        Args:
            customer_id: The customer's primary key.

        Returns:
            QuerySet of Loan instances.
        """
        # Verify customer exists
        if not Customer.objects.filter(pk=customer_id).exists():
            raise CustomerNotFoundError(
                detail=f"Customer with ID {customer_id} not found."
            )

        return Loan.objects.filter(
            customer_id=customer_id,
        ).order_by('-created_at')
