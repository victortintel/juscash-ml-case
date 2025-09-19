# app/llm.py
import os
import json
import logging
from typing import Dict, Any

import requests
import httpx
from openai import OpenAI

from .schemas import Processo, DecisionOut
from .settings import settings


# ---------------------- utilidades ----------------------
def _read_prompt_header() -> str:
    with open("prompts/v1.md", "r", encoding="utf-8") as f:
        return f.read().strip()


def _build_prompt(process: Processo, prelim_obs: str = "") -> str:
    header = _read_prompt_header()
    dados = process.model_dump()
    return (
        f"{header}\n\nOBSERVAÇÕES PRELIMINARES (não-vinculantes): {prelim_obs}"
        f"\n\nDADOS DO PROCESSO:\n{json.dumps(dados, ensure_ascii=False, indent=2)}"
    )


def _coerce_json(s: str) -> Dict[str, Any]:
    """Extrai o primeiro JSON válido de uma string (bem tolerante)."""
    first, last = s.find("{"), s.rfind("}")
    if first == -1 or last == -1 or last < first:
        raise ValueError("Resposta do LLM não contém JSON.")
    return json.loads(s[first : last + 1])


# ---------------------- OLLAMA --------------------------
def _ask_ollama(prompt: str, model: str) -> str:
    """
    Chama o Ollama local via REST e retorna APENAS o conteúdo textual.
    A URL base vem de OLLAMA_BASE_URL (ex.: http://localhost:11434 no dev,
    e http://ollama:11434 quando estiver rodando por Docker Compose).
    """
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    url = f"{base}/api/chat"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Responda APENAS com JSON válido no formato pedido."},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {"temperature": 0},
    }

    r = requests.post(url, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    return data["message"]["content"]


# ---------------------- OPENAI (opcional) ---------------
_http_client = httpx.Client(timeout=60.0, follow_redirects=True)
_openai = lambda: OpenAI(api_key=settings.OPENAI_API_KEY, http_client=_http_client)


# ---------------------- Função principal ----------------
def call_llm_and_validate(prompt: str) -> DecisionOut:
    provider = settings.LLM_PROVIDER.lower()

    # 1) OLLAMA local
    if provider == "ollama":
        content = _ask_ollama(prompt, settings.LLM_MODEL)
        data = _coerce_json(content)
        return DecisionOut.model_validate(data)

    # 2) OPENAI (se um dia você ativar)
    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY ausente.")
        content = None
        try:
            resp = _openai().chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": "Responda apenas com JSON válido no formato pedido."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
            )
            content = resp.choices[0].message.content
        except Exception as e:
            logging.warning("Falha no chat.completions: %s", e)

        if not content:
            # fallback na Responses API
            try:
                resp = _openai().responses.create(
                    model=settings.LLM_MODEL,
                    input=f"Responda SOMENTE com JSON no formato exigido.\n{prompt}",
                )
                content = resp.output_text
            except Exception as e:
                logging.error("Falha também em responses.create: %s", e)
                raise

        data = _coerce_json(content)
        return DecisionOut.model_validate(data)

    # 3) STUB (apenas para desenvolvimento)
    if provider == "stub":
        raise RuntimeError("LLM em modo 'stub' – não chama modelo.")

    raise RuntimeError(f"LLM provider não suportado: {provider}")
