"""Interactive Shiny port of the MATLAB Case 1 trading simulation."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from shiny import App, reactive, render, ui
import model

TRADE_COUNTS = (1, 2, 3, 5, 10, 20, 50, 100)


app_ui = ui.page_fluid(
    ui.tags.style('''
        body { background: #f7f9fc; color: #1f2937; }
        .container-fluid { max-width: 1200px; }
        h2 { margin: 18px 0 4px; }
        .subtitle { color: #64748b; margin-bottom: 18px; }
        .card { margin-bottom: 6px; border-color: #dce3ec; }
        bslib-layout-columns { margin-bottom: 6px !important; }
        bslib-layout-columns .card { margin-bottom: 0; }
        .card-header { font-weight: 650; background: white; }
        .controls-card .card-body { padding: 12px; }
        .controls { display:grid; grid-template-columns:repeat(7, minmax(0, 1fr)); gap:12px; align-items:end; }
        .controls > * { min-width:0; }
        .controls .form-group { margin-bottom:0; }
        .controls .control-label { margin-bottom:3px; }
        .controls .btn { margin:0; width:100%; height:38px; }
        .trade-slider .form-group { width:100%; }
        .trade-slider .irs-single, .trade-slider .irs-min, .trade-slider .irs-max { display:none; }
        .trade-slider .shiny-text-output { display:inline; }
        .trade-slider .irs--shiny { height:20px; }
        .trade-slider .irs--shiny .irs-line, .trade-slider .irs--shiny .irs-bar { top:6px; }
        .trade-slider .irs--shiny .irs-handle { top:2px; width:16px; height:16px; }
        .direction { font-weight:600; padding-bottom:8px; }
        #message:empty { display:none; }
        @media (max-width: 900px) { .controls { grid-template-columns:repeat(3, minmax(0, 1fr)); } }
        @media (max-width: 560px) { .controls { grid-template-columns:repeat(2, minmax(0, 1fr)); } }
        table { width:100%; font-size:88%; font-variant-numeric:tabular-nums; }
        th, td { padding:5px 8px; text-align:right; border-bottom:1px solid #edf0f4; }
        th:first-child, td:first-child { text-align:left; }
        .notice { color:#9a3412; }
    '''),
    ui.h2('Trading simulation — Case 1'),
    ui.p('Choose an asset, price and quantity, then execute trades between Mario and Hue.', class_='subtitle'),
    ui.layout_columns(
        ui.card(ui.card_header('Portfolios'), ui.output_ui('holdings_table')),
        ui.card(ui.card_header('Consumption'), ui.output_ui('consumption_table')),
        ui.card(ui.card_header('Reservation prices'), ui.output_ui('prices_table')),
        col_widths=[4, 4, 4], gap='6px',
    ),
    ui.card(ui.card_body(ui.div(
        ui.input_select('asset', 'Asset', {str(i): name for i, name in enumerate(model.ASSETS)}, selected='2'),
        ui.input_text('price', 'Trade price', '0.000'),
        ui.input_text('amount', 'Traded amount', '0.000'),
        ui.div(ui.output_text('direction'), class_='direction'),
        ui.div(ui.input_slider('trade_count', ui.span('Trades: ', ui.output_text('trade_count_label', inline=True)), min=0, max=7, value=0, step=1), class_='trade-slider'),
        ui.input_action_button('trade', 'Execute trade', class_='btn-primary'),
        ui.input_action_button('reset', 'Reset'),
        class_='controls',
    ), ui.output_text('message')), class_='controls-card'),
    ui.layout_columns(
        ui.card(ui.card_header('Total utility of the investors'), ui.output_plot('history_plot', height='320px')),
        ui.card(ui.card_header('Supply and demand'), ui.output_plot('supply_plot', height='320px')),
        ui.card(ui.card_header('Mario: total utility'), ui.output_plot('mario_plot', height='320px')),
        ui.card(ui.card_header('Hue: total utility'), ui.output_plot('hue_plot', height='320px')),
        col_widths=[6, 6, 6, 6], gap='6px',
    ),
    title='Trading simulation',
)


def table(data, headings, decimals):
    return ui.tags.table(
        ui.tags.thead(ui.tags.tr(ui.tags.th('Investor'), *[ui.tags.th(x) for x in headings])),
        ui.tags.tbody(*[ui.tags.tr(ui.tags.td(model.INVESTORS[i]), *[ui.tags.td(f'{v:.{decimals}f}') for v in row]) for i, row in enumerate(data)]),
    )


def parse_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def server(input, output, session):
    holdings = reactive.value(model.INITIAL.copy())
    history = reactive.value([model.total_utility(model.consumption(model.INITIAL))])
    current = reactive.value(None)
    message_value = reactive.value('')

    def trade_inputs():
        price_text, amount_text = input.price(), input.amount()
        price, amount = parse_number(price_text), parse_number(amount_text)
        suggestion = current.get()
        # Display suggestions rounded, but preserve MATLAB's full precision until edited.
        if suggestion is not None:
            if price_text == f'{suggestion.price:.3f}':
                price = suggestion.price
            if amount_text == f'{suggestion.amount:.3f}':
                amount = suggestion.amount
        return price, amount

    def set_curves(h, asset, automatic_quantity=None):
        cons = model.consumption(h)
        result = model.curves(cons, model.reservation_prices(cons), asset, automatic_quantity)
        current.set(result)
        ui.update_text('price', value=f'{result.price:.3f}')
        ui.update_text('amount', value=f'{result.amount:.3f}')

    @reactive.effect
    @reactive.event(input.asset, ignore_init=False)
    def asset_changed():
        with reactive.isolate():
            asset = int(input.asset())
            if current.get() is None or current.get().asset != asset:
                set_curves(holdings.get(), asset)
                message_value.set('')

    @reactive.effect
    @reactive.event(input.trade)
    def trade():
        result = current.get()
        if result is None:
            return
        price, amount = trade_inputs()
        if price is None or amount is None or price < 0 or amount < 0:
            message_value.set('Enter a non-negative price and quantity using a decimal point.')
            return
        count = TRADE_COUNTS[int(input.trade_count())]
        new, added_history, next_suggestion, reason = model.execute_sequence(
            holdings.get(), result, price, amount, count
        )
        if added_history:
            holdings.set(new)
            history.set(history.get() + added_history)
            current.set(next_suggestion)
            ui.update_text('price', value=f'{next_suggestion.price:.3f}')
            ui.update_text('amount', value=f'{next_suggestion.amount:.3f}')
            ui.update_select('asset', selected=str(next_suggestion.asset))
        if reason:
            message_value.set(f'Completed {len(added_history)} of {count} trades. {reason}')
        else:
            message_value.set('')

    @reactive.effect
    @reactive.event(input.reset)
    def reset():
        h = model.INITIAL.copy()
        holdings.set(h)
        history.set([model.total_utility(model.consumption(h))])
        set_curves(h, 2)
        ui.update_select('asset', selected='2')
        message_value.set('')

    @render.ui
    def holdings_table():
        return table(holdings.get(), ('Consume', *model.ASSETS), 2)

    @render.ui
    def consumption_table():
        return table(model.consumption(holdings.get()), ('Now', 'BadS', 'BadN', 'GoodS', 'GoodN'), 2)

    @render.ui
    def prices_table():
        return table(model.reservation_prices(model.consumption(holdings.get())), model.ASSETS, 3)

    @render.text
    def trade_count_label():
        return str(TRADE_COUNTS[int(input.trade_count())])

    @render.text
    def direction():
        c = current.get()
        if c is None or c.direction == 0:
            return 'No trade direction'
        return 'Mario buys from Hue' if c.direction > 0 else 'Hue buys from Mario'

    @render.text
    def message():
        return message_value.get()

    @render.plot
    def history_plot():
        vals = np.asarray(history.get())
        fig, ax = plt.subplots(figsize=(6, 3.1), layout='constrained')
        other = ax.twinx()
        ax.plot(np.arange(len(vals)), vals[:, 0], '-o', color='tab:blue', markersize=3)
        other.plot(np.arange(len(vals)), vals[:, 1], '-o', color='tab:orange', markersize=3)
        ax.set(xlabel='Number of trades', ylabel='Mario', xlim=(0, max(10, len(vals) - 1)))
        other.set_ylabel('Hue')
        ax.yaxis.label.set_color('tab:blue')
        ax.tick_params(axis='y', colors='tab:blue')
        other.yaxis.label.set_color('tab:orange')
        other.tick_params(axis='y', colors='tab:orange')
        ax.grid(True, alpha=.3)
        return fig

    @render.plot
    def supply_plot():
        c = current.get()
        fig, ax = plt.subplots(figsize=(6, 3.1), layout='constrained')
        if c is None:
            return fig
        labels = ('Mario demand', 'Mario supply', 'Hue supply', 'Hue demand') if c.direction >= 0 else ('Mario supply', 'Mario demand', 'Hue demand', 'Hue supply')
        for line, label, color, style in zip(c.lines, labels, ('tab:blue', 'tab:blue', 'tab:orange', 'tab:orange'), ('-', '--', '-', '--')):
            ax.plot(line, c.pvec, style, color=color, linewidth=2, label=label)
        price, amount = trade_inputs()
        if price is not None and amount is not None:
            ax.axhline(price, color='black', linestyle=':', linewidth=1)
            ax.plot(amount, price, 'xk', markersize=8)
        ax.set(xlabel='Number of shares', ylabel='Price per share', xlim=(0, c.dh[-1]), ylim=(c.pvec[0], c.pvec[-1]))
        ax.legend(fontsize=7, ncol=2, loc='lower center')
        return fig

    def investor_plot(inv):
        c = current.get()
        fig, ax = plt.subplots(figsize=(6, 3.1), layout='constrained')
        price, amount = trade_inputs()
        if c is None or price is None or amount is None:
            return fig
        cons = model.consumption(holdings.get())
        dh = np.linspace(-1.5 * c.dh[-1] / 2.5, 1.5 * c.dh[-1] / 2.5, model.GRID)
        values = model.utility(cons[inv, 0] - price * dh, model.RISK[inv])
        for s in range(4):
            values += model.DELTA[inv] * model.PROB[s] * model.utility(cons[inv, s + 1] + dh * model.PAYOFF[s, c.asset], model.RISK[inv])
        finite_values = np.where(np.isfinite(values), values, -np.inf)
        ix = int(np.argmax(finite_values))
        sl = slice(350, 1001) if ix > 500 else slice(0, 650) if ix < 500 else slice(250, 750)
        ax.plot(dh[sl], values[sl], color=('tab:blue', 'tab:orange')[inv], linewidth=2)
        base = model.total_utility(cons)[inv]
        direction = c.direction if inv == 0 else -c.direction
        traded = model.proposed_utilities(cons, c.asset, c.direction, price, amount)[inv]
        ax.axhline(base, color='black', linestyle='--', linewidth=1)
        ax.axvline(0, color='black', linestyle='--', linewidth=1)
        ax.plot(direction * amount, traded, 'xk', markersize=8)
        ax.set(xlabel=f'Change in {model.ASSETS[c.asset]} holdings', ylabel=f'Total utility of {model.INVESTORS[inv]}')
        ax.tick_params(axis='y', labelleft=False)
        return fig

    @render.plot
    def mario_plot():
        return investor_plot(0)

    @render.plot
    def hue_plot():
        return investor_plot(1)


app = App(app_ui, server)
