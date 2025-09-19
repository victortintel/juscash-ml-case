from fastapi import FastAPI
from .schemas import Processo, DecisionOut
from .policy import preliminar_checks
from .llm import _build_prompt, call_llm_and_validate
from .settings import settings
import os
import logging
import requests  

logging.basicConfig(level=logging.INFO)
logging.getLogger("uvicorn.error").setLevel(logging.INFO)

logging.info(f"[BOOT] LLM_PROVIDER={os.getenv('LLM_PROVIDER')} LLM_MODEL={os.getenv('LLM_MODEL')}")

logger = logging.getLogger(__name__)

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


def _enforce_policy_precedence(out: DecisionOut, cites_from_rules):
    """
    Ajusta a decisão final de acordo com as políticas determinísticas,
    mesmo após a sugestão do LLM.
    - POL-8 => incomplete (falta documento essencial)
    - POL-3, POL-4, POL-5, POL-6 => rejected (regras de reprovação)
    - POL-1, POL-2, POL-7 não reprovam sozinhas
    """
    must_incomplete = {"POL-8"}
    must_reject = {"POL-3", "POL-4", "POL-5", "POL-6"}

    
    if any(c in cites_from_rules for c in must_incomplete):
        out.decision = "incomplete"
        out.citacoes = sorted(set((out.citacoes or []) + ["POL-8"]))
        if not out.rationale:
            out.rationale = "Falta documento essencial (ex.: trânsito em julgado)."
        return out

    
    reject_hits = [c for c in cites_from_rules if c in must_reject]
    if reject_hits:
        out.decision = "rejected"
        out.citacoes = sorted(set((out.citacoes or []) + reject_hits))
        if not out.rationale:
            out.rationale = "Reprovação por regra determinística."
        return out

    
    return out


@app.get("/debug/llm")
def debug_llm():
    return {
        "provider": settings.LLM_PROVIDER,
        "model": settings.LLM_MODEL,
        "has_key": bool(getattr(settings, "OPENAI_API_KEY", "")),
    }


@app.post("/predict", response_model=DecisionOut)
def predict(proc: Processo) -> DecisionOut:
    logging.info("LLM provider=%s | model=%s", settings.LLM_PROVIDER, settings.LLM_MODEL)

    
    suggested, reasons, cites = preliminar_checks(proc)
    prelim_obs = "; ".join(reasons) if reasons else "Sem observações determinísticas relevantes."

    
    prompt = _build_prompt(proc, prelim_obs)

    
    try:
        out = call_llm_and_validate(prompt)

        
        if not out.citacoes:
            out.citacoes = sorted(set(cites or []))

        valid = {"approved", "rejected", "incomplete"}
        if out.decision not in valid:
            out.decision = suggested
            if not out.rationale:
                out.rationale = "Ajuste automático com base nas regras determinísticas."

        
        out = _enforce_policy_precedence(out, cites)

        
        try:
            if getattr(settings, "N8N_WEBHOOK_URL", ""):
                requests.post(
                    settings.N8N_WEBHOOK_URL,
                    json={
                        "input": proc.dict(),        
                        "output": out.dict(),        
                        "provider": settings.LLM_PROVIDER,
                        "model": settings.LLM_MODEL,
                    },
                    timeout=10,
                )
        except Exception as e:
            logger.warning(f"n8n webhook falhou: {e}")

        return out

    except Exception:
        logging.exception("LLM error (usando fallback)")

    
    if suggested == "rejected":
        out = DecisionOut(
            decision="rejected",
            rationale="Regra determinística aplicada.",
            citacoes=sorted(set(cites or [])),
        )
    elif suggested == "incomplete":
        out = DecisionOut(
            decision="incomplete",
            rationale="Documento ou informação essencial ausente.",
            citacoes=sorted(set(cites or [])),
        )
    else:
        out = DecisionOut(
            decision="approved",
            rationale="Trânsito/execução/valor parecem consistentes; LLM indisponível.",
            citacoes=sorted(set((cites or []) + ["POL-1", "POL-2"])),
        )

    
    try:
        if getattr(settings, "N8N_WEBHOOK_URL", ""):
            requests.post(
                settings.N8N_WEBHOOK_URL,
                json={
                    "input": proc.dict(),
                    "output": out.dict(),
                    "provider": settings.LLM_PROVIDER,
                    "model": settings.LLM_MODEL,
                },
                timeout=10,
            )
    except Exception as e:
        logger.warning(f"n8n webhook falhou (fallback): {e}")

    return out
