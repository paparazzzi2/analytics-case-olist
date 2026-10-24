"""
Этапы 4–6: метрики процесса AS-IS, диагностика причин, данные для сценариев TO-BE.
Запуск: python src/04_process_analysis.py
Результаты печатаются в консоль; цифры перенесены в docs/04–06.
"""
from pathlib import Path
import pandas as pd

D = Path(__file__).resolve().parent.parent / "data" / "raw"
dates = ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
         "order_delivered_customer_date", "order_estimated_delivery_date"]
orders = pd.read_csv(D / "olist_orders_dataset.csv", parse_dates=dates)
cust = pd.read_csv(D / "olist_customers_dataset.csv")
items = pd.read_csv(D / "olist_order_items_dataset.csv", parse_dates=["shipping_limit_date"])
reviews = pd.read_csv(D / "olist_order_reviews_dataset.csv", parse_dates=["review_answer_timestamp"])
pay = pd.read_csv(D / "olist_order_payments_dataset.csv")
prod = pd.read_csv(D / "olist_products_dataset.csv")
tr = pd.read_csv(D / "product_category_name_translation.csv", encoding="utf-8-sig")

def h(t): print("\n" + "=" * 70 + "\n" + t)

# ---------- ЭТАП 4. AS-IS ----------
h("Статусы")
s = orders.order_status.value_counts()
print(pd.DataFrame({"orders": s, "pct": (s / len(orders) * 100).round(2)}))

d = orders[(orders.order_status == "delivered") & orders.order_delivered_customer_date.notna()].copy()
day = lambda a, b: (a - b).dt.total_seconds() / 86400
d["approval"] = day(d.order_approved_at, d.order_purchase_timestamp)
d["seller"] = day(d.order_delivered_carrier_date, d.order_approved_at)
d["carrier"] = day(d.order_delivered_customer_date, d.order_delivered_carrier_date)
d["total"] = day(d.order_delivered_customer_date, d.order_purchase_timestamp)
d["promised"] = day(d.order_estimated_delivery_date, d.order_purchase_timestamp)

h("Аномалии порядка дат (доставленные)")
print("carrier < approved:", (d.order_delivered_carrier_date < d.order_approved_at).sum())
print("customer < carrier:", (d.order_delivered_customer_date < d.order_delivered_carrier_date).sum())
print("нет approved/carrier:", (d.order_approved_at.isna() | d.order_delivered_carrier_date.isna()).sum())

v = d.dropna(subset=["order_approved_at", "order_delivered_carrier_date"])
v = v[(v.approval >= 0) & (v.seller >= 0) & (v.carrier >= 0)]
h(f"Длительность этапов, дней (заказов: {len(v)})")
print(v[["approval", "seller", "carrier", "total", "promised"]]
      .describe(percentiles=[.5, .9]).loc[["mean", "50%", "90%"]].round(2).T)

d["late_days"] = (d.order_delivered_customer_date.dt.normalize() - d.order_estimated_delivery_date.dt.normalize()).dt.days
d["late"] = d.late_days > 0
h("Выполнение обещания")
print("заказов:", len(d))
print("раньше срока %:", round((d.late_days < 0).mean() * 100, 2))
print("в день срока %:", round((d.late_days == 0).mean() * 100, 2))
print("опоздали %:", round(d.late.mean() * 100, 2), "| шт:", int(d.late.sum()))
print("запас до срока, среднее дн:", round(-d.late_days.mean(), 1))
print("опоздание у опоздавших: среднее", round(d.loc[d.late, "late_days"].mean(), 1),
      "медиана", d.loc[d.late, "late_days"].median())

# ---------- ЭТАП 5. Диагностика ----------
rv = reviews.sort_values("review_answer_timestamp").drop_duplicates("order_id", keep="last")
dr = d.merge(rv[["order_id", "review_score"]], on="order_id", how="inner")
h(f"Оценки: вовремя vs опоздание (заказов с отзывом: {len(dr)})")
g = dr.groupby("late").review_score.agg(["count", "mean", lambda x: (x <= 2).mean() * 100])
g.columns = ["orders", "avg_score", "neg_pct"]; print(g.round(2))
bins = [-1000, -8, -1, 0, 3, 7, 14, 1000]
labels = ["раньше 8+ дн", "раньше 1-7 дн", "в срок", "опозд 1-3", "опозд 4-7", "опозд 8-14", "опозд 15+"]
dr["bucket"] = pd.cut(dr.late_days, bins=bins, labels=labels)
g = dr.groupby("bucket", observed=True).review_score.agg(["count", "mean", lambda x: (x <= 2).mean() * 100])
g.columns = ["orders", "avg_score", "neg_pct"]; print(g.round(2))
print("всего: avg", round(dr.review_score.mean(), 3), "neg%", round((dr.review_score <= 2).mean() * 100, 2))
late_neg = ((dr.review_score <= 2) & dr.late).sum()
print("доля всех негативных отзывов, приходящихся на опоздания %:",
      round(late_neg / (dr.review_score <= 2).sum() * 100, 1))

