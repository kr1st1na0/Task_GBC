import requests
import time

USD_URL = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{date}/v1/currencies/usd.json"

MAX_ATTEMPTS = 3
RETRY_DELAY = 1.0


def get_rate_to_usd(currency: str, order_date: str) -> float:
    url = USD_URL.format(date=order_date)
    for attempt in range(MAX_ATTEMPTS):
        try: 
            # ловим сетевые и 5xx
            response = requests.get(url, timeout=5.0)
            if response.status_code >= 500:
                raise requests.HTTPError(f"server error {response.status_code}", response=response)
            
            usd_rates = response.json()["usd"]
            return 1 / usd_rates[currency.lower()]
        except requests.RequestException as exc:
            last_error = exc
            if attempt < MAX_ATTEMPTS - 1:
                time.sleep(RETRY_DELAY)

    raise RuntimeError(f"failed after {MAX_ATTEMPTS} attempts: {last_error}")