import ccxt
import pandas as pd
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading

app = Flask(__name__)
CORS(app)

class BlackSniperEngine:
    def __init__(self, ex_id, ak, secret, passph=None):
        config = {
            'apiKey': ak, 
            'secret': secret, 
            'enableRateLimit': True, 
            'options': {'defaultType': 'swap'}
        }
        if passph and passph.strip() != "": 
            config['password'] = passph
            
        # Initialisation dynamique de l'échangeur
        self.ex = getattr(ccxt, ex_id.lower())(config)
        self.is_running = False
        self.symbol = "BTC/USDT"
        self.amount_usdt = 10.0
        self.logs = []
        self.pnl = 0.0

    def add_log(self, msg):
        log = f"[{time.strftime('%H:%M:%S')}] {msg}"
        self.logs.append(log)
        if len(self.logs) > 30: self.logs.pop(0)

    def analyze_and_trade(self):
        self.add_log(f"🚀 Bouclier SANGMELIMA activé sur {self.symbol}")
        while self.is_running:
            try:
                for tf in ['1h', '15m']:
                    ohlcv = self.ex.fetch_ohlcv(self.symbol, timeframe=tf, limit=5)
                    df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
                    b1_h, b1_l = df['h'].iloc[-3], df['l'].iloc[-3]
                    b2_h, b2_l, b2_c = df['h'].iloc[-2], df['l'].iloc[-2], df['c'].iloc[-2]

                    side = None
                    if b2_h > b1_h and b2_c < b1_h: side = 'sell'
                    if b2_l < b1_l and b2_c > b1_l: side = 'buy'

                    if side:
                        price = self.ex.fetch_ticker(self.symbol)['last']
                        amount_crypto = self.amount_usdt / price
                        self.ex.create_market_order(self.symbol, side, amount_crypto)
                        self.add_log(f"🎯 ORDRE {side.upper()} EXÉCUTÉ ({self.amount_usdt} USDT)")
                        time.sleep(600) 
                time.sleep(30)
            except Exception as e:
                self.add_log(f"⚠️ Erreur : {str(e)}")
                time.sleep(10)

engine = None

@app.route('/toggle_bot', methods=['POST', 'OPTIONS'])
def toggle_bot():
    if request.method == 'OPTIONS': return jsonify({"status": "ok"})
    global engine
    data = request.json
    try:
        if not engine:
            engine = BlackSniperEngine(data['exchange'], data['ak'], data['as'], data.get('passphrase'))
        
        if data.get('action') == 'start':
            engine.amount_usdt = float(data.get('qty', 10))
            engine.is_running = True
            threading.Thread(target=engine.analyze_and_trade).start()
            return jsonify({"status": "RUNNING"})
        else:
            engine.is_running = False
            return jsonify({"status": "STOPPED"})
    except Exception as e:
        return jsonify({"status": "ERROR", "msg": str(e)}), 400

@app.route('/get_status', methods=['GET'])
def get_status():
    if engine:
        return jsonify({"logs": engine.logs, "pnl": engine.pnl, "running": engine.is_running})
    return jsonify({"logs": ["Système en attente..."], "pnl": 0, "running": False})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
        
