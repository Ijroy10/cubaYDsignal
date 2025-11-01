import json
import os
from datetime import datetime
import pandas as pd

# Guardar la señal en un historial local
def guardar_senal_historial(direccion, efectividad):
    historial_path = os.path.join('data', 'historial_senales.json')
    nueva_senal = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'tipo': 'CALL' if direccion == 'alcista' else 'PUT',
        'efectividad_promedio': efectividad
    }

    try:
        with open(historial_path, 'r', encoding='utf-8') as f:
            historial = json.load(f)
    except FileNotFoundError:
        historial = []

    historial.append(nueva_senal)

    with open(historial_path, 'w', encoding='utf-8') as f:
        json.dump(historial, f, indent=4)

    print(f"✅ Señal guardada correctamente: {nueva_senal['tipo']} con {efectividad:.2f}%")

# Enviar señal por consola
def enviar_senal(direccion, efectividad):
    tipo_senal = 'CALL' if direccion == 'alcista' else 'PUT'
    print(f"\n📢 Señal generada: {tipo_senal} ({efectividad:.2f}%)")
    guardar_senal_historial(direccion, efectividad)

# -------------------------------
# Análisis completo de estrategias
# -------------------------------
from strategy.evaluar_estrategia_completa import evaluar_estrategia_completa

if __name__ == '__main__':
    # Simulación de velas para test
    df = pd.DataFrame({
        'open': [100, 103, 107, 105, 110],
        'high': [105, 110, 112, 108, 114],
        'low': [98, 101, 104, 103, 107],
        'close': [104, 108, 109, 107, 113],
        'volume': [1200, 1500, 1400, 1300, 1600]
    })
    mercado = 'EUR/USD'

    resultado = evaluar_estrategia_completa(df, mercado)

    if resultado['decision']:
        enviar_senal('alcista' if resultado['decision'] == 'CALL' else 'bajista', resultado['efectividad_total'])
    else:
        print("⚠️ No se generó señal. Efectividad insuficiente.")