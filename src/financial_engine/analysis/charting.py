import plotly.graph_objects as go


def generate_revenue_chart(state):
    if not state.income_statements:
        return None

    years = sorted(state.income_statements.keys())
    revenues = [state.income_statements[y].revenue for y in years]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=years, y=revenues, mode="lines+markers"))
    fig.update_layout(
        title="Revenue Trend",
        xaxis_title="Year",
        yaxis_title="Revenue",
    )

    return fig
