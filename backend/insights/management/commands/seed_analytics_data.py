# insights/management/commands/seed_analytics_data.py

import random
from decimal import Decimal
from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction as db_transaction
from customers.models import Customer
from transactions.models import Transaction

class Command(BaseCommand):
    help = 'Seeds realistic analytics/financial test data for a given user.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Username of the user to seed data for. Defaults to the first user.'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all previously seeded test data instead of seeding.'
        )

    def handle(self, *args, **options):
        # 1. Identify User
        username = options.get('username')
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise CommandError(f"User with username '{username}' does not exist.")
        else:
            user = User.objects.first()
            if not user:
                # Create a default demo user if none exists
                user = User.objects.create_user(
                    username='demo_user',
                    email='demo@voicekhata.com',
                    password='password123'
                )
                self.stdout.write(self.style.SUCCESS("No user found in the database. Created a default user 'demo_user' (password: password123)."))

        self.stdout.write(f"Target user for seeding: {user.username}")

        # 2. Check for clear option
        TEST_MARKER = "[TEST_DATA]"
        
        if options.get('clear'):
            self.stdout.write("Clearing existing test data...")
            deleted_txs, _ = Transaction.objects.filter(user=user, description__contains=TEST_MARKER).delete()
            deleted_custs, _ = Customer.objects.filter(user=user, notes__contains=TEST_MARKER).delete()
            self.stdout.write(self.style.SUCCESS(f"Successfully deleted {deleted_txs} transactions and {deleted_custs} customers."))
            return

        # 3. Prevent duplicates: Delete existing test data first
        self.stdout.write("Cleaning previous test data for this user to avoid duplication...")
        Transaction.objects.filter(user=user, description__contains=TEST_MARKER).delete()
        Customer.objects.filter(user=user, notes__contains=TEST_MARKER).delete()

        # 4. Generate Customers
        self.stdout.write("Generating 20 realistic customers...")
        first_names = ["Rahul", "Amit", "Ramesh", "Suresh", "Priya", "Neha", "Sneha", "Rohit", "Pooja", "Akshay", 
                       "Ankit", "Deepak", "Karan", "Sunita", "Vikram", "Sanjay", "Rajesh", "Aarav", "Riya", "Kiran"]
        last_names = ["Sharma", "Kumar", "Verma", "Singh", "Gupta", "Joshi", "Mehra", "Patel", "Reddy", "Nair"]
        
        customers = []
        for i in range(20):
            name = f"{random.choice(first_names)} {random.choice(last_names)}"
            # Ensure uniqueness
            while Customer.objects.filter(user=user, name=name).exists():
                name = f"{random.choice(first_names)} {random.choice(last_names)} {random.randint(1, 100)}"
            
            phone = f"+91{random.randint(7000000000, 9999999999)}"
            email = f"{name.lower().replace(' ', '.')}@testmail.com"
            cust = Customer.objects.create(
                user=user,
                name=name,
                phone=phone,
                email=email,
                address=f"Shop No. {random.randint(1, 50)}, Market Road, City",
                notes=f"Regular retail buyer. {TEST_MARKER}"
            )
            customers.append(cust)

        # 5. Products configuration
        products = [
            {"name": "Rice", "unit": "kg", "price": 60.0},
            {"name": "Sugar", "unit": "kg", "price": 45.0},
            {"name": "Wheat Flour", "unit": "kg", "price": 40.0},
            {"name": "Milk", "unit": "litre", "price": 50.0},
            {"name": "Mustard Oil", "unit": "litre", "price": 170.0},
            {"name": "Toor Dal", "unit": "kg", "price": 120.0},
            {"name": "Green Tea", "unit": "pcs", "price": 150.0},
            {"name": "Marie Biscuits", "unit": "packet", "price": 10.0},
            {"name": "Potatoes", "unit": "kg", "price": 25.0},
            {"name": "Onions", "unit": "kg", "price": 35.0},
            {"name": "Garam Masala", "unit": "packet", "price": 50.0},
            {"name": "Bath Soap", "unit": "pcs", "price": 30.0},
            {"name": "Shampoo", "unit": "bottle", "price": 120.0},
            {"name": "Toothpaste", "unit": "pcs", "price": 45.0},
            {"name": "Refined Oil", "unit": "litre", "price": 140.0},
            {"name": "Basmati Rice", "unit": "kg", "price": 110.0},
            {"name": "Butter", "unit": "pcs", "price": 55.0},
            {"name": "Salt", "unit": "kg", "price": 20.0},
            {"name": "Washing Powder", "unit": "kg", "price": 90.0},
            {"name": "Dishwash Gel", "unit": "bottle", "price": 65.0}
        ]

        # 6. Time distribution (last 10 months to spread out)
        today = timezone.now().date()
        date_pool = []
        for d in range(10, 300): # between 10 days ago and 300 days ago
            date_pool.append(today - timedelta(days=d))

        # Helper to generate items data
        def get_random_items():
            num_items = random.randint(1, 5)
            items_list = []
            total_amt = Decimal("0.0")
            chosen_prods = random.sample(products, num_items)
            for p in chosen_prods:
                # quantities: 0.5, 1, 1.5, 2, 5, 10 etc
                qty = random.choice([0.5, 1.0, 1.5, 2.0, 5.0, 10.0])
                total = Decimal(str(p['price'])) * Decimal(str(qty))
                items_list.append({
                    "name": p['name'],
                    "qty": qty,
                    "unit": p['unit'],
                    "price": p['price'],
                    "total": float(total)
                })
                total_amt += total
            return items_list, total_amt

        # 7. Generate SALES transactions (80 - 100)
        self.stdout.write("Generating sales transactions...")
        sales_count = random.randint(85, 95)
        for _ in range(sales_count):
            items, total = get_random_items()
            tx_date = random.choice(date_pool)
            cust = random.choice(customers) if random.random() < 0.8 else None # 80% have customer
            Transaction.objects.create(
                user=user,
                customer=cust,
                customer_name_raw=cust.name if cust else None,
                amount=total,
                transaction_type='sales',
                date=tx_date,
                status='completed',
                description=f"Standard retail sales transaction. {TEST_MARKER}",
                items_data=items
            )

        # 8. Generate EXPENSE transactions (30 - 50)
        self.stdout.write("Generating expense transactions...")
        expense_cats = ["Rent", "Electricity", "Transport", "Petrol", "Packaging", "Food", "Maintenance", "Supplies", "Internet", "Other"]
        expense_count = random.randint(35, 45)
        for _ in range(expense_count):
            cat = random.choice(expense_cats)
            # Pick a realistic amount based on expense type
            if cat == "Rent":
                amount = Decimal(random.randint(5000, 12000))
            elif cat == "Electricity":
                amount = Decimal(random.randint(1500, 4500))
            elif cat == "Internet":
                amount = Decimal(random.randint(500, 1500))
            else:
                amount = Decimal(random.randint(100, 2000))
            
            tx_date = random.choice(date_pool)
            Transaction.objects.create(
                user=user,
                amount=amount,
                transaction_type='expense',
                date=tx_date,
                status='completed',
                description=f"{cat} {TEST_MARKER}"
            )

        # 9. Generate CREDIT and PAYMENT transactions (repayments / loans)
        # 20 - 30 Credit transactions
        # 25 - 40 Payment transactions
        # We want to structure some credit/payment relationships for specific customers
        self.stdout.write("Generating credit and payment (repayment) relationships...")
        
        # Select a subset of customers to have credit relations
        credit_customers = random.sample(customers, 12)
        
        # Distribute these credit relations:
        # Case A: Fully unpaid credit (outstanding > 0, 0 payments)
        # Case B: Partially paid credit (outstanding > 0, partial payments)
        # Case C: Fully settled credit (outstanding = 0, matching payments, status = settled)
        
        # Let's track outstanding credit per customer to generate matching payments later
        customer_credit_records = []
        
        for idx, cust in enumerate(credit_customers):
            # Create a credit transaction
            amount = Decimal(random.randint(1, 10) * 1000) # 1000 to 10000
            tx_date = random.choice(date_pool)
            due_date = tx_date + timedelta(days=random.randint(15, 60))
            
            # Determine relationship category based on index
            if idx < 4: # Case A: Fully unpaid
                status = 'pending'
                customer_credit_records.append({
                    "cust": cust,
                    "amount": amount,
                    "date": tx_date,
                    "type": "unpaid",
                    "due_date": due_date
                })
            elif idx < 8: # Case B: Partially paid
                status = 'pending'
                customer_credit_records.append({
                    "cust": cust,
                    "amount": amount,
                    "date": tx_date,
                    "type": "partial",
                    "due_date": due_date
                })
            else: # Case C: Fully settled
                status = 'settled'
                customer_credit_records.append({
                    "cust": cust,
                    "amount": amount,
                    "date": tx_date,
                    "type": "settled",
                    "due_date": due_date
                })
                
            Transaction.objects.create(
                user=user,
                customer=cust,
                customer_name_raw=cust.name,
                amount=amount,
                transaction_type='credit',
                date=tx_date,
                due_date=due_date,
                status=status,
                description=f"Credit extended to customer. {TEST_MARKER}"
            )

        # Generate Payments corresponding to Cases B and C plus some generic payments
        # Let's create the matching payments
        payment_count = 0
        for rec in customer_credit_records:
            cust = rec['cust']
            orig_amt = rec['amount']
            orig_date = rec['date']
            
            if rec['type'] == "partial":
                # Create a partial payment (e.g. 30% to 70% of credit)
                pay_amt = orig_amt * Decimal(str(random.choice([0.3, 0.4, 0.5, 0.6])))
                pay_amt = Decimal(round(pay_amt, 2))
                # Payment happens after the credit date
                pay_date = orig_date + timedelta(days=random.randint(5, 20))
                if pay_date > today:
                    pay_date = today
                
                Transaction.objects.create(
                    user=user,
                    customer=cust,
                    customer_name_raw=cust.name,
                    amount=pay_amt,
                    transaction_type='payment',
                    date=pay_date,
                    status='completed',
                    description=f"Partial repayment for credit of ₹{orig_amt}. {TEST_MARKER}"
                )
                payment_count += 1
                
            elif rec['type'] == "settled":
                # Create a matching payment of equal value
                pay_date = orig_date + timedelta(days=random.randint(5, 30))
                if pay_date > today:
                    pay_date = today
                    
                Transaction.objects.create(
                    user=user,
                    customer=cust,
                    customer_name_raw=cust.name,
                    amount=orig_amt,
                    transaction_type='payment',
                    date=pay_date,
                    status='completed',
                    description=f"Full repayment settling credit of ₹{orig_amt}. {TEST_MARKER}"
                )
                payment_count += 1

        # Add additional random generic payments/credits to reach targets
        # Target credit: 20-30. We already have 12. Let's add 10 more random credits.
        for _ in range(10):
            cust = random.choice(customers)
            amount = Decimal(random.randint(5, 30) * 100) # 500 to 3000
            tx_date = random.choice(date_pool)
            Transaction.objects.create(
                user=user,
                customer=cust,
                customer_name_raw=cust.name,
                amount=amount,
                transaction_type='credit',
                date=tx_date,
                status='pending',
                description=f"Small credit transaction. {TEST_MARKER}"
            )
            
        # Target payment: 25-40. We have 8 from settled/partial logic. Let's add 22 more generic payments.
        for _ in range(22):
            cust = random.choice(customers)
            amount = Decimal(random.randint(2, 20) * 100) # 200 to 2000
            tx_date = random.choice(date_pool)
            Transaction.objects.create(
                user=user,
                customer=cust,
                customer_name_raw=cust.name,
                amount=amount,
                transaction_type='payment',
                date=tx_date,
                status='completed',
                description=f"Direct customer payment. {TEST_MARKER}"
            )

        # 10. Summary Report
        total_seeded_custs = Customer.objects.filter(user=user, notes__contains=TEST_MARKER).count()
        total_seeded_txs = Transaction.objects.filter(user=user, description__contains=TEST_MARKER).count()
        
        self.stdout.write(self.style.SUCCESS("========================================"))
        self.stdout.write(self.style.SUCCESS(f"Seeding completed successfully for user '{user.username}'!"))
        self.stdout.write(self.style.SUCCESS(f"Customers created: {total_seeded_custs}"))
        self.stdout.write(self.style.SUCCESS(f"Transactions created: {total_seeded_txs}"))
        
        # Breakdown by transaction type
        for t_type, t_name in Transaction.TRANSACTION_TYPES:
            c = Transaction.objects.filter(user=user, transaction_type=t_type, description__contains=TEST_MARKER).count()
            self.stdout.write(f"  - {t_name} ({t_type}): {c}")
        self.stdout.write(self.style.SUCCESS("========================================"))
