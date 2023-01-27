import uvicorn

uvicorn.run(
    "server_manager:app",
    port=8007,
    host="0.0.0.0",
    ssl_keyfile="/etc/ssl/woowakgood.live.key",
    ssl_certfile="/etc/ssl/woowakgood.live.crt",
)
