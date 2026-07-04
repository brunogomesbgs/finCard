import httpx
import asyncio
import structlog
from app.infrastructure.persistence.config import settings

logger = structlog.get_logger()

class GatewayError(Exception):
    pass

class GatewayClient:
    def __init__(self):
        self.base_url = settings.GATEWAY_URL
        self.timeout = httpx.Timeout(5.0, connect=2.0)

    async def process_payment(self, transaction_id: str, amount: float, currency: str):
        url = f"{self.base_url}/payments"
        payload = {
            "transaction_id": transaction_id,
            "amount": amount,
            "currency": currency
        }

        retries = 3
        backoff = 1.0

        for attempt in range(retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    logger.info("calling_gateway", transaction_id=transaction_id, url=url, payload=payload, attempt=attempt+1)
                    response = await client.post(url, json=payload)
                    
                    if response.status_code == 200:
                        return response.json()
                    
                    logger.error("gateway_response_error", status_code=response.status_code, body=response.text, transaction_id=transaction_id)
                    
                    if 500 <= response.status_code < 600:
                        logger.warn("gateway_server_error", status_code=response.status_code, transaction_id=transaction_id)
                    else:
                        logger.error("gateway_client_error", status_code=response.status_code, transaction_id=transaction_id)
                        raise GatewayError(f"Gateway returned {response.status_code}: {response.text}")

            except (httpx.RequestError, asyncio.TimeoutError) as exc:
                logger.warn("gateway_connection_error", error=str(exc), transaction_id=transaction_id)
            
            if attempt < retries - 1:
                sleep_time = backoff * (2 ** attempt)
                await asyncio.sleep(sleep_time)
            
        raise GatewayError("Max retries exceeded for gateway")
