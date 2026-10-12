"""
Профилирование данных Olist (этап 2 проекта).

Что делает скрипт:
  для каждой таблицы выводит количество строк и столбцов,
  типы данных, долю пропусков и количество дубликатов.

Зачем:
  прежде чем строить метрики, аналитик должен понять, что лежит в данных
  и насколько им можно доверять (качество данных, data quality).

Запуск:
  python src/01_profile_data.py
"""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

# Таблицы датасета и их первичные ключи (поле, которое должно быть уникальным)
TABLES = {
    "olist_orders_dataset.csv": ["order_id"],
    "olist_customers_dataset.csv": ["customer_id"],
    "olist_order_items_dataset.csv": ["order_id", "order_item_id"],
    "olist_order_payments_dataset.csv": ["order_id", "payment_sequential"],
    "olist_order_reviews_dataset.csv": ["review_id", "order_id"],
    "olist_products_dataset.csv": ["product_id"],
    "olist_sellers_dataset.csv": ["seller_id"],
    "olist_geolocation_dataset.csv": None,  # ключа нет, это справочник координат
    "product_category_name_translation.csv": ["product_category_name"],
}


def profile_table(file_name: str, key: list[str] | None) -> None:
    path = DATA_DIR / file_name
    if not path.exists():
        print(f"[!] Файл не найден: {path}")
        return

    df = pd.read_csv(path)

    print("=" * 70)
    print(f"Таблица: {file_name}")
    print(f"Строк: {len(df):,} | Столбцов: {df.shape[1]}")

    # Полные дубликаты строк
    print(f"Полных дубликатов строк: {df.duplicated().sum():,}")

    # Проверка уникальности первичного ключа
    if key:
        key_dupes = df.duplicated(subset=key).sum()
        status = "OK" if key_dupes == 0 else "ЕСТЬ ДУБЛИ"
        print(f"Ключ {key}: дубликатов {key_dupes:,} -> {status}")

    # Типы и пропуски по каждому столбцу
    summary = pd.DataFrame({
        "тип": df.dtypes.astype(str),
        "пропуски": df.isna().sum(),
        "пропуски_%": (df.isna().mean() * 100).round(2),
        "уникальных": df.nunique(),
    })
    print(summary.to_string())
    print()


def main() -> None:
    for file_name, key in TABLES.items():
        profile_table(file_name, key)


if __name__ == "__main__":
    main()
