import json
from typing import Dict, List, Optional, Any, Tuple
from src.financial_engine.company_state import CompanyFinancialState

class DeterministicComputationController:
    """
    Deterministic Financial Computation Controller.
    Enforces strict separation between extraction, computation, and interpretation.
    Supports partial analysis via field-specific validation.
    """

    def __init__(self, state: CompanyFinancialState):
        self.state = state

    def run_computation(self, request_type: str) -> Dict[str, Any]:
        """
        Main entry point for computational requests.
        """
        try:
            if request_type == "full_analysis":
                return self._compute_comprehensive_metrics()
            elif request_type == "piotroski":
                return self._compute_piotroski()
            elif request_type == "growth":
                return self._compute_growth_metrics()
            else:
                return {
                    "status": "error",
                    "reason": f"Unknown computation type: {request_type}"
                }
        except Exception as e:
            return {
                "status": "error",
                "reason": f"Internal computation error: {str(e)}"
            }

    def _get_metric(self, name: str, year_offset: int = 0) -> Optional[float]:
        try:
            if name == "revenue":
                statements = self.state.income_statements
                if len(statements) > abs(year_offset):
                    return float(statements[year_offset].total_revenue)
            elif name == "net_income":
                statements = self.state.income_statements
                if len(statements) > abs(year_offset):
                    return float(statements[year_offset].net_income)
            elif name == "total_assets":
                statements = self.state.balance_sheets
                if len(statements) > abs(year_offset):
                    return float(statements[year_offset].total_assets)
            elif name == "cfo":
                statements = self.state.cash_flow_statements
                if len(statements) > abs(year_offset):
                    return float(statements[year_offset].net_cash_ops)
            elif name == "capex":
                statements = self.state.cash_flow_statements
                if len(statements) > abs(year_offset):
                    return float(statements[year_offset].capex)
            elif name == "current_assets":
                statements = self.state.balance_sheets
                if len(statements) > abs(year_offset):
                    return float(statements[year_offset].current_assets)
            elif name == "current_liabilities":
                statements = self.state.balance_sheets
                if len(statements) > abs(year_offset):
                    return float(statements[year_offset].current_liabilities)
        except (AttributeError, IndexError, TypeError, ValueError):
            return None
        return None

    def _compute_comprehensive_metrics(self) -> Dict[str, Any]:
        """
        Computes all available metrics. Uses field-specific validation.
        """
        computed = {}
        failed = {}
        
        # 1. Revenue Growth
        rev_cy = self._get_metric("revenue", 0)
        rev_py = self._get_metric("revenue", -1)
        if rev_cy is not None and rev_py is not None:
            computed["revenue_growth"] = f"{(rev_cy / rev_py - 1):.2%}"
        else:
            failed["revenue_growth"] = "insufficient_data (Missing Revenue CY/PY)"

        # 2. Net Income Growth
        ni_cy = self._get_metric("net_income", 0)
        ni_py = self._get_metric("net_income", -1)
        if ni_cy is not None and ni_py is not None:
            computed["net_income_growth"] = f"{(ni_cy / ni_py - 1):.2%}"
        else:
            failed["net_income_growth"] = "insufficient_data (Missing Net Income CY/PY)"

        # 3. ROA
        assets_cy = self._get_metric("total_assets", 0)
        if ni_cy is not None and assets_cy is not None:
            computed["roa"] = f"{(ni_cy / assets_cy):.4f}"
        else:
            failed["roa"] = "insufficient_data (Missing Net Income or Total Assets)"

        # 4. CFO/PAT
        cfo_cy = self._get_metric("cfo", 0)
        if cfo_cy is not None and ni_cy is not None and ni_cy != 0:
            computed["cfo_to_pat"] = f"{(cfo_cy / ni_cy):.2f}"
        else:
            failed["cfo_to_pat"] = "insufficient_data (Missing CFO or Net Income)"

        # 5. Free Cash Flow
        capex_cy = self._get_metric("capex", 0)
        if cfo_cy is not None and capex_cy is not None:
            computed["free_cash_flow"] = f"{(cfo_cy - abs(capex_cy)):,.2f}"
        else:
            failed["free_cash_flow"] = "insufficient_data (Missing CFO or Capex)"

        # 6. Current Ratio
        ca_cy = self._get_metric("current_assets", 0)
        cl_cy = self._get_metric("current_liabilities", 0)
        if ca_cy is not None and cl_cy is not None and cl_cy != 0:
            computed["current_ratio"] = f"{(ca_cy / cl_cy):.2f}"
        else:
            failed["current_ratio"] = "insufficient_data (Missing Current Assets/Liabilities)"

        # 7. Piotroski Score
        piotroski = self._compute_piotroski_internal()
        
        # Final Status Determination
        if not computed and not piotroski["details"]:
            return {
                "status": "error",
                "reason": "INSUFFICIENT NUMERIC DATA FOR ALL METRICS",
                "failed_metrics": failed
            }
        
        status = "success" if not failed else "partial_success"
        
        return {
            "status": status,
            "computed_metrics": computed,
            "failed_metrics": failed,
            "piotroski_score": piotroski["total_score"],
            "piotroski_details": piotroski["details"],
            "validation_passed": True
        }

    def _compute_piotroski_internal(self) -> Dict[str, Any]:
        """
        Improved Piotroski logic with operand-specific checks.
        """
        ni_cy = self._get_metric("net_income", 0)
        ni_py = self._get_metric("net_income", -1)
        assets_cy = self._get_metric("total_assets", 0)
        assets_py = self._get_metric("total_assets", -1)
        cfo = self._get_metric("cfo", 0)
        ca_cy = self._get_metric("current_assets", 0)
        cl_cy = self._get_metric("current_liabilities", 0)
        
        rules = {}
        
        # Profitability
        if ni_cy is not None: rules["Positive Net Income"] = ni_cy > 0
        if cfo is not None: rules["Positive Operating Cash Flow"] = cfo > 0
        
        if ni_cy is not None and assets_cy is not None and ni_py is not None and assets_py is not None:
            roa_cy = ni_cy / assets_cy
            roa_py = ni_py / assets_py
            rules["Increasing ROA"] = roa_cy > roa_py
            
        if cfo is not None and ni_cy is not None:
            rules["Accrual (CFO > PAT)"] = cfo > ni_cy
            
        # Liquidity
        if ca_cy is not None and cl_cy is not None and cl_cy != 0:
            rules["Increasing Liquidity (Current Ratio)"] = (ca_cy / cl_cy) > 1.0 

        score = sum(1 for v in rules.values() if v)
        
        return {
            "total_score": score,
            "details": rules
        }

    def _compute_piotroski(self) -> Dict[str, Any]:
        res = self._compute_piotroski_internal()
        if not res["details"]:
            return {
                "status": "error",
                "reason": "Insufficient data to compute any Piotroski criteria."
            }
        return {
            "status": "success",
            "piotroski_score": res["total_score"],
            "piotroski_details": res["details"],
            "validation_passed": True
        }

    def _compute_growth_metrics(self) -> Dict[str, Any]:
        computed = {}
        failed = {}
        
        rev_cy = self._get_metric("revenue", 0)
        rev_py = self._get_metric("revenue", -1)
        if rev_cy is not None and rev_py is not None:
            computed["revenue_growth"] = f"{(rev_cy/rev_py - 1):.2%}"
        else:
            failed["revenue_growth"] = "insufficient_data"

        ni_cy = self._get_metric("net_income", 0)
        ni_py = self._get_metric("net_income", -1)
        if ni_cy is not None and ni_py is not None:
            computed["net_income_growth"] = f"{(ni_cy/ni_py - 1):.2%}"
        else:
            failed["net_income_growth"] = "insufficient_data"

        if not computed:
            return {
                "status": "error",
                "reason": "No growth metrics could be computed."
            }

        return {
            "status": "success" if not failed else "partial_success",
            "computed_metrics": computed,
            "failed_metrics": failed,
            "validation_passed": True
        }
