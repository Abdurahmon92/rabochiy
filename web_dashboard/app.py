# ============================================================
#  IBKR Trading Bot — Flask Web Dashboard
#  Asosiy ilova fayli
# ============================================================

from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_socketio import SocketIO, emit
import pandas as pd
import os, json, random, threading, time
from datetime import datetime, timedelta
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# ============================================================
#  Demo ma'lumotlar (IBKR ulanmagan holda)
# ============================================================

def get_demo_stats():
    """Dashboard uchun demo statistika"""
    return {
        'account_value':   round(10000 + random.uniform(-200, 500), 2),
        'daily_pnl':       round(random.uniform(-150, 350), 2),
        'daily_pnl_pct':   round(random.uniform(-1.5, 3.5), 2),
        'total_trades':    random.randint(3, 12),
        'win_trades':      random.randint(2, 8),
        'loss_trades':     random.randint(1, 4),
        'open_positions':  random.randint(0, 3),
        'bot_status':      'running',
        'last_scan':       datetime.now().strftime('%H:%M:%S'),
        'win_rate':        round(random.uniform(55, 75), 1),
    }

def get_demo_positions():
    """Demo ochiq pozitsiyalar"""
    stocks = ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'AMD']
    positions = []
    for i in range(random.randint(1, 3)):
        symbol  = stocks[i]
        entry   = round(random.uniform(100, 500), 2)
        current = round(entry * (1 + random.uniform(-0.03, 0.05)), 2)
        qty     = random.randint(5, 50)
        pnl     = round((current - entry) * qty, 2)
        positions.append({
            'symbol':        symbol,
            'qty':           qty,
            'entry':         entry,
            'current':       current,
            'pnl':           pnl,
            'pnl_pct':       round((current - entry) / entry * 100, 2),
            'stop':          round(entry * 0.98, 2),
            'target':        round(entry * 1.04, 2),
            'partial_done':  random.choice([True, False]),
            'time_opened':   (datetime.now() - timedelta(minutes=random.randint(10,120))).strftime('%H:%M'),
        })
    return positions

def get_demo_trades():
    """Demo savdo tarixi"""
    symbols  = ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'AMD', 'META', 'GOOG', 'AMZN']
    actions  = ['BUY', 'SELL', 'PARTIAL_SELL']
    reasons  = [
        'EMA kesishdi, RSI normal',
        'MACD kesishdi (yuqoriga)',
        'EMA trend yuqori, Volume kuchli',
        'TAKE_PROFIT',
        'STOP_LOSS',
        '50% yopildi | PnL: $120.00',
    ]
    trades = []
    for i in range(20):
        action = random.choice(actions)
        entry  = round(random.uniform(50, 600), 2)
        trades.append({
            'time':   (datetime.now() - timedelta(minutes=i*15)).strftime('%Y-%m-%d %H:%M'),
            'action': action,
            'symbol': random.choice(symbols),
            'qty':    random.randint(5, 50),
            'price':  entry,
            'sl':     round(entry * 0.98, 2),
            'tp':     round(entry * 1.04, 2),
            'reason': random.choice(reasons),
            'pnl':    round(random.uniform(-200, 400), 2) if action == 'SELL' else None,
        })
    return trades

def get_demo_chart_data(symbol='AAPL'):
    """Demo grafik ma'lumotlari"""
    prices = []
    base   = 180.0
    now    = datetime.now()
    for i in range(50):
        t     = now - timedelta(minutes=(50 - i) * 5)
        base += random.uniform(-2, 2)
        prices.append({
            'time':  t.strftime('%H:%M'),
            'open':  round(base, 2),
            'high':  round(base + random.uniform(0, 1.5), 2),
            'low':   round(base - random.uniform(0, 1.5), 2),
            'close': round(base + random.uniform(-1, 1), 2),
            'vol':   random.randint(100000, 500000),
            'ema9':  round(base + random.uniform(-0.5, 0.5), 2),
            'ema21': round(base - random.uniform(0, 1), 2),
        })
    return prices

def read_trade_log():
    """trades.csv dan o'qish"""
    log_path = app.config['TRADE_LOG']
    if os.path.exists(log_path):
        try:
            df = pd.read_csv(log_path)
            return df.to_dict('records')
        except Exception:
            pass
    return get_demo_trades()

def read_bot_log(lines=50):
    """trading_bot.log dan oxirgi N qatorni o'qish"""
    log_path = app.config['BOT_LOG']
    if os.path.exists(log_path):
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
            return [l.strip() for l in all_lines[-lines:]]
        except Exception:
            pass
    # Demo log
    demo_logs = [
        f"[{(datetime.now()-timedelta(minutes=i)).strftime('%H:%M:%S')}] "
        + random.choice([
            "✅ AAPL BUY signal | Kuch: 75",
            "🔍 Finviz skaneri ishlamoqda...",
            "📈 NVDA EMA kesishdi (yuqoriga)",
            "✂️  TSLA 50% yopildi | PnL: $145.00",
            "📐 Pozitsiya hajmi: 20 ta aksiya",
            "🔄 Yangi tsikl: " + datetime.now().strftime('%H:%M:%S'),
            "⏸️  MSFT HOLD | BUY:45 SELL:30",
        ])
        for i in range(lines)
    ]
    return demo_logs

# ============================================================
#  Sozlamalar (xotirada saqlash)
# ============================================================

current_settings = {
    'account_size':   app.config['ACCOUNT_SIZE'],
    'risk_percent':   app.config['RISK_PERCENT'],
    'reward_ratio':   app.config['REWARD_RATIO'],
    'partial_close':  app.config['PARTIAL_CLOSE'],
    'trailing_stop':  app.config['TRAILING_STOP'],
    'max_positions':  app.config['MAX_POSITIONS'],
    'max_daily_loss': app.config['MAX_DAILY_LOSS'],
    'scan_interval':  app.config['SCAN_INTERVAL'],
    'ibkr_host':      app.config['IBKR_HOST'],
    'ibkr_port':      app.config['IBKR_PORT'],
}

bot_state = {
    'running':    False,
    'start_time': None,
    'mode':       'paper',   # paper | live
}

# ============================================================
#  HTML Sahifalar
# ============================================================

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    stats     = get_demo_stats()
    positions = get_demo_positions()
    logs      = read_bot_log(20)
    return render_template('dashboard.html',
        stats=stats,
        positions=positions,
        logs=logs,
        bot_state=bot_state,
        active='dashboard'
    )

@app.route('/trades')
def trades():
    trade_list = read_trade_log()
    return render_template('trades.html',
        trades=trade_list,
        active='trades'
    )

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    global current_settings
    if request.method == 'POST':
        current_settings['account_size']   = float(request.form.get('account_size',   10000))
        current_settings['risk_percent']   = float(request.form.get('risk_percent',   1.5))
        current_settings['reward_ratio']   = float(request.form.get('reward_ratio',   2.0))
        current_settings['partial_close']  = int(request.form.get('partial_close',    50))
        current_settings['trailing_stop']  = float(request.form.get('trailing_stop',  1.0))
        current_settings['max_positions']  = int(request.form.get('max_positions',    5))
        current_settings['max_daily_loss'] = float(request.form.get('max_daily_loss', 3.0))
        current_settings['scan_interval']  = int(request.form.get('scan_interval',    300))
        current_settings['ibkr_port']      = int(request.form.get('ibkr_port',        7497))
        flash('✅ Sozlamalar saqlandi!', 'success')
        return redirect(url_for('settings'))
    return render_template('settings.html',
        settings=current_settings,
        active='settings'
    )

@app.route('/chart')
def chart():
    symbol     = request.args.get('symbol', 'AAPL')
    chart_data = get_demo_chart_data(symbol)
    return render_template('chart.html',
        symbol=symbol,
        chart_data=json.dumps(chart_data),
        active='chart'
    )

# ============================================================
#  API Endpoints (JavaScript uchun)
# ============================================================

@app.route('/api/stats')
def api_stats():
    return jsonify(get_demo_stats())

@app.route('/api/positions')
def api_positions():
    return jsonify(get_demo_positions())

@app.route('/api/trades')
def api_trades():
    return jsonify(read_trade_log()[:50])

@app.route('/api/logs')
def api_logs():
    return jsonify({'logs': read_bot_log(30)})

@app.route('/api/chart/<symbol>')
def api_chart(symbol):
    return jsonify(get_demo_chart_data(symbol.upper()))

@app.route('/api/bot/start', methods=['POST'])
def bot_start():
    global bot_state
    bot_state['running']    = True
    bot_state['start_time'] = datetime.now().strftime('%H:%M:%S')
    socketio.emit('bot_status', {'status': 'running'})
    return jsonify({'success': True, 'message': '🚀 Bot ishga tushdi!'})

@app.route('/api/bot/stop', methods=['POST'])
def bot_stop():
    global bot_state
    bot_state['running']    = False
    bot_state['start_time'] = None
    socketio.emit('bot_status', {'status': 'stopped'})
    return jsonify({'success': True, 'message': '🔴 Bot to\'xtatildi!'})

@app.route('/api/bot/status')
def bot_status():
    return jsonify(bot_state)

# ============================================================
#  SocketIO — Real-time yangilanish
# ============================================================

def background_updater():
    """Har 5 sekundda frontend ga yangi ma'lumot yuborish"""
    while True:
        socketio.sleep(5)
        socketio.emit('stats_update',    get_demo_stats())
        socketio.emit('position_update', get_demo_positions())
        new_log = read_bot_log(1)
        if new_log:
            socketio.emit('new_log', {'line': new_log[-1]})

@socketio.on('connect')
def on_connect():
    emit('bot_status', {'status': 'running' if bot_state['running'] else 'stopped'})
    socketio.start_background_task(background_updater)

# ============================================================
#  Ishga tushirish
# ============================================================

if __name__ == '__main__':
    print("=" * 55)
    print("  🤖 IBKR Trading Bot — Web Dashboard")
    print("=" * 55)
    print(f"  🌐 Manzil: http://localhost:{app.config['PORT']}")
    print(f"  🔧 Debug:  {app.config['DEBUG']}")
    print("=" * 55)
    socketio.run(app,
        host=app.config['HOST'],
        port=app.config['PORT'],
        debug=app.config['DEBUG']
    )
