import requests
import time

USD_URL = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{date}/v1/currencies/usd.json"

MAX_ATTEMPTS = 3
RETRY_DELAY = 1.0


def get_rate_to_usd(currency: str, order_date: str) -> float:
    url = USD_URL.format(date=order_date)
    for attempt in range(MAX_ATTEMPTS):
        try: 
            response = requests.get(url, timeout=5.0)
            response.raise_for_status() # ловим и 4xx, потом подправлю...
            #? только на 5xx вообще надо бы
            usd_rates = response.json()["usd"]
            return 1 / usd_rates[currency.lower()]
        except requests.RequestException as exc:
            last_error = exc
            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_DELAY)

    raise RuntimeError(f"failed after {MAX_ATTEMPTS} attempts: {last_error}")