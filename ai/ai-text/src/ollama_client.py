from typing import Any
import requests

class OllamaError(Exception):
    def __init__(self, error_type: str, message: str): super().__init__(message); self.error_type = error_type

class OllamaClient:
    def __init__(self, base_url: str, connect_timeout: float, read_timeout: float): self.base_url = base_url.rstrip("/"); self.timeout = (connect_timeout, read_timeout)
    def models(self) -> list[str]:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=self.timeout); r.raise_for_status()
            return [x["name"] for x in r.json().get("models", [])]
        except requests.RequestException as exc: raise OllamaError("OLLAMA_NOT_RUNNING", str(exc)) from exc
    def unload(self, model: str) -> None:
        try: requests.post(f"{self.base_url}/api/chat", json={"model": model, "messages": [], "keep_alive": 0}, timeout=self.timeout).raise_for_status()
        except requests.RequestException: pass
    def chat(
        self,
        model: str,
        prompt: str,
        temperature: float,
        keep_alive: str,
        schema: dict[str, Any],
        seed: int | None = None,
        context_length: int | None = None,
        thinking: bool | None = None,
    ) -> tuple[dict, dict]:
        options: dict[str, Any] = {"temperature": temperature}
        if seed is not None: options["seed"] = seed
        if context_length is not None: options["num_ctx"] = context_length
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "stream": False, "format": schema, "options": options, "keep_alive": keep_alive}
        if thinking is not None: payload["think"] = thinking
        try:
            r = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout)
            if r.status_code >= 400: raise OllamaError("MODEL_EXECUTION_FAILED", r.text[:500])
            return payload, r.json()
        except requests.ConnectTimeout as exc: raise OllamaError("CONNECTION_TIMEOUT", str(exc)) from exc
        except requests.ReadTimeout as exc: raise OllamaError("READ_TIMEOUT", str(exc)) from exc
        except OllamaError: raise
        except requests.RequestException as exc: raise OllamaError("MODEL_EXECUTION_FAILED", str(exc)) from exc

def performance(response: dict) -> dict:
    ns = lambda key: float(response.get(key, 0) or 0) / 1_000_000
    eval_ns, count = float(response.get("eval_duration", 0) or 0), int(response.get("eval_count", 0) or 0)
    return {"totalDurationMs": ns("total_duration"), "loadDurationMs": ns("load_duration"), "promptEvalDurationMs": ns("prompt_eval_duration"), "evalDurationMs": ns("eval_duration"), "promptEvalCount": int(response.get("prompt_eval_count", 0) or 0), "evalCount": count, "tokensPerSecond": count / (eval_ns / 1e9) if eval_ns > 0 else 0.0}
