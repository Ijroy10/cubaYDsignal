import pytest 
from strategy.calculo_velas_patrones.clasificar_senal_patron import clasificar_senal
from strategy.calculo_velas_patrones.detectar_patrones import detectar_patrones
from strategy.calculo_velas_patrones.evaluar_patrones import evaluar_patron

def test_clasificar_senal_call():
    patron = "martillo"
    tendencia = "alcista"
    resultado = clasificar_senal(patron, tendencia)
    assert resultado == "CALL"

def test_clasificar_senal_sell():
    patron = "envolvente bajista"
    tendencia = "bajista"
    resultado = clasificar_senal(patron, tendencia)
    assert resultado == "SELL"

def test_clasificar_senal_none():
    patron = "patron desconocido"
    tendencia = "neutral"
    resultado = clasificar_senal(patron, tendencia)
    assert resultado is None

def test_detectar_patrones_retorno():
    # Aquí pruebas la función detectar_patrones con datos simulados o mock
    # Por ejemplo:
    df_mock = ... # crea un DataFrame con datos de ejemplo
    patrones = detectar_patrones(df_mock)
    assert isinstance(patrones, list)

def test_evaluar_patron_retorno():
    patron = "martillo"
    resultado = evaluar_patron(patron)
    assert isinstance(resultado, dict)  # o el tipo que retorne
