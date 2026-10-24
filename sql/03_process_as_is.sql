-- =====================================================================
-- Этап 4. Процесс выполнения заказа AS-IS: метрики по этапам
--
-- Процесс раскладывается на этапы с разными владельцами:
--   1. Подтверждение оплаты     (Olist)       purchase  -> approved
--   2. Сборка и передача        (продавец)    approved  -> carrier
--   3. Доставка                 (перевозчик)  carrier   -> customer
--   Итог: сравнение фактической даты с обещанной покупателю
--
-- Каждый запрос выполняй отдельно: выдели его и нажми Ctrl+Enter.
-- =====================================================================


-- ---------------------------------------------------------------------
-- Запрос 1. Где процесс обрывается: заказы по статусам
-- Бизнес-смысл: сколько заказов не доходит до покупателя и на каком шаге
-- ---------------------------------------------------------------------
SELECT
    order_status,
    COUNT(*) AS orders,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM orders), 2) AS share_pct
FROM orders
GROUP BY order_status
ORDER BY orders DESC;


-- ---------------------------------------------------------------------
-- Запрос 2. Аномалии: этапы с отрицательной длительностью
-- Бизнес-смысл: проверяем, можно ли доверять датам этапов.
-- Передача перевозчику не может случиться раньше подтверждения оплаты.
-- ---------------------------------------------------------------------
SELECT
    COUNT(*) FILTER (WHERE order_delivered_carrier_date < order_approved_at)       AS carrier_before_approval,
    COUNT(*) FILTER (WHERE order_delivered_customer_date < order_delivered_carrier_date) AS delivered_before_carrier,
    COUNT(*) FILTER (WHERE order_approved_at < order_purchase_timestamp)           AS approved_before_purchase
FROM orders
WHERE order_status = 'delivered';


-- ---------------------------------------------------------------------
-- Запрос 3. Длительность каждого этапа (в днях)
-- Берём только доставленные заказы, где все даты заполнены
-- и идут в правильном порядке (аномалии из запроса 2 исключаем).
--
-- Почему смотрим медиану и 90-й перцентиль, а не только среднее:
--   среднее «тянут» вверх редкие заказы, ехавшие 100+ дней;
--   медиана показывает типичный заказ,
--   90-й перцентиль — насколько плохо бывает у 10% самых медленных.
-- ---------------------------------------------------------------------
WITH stages AS (
    SELECT
        order_id,
        EXTRACT(EPOCH FROM order_approved_at - order_purchase_timestamp) / 86400.0
            AS approval_days,
        EXTRACT(EPOCH FROM order_delivered_carrier_date - order_approved_at) / 86400.0
            AS seller_days,
        EXTRACT(EPOCH FROM order_delivered_customer_date - order_delivered_carrier_date) / 86400.0
            AS carrier_days,
        EXTRACT(EPOCH FROM order_delivered_customer_date - order_purchase_timestamp) / 86400.0
            AS total_days,
        EXTRACT(EPOCH FROM order_estimated_delivery_date - order_purchase_timestamp) / 86400.0
            AS promised_days
    FROM orders
    WHERE order_status = 'delivered'
      AND order_approved_at IS NOT NULL
      AND order_delivered_carrier_date IS NOT NULL
      AND order_delivered_customer_date IS NOT NULL
      AND order_approved_at >= order_purchase_timestamp
      AND order_delivered_carrier_date >= order_approved_at
      AND order_delivered_customer_date >= order_delivered_carrier_date
)
SELECT '1. Подтверждение оплаты (Olist)' AS stage,
       COUNT(*) AS orders,
       ROUND(AVG(approval_days)::numeric, 2) AS avg_days,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY approval_days)::numeric, 2) AS median_days,
       ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY approval_days)::numeric, 2) AS p90_days
FROM stages
UNION ALL
SELECT '2. Сборка и передача (продавец)', COUNT(*),
       ROUND(AVG(seller_days)::numeric, 2),
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY seller_days)::numeric, 2),
       ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY seller_days)::numeric, 2)
FROM stages
UNION ALL
SELECT '3. Доставка (перевозчик)', COUNT(*),
       ROUND(AVG(carrier_days)::numeric, 2),
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY carrier_days)::numeric, 2),
       ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY carrier_days)::numeric, 2)
FROM stages
UNION ALL
SELECT 'Итого: от заказа до получения', COUNT(*),
       ROUND(AVG(total_days)::numeric, 2),
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_days)::numeric, 2),
       ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY total_days)::numeric, 2)
FROM stages
UNION ALL
SELECT 'Обещанный срок', COUNT(*),
       ROUND(AVG(promised_days)::numeric, 2),
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY promised_days)::numeric, 2),
       ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY promised_days)::numeric, 2)
FROM stages;


-- ---------------------------------------------------------------------
-- Запрос 4. Выполнение обещания по сроку
-- Бизнес-смысл: как часто платформа нарушает обещание покупателю
-- Сравниваем по датам (::date), т.к. обещание дано с точностью до дня
-- ---------------------------------------------------------------------
SELECT
    COUNT(*) AS delivered_orders,
    ROUND(AVG(CASE WHEN order_delivered_customer_date::date < order_estimated_delivery_date::date
                   THEN 1 ELSE 0 END) * 100, 2) AS early_pct,
    ROUND(AVG(CASE WHEN order_delivered_customer_date::date = order_estimated_delivery_date::date
                   THEN 1 ELSE 0 END) * 100, 2) AS exact_day_pct,
    ROUND(AVG(CASE WHEN order_delivered_customer_date::date > order_estimated_delivery_date::date
                   THEN 1 ELSE 0 END) * 100, 2) AS late_pct,
    ROUND(AVG(order_estimated_delivery_date::date - order_delivered_customer_date::date), 1)
        AS avg_days_reserve
FROM orders
WHERE order_status = 'delivered'
  AND order_delivered_customer_date IS NOT NULL;


-- ---------------------------------------------------------------------
-- Запрос 5. Насколько сильно опаздывают опоздавшие
-- ---------------------------------------------------------------------
SELECT
    COUNT(*) AS late_orders,
    ROUND(AVG(order_delivered_customer_date::date - order_estimated_delivery_date::date), 1)
        AS avg_days_late,
    PERCENTILE_CONT(0.5) WITHIN GROUP (
        ORDER BY order_delivered_customer_date::date - order_estimated_delivery_date::date
    ) AS median_days_late
FROM orders
WHERE order_status = 'delivered'
  AND order_delivered_customer_date::date > order_estimated_delivery_date::date;
