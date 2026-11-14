from app.tasks.summary import build_summary

def test_build_summary_empty():
    result = build_summary([])
    assert result["total_usd"] == 0.0
    assert result["avg_check_usd"] == 0.0
    assert result["customer_x_currency"] == []
    assert result["top3_customers"] == []
    assert result["weekly_usd"] == []

def test_build_summary_simple():
    orders = [
        {
            "order_id": 1,
            "customer": "alex",
            "product": "Война и мир",
            "amount": 20.77,
            "currency": "USD",
            "order_date": "2026-10-18",
            "review": "Плохое качество печати, страницы рваные, разочарован",
            "amount_usd": 20.77
        },
        {
            "order_id": 4,
            "customer": "maria",
            "product": "1984",
            "amount": 11.75,
            "currency": "EUR",
            "order_date": "2024-09-25",
            "review": "Обычная книга, ничего особенного",
            "amount_usd": 13.15
        },
        {
            "order_id": 5,
            "customer": "elena",
            "product": "Война и мир",
            "amount": 11.75,
            "currency": "EUR",
            "order_date": "2026-10-05",
            "review": "Обычная книга, ничего особенного",
            "amount_usd": 13.14
        }
    ]
    result = build_summary(orders)

    assert len(result["customer_x_currency"]) == 3

    assert result["top3_customers"][0]["customer"] == "alex"
    assert result["top3_customers"][1]["customer"] == "maria"
    assert result["top3_customers"][2]["customer"] == "elena"

    assert result["weekly_usd"][0]["week"] == "2024-09-23/2024-09-29"
    assert result["weekly_usd"][0]["amount_usd"] == 13.15

    assert result["total_usd"] == 47.06
    assert result["avg_check_usd"] == 15.69