h("Кто виноват в опоздании: продавец не уложился в shipping_limit_date?")
lim = items.groupby("order_id").shipping_limit_date.max().rename("limit")
dl = d.join(lim, on="order_id").dropna(subset=["order_delivered_carrier_date", "limit"])
dl["seller_late"] = dl.order_delivered_carrier_date > dl["limit"]
print("продавцы нарушили срок передачи, % всех доставленных:", round(dl.seller_late.mean() * 100, 2))
x = pd.crosstab(dl.seller_late, dl.late, normalize="index") * 100
print("доля опозданий к покупателю при нарушении/без нарушения срока продавцом:\n", x.round(2))
print("доля опоздавших заказов, где продавец нарушил свой срок %:",
      round(dl.loc[dl.late, "seller_late"].mean() * 100, 1))
lt = v.merge(d[["order_id", "late"]], on="order_id")
print("медианы этапов (дн) вовремя vs опоздание:\n",
      lt.groupby("late")[["approval", "seller", "carrier"]].median().round(2))

h("Регионы покупателей: доля опозданий (штаты с 500+ заказами)")
ds = d.merge(cust[["customer_id", "customer_state", "customer_unique_id"]], on="customer_id")
st = ds.groupby("customer_state").agg(orders=("order_id", "count"), late_pct=("late", "mean"),
                                      median_days=("total", "median"))
st["late_pct"] = (st.late_pct * 100).round(2)
st = st[st.orders >= 500].sort_values("late_pct", ascending=False)
print(st.round(1))
top = st.head(5)
print("топ-5 штатов: заказов", int(top.orders.sum()), "| опозданий в них",
      int((ds[ds.customer_state.isin(top.index)].late).sum()), "из", int(d.late.sum()))

h("Повторные покупки по исходу первого заказа")
allo = orders.merge(cust, on="customer_id")
n = allo.groupby("customer_unique_id").order_id.nunique()
print("покупателей:", len(n), "| 2+ заказа:", int((n >= 2).sum()), "pct", round((n >= 2).mean() * 100, 2))
first = ds.sort_values("order_purchase_timestamp").drop_duplicates("customer_unique_id")
first = first.merge(rv[["order_id", "review_score"]], on="order_id", how="left")
first["repeat"] = first.customer_unique_id.map(n) >= 2
first["outcome"] = pd.cut(first.late_days, [-1000, -1, 0, 1000], labels=["раньше", "в срок", "опоздание"])
print(first.groupby("outcome", observed=True).repeat.agg(["count", "mean"]).assign(mean=lambda t: (t["mean"] * 100).round(2)))
print(first.groupby("review_score").repeat.agg(["count", "mean"]).assign(mean=lambda t: (t["mean"] * 100).round(2)))

h("Выручка и категории")
print("GMV (payments, delivered):", round(pay[pay.order_id.isin(d.order_id)].payment_value.sum() / 1e6, 2), "млн BRL")
print("AOV:", round(pay[pay.order_id.isin(d.order_id)].groupby("order_id").payment_value.sum().mean(), 2))
ic = items.merge(prod[["product_id", "product_category_name"]], on="product_id").merge(tr, on="product_category_name", how="left")
ic = ic.merge(d[["order_id", "late"]], on="order_id")
c = ic.groupby("product_category_name_english").agg(rev=("price", "sum"), late=("late", "mean"))
c = c.sort_values("rev", ascending=False).head(5); c["late"] = (c.late * 100).round(1); c["rev"] = (c.rev / 1e6).round(2)
print(c)

# ---------- ЭТАП 6. Оценка эффекта сценариев ----------
h("Сценарии: эффект при полном и реалистичном (50%) внедрении")
N = len(dr); base_avg = dr.review_score.mean(); base_neg = (dr.review_score <= 2).mean()
d_score = dr[~dr.late].review_score.mean() - dr[dr.late].review_score.mean()
d_neg = (dr[dr.late].review_score <= 2).mean() - (dr[~dr.late].review_score <= 2).mean()
late_n = int(d.late.sum())
def effect(name, avoided):
    for k in (1.0, 0.5):
        a = avoided * k
        print(f"{name} [{int(k*100)}%]: опозданий меньше на {a:,.0f} "
              f"(доля {late_n/len(d)*100:.2f}% -> {(late_n-a)/len(d)*100:.2f}%), "
              f"ср. оценка {base_avg:.3f} -> {base_avg + a*d_score/N:.3f}, "
              f"негатив {base_neg*100:.2f}% -> {(base_neg - a*d_neg/N)*100:.2f}%")
sl = dl.seller_late
avoid_a = sl.sum() * (dl.loc[sl, "late"].mean() - dl.loc[~sl, "late"].mean())
effect("A. SLA продавцов", avoid_a)
top5 = top.index; in5 = ds.customer_state.isin(top5)
other_rate = ds.loc[~in5, "late"].mean()
avoid_b = in5.sum() * (ds.loc[in5, "late"].mean() - other_rate)
print("B: опоздания в топ-5 штатах", round(ds.loc[in5, 'late'].mean()*100, 2), "% vs остальные", round(other_rate*100, 2), "%")
effect("B. Перевозчик в 5 штатах", avoid_b)
rj = ds.customer_state == "RJ"
effect("B-пилот. Только RJ", rj.sum() * (ds.loc[rj, "late"].mean() - other_rate))
neg_late = int(((dr.review_score <= 2) & dr.late).sum())
for r in (0.2, 0.1):
    print(f"C. Проактивное уведомление и компенсация: если негатив у опоздавших снизится на {int(r*100)}%, "
          f"минус {neg_late*r:,.0f} негативных отзывов, негатив {base_neg*100:.2f}% -> {(base_neg - neg_late*r/N)*100:.2f}%")
