
import datetime
import random

# Simulador de datos históricos (esto se reemplaza luego por datos reales)
def cargar_datos_historicos(dias=7):
    hoy = datetime.date.today()
    datos = {}
    for i in range(dias):
        dia = hoy - datetime.timedelta(days=i)
        datos[str(dia)] = {
            "señales_totales": random.randint(8, 15),
            "aciertos": random.randint(5, 14),
        }
    return datos

# Genera un resumen del backtest
def resumen_backtest(dias=7):
    datos = cargar_datos_historicos(dias)
    resumen = "📈 Backtest últimos {} días:\n".format(dias)
    for fecha, valores in sorted(datos.items(), reverse=True):
        efectividad = round((valores["aciertos"] / valores["señales_totales"]) * 100)
        resumen += "- {}: {}% de efectividad\n".format(fecha, efectividad)
    return resumen

# Si se ejecuta directamente
if __name__ == "__main__":
    print(resumen_backtest(7))
