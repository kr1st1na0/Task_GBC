import asyncio
import httpx

USD_URL = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{date}/v1/currencies/usd.json"

MAX_ATTEMPTS = 3
RETRY_DELAY = 1.0


async def get_rate_to_usd(currency: str, order_date: str) -> float:
    url = USD_URL.format(date=order_date)
    last_error: Exception | None = None

    async with httpx.AsyncClient(timeout=5.0) as client:
        for attempt in range(MAX_ATTEMPTS):
            try: 
                # ловим сетевые и 5xx
                response = await client.get(url)
                if response.status_code >= 500:
                    raise httpx.HTTPStatusError(f"server error {response.status_code}", response=response)
                
                usd_rates = response.json()["usd"]
                return 1 / usd_rates[currency.lower()]
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt < MAX_ATTEMPTS - 1:
                    await asyncio.sleep(RETRY_DELAY)

    raise RuntimeError(f"failed after {MAX_ATTEMPTS} attempts: {last_error}")