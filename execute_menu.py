import uvicorn

uvicorn.run(
    "menu:app",
    port=8013,
    host="0.0.0.0",
    ssl_keyfile="/etc/ssl/woowakgood.live.key",
    ssl_certfile="/etc/ssl/woowakgood.live.crt",
)
