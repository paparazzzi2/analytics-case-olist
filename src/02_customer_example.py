"""
Пример: собираем «карточку» одного покупателя из четырёх таблиц.

Зачем:
  показать, как анонимизированные ID связывают таблицы между собой
  и что по ним можно узнать, не зная имени покупателя.

Откуда берём данные:
  customers  -> где живёт (город, штат) и customer_unique_id
  orders     -> какие заказы сделал и когда
  payments   -> на какую сумму
  reviews    -> какие оценки поставил

Запуск:
  python src/02_customer_example.py
"""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

customers = pd.read_csv(DATA_DIR / "olist_customers_dataset.csv")
orders = pd.read_csv(DATA_DIR / "olist_orders_dataset.csv")
payments = pd.read_csv(DATA_DIR / "olist_order_payments_dataset.csv")
reviews = pd.read_csv(DATA_DIR / "olist_order_reviews_dataset.csv")

# 1. Склеиваем заказы с покупателями по customer_id (JOIN)
orders_full = orders.merge(customers, on="customer_id", how="left")

# 2. Находим реального человека с наибольшим числом заказов.
#    customer_id новый в каждом заказе, а customer_unique_id — один на человека.
orders_per_person = orders_full.groupby("customer_unique_id")["order_id"].count()
person = orders_per_person.idxmax()

print("=" * 70)
print(f"Покупатель (customer_unique_id): {person}")
print(f"Сколько заказов сделал: {orders_per_person.max()}")

# 3. Где живёт
person_orders = orders_full[orders_full["customer_unique_id"] == person]
first = person_orders.iloc[0]
print(f"Где живёт: город {first['customer_city']}, штат {first['customer_state']}")

# 4. На какую сумму (сумма всех платежей по его заказам)
person_payments = payments[payments["order_id"].isin(person_orders["order_id"])]
print(f"Сумма всех покупок: {person_payments['payment_value'].sum():.2f} BRL")

# 5. Какие оценки поставил
person_reviews = reviews[reviews["order_id"].isin(person_orders["order_id"])]
print(f"Оценки: {person_reviews['review_score'].tolist()}")

# 6. Все его заказы списком
print("\nЕго заказы:")
cols = ["order_id", "order_purchase_timestamp", "order_status"]
print(person_orders[cols].sort_values("order_purchase_timestamp").to_string(index=False))

# 7. Бонус: сколько людей вообще вернулись за вторым заказом
repeaters = (orders_per_person >= 2).sum()
total = len(orders_per_person)
print("\n" + "=" * 70)
print(f"Уникальных покупателей: {total:,}")
print(f"Из них сделали 2+ заказа: {repeaters:,} ({repeaters / total:.1%})")
