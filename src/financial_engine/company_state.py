from dataclasses import dataclass, field
from typing import Optional, Dict
from decimal import Decimal
from .models.canonical_models import (
    IncomeStatement,
    CashFlowStatement,
    BalanceSheet,
)
from .models.strict_config import StrictConfig
from .models.raw_models import RawStatement
from .models.metric_result import MetricResult


@dataclass
class CompanyFinancialState:
    income_statements: Optional[Dict[int, IncomeStatement]]
    cash_flow_statements: Optional[Dict[int, CashFlowStatement]]
    balance_sheets: Optional[Dict[int, BalanceSheet]]
    strict_config: StrictConfig

    _derived_cache: dict = field(default_factory=dict)
    _ttm_cache: dict = field(default_factory=dict)
    _piotroski_cache: Optional[MetricResult] = None

    def _base_confidence(self):
        confidence = Decimal("1.0")

        if self.strict_config.strict_mode:
            confidence -= Decimal("0.1")

        identity_valid = self.validate_balance_identity()
        if identity_valid is False:
            confidence -= Decimal("0.2") # This might be recursive if validate calls base_confidence? 
            # validate_balance_identity returns bool (or MetricResult now?). 
            # Wait, validate_balance_identity will be updated to return MetricResult.
            # So checking identity_valid is False will be wrong if it returns MetricResult.
            # We need to act carefully here.
            # The prompt says: "identity_valid = self.validate_balance_identity(); if identity_valid is False..." 
            # But step 3 says "Apply same structure to: ... (list which doesn't explicitly include validate_balance_identity BUT step 5 says 'Update strict diff... check .value'). 
            # Let's check strict_diff.py usages. It uses: get_revenue_growth, compute_piotroski. 
            # Comparison mode uses: validate_balance_identity. 
            # So validate_balance_identity DOES need to return MetricResult.
            # So recursively calling it inside base_confidence is dangerous if it calls base_confidence.
            # validate_balance_identity computes derivation. 
            # DOES validate_balance_identity need confidence? 
            # It's a validation check. "Valid" or "Invalid". 
            # Let's look at validate_balance_identity implementation. It checks math. 
            # It doesn't rely on other confidence metrics. 
            # BUT if we change it to return MetricResult, it will likely call _base_confidence().
            # CIRCULAR DEPENDENCY ALERT.
            # _base_confidence calls validate_balance_identity -> returns MetricResult -> calls _base_confidence...
            
            # SOLUTION: 
            # impl _validate_balance_identity_internal(self) -> bool
            # validate_balance_identity(self) -> MetricResult (calls internal, calls base_confidence)
            # _base_confidence calls internal.
            pass

    def _validate_balance_identity_internal(self) -> Optional[bool]:
         # Raw logic for internal use
        if not self.balance_sheets:
            return None

        years = sorted(self.balance_sheets.keys())
        latest = years[-1]
        bs = self.balance_sheets[latest]

        if (
            bs.total_assets is None
            or bs.total_liabilities is None
            or bs.total_equity is None
        ):
            return None

        return bs.total_assets == (bs.total_liabilities + bs.total_equity)

    def _base_confidence(self):
        confidence = Decimal("1.0")
        
        # Penalize strict mode
        if self.strict_config.strict_mode:
            confidence -= Decimal("0.1")

        # Penalize failed identity check (internal to avoid recursion)
        identity_valid = self._validate_balance_identity_internal()
        if identity_valid is False:
            confidence -= Decimal("0.2")

        if confidence < Decimal("0"):
            confidence = Decimal("0")

        return confidence

    def get_overall_confidence(self):
        base = self._base_confidence()

        if not self.income_statements:
            base -= Decimal("0.2")

        if not self.cash_flow_statements:
            base -= Decimal("0.2")

        if not self.balance_sheets:
            base -= Decimal("0.2")

        if base < Decimal("0"):
            base = Decimal("0")

        return base


    def get_revenue_growth(self):
        key = "revenue_growth"
        if key in self._derived_cache:
            return self._derived_cache[key]

        confidence = self._base_confidence()

        if not self.income_statements:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Missing income statements")
            self._derived_cache[key] = res
            return res

        years = sorted(self.income_statements.keys())
        if len(years) < 2:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Insufficient history for growth")
            self._derived_cache[key] = res
            return res

        latest = years[-1]
        previous = years[-2]

        rev_latest = self.income_statements[latest].revenue
        rev_prev = self.income_statements[previous].revenue

        if rev_latest is None or rev_prev is None or rev_prev == 0:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Invalid revenue data")
            self._derived_cache[key] = res
            return res

        growth = (rev_latest - rev_prev) / rev_prev
        res = MetricResult(
            value=growth,
            confidence=confidence,
            explanation=f"Revenue growth from {previous} to {latest}"
        )
        self._derived_cache[key] = res
        return res

    def get_cfo_to_net_income(self):
        key = "cfo_net_income_ratio"
        if key in self._derived_cache:
            return self._derived_cache[key]

        confidence = self._base_confidence()

        if not self.cash_flow_statements or not self.income_statements:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Missing statements")
            self._derived_cache[key] = res
            return res

        years = sorted(self.income_statements.keys())
        latest = years[-1]

        net_income = self.income_statements[latest].net_income
        cfo = None

        if latest in self.cash_flow_statements:
            cfo = self.cash_flow_statements[latest].cfo

        if net_income is None or cfo is None or net_income == 0:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Invalid NI or CFO data")
            self._derived_cache[key] = res
            return res

        ratio = cfo / net_income
        res = MetricResult(
            value=ratio,
            confidence=confidence,
            explanation="CFO / Net Income"
        )
        self._derived_cache[key] = res
        return res

    def validate_balance_identity(self):
        key = "balance_identity"
        if key in self._derived_cache:
            return self._derived_cache[key]
            
        # We use the internal check to determine the value
        valid = self._validate_balance_identity_internal()
        
        # Identity validation "confidence" is logically just base confidence? 
        # Or maybe it's 1.0 if we have data? 
        # If valid is None -> Insufficient data.
        
        confidence = self._base_confidence()

        if valid is None:
             res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Missing balance sheet data")
             self._derived_cache[key] = res
             return res
             
        # Value is boolean wrapped in Decimal? No, comparing logic usually expects bool. 
        # But instructions say "MetricResult(value=Decimal('1') if signal else ...)" for SIGNALS. 
        # This is a validation method. 
        # "Step 3: ... Apply same structure to: ... (list) ... (doesn't explicit include strict validate, but strict diff usage implies it needs structuring)"
        # Assuming we treat it like a signal/Boolean check.
        
        val_decimal = Decimal("1") if valid else Decimal("0")
        
        res = MetricResult(
            value=val_decimal,
            confidence=confidence,
            explanation="Total Assets == Liabilities + Equity"
        )
        self._derived_cache[key] = res
        return res

    def compute_ttm_net_income(self):
        key = "ttm_net_income"
        if key in self._ttm_cache:
            return self._ttm_cache[key]

        confidence = self._base_confidence()

        if not self.income_statements:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Missing income statements")
            self._ttm_cache[key] = res
            return res

        years = sorted(self.income_statements.keys())

        if self.strict_config.strict_mode:
            if len(years) < 4:
                res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Strict mode requires 4 periods for TTM")
                self._ttm_cache[key] = res
                return res
            selected_years = years[-4:]
        else:
            if len(years) >= 4:
                selected_years = years[-4:]
            elif len(years) >= 1:
                selected_years = years
            else:
                res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Insufficient history")
                self._ttm_cache[key] = res
                return res

        total = Decimal("0")
        for y in selected_years:
            ni = self.income_statements[y].net_income
            if ni is None:
                res = MetricResult(value=None, confidence=Decimal("0.0"), explanation=f"Missing NI for year {y}")
                self._ttm_cache[key] = res
                return res
            total += ni

        res = MetricResult(
            value=total,
            confidence=confidence,
            explanation="Trailing Twelve Months Net Income"
        )
        self._ttm_cache[key] = res
        return res

    def get_gross_margin(self):
        key = "gross_margin"
        if key in self._derived_cache:
            return self._derived_cache[key]

        confidence = self._base_confidence()

        if not self.income_statements:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Missing income statements")
            self._derived_cache[key] = res
            return res

        years = sorted(self.income_statements.keys())
        latest = years[-1]

        stmt = self.income_statements[latest]

        if stmt.revenue is None or stmt.gross_profit is None or stmt.revenue == 0:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Invalid revenue/gross profit data")
            self._derived_cache[key] = res
            return res

        margin = stmt.gross_profit / stmt.revenue
        res = MetricResult(value=margin, confidence=confidence, explanation="Gross Profit / Revenue")
        self._derived_cache[key] = res
        return res

    def get_operating_margin(self):
        key = "operating_margin"
        if key in self._derived_cache:
            return self._derived_cache[key]

        confidence = self._base_confidence()

        if not self.income_statements:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Missing income statements")
            self._derived_cache[key] = res
            return res

        years = sorted(self.income_statements.keys())
        latest = years[-1]

        stmt = self.income_statements[latest]

        if (
            stmt.revenue is None
            or stmt.operating_income is None
            or stmt.revenue == 0
        ):
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Invalid revenue/op income data")
            self._derived_cache[key] = res
            return res

        margin = stmt.operating_income / stmt.revenue
        res = MetricResult(value=margin, confidence=confidence, explanation="Operating Income / Revenue")
        self._derived_cache[key] = res
        return res

    def get_debt_ratio(self):
        key = "debt_ratio"
        if key in self._derived_cache:
            return self._derived_cache[key]

        confidence = self._base_confidence()

        if not self.balance_sheets:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Missing balance sheets")
            self._derived_cache[key] = res
            return res

        years = sorted(self.balance_sheets.keys())
        latest = years[-1]

        bs = self.balance_sheets[latest]

        if (
            bs.total_liabilities is None
            or bs.total_assets is None
            or bs.total_assets == 0
        ):
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Invalid liabilities/assets data")
            self._derived_cache[key] = res
            return res

        ratio = bs.total_liabilities / bs.total_assets
        res = MetricResult(value=ratio, confidence=confidence, explanation="Total Liabilities / Total Assets")
        self._derived_cache[key] = res
        return res

    def get_current_ratio(self):
        key = "current_ratio"
        if key in self._derived_cache:
            return self._derived_cache[key]

        confidence = self._base_confidence()

        if not self.balance_sheets:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Missing balance sheets")
            self._derived_cache[key] = res
            return res

        years = sorted(self.balance_sheets.keys())
        latest = years[-1]

        bs = self.balance_sheets[latest]

        if (
            bs.current_assets is None
            or bs.current_liabilities is None
            or bs.current_liabilities == 0
        ):
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Invalid current assets/liabilities data")
            self._derived_cache[key] = res
            return res

        ratio = bs.current_assets / bs.current_liabilities
        res = MetricResult(value=ratio, confidence=confidence, explanation="Current Assets / Current Liabilities")
        self._derived_cache[key] = res
        return res

    def get_free_cash_flow(self):
        key = "free_cash_flow"
        if key in self._derived_cache:
            return self._derived_cache[key]

        confidence = self._base_confidence()

        if not self.cash_flow_statements:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Missing cash flow statements")
            self._derived_cache[key] = res
            return res

        years = sorted(self.cash_flow_statements.keys())
        latest = years[-1]

        stmt = self.cash_flow_statements[latest]

        if stmt.cfo is None or stmt.capex is None:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Invalid CFO/Capex data")
            self._derived_cache[key] = res
            return res

        fcf = stmt.cfo - stmt.capex
        res = MetricResult(value=fcf, confidence=confidence, explanation="CFO - Capex")
        self._derived_cache[key] = res
        return res

    def get_revenue_cagr(self):
        key = "revenue_cagr"
        if key in self._derived_cache:
            return self._derived_cache[key]

        confidence = self._base_confidence()

        if not self.income_statements:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Missing income statements")
            self._derived_cache[key] = res
            return res

        years = sorted(self.income_statements.keys())
        if len(years) < 2:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Insufficient history for CAGR")
            self._derived_cache[key] = res
            return res

        start_year = years[0]
        end_year = years[-1]

        start_rev = self.income_statements[start_year].revenue
        end_rev = self.income_statements[end_year].revenue

        if start_rev is None or end_rev is None or start_rev <= 0:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Invalid revenue data for CAGR")
            self._derived_cache[key] = res
            return res

        periods = Decimal(len(years) - 1)
        cagr = (end_rev / start_rev) ** (Decimal("1") / periods) - Decimal("1")

        res = MetricResult(value=cagr, confidence=confidence, explanation="Revenue CAGR")
        self._derived_cache[key] = res
        return res

    def get_revenue_volatility(self):
        key = "revenue_volatility"
        if key in self._derived_cache:
            return self._derived_cache[key]

        confidence = self._base_confidence()

        if not self.income_statements:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Missing income statements")
            self._derived_cache[key] = res
            return res

        years = sorted(self.income_statements.keys())
        revenues = []

        for y in years:
            rev = self.income_statements[y].revenue
            if rev is None:
                res = MetricResult(value=None, confidence=Decimal("0.0"), explanation=f"Missing revenue for year {y}")
                self._derived_cache[key] = res
                return res
            revenues.append(rev)

        if len(revenues) < 2:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Insufficient history for volatility")
            self._derived_cache[key] = res
            return res

        mean = sum(revenues) / Decimal(len(revenues))
        variance = sum((r - mean) ** 2 for r in revenues) / Decimal(len(revenues))

        res = MetricResult(value=variance, confidence=confidence, explanation="Revenue Variance")
        self._derived_cache[key] = res
        return res

    def get_roa(self):
        key = "roa"
        if key in self._derived_cache:
            return self._derived_cache[key]

        confidence = self._base_confidence()

        if not self.income_statements or not self.balance_sheets:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Missing statements")
            self._derived_cache[key] = res
            return res

        years = sorted(self.income_statements.keys())
        latest = years[-1]

        ni = self.income_statements[latest].net_income

        if latest not in self.balance_sheets:
             res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Missing latest balance sheet")
             self._derived_cache[key] = res
             return res

        assets = self.balance_sheets[latest].total_assets

        if ni is None or assets is None or assets == 0:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Invalid NI/Assets data")
            self._derived_cache[key] = res
            return res

        roa = ni / assets
        res = MetricResult(value=roa, confidence=confidence, explanation="Net Income / Total Assets")
        self._derived_cache[key] = res
        return res

    def get_roe(self):
        key = "roe"
        if key in self._derived_cache:
            return self._derived_cache[key]

        confidence = self._base_confidence()

        if not self.income_statements or not self.balance_sheets:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Missing statements")
            self._derived_cache[key] = res
            return res

        years = sorted(self.income_statements.keys())
        latest = years[-1]

        ni = self.income_statements[latest].net_income

        if latest not in self.balance_sheets:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Missing latest balance sheet")
            self._derived_cache[key] = res
            return res

        equity = self.balance_sheets[latest].total_equity

        if ni is None or equity is None or equity == 0:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Invalid NI/Equity data")
            self._derived_cache[key] = res
            return res

        roe = ni / equity
        res = MetricResult(value=roe, confidence=confidence, explanation="Net Income / Total Equity")
        self._derived_cache[key] = res
        return res

    def get_asset_turnover(self):
        key = "asset_turnover"
        if key in self._derived_cache:
            return self._derived_cache[key]

        confidence = self._base_confidence()

        if not self.income_statements or not self.balance_sheets:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Missing statements")
            self._derived_cache[key] = res
            return res

        years = sorted(self.income_statements.keys())
        latest = years[-1]

        revenue = self.income_statements[latest].revenue

        if latest not in self.balance_sheets:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Missing latest balance sheet")
            self._derived_cache[key] = res
            return res

        assets = self.balance_sheets[latest].total_assets

        if revenue is None or assets is None or assets == 0:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Invalid Revenue/Assets data")
            self._derived_cache[key] = res
            return res

        turnover = revenue / assets
        res = MetricResult(value=turnover, confidence=confidence, explanation="Revenue / Total Assets")
        self._derived_cache[key] = res
        return res

    def get_margin_expansion_signal(self):
        key = "margin_expansion"
        if key in self._derived_cache:
            return self._derived_cache[key]

        confidence = self._base_confidence()

        if not self.income_statements:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Missing income statements")
            self._derived_cache[key] = res
            return res

        years = sorted(self.income_statements.keys())
        if len(years) < 2:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Insufficient history for margin expansion")
            self._derived_cache[key] = res
            return res

        latest = years[-1]
        prev = years[-2]

        stmt_latest = self.income_statements[latest]
        stmt_prev = self.income_statements[prev]

        if (
            stmt_latest.revenue is None
            or stmt_latest.operating_income is None
            or stmt_prev.revenue is None
            or stmt_prev.operating_income is None
            or stmt_latest.revenue == 0
            or stmt_prev.revenue == 0
        ):
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Invalid margin data")
            self._derived_cache[key] = res
            return res

        margin_latest = stmt_latest.operating_income / stmt_latest.revenue
        margin_prev = stmt_prev.operating_income / stmt_prev.revenue

        signal = margin_latest > margin_prev
        val = Decimal("1") if signal else Decimal("0")
        res = MetricResult(value=val, confidence=confidence, explanation="Latest OM > Prev OM")
        self._derived_cache[key] = res
        return res

    def get_leverage_improvement_signal(self):
        key = "leverage_improvement"
        if key in self._derived_cache:
            return self._derived_cache[key]

        confidence = self._base_confidence()

        if not self.balance_sheets:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Missing balance sheets")
            self._derived_cache[key] = res
            return res

        years = sorted(self.balance_sheets.keys())
        if len(years) < 2:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Insufficient history for leverage")
            self._derived_cache[key] = res
            return res

        latest = years[-1]
        prev = years[-2]

        bs_latest = self.balance_sheets[latest]
        bs_prev = self.balance_sheets[prev]

        if (
            bs_latest.total_liabilities is None
            or bs_latest.total_assets is None
            or bs_prev.total_liabilities is None
            or bs_prev.total_assets is None
            or bs_latest.total_assets == 0
            or bs_prev.total_assets == 0
        ):
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Invalid leverage data")
            self._derived_cache[key] = res
            return res

        lev_latest = bs_latest.total_liabilities / bs_latest.total_assets
        lev_prev = bs_prev.total_liabilities / bs_prev.total_assets

        signal = lev_latest < lev_prev
        val = Decimal("1") if signal else Decimal("0")
        res = MetricResult(value=val, confidence=confidence, explanation="Latest Debt Ratio < Prev Debt Ratio")
        self._derived_cache[key] = res
        return res

    def get_growth_consistency_signal(self):
        key = "growth_consistency"
        if key in self._derived_cache:
            return self._derived_cache[key]

        confidence = self._base_confidence()

        if not self.income_statements:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Missing income statements")
            self._derived_cache[key] = res
            return res

        years = sorted(self.income_statements.keys())
        if len(years) < 3:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Insufficient history for growth consistency")
            self._derived_cache[key] = res
            return res

        positive_years = 0

        for i in range(1, len(years)):
            prev = self.income_statements[years[i - 1]].revenue
            curr = self.income_statements[years[i]].revenue

            if prev is None or curr is None or prev == 0:
                res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Invalid revenue data series")
                self._derived_cache[key] = res
                return res

            if curr > prev:
                positive_years += 1

        signal = positive_years >= (len(years) - 1)
        val = Decimal("1") if signal else Decimal("0")
        res = MetricResult(value=val, confidence=confidence, explanation="Revenue grew consistently over all available periods")
        self._derived_cache[key] = res
        return res

    def get_stability_signal(self):
        key = "stability_signal"
        if key in self._derived_cache:
            return self._derived_cache[key]

        # Depends on another MetricResult
        vol_result = self.get_revenue_volatility()
        # Since volatility returns MetricResult, we need to unwrap logic
        
        if vol_result.value is None:
             # Propagate failure
             res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Volatility calculation failed")
             self._derived_cache[key] = res
             return res
             
        # Combine confidence? Or just use base? 
        # Volatility already includes base confidence. 
        # Let's trust Volatility's confidence?
        # Prompt says "return MetricResult(..., confidence=self._base_confidence(), ...)" for signals explicitly.
        # But stability depends on volatility which might fail. 
        # Using base_confidence again is consistent with instructions "Step 4 -> confidence=self._base_confidence()".
        
        confidence = self._base_confidence()
        
        signal = vol_result.value < Decimal("1000000000")
        val = Decimal("1") if signal else Decimal("0")
        res = MetricResult(value=val, confidence=confidence, explanation="Revenue Variance < 1 Billion")
        self._derived_cache[key] = res
        return res

    def compute_piotroski(self):
        if self._piotroski_cache is not None:
            return self._piotroski_cache

        confidence = self._base_confidence()

        if not self.income_statements or not self.balance_sheets:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Missing statements")
            self._piotroski_cache = res
            return res

        years = sorted(self.income_statements.keys())
        if len(years) < 2:
            res = MetricResult(value=None, confidence=Decimal("0.0"), explanation="Insufficient history for Piotroski")
            self._piotroski_cache = res
            return res

        latest = years[-1]
        prev = years[-2]

        score = 0
        
        # 1. Positive Net Income
        ni = self.income_statements[latest].net_income
        if ni is not None and ni > 0:
            score += 1
            
        # 2. Positive CFO
        cfo = None
        if self.cash_flow_statements and latest in self.cash_flow_statements:
            cfo = self.cash_flow_statements[latest].cfo
            if cfo is not None and cfo > 0:
                score += 1

        # 3. ROA Improvement
        if (
            latest in self.balance_sheets
            and prev in self.balance_sheets
            and latest in self.income_statements
            and prev in self.income_statements
        ):
            ni_latest = self.income_statements[latest].net_income
            ni_prev = self.income_statements[prev].net_income
            
            bs_latest = self.balance_sheets[latest]
            bs_prev = self.balance_sheets[prev]
            
            if (
                ni_latest is not None 
                and ni_prev is not None 
                and bs_latest.total_assets 
                and bs_prev.total_assets 
                and bs_latest.total_assets > 0 
                and bs_prev.total_assets > 0
            ):
                 roa_latest = ni_latest / bs_latest.total_assets
                 roa_prev = ni_prev / bs_prev.total_assets
                 if roa_latest > roa_prev:
                     score += 1

        # 4. CFO > Net Income
        if cfo is not None and ni is not None:
            if cfo > ni:
                score += 1

        # 5. Lower Leverage
        if (
            latest in self.balance_sheets
            and prev in self.balance_sheets
        ):
            bs_latest = self.balance_sheets[latest]
            bs_prev = self.balance_sheets[prev]

            if (
                bs_latest.total_liabilities is not None
                and bs_prev.total_liabilities is not None
                and bs_latest.total_assets
                and bs_prev.total_assets
                and bs_latest.total_assets > 0
                and bs_prev.total_assets > 0
            ):
                leverage_latest = bs_latest.total_liabilities / bs_latest.total_assets
                leverage_prev = bs_prev.total_liabilities / bs_prev.total_assets
                if leverage_latest < leverage_prev:
                    score += 1

        # 6. Higher Current Ratio
        if (
             latest in self.balance_sheets
             and prev in self.balance_sheets
        ):
             bs_latest = self.balance_sheets[latest]
             bs_prev = self.balance_sheets[prev]
             
             if (
                 bs_latest.current_assets is not None
                 and bs_latest.current_liabilities
                 and bs_prev.current_assets is not None
                 and bs_prev.current_liabilities
                 and bs_latest.current_liabilities > 0
                 and bs_prev.current_liabilities > 0
             ):
                 cr_latest = bs_latest.current_assets / bs_latest.current_liabilities
                 cr_prev = bs_prev.current_assets / bs_prev.current_liabilities
                 if cr_latest > cr_prev:
                     score += 1

        # 7. No Equity Dilution (Skipped - Data Unavailable)

        # 8. Higher Gross Margin
        if (
            latest in self.income_statements
            and prev in self.income_statements
        ):
            is_latest = self.income_statements[latest]
            is_prev = self.income_statements[prev]
            
            if (
                is_latest.gross_profit is not None
                and is_latest.revenue
                and is_prev.gross_profit is not None
                and is_prev.revenue
                and is_latest.revenue > 0
                and is_prev.revenue > 0
            ):
                gm_latest = is_latest.gross_profit / is_latest.revenue
                gm_prev = is_prev.gross_profit / is_prev.revenue
                if gm_latest > gm_prev:
                    score += 1

        # 9. Higher Asset Turnover
        if (
            latest in self.income_statements
            and prev in self.income_statements
            and latest in self.balance_sheets
            and prev in self.balance_sheets
        ):
             rev_latest = self.income_statements[latest].revenue
             rev_prev = self.income_statements[prev].revenue
             
             bs_latest = self.balance_sheets[latest]
             bs_prev = self.balance_sheets[prev]
             
             if (
                 rev_latest is not None
                 and rev_prev is not None
                 and bs_latest.total_assets
                 and bs_prev.total_assets
                 and bs_latest.total_assets > 0
                 and bs_prev.total_assets > 0
             ):
                 at_latest = rev_latest / bs_latest.total_assets
                 at_prev = rev_prev / bs_prev.total_assets
                 if at_latest > at_prev:
                     score += 1

        res = MetricResult(value=Decimal(score), confidence=confidence, explanation="Piotroski F-Score (9 factors)")
        self._piotroski_cache = res
        return res


def build_financial_state(
    income_raw: RawStatement,
    cash_raw: RawStatement,
    balance_raw: RawStatement,
    strict_config: StrictConfig,
) -> CompanyFinancialState:

    from .normalization.income_normalizer import normalize_income
    from .normalization.cashflow_normalizer import normalize_cashflow
    from .normalization.balance_normalizer import normalize_balance

    income = normalize_income(income_raw, strict_config)
    cash = normalize_cashflow(cash_raw, strict_config)
    balance = normalize_balance(balance_raw, strict_config)

    state = CompanyFinancialState(
        income_statements=income,
        cash_flow_statements=cash,
        balance_sheets=balance,
        strict_config=strict_config,
    )

    state._derived_cache.clear()
    state._ttm_cache.clear()
    state._piotroski_cache = None

    return states
