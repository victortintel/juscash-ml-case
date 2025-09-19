from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class Documento(BaseModel):
    id: str
    dataHoraJuntada: Optional[datetime] = None
    nome: str
    texto: str

class Movimento(BaseModel):
    dataHora: Optional[datetime] = None
    descricao: str

class Processo(BaseModel):
    numeroProcesso: str
    classe: Optional[str] = None
    orgaoJulgador: Optional[str] = None
    ultimaDistribuicao: Optional[datetime] = None
    assunto: Optional[str] = None
    segredoJustica: Optional[bool] = None
    justicaGratuita: Optional[bool] = None
    siglaTribunal: Optional[str] = None
    esfera: Optional[str] = None
    valorCondenacao: Optional[float] = None  # POL-2
    documentos: List[Documento] = Field(default_factory=list)
    movimentos: List[Movimento] = Field(default_factory=list)

class DecisionOut(BaseModel):
    decision: Literal["approved", "rejected", "incomplete"]
    rationale: str
    citacoes: List[str]