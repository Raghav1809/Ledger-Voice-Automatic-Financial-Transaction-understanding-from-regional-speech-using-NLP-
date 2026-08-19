from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta
from customers.models import Customer
from transactions.models import Transaction


class InsightSummaryView(APIView):
    """
    PROTECTED DASHBOARD METRICS API (DO NOT MODIFY DATA CONTRACT)
    Serves the primary VoiceKhata dashboard Overview.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        customers = Customer.objects.filter(user=user)
        transactions = Transaction.objects.filter(user=user)

        total_customers = customers.count()
        total_transactions = transactions.count()

        # Calculate Credit (gave out) vs Payment (received) — sales separate
        total_credit = float(transactions.filter(transaction_type='credit').aggregate(total=Sum('amount'))['total'] or 0.0)
        total_payments = float(transactions.filter(transaction_type='payment').aggregate(total=Sum('amount'))['total'] or 0.0)
        total_sales = float(transactions.filter(transaction_type='sales').aggregate(total=Sum('amount'))['total'] or 0.0)
        total_expense = float(transactions.filter(transaction_type='expense').aggregate(total=Sum('amount'))['total'] or 0.0)
        pending_amount = max(0.0, total_credit - total_payments)
        recovered_amount = min(total_credit, total_payments)

        # Monthly trends (last 6 months)
        today = timezone.now().date()
        monthly_labels = []
        monthly_credits = []
        monthly_payments = []

        for i in range(5, -1, -1):
            # Calculate month range
            first_day = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
            next_month = (first_day + timedelta(days=32)).replace(day=1)
            
            label = first_day.strftime('%b %Y')
            monthly_labels.append(label)

            m_txs = transactions.filter(date__gte=first_day, date__lt=next_month)
            m_cred = float(m_txs.filter(transaction_type__in=['credit', 'sales']).aggregate(t=Sum('amount'))['t'] or 0.0)
            m_pay = float(m_txs.filter(transaction_type__in=['payment', 'expense']).aggregate(t=Sum('amount'))['t'] or 0.0)

            monthly_credits.append(m_cred)
            monthly_payments.append(m_pay)

        # Recent 5 transactions
        from transactions.serializers import TransactionSerializer
        recent_transactions = TransactionSerializer(transactions.order_by('-date', '-created_at')[:5], many=True).data

        return Response({
            'total_customers': total_customers,
            'total_transactions': total_transactions,
            'total_credit': total_credit,
            'total_payments': total_payments,
            'total_sales': total_sales,
            'total_expense': total_expense,
            'pending_amount': pending_amount,
            'recovered_amount': recovered_amount,
            'monthly_trends': {
                'labels': monthly_labels,
                'credits': monthly_credits,
                'payments': monthly_payments,
            },
            'recent_transactions': recent_transactions
        })


class AdvancedAnalyticsView(APIView):
    """
    READ-ONLY ADVANCED FINANCIAL ANALYTICS API
    Aggregates transactions, product sales, expenses, cash flows, and credit recovery metrics.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        qp = getattr(request, 'query_params', request.GET)
        time_filter = qp.get('time_filter', 'month')
        start_date_str = qp.get('start_date')
        end_date_str = qp.get('end_date')

        today = timezone.now().date()

        # Date range filtering logic
        start_date = None
        end_date = None

        if time_filter == 'today':
            start_date = today
            end_date = today
        elif time_filter == 'week':
            start_date = today - timedelta(days=6)
            end_date = today
        elif time_filter == 'month':
            start_date = today.replace(day=1)
            end_date = today
        elif time_filter == 'year':
            start_date = today.replace(month=1, day=1)
            end_date = today
        elif time_filter == 'custom' and start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                start_date = today - timedelta(days=30)
                end_date = today

        # Base user transactions
        all_txs = Transaction.objects.filter(user=user)
        filtered_txs = all_txs
        if start_date:
            filtered_txs = filtered_txs.filter(date__gte=start_date)
        if end_date:
            filtered_txs = filtered_txs.filter(date__lte=end_date)

        # 1. Summary KPIs
        sales_txs = filtered_txs.filter(transaction_type='sales')
        expense_txs = filtered_txs.filter(transaction_type='expense')
        payment_txs = filtered_txs.filter(transaction_type__in=['payment', 'cash_in'])
        credit_txs = filtered_txs.filter(transaction_type__in=['credit', 'cash_out'])

        total_sales = float(sales_txs.aggregate(s=Sum('amount'))['s'] or 0.0)
        sales_count = sales_txs.count()
        avg_sale_value = round(total_sales / sales_count, 2) if sales_count > 0 else 0.0

        total_expense = float(expense_txs.aggregate(s=Sum('amount'))['s'] or 0.0)
        total_payments = float(payment_txs.aggregate(s=Sum('amount'))['s'] or 0.0)
        total_credit = float(credit_txs.aggregate(s=Sum('amount'))['s'] or 0.0)

        # Lifetime credit recovery calculation
        all_credit = float(all_txs.filter(transaction_type='credit').aggregate(s=Sum('amount'))['s'] or 0.0)
        all_payment = float(all_txs.filter(transaction_type='payment').aggregate(s=Sum('amount'))['s'] or 0.0)
        outstanding_credit = max(0.0, all_credit - all_payment)
        recovered_credit = min(all_credit, all_payment)
        recovery_rate = round((recovered_credit / all_credit * 100), 1) if all_credit > 0 else 100.0

        # Cash Flow Calculations
        money_in = total_sales + total_payments
        money_out = total_expense + total_credit
        net_cash_flow = round(money_in - money_out, 2)

        # 2. Product Performance (from sales items_data)
        product_stats = {}
        for tx in sales_txs:
            items = tx.items_data
            if items and isinstance(items, list):
                for item in items:
                    p_name = item.get('name', 'Unknown Product').strip().title()
                    p_qty = float(item.get('qty', 1.0))
                    p_unit = item.get('unit', 'pcs')
                    p_rev = float(item.get('total', 0.0))
                    if p_name not in product_stats:
                        product_stats[p_name] = {'name': p_name, 'qty': 0.0, 'unit': p_unit, 'revenue': 0.0}
                    product_stats[p_name]['qty'] += p_qty
                    product_stats[p_name]['revenue'] += p_rev

        top_products_by_revenue = sorted(product_stats.values(), key=lambda x: x['revenue'], reverse=True)[:10]
        top_products_by_qty = sorted(product_stats.values(), key=lambda x: x['qty'], reverse=True)[:10]

        # 3. Customer Performance
        customers_qs = Customer.objects.filter(user=user)
        active_customers = customers_qs.count()

        cust_sales = {}
        for tx in filtered_txs:
            if tx.customer:
                c_name = tx.customer.name
                cust_sales[c_name] = cust_sales.get(c_name, 0.0) + float(tx.amount)
        top_customers = sorted([{'name': k, 'amount': round(v, 2)} for k, v in cust_sales.items()], key=lambda x: x['amount'], reverse=True)[:10]

        # Outstanding customers (Net credit balance > 0)
        outstanding_customers = []
        for c in customers_qs:
            nb = c.net_balance
            if nb > 0:
                outstanding_customers.append({
                    'id': c.id,
                    'name': c.name,
                    'phone': c.phone,
                    'outstanding': round(nb, 2)
                })
        outstanding_customers.sort(key=lambda x: x['outstanding'], reverse=True)

        # 4. Expense Categories Breakdown
        expense_cats = {}
        for tx in expense_txs:
            cat = (tx.description or 'General Expense').strip().title()
            expense_cats[cat] = expense_cats.get(cat, 0.0) + float(tx.amount)
        top_expense_categories = sorted([{'category': k, 'amount': round(v, 2)} for k, v in expense_cats.items()], key=lambda x: x['amount'], reverse=True)[:10]

        # 5. Transaction Type Mix
        tx_mix = {}
        for tx in filtered_txs:
            t = tx.transaction_type.upper()
            tx_mix[t] = tx_mix.get(t, 0) + 1

        # 6. Weekly Day-of-Week Activity (Mon-Sun)
        day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        day_sales = [0.0] * 7
        day_expenses = [0.0] * 7
        day_tx_count = [0] * 7

        for tx in filtered_txs:
            w_idx = tx.date.weekday()
            day_tx_count[w_idx] += 1
            if tx.transaction_type == 'sales':
                day_sales[w_idx] += float(tx.amount)
            elif tx.transaction_type == 'expense':
                day_expenses[w_idx] += float(tx.amount)

        max_sales_val = max(day_sales)
        best_sales_day = day_names[day_sales.index(max_sales_val)] if max_sales_val > 0 else 'N/A'

        # 7. Trend Progression (Dynamic Granularity)
        if time_filter in ['today', 'week'] or (start_date and end_date and (end_date - start_date).days <= 31):
            s_date = start_date or (today - timedelta(days=30))
            e_date = end_date or today
            delta_days = max(1, (e_date - s_date).days + 1)
            dates_list = [s_date + timedelta(days=i) for i in range(delta_days)]

            trend_labels = [d.strftime('%b %d') for d in dates_list]
            trend_sales = [0.0] * len(dates_list)
            trend_expenses = [0.0] * len(dates_list)
            trend_payments = [0.0] * len(dates_list)
            trend_credits = [0.0] * len(dates_list)

            date_to_idx = {d: i for i, d in enumerate(dates_list)}
            for tx in filtered_txs:
                if tx.date in date_to_idx:
                    idx = date_to_idx[tx.date]
                    amt = float(tx.amount)
                    if tx.transaction_type == 'sales':
                        trend_sales[idx] += amt
                    elif tx.transaction_type == 'expense':
                        trend_expenses[idx] += amt
                    elif tx.transaction_type == 'payment':
                        trend_payments[idx] += amt
                    elif tx.transaction_type == 'credit':
                        trend_credits[idx] += amt
        else:
            s_date = start_date or (today - timedelta(days=365))
            e_date = end_date or today

            month_tuples = []
            curr = s_date.replace(day=1)
            while curr <= e_date:
                month_tuples.append((curr.year, curr.month, curr.strftime('%b %Y')))
                if curr.month == 12:
                    curr = curr.replace(year=curr.year + 1, month=1)
                else:
                    curr = curr.replace(month=curr.month + 1)

            trend_labels = [m[2] for m in month_tuples]
            trend_sales = [0.0] * len(month_tuples)
            trend_expenses = [0.0] * len(month_tuples)
            trend_payments = [0.0] * len(month_tuples)
            trend_credits = [0.0] * len(month_tuples)

            ym_to_idx = {(m[0], m[1]): i for i, m in enumerate(month_tuples)}
            for tx in filtered_txs:
                ym = (tx.date.year, tx.date.month)
                if ym in ym_to_idx:
                    idx = ym_to_idx[ym]
                    amt = float(tx.amount)
                    if tx.transaction_type == 'sales':
                        trend_sales[idx] += amt
                    elif tx.transaction_type == 'expense':
                        trend_expenses[idx] += amt
                    elif tx.transaction_type == 'payment':
                        trend_payments[idx] += amt
                    elif tx.transaction_type == 'credit':
                        trend_credits[idx] += amt

        # 8. Key Business Insights Bullets
        insights_bullets = []
        if total_sales > 0:
            insights_bullets.append(f"Generated ₹{total_sales:,.2f} in sales revenue across {sales_count} transaction(s).")
            if best_sales_day != 'N/A':
                insights_bullets.append(f"{best_sales_day} was your highest sales day in this period.")
        if top_products_by_revenue:
            top_p = top_products_by_revenue[0]
            insights_bullets.append(f"{top_p['name']} was your top-selling product generating ₹{top_p['revenue']:,.2f}.")
        if all_credit > 0:
            insights_bullets.append(f"Overall credit recovery rate stands at {recovery_rate}% (₹{recovered_credit:,.2f} recovered).")
        if outstanding_credit > 0:
            insights_bullets.append(f"₹{outstanding_credit:,.2f} currently outstanding across {len(outstanding_customers)} customer ledger(s).")
        if total_expense > 0:
            insights_bullets.append(f"Recorded ₹{total_expense:,.2f} in operational expenses.")
        if net_cash_flow > 0:
            insights_bullets.append(f"Positive net cash flow of +₹{net_cash_flow:,.2f}.")
        elif net_cash_flow < 0:
            insights_bullets.append(f"Net cash outflow of -₹{abs(net_cash_flow):,.2f}.")

        if not insights_bullets:
            insights_bullets.append("No transaction records found for the selected period.")

        return Response({
            'time_filter': time_filter,
            'summary': {
                'total_sales': total_sales,
                'sales_count': sales_count,
                'avg_sale_value': avg_sale_value,
                'total_expense': total_expense,
                'total_payments': total_payments,
                'total_credit': total_credit,
                'outstanding_credit': outstanding_credit,
                'recovered_credit': recovered_credit,
                'recovery_rate': recovery_rate,
                'money_in': money_in,
                'money_out': money_out,
                'net_cash_flow': net_cash_flow,
                'total_transactions': filtered_txs.count(),
                'active_customers': active_customers,
            },
            'trends': {
                'labels': trend_labels,
                'sales': trend_sales,
                'expenses': trend_expenses,
                'payments': trend_payments,
                'credits': trend_credits,
            },
            'top_products_revenue': top_products_by_revenue,
            'top_products_qty': top_products_by_qty,
            'top_customers': top_customers,
            'outstanding_customers': outstanding_customers,
            'expense_categories': top_expense_categories,
            'transaction_mix': tx_mix,
            'weekly_activity': {
                'days': day_names,
                'sales': day_sales,
                'expenses': day_expenses,
                'tx_counts': day_tx_count,
                'best_sales_day': best_sales_day
            },
            'key_insights': insights_bullets
        })
