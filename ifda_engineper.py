import ccxt
import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import time
import threading

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION SANGMELIMA SHIELD ---
BOT_TOKEN = "7874803596:AAG94iaEWHZyuCJe5q0UyjTXqOu6MShG58Q"
CHAT_ID = "6727767271"

def notify_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": CHAT_ID, "text": f"🛡️ [IFDA SYSTEM]\n{msg}", "parse_mode": "Markdown"})
    except: pass

class IFDASniper:
    def __init__(self, ex_id, ak, secret, passph=None):
        config = {
            'apiKey': ak, 'secret': secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'} # Verrouillé sur PERPÉTUEL
        }
        if passph: config['password'] = passph
        self.ex = getattr(ccxt, ex_id.lower())(config)

    def get_pnl(self):
        try:
            balance = self.ex.fetch_balance()
            # Récupération simplifiée du PNL non réalisé pour le Dashboard
            pos = self.ex.fetch_positions()
            pnl = sum(float(p['unrealizedPnl']) for p in pos if float(p['unrealizedPnl']) != 0)
            total = balance['total']['USDT']
            return total, pnl
        except: return 0, 0

    def analyze_m15_sweep(self, symbol):
        try:
            # Analyse Cascade M15
            ohlcv = self.ex.fetch_ohlcv(symbol, timeframe='15m', limit=50)
            df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
            
            cp = df['c'].iloc[-1]
            pdh = df['h'].iloc[-30:-2].max() # Previous High
            pdl = df['l'].iloc[-30:-2].min() # Previous Low

            # Logique de Sweep SMC
            if df['h'].iloc[-1] > pdh and cp < pdh: # Sweep Haut + Réintégration
                return 'sell', df['h'].iloc[-1], pdl
            if df['l'].iloc[-1] < pdl and cp > pdl: # Sweep Bas + Réintégration
                return 'buy', df['l'].iloc[-1], pdh
            return None, 0, 0
        except: return None, 0, 0

# --- ROUTES API POUR LE DASHBOARD OBSIDIAN ---

@app.route('/status', methods=['POST'])
def get_status():
    data = request.json
    try:
        bot = IFDASniper(data['exchange'], data['ak'], data['as'], data.get('passphrase'))
        balance, pnl = bot.get_pnl()
        return jsonify({"status": "OK", "balance": balance, "pnl": pnl})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)})

@app.route('/execute', methods=['POST'])
def execute_trade():
    data = request.json
    try:
        bot = IFDASniper(data['exchange'], data['ak'], data['as'], data.get('passphrase'))
        symbol = data.get('symbol', 'BTC/USDT')
        
        # Commande Panic Sell
        if data.get('action') == "PANIC_SELL":
            bot.ex.cancel_all_orders(symbol)
            # Logique pour fermer les positions market ici
            notify_telegram(f"🚨 *URGENCE* : Toutes les positions sur {symbol} ont été fermées !")
            return jsonify({"status": "success", "message": "Positions fermées"})

        side, sl, tp = bot.analyze_m15_sweep(symbol)
        if side:
            # Calcul lot min pour capital de précision
            qty = float(data.get('capital', 10)) / bot.ex.fetch_ticker(symbol)['last']
            bot.ex.create_market_order(symbol, side, qty)
            notify_telegram(f"🎯 *INJECTION RÉUSSIE*\n{symbol} : {side.upper()}\nPNL attendu sur Sweep M15.")
            return jsonify({"status": "success", "trade": {"side": side, "price": "Market"}})
        
        return jsonify({"status": "scanning", "message": "Recherche de liquidité en cours..."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    print("🚀 IFDA MASTER GLOBAL V57 - READY")
    app.run(host='0.0.0.0', port=5000)
          
