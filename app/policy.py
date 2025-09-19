import re
from typing import List, Tuple
from .schemas import Processo, Documento

POL = {
    "POL-1": "Só compramos crédito de processos transitados em julgado e em fase de execução.",
    "POL-2": "Exigir valor de condenação informado.",
    "POL-3": "Valor de condenação < R$ 1.000,00 → não compra.",
    "POL-4": "Condenações na esfera trabalhista → não compra.",
    "POL-5": "Óbito do autor sem habilitação no inventário → não compra.",
    "POL-6": "Substabelecimento sem reserva de poderes → não compra.",
    "POL-7": "Informar honorários contratuais, periciais e sucumbenciais quando existirem.",
    "POL-8": "Se faltar documento essencial (ex.: trânsito em julgado não comprovado) → incomplete.",
}

def has_transito_em_julgado(process: Processo) -> bool:
    """Busca por 'Trânsito em Julgado' nos documentos."""
    pat = re.compile(r"tr[aâ]nsito.*julgado", re.I | re.S)
    return any(pat.search(d.nome) or pat.search(d.texto) for d in process.documentos)

def is_em_execucao(process: Processo) -> bool:
    """Sinais de fase de execução: 'Cumprimento definitivo', 'RPV', 'Precatório' etc."""
    texto_docs = " ".join((d.nome + " " + d.texto) for d in process.documentos)
    texto_movs = " ".join(m.descricao for m in process.movimentos)
    return bool(re.search(r"cumprimento.*definitivo", texto_movs, re.I) or
                re.search(r"\bRPV\b|Requisi[cç][aã]o de Pequeno Valor", texto_docs, re.I) or
                re.search(r"Precat[óo]rio", texto_docs, re.I))

def is_trabalhista(process: Processo) -> bool:
    return (process.esfera or "").lower().strip() == "trabalhista" or (process.siglaTribunal or "").upper().startswith("TRT")

def has_substabelecimento_sem_reserva(process: Processo) -> bool:
    pat = re.compile(r"Substabelecimento.*sem\s+reserva", re.I | re.S)
    return any(pat.search(d.nome) or pat.search(d.texto) for d in process.documentos)

def has_obito_sem_habilitacao(process: Processo) -> bool:
    texto_docs = " ".join((d.nome + " " + d.texto) for d in process.documentos)
    return bool(re.search(r"\b[óo]bito\b", texto_docs, re.I) and not re.search(r"habilita[cç][aã]o", texto_docs, re.I))

def preliminar_checks(process: Processo) -> Tuple[str, List[str], List[str]]:
    """
    Retorna (suggested_decision, rationale_points, citacoes) quando uma regra é conclusiva
    ou ("", [], []) quando precisamos do LLM decidir.
    """
    reasons, cites = [], []

    # POL-4: esfera trabalhista
    if is_trabalhista(process):
        return ("rejected", ["Condenação na esfera trabalhista."], ["POL-4"])

    # POL-2 / POL-3: valor de condenação
    if process.valorCondenacao is None:
        return ("incomplete", ["Valor de condenação ausente."], ["POL-2"])
    if process.valorCondenacao < 1000:
        return ("rejected", [f"Valor de condenação inferior a R$1.000 (R${process.valorCondenacao:.2f})."], ["POL-3"])

    # POL-6: substabelecimento sem reserva
    if has_substabelecimento_sem_reserva(process):
        return ("rejected", ["Substabelecimento sem reserva de poderes."], ["POL-6"])

    # POL-5: óbito sem habilitação
    if has_obito_sem_habilitacao(process):
        return ("rejected", ["Óbito do autor sem habilitação no inventário."], ["POL-5"])

    # POL-1: precisa de trânsito + fase de execução
    tem_transito = has_transito_em_julgado(process)
    em_execucao = is_em_execucao(process)
    if not tem_transito:
        return ("incomplete", ["Falta comprovação do trânsito em julgado."], ["POL-8"])  # qualidade/documento essencial
    if not em_execucao:
        reasons.append("Trânsito presente, mas sinais de execução não identificados.")
        cites.extend(["POL-1"])

    # POL-7: honorários (não barra; vira observação para o LLM reforçar a explicação)
    # Aqui só registramos para o prompt.

    return ("", reasons, list(set(cites)))