import uvicorn

uvicorn.run(
    "server_manager:app",
    port=8007,
    host="0.0.0.0",
)
