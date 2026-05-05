import pytest
from decimal import Decimal
from src.financial_engine.models.canonical_models import (
    IncomeStatement,
    BalanceSheet,
    CashFlowStatement,
)
from src.financial_engine.company_state import CompanyFinancialState, build_financial_state
from src.financial_engine.models.strict_config import StrictConfig
from src.financial_engine.models.raw_models import RawStatement
from src.financial_engine.models.metric_result import MetricResult

@pytest.fixture
def sample_state():
    # Mock data for 2023, 2024
    # 2023
    is_2023 = IncomeStatement(
        year=2023,
        revenue=Decimal("100.00"),
        cogs=Decimal("60.00"),
        gross_profit=Decimal("40.00"),
        operating_income=Decimal("20.00"),
        net_income=Decimal("15.00"),
    )
    bs_2023 = BalanceSheet(
        year=2023,
        total_assets=Decimal("200.00"),
        total_liabilities=Decimal("100.00"),
        total_equity=Decimal("100.00"),
        current_assets=Decimal("50.00"),
        current_liabilities=Decimal("25.00"),
        total_debt=Decimal("80.00"),
        cash=Decimal("10.00"),
    )
    # No CF for 2023 needed for most deltas, but good to have
    cf_2023 = CashFlowStatement(
        year=2023,
        cfo=Decimal("20.00"),
        cfi=Decimal("-10.00"),
        cff=Decimal("-5.00"),
        capex=Decimal("10.00"),
    )

    # 2024 (Growth in Rev, Improvement in Margins, etc for Piotroski)
    is_2024 = IncomeStatement(
        year=2024,
        revenue=Decimal("120.00"),
        cogs=Decimal("70.00"),
        gross_profit=Decimal("50.00"), # GM = 50/120 = 0.416 vs 40/100 = 0.40 -> Improvement
        operating_income=Decimal("30.00"), # OM = 30/120 = 0.25 vs 20/100 = 0.20
        net_income=Decimal("20.00"), # Positive NI
    )
    bs_2024 = BalanceSheet(
        year=2024,
        total_assets=Decimal("220.00"),
        total_liabilities=Decimal("105.00"), # Lev = 105/220 = 0.477 vs 100/200 = 0.50 -> Improvement (Lower)
        total_equity=Decimal("115.00"),
        current_assets=Decimal("60.00"),
        current_liabilities=Decimal("25.00"), # CR = 60/25 = 2.4 vs 50/25 = 2.0 -> Improvement
        total_debt=Decimal("80.00"),
        cash=Decimal("25.00"),
    )
    cf_2024 = CashFlowStatement(
        year=2024,
        cfo=Decimal("30.00"), # Positive CFO, CFO > NI (30 > 20)
        cfi=Decimal("-10.00"),
        cff=Decimal("-5.00"),
        capex=Decimal("12.00"),
    )

    state = CompanyFinancialState(
        income_statements={2023: is_2023, 2024: is_2024},
        balance_sheets={2023: bs_2023, 2024: bs_2024},
        cash_flow_statements={2023: cf_2023, 2024: cf_2024},
        strict_config=StrictConfig(
            strict_mode=True,
            require_full_core_rows=True,
            disable_fallback_matching=True,
            disable_section_summation=True,
            require_identity_validation=True,
        ),
    )
    return state

def test_profitability_metrics(sample_state):
    # Gross Margin 2024: 50/120 = 0.416666...
    gm = sample_state.get_gross_margin()
    assert isinstance(gm, MetricResult)
    assert gm.value == Decimal("50.00") / Decimal("120.00")
    assert gm.confidence >= Decimal("0")
    
    # Operating Margin 2024: 30/120 = 0.25
    om = sample_state.get_operating_margin()
    assert om.value == Decimal("0.25")

def test_leverage_metrics(sample_state):
    # Debt Ratio 2024: 105/220
    dr = sample_state.get_debt_ratio()
    assert dr.value == Decimal("105.00") / Decimal("220.00")

    # Current Ratio 2024: 60/25 = 2.4
    cr = sample_state.get_current_ratio()
    assert cr.value == Decimal("2.4")

