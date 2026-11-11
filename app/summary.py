import pandas as pd


def build_summary(processed_orders: list[dict]) -> dict:
    if not processed_orders:
        return {
            "customer_x_currency": [],
            "top3_customers": [],
            "weekly_usd": [],
            "total_usd": 0.0,
            "avg_check_usd": 0.0,
        }

    df = pd.DataFrame(processed_orders)
    df["order_id"] = df["order_id"].astype(int)
    df["amount"] = df["amount"].astype(float)
    df["order_date"] = pd.to_datetime(df["order_date"])
    df["amount_usd"] = df["amount_usd"].astype(float)

    # таблица «клиент × исходная валюта»: сумма в USD
    customer_x_currency = (
        df.groupby(["customer", "currency"], as_index=False)["amount_usd"].sum()
        .round(2)
        .to_dict(orient="records")
    )
    # топ-3 клиента по сумме
    top3_customers = (
        df.groupby(["customer"], as_index=False)["amount_usd"].sum()
        .sort_values("amount_usd", ascending=False)
        .round(2)
        .head(3)
        .to_dict(orient="records")
    )

    # динамика: сумма в USD по неделям (по order_date)
    weekly_usd = (
        df.assign(week=df["order_date"].dt.to_period("W").astype(str))
        .groupby("week", as_index=False)["amount_usd"].sum()
        .round(2)
        .to_dict(orient="records")
    )

    # общая сумма и средний чек
    total_usd = round(float(df["amount_usd"].sum()), 2)
    avg_check_usd = round(float(df["amount_usd"].mean()), 2)

    return {
        "customer_x_currency": customer_x_currency,
        "top3_customers": top3_customers,
        "weekly_usd": weekly_usd,
        "total_usd": total_usd,
        "avg_check_usd": avg_check_usd,
    }
    
