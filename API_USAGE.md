# Incandescent local API

Incandescent exposes an OpenAI-style chat endpoint on the machine running the service:

`POST http://127.0.0.1:8765/v1/chat/completions`

Create a key in the UI under **Your AIs → API**. Keys are shown once and stored as SHA-256 hashes in the local runtime file `incandescent_api_data.json`. Revoke keys in the same UI. Do not commit or share that runtime file or raw keys.

Example request:

```bash
curl http://127.0.0.1:8765/v1/chat/completions ^
  -H "Authorization: Bearer inc_live_REPLACE_WITH_YOUR_KEY" ^
  -H "Content-Type: application/json" ^
  -d "{\"messages\":[{\"role\":\"user\",\"content\":\"Hello\"}]}"
```

The endpoint accepts non-streaming chat-completion requests. Streaming is not supported yet. Requests have no application-level count quota, but generation speed and availability are limited by the PC, the selected Ollama model, and whether Incandescent is running.

**Connectivity:** the default service binds to `127.0.0.1`, so this endpoint works only from the same PC. It is not a public Internet API yet. A website hosted elsewhere cannot use that localhost address to reach your PC. Public use requires a deployment or secure tunnel with HTTPS, access controls, and a deliberate network configuration. Do not expose the service to the Internet as-is.
