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
        if passph: config['password'] = passph
        
        # Initialisation de l'échangeur via CCXT
        self.ex = getattr(ccxt, ex_id.lower())(config)
        self.is_running = False
        self.symbol = "BTC/USDT"
        self.amount_usdt = 10.0  # Mise de départ fixe pour accumuler le profit à côté
        self.logs = []
        self.pnl = 0.0

    def add_log(self, msg):
        log = f"[{time.strftime('%H:%M:%S')}] {msg}"
        print(log) # Log dans la console Termux
        self.logs.append(log)
        if len(self.logs) > 30: self.logs.pop(0)

    def analyze_and_trade(self):
        """ BOUCLE DE TRADING AUTOMATIQUE SMC/CRT """
        self.add_log(f"🚀 Bouclier activé sur {self.symbol}")
        
        while self.is_running:
            try:
                # Analyse sur 1h et 15m pour la précision Sniper
                for tf in ['1h', '15m']:
                    ohlcv = self.ex.fetch_ohlcv(self.symbol, timeframe=tf, limit=5)
                    df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
                    
                    # Définition des bougies B1 (Range) et B2 (Sweep)
                    b1_h, b1_l = df['h'].iloc[-3], df['l'].iloc[-3]
                    b2_h, b2_l, b2_c = df['h'].iloc[-2], df['l'].iloc[-2], df['c'].iloc[-2]

                    side = None
                    # LOGIQUE CRT : SWEEP + RÉINTÉGRATION
                    if b2_h > b1_h and b2_c < b1_h: side = 'sell' # Short
                    if b2_l < b1_l and b2_c > b1_l: side = 'buy'  # Long

                    if side:
                        self.add_log(f"🎯 SIGNAL {side.upper()} DÉTECTÉ ({tf})")
                        
                        # Prix actuel pour calculer la taille de la position
                        ticker = self.ex.fetch_ticker(self.symbol)
                        price = ticker['last']
                        amount_crypto = self.amount_usdt / price
                        
                        # EXECUTION DE L'ORDRE RÉEL
                        self.ex.create_market_order(self.symbol, side, amount_crypto)
                        self.add_log(f"✅ ORDRE PLACÉ : {self.amount_usdt}$ utilisé. Profits accumulés.")
                        
                        # Pause de sécurité après trade (10 min)
                        time.sleep(600) 
                
                time.sleep(30) # Scan toutes les 30 secondes
            except Exception as e:
                self.add_log(f"⚠️ Erreur Marché : {str(e)}")
                time.sleep(15)

# Instance globale du moteur
engine = None

@app.route('/toggle_bot', methods=['POST'])
def toggle_bot():
    global engine
    data = request.json
    
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

@app.route('/get_status', methods=['GET'])
def get_status():
    if engine:
        return jsonify({
            "logs": engine.logs, 
            "pnl": engine.pnl, 
            "running": engine.is_running
        })
    return jsonify({"logs": ["En attente de lancement..."], "pnl": 0, "running": False})

if __name__ == '__main__':
    # Lancement du serveur sur le port 5000
    app.run(host='0.0.0.0', port=5000)
            
