from dataclasses import dataclass, field
from typing import Dict, List
from .company_state import CompanyFinancialState


@dataclass
class SessionContext:
    companies: Dict[str, CompanyFinancialState]
    strict_companies: Dict[str, CompanyFinancialState]
    active_company: str
    strict_mode: bool
    chat_history: List[dict] = field(default_factory=list)

    def get_active_state(self) -> CompanyFinancialState:
        if self.strict_mode:
            return self.strict_companies[self.active_company]
        return self.companies[self.active_company]
