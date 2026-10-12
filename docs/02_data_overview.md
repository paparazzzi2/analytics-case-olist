# Описание данных

| Параметр | Значение |
|---|---|
| Версия | 0.1 (черновик) |
| Дата | 12.10.2026 |
| Статус | В работе: заполняется по результатам профилирования |

## 1. Источник

- **Название:** Brazilian E-Commerce Public Dataset by Olist
- **Где взят:** [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
- **Лицензия:** CC BY-NC-SA 4.0 (некоммерческое использование)
- **Период:** сентябрь 2016 — октябрь 2018
- **Формат:** 9 CSV-файлов, связанных между собой через идентификаторы
- **Анонимизация:** имена покупателей и продавцов заменены на хеш-идентификаторы

## 2. Таблицы

| Таблица | Что хранит | Одна строка = | Ключ |
|---|---|---|---|
| orders | Заказы и их статусы, даты всех этапов | один заказ | order_id |
| customers | Покупатели и их адрес (город, штат) | один покупатель в рамках заказа | customer_id |
| order_items | Товары внутри заказа, цена, доставка | одна позиция заказа | order_id + order_item_id |
| order_payments | Оплаты заказа | один платёж | order_id + payment_sequential |
| order_reviews | Отзывы и оценки | один отзыв | review_id |
| products | Товары и их категории, размеры | один товар | product_id |
| sellers | Продавцы и их адрес | один продавец | seller_id |
| geolocation | Координаты почтовых индексов | одна точка индекса | нет |
| category_translation | Перевод категорий с португальского на английский | одна категория | product_category_name |

## 3. Ключевые поля для наших KPI

| KPI (из BRD) | Поля |
|---|---|
| GMV, AOV | `order_payments.payment_value` или `order_items.price + freight_value` |
| Количество заказов | `orders.order_id`, `orders.order_status` |
| On-time delivery rate | `orders.order_delivered_customer_date`, `orders.order_estimated_delivery_date` |
| Средняя оценка, доля негатива | `order_reviews.review_score` |
| Repeat purchase rate | `customers.customer_unique_id` |

## 4. Результаты профилирования

_Заполняется после запуска `src/01_profile_data.py`._

| Таблица | Строк | Проблемы качества |
|---|---|---|
| orders | | |
| customers | | |
| order_items | | |
| order_payments | | |
| order_reviews | | |
| products | | |
| sellers | | |
| geolocation | | |
| category_translation | | |

## 5. Выявленные проблемы качества данных и решения

_Заполняется по результатам профилирования._

| # | Проблема | Влияние на анализ | Решение |
|---|---|---|---|
| | | | |