def test_free_cash_flow(sample_state):
    # FCF 2024: CFO 30 - Capex 12 = 18
    fcf = sample_state.get_free_cash_flow()
    assert fcf.value == Decimal("18.00")

def test_cagr(sample_state):
    # Rev CAGR: (120/100)^(1/1) - 1 = 0.20
    cagr = sample_state.get_revenue_cagr()
    assert cagr.value == Decimal("0.20")

def test_volatility(sample_state):
    # Volatility of Revenue [100, 120]
    # Mean = 110
    # Variance = 100
    vol = sample_state.get_revenue_volatility()
    assert vol.value == Decimal("100")

def test_piotroski_score(sample_state):
    score = sample_state.compute_piotroski()
    assert score.value == Decimal("8")
    assert score.explanation == "Piotroski F-Score (9 factors)"

def test_missing_data(sample_state):
    # Clear cash flow to test graceful degradation
    sample_state.cash_flow_statements = None
    sample_state._derived_cache.clear()
    
    fcf = sample_state.get_free_cash_flow()
    assert fcf.value is None
    assert fcf.confidence == Decimal("0.0")
    
    sample_state._piotroski_cache = None
    score = sample_state.compute_piotroski()
    # Lost CFO points. Score 6.
    assert score.value == Decimal("6")

def test_caching(sample_state):
    gm1 = sample_state.get_gross_margin()
    gm2 = sample_state.get_gross_margin()
    assert gm1 is gm2 
    assert "gross_margin" in sample_state._derived_cache

def test_new_analytical_metrics(sample_state):
    # ROA
    roa = sample_state.get_roa()
    assert roa.value == Decimal("20.00") / Decimal("220.00")

    # ROE
    roe = sample_state.get_roe()
    assert roe.value == Decimal("20.00") / Decimal("115.00")

    # Asset Turnover
    at = sample_state.get_asset_turnover()
    assert at.value == Decimal("120.00") / Decimal("220.00")

def test_signals(sample_state):
    # Margin Expansion -> True -> 1
    sig = sample_state.get_margin_expansion_signal()
    assert sig.value == Decimal("1")
    assert "Latest OM > Prev OM" in sig.explanation

    # Leverage Improvement -> True -> 1
    sig = sample_state.get_leverage_improvement_signal()
    assert sig.value == Decimal("1")

    # Growth Consistency -> None
    sig = sample_state.get_growth_consistency_signal()
    assert sig.value is None
    
    # Stability -> True -> 1
    sig = sample_state.get_stability_signal()
    assert sig.value == Decimal("1")

def test_growth_consistency_logic():
    is_21 = IncomeStatement(year=2021, revenue=Decimal("10"), cogs=None, gross_profit=None, operating_income=None, net_income=None)
    is_22 = IncomeStatement(year=2022, revenue=Decimal("12"), cogs=None, gross_profit=None, operating_income=None, net_income=None)
    is_23 = IncomeStatement(year=2023, revenue=Decimal("15"), cogs=None, gross_profit=None, operating_income=None, net_income=None)
    
    state = CompanyFinancialState(
        income_statements={2021: is_21, 2022: is_22, 2023: is_23},
        balance_sheets=None,
        cash_flow_statements=None,
        strict_config=StrictConfig(strict_mode=True, require_full_core_rows=False, disable_fallback_matching=False, disable_section_summation=False, require_identity_validation=False),
    )
    
    sig = state.get_growth_consistency_signal()
    assert sig.value == Decimal("1")
    
    is_23_bad = IncomeStatement(year=2023, revenue=Decimal("11"), cogs=None, gross_profit=None, operating_income=None, net_income=None)
    state_bad = CompanyFinancialState(
        income_statements={2021: is_21, 2022: is_22, 2023: is_23_bad},
        balance_sheets=None,
        cash_flow_statements=None,
        strict_config=StrictConfig(strict_mode=True, require_full_core_rows=False, disable_fallback_matching=False, disable_section_summation=False, require_identity_validation=False),
    )
    sig_bad = state_bad.get_growth_consistency_signal()
    assert sig_bad.value == Decimal("0")
