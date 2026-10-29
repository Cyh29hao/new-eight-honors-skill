from decimal import Decimal


def completed_total(orders):
    return sum((Decimal(order['amount']) for order in orders
                if order['status'] == 'completed'), Decimal('0.00'))
