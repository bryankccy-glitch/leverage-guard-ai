"""AI 結構化輸出 Schema。AI 只產生文字欄位；verified_metrics 由系統填入，AI 不能改。"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


def _trim(v: str, n: int) -> str:
    return v if len(v) <= n else v[: n - 1] + "…"


class AIEvent(BaseModel):
    event_type: str
    explanation: str

    @field_validator("explanation")
    @classmethod
    def _t(cls, v: str) -> str:
        return _trim(v.strip(), 600)


class AIExplanation(BaseModel):
    """長度超過上限時截短（不視為失敗）；結構錯誤才算驗證失敗。"""
    summary: str
    financial_summary: str
    event_explanations: list[AIEvent] = Field(default_factory=list)
    investor_rights: list[str] = Field(default_factory=list)
    investor_obligations: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)

    @field_validator("summary", "financial_summary")
    @classmethod
    def _s(cls, v: str) -> str:
        return _trim(v.strip(), 1200)

    @field_validator("event_explanations")
    @classmethod
    def _e(cls, v: list) -> list:
        return v[:20]

    @field_validator("investor_rights", "investor_obligations", "uncertainties")
    @classmethod
    def _l(cls, v: list[str]) -> list[str]:
        return [_trim(x, 300) for x in v[:10]]


class CopilotAnswer(BaseModel):
    answer: str = Field(..., max_length=2000)
    cited_article_ids: list[str] = Field(default_factory=list, max_length=8)
    uncertainties: list[str] = Field(default_factory=list, max_length=6)


class ClauseItem(BaseModel):
    category: Literal["financing_rate", "interest_method", "financing_term", "collateral", "maintenance_ratio",
                      "margin_call", "notification", "top_up_deadline", "disposal", "default", "fees",
                      "remaining_debt", "termination", "dispute", "personal_data", "other"]
    clause_number: str | None = None
    quote: str = Field(..., max_length=800)
    plain_language: str = Field(..., max_length=500)
    party: Literal["investor_right", "investor_obligation", "broker_right", "broker_obligation", "neutral"]


class ContractAIResult(BaseModel):
    document_type: Literal["margin_contract", "credit_trading_contract", "brokerage_contract", "day_trading_document",
                           "risk_disclosure", "fee_schedule", "unknown"]
    clauses: list[ClauseItem] = Field(default_factory=list, max_length=40)
    pending_questions: list[str] = Field(default_factory=list, max_length=10)
