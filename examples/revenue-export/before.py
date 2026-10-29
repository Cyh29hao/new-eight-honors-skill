import json
from pathlib import Path


def main():
    orders = json.loads(Path('orders.json').read_text(encoding='utf-8'))
    total = sum(float(order['amount']) for order in orders)
    Path('summary.txt').write_text(f'Completed revenue: {total:.2f}\n', encoding='utf-8')


if __name__ == '__main__':
    main()
