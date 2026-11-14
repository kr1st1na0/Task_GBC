from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from fastapi import Security
from app.config import API_KEY

api_key_header = APIKeyHeader(name="x-key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key is None:
        raise HTTPException(
            status_code=403,
            detail="not authenticated"
        )
    if api_key != API_KEY:
        raise HTTPException(
            status_code=403,
            detail="invalid API key"
        )
    return "default_user" 
# так-то здесь возвращать user_id,, но тут пусть будет один пользователь))
# если много пользователей, их данные где-то же лежат...

# API-key_1 : user_id_1, API-key2 : user_id_2
# авторизация по API-keys, а сверяемся по user_id
