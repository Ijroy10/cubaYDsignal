# 📊 ESTRUCTURA DE INSTRUMENTS EN PYQUOTEX

## 🔍 Descubrimiento

Los instrumentos en `pyquotex` son **listas** (arrays), no diccionarios.

## 📋 Estructura de Cada Instrumento

```python
[
  376,                    # [0] ID del instrumento
  "ADAUSD_otc",          # [1] Symbol (código)
  "Cardano (OTC)",       # [2] Nombre completo
  "cryptocurrency",      # [3] Tipo de activo
  5,                     # [4] ?
  85,                    # [5] ⭐ PAYOUT (%)
  60,                    # [6] ?
  30,                    # [7] ?
  3,                     # [8] ?
  1,                     # [9] ?
  0,                     # [10] ?
  0,                     # [11] ?
  [],                    # [12] ?
  1761264000,            # [13] Timestamp
  true,                  # [14] Abierto/Cerrado
  [                      # [15] Precios por timeframe
    {"time": 60, "price": 0},
    {"time": 120, "price": 0},
    {"time": 180, "price": 0},
    {"time": 300, "price": 0}
  ],
  15,                    # [16] ?
  2.09,                  # [17] Precio actual?
  85,                    # [18] Payout duplicado?
  90,                    # [19] Payout máximo?
  0,                     # [20] ?
  0,                     # [21] ?
  0.11,                  # [22] Cambio %?
  -21.73,                # [23] ?
  19,                    # [24] ?
  19,                    # [25] ?
  0.17                   # [26] ?
]
```

## ⭐ CAMPOS CLAVE IDENTIFICADOS

| Índice | Campo | Descripción | Ejemplo |
|--------|-------|-------------|---------|
| **[0]** | ID | ID único del instrumento | 376 |
| **[1]** | Symbol | Código del mercado | "ADAUSD_otc" |
| **[2]** | Name | Nombre completo | "Cardano (OTC)" |
| **[3]** | Type | Tipo de activo | "cryptocurrency" |
| **[5]** | **Payout** | **Payout en %** | **85** |
| **[14]** | Open | Mercado abierto/cerrado | true/false |
| **[17]** | Price | Precio actual | 2.09 |

## 💻 CÓDIGO PARA ACCEDER

```python
# Obtener instruments
instruments = quotex.instruments

# Acceder a datos de un instrumento
for inst in instruments:
    instrument_id = inst[0]
    symbol = inst[1]
    name = inst[2]
    asset_type = inst[3]
    payout = inst[5]  # ⭐ PAYOUT
    is_open = inst[14]
    price = inst[17]
    
    print(f"{name}: {payout}% payout")
```

## 📊 EJEMPLO REAL

```python
# Instrumento: Cardano (OTC)
inst = instruments[0]

# Extraer datos
id = inst[0]          # 376
symbol = inst[1]      # "ADAUSD_otc"
name = inst[2]        # "Cardano (OTC)"
type = inst[3]        # "cryptocurrency"
payout = inst[5]      # 85 (%)
is_open = inst[14]    # True
price = inst[17]      # 2.09

# Resultado
print(f"{name}: {payout}% payout, Precio: {price}")
# Output: Cardano (OTC): 85% payout, Precio: 2.09
```

## ✅ CONCLUSIÓN

- ✅ Los payouts **SÍ están disponibles** en `pyquotex`
- ✅ Están en la **posición [5]** de cada instrumento
- ✅ Hay **121 instrumentos** disponibles
- ✅ Formato: Lista (array), no diccionario

## 🔧 ACTUALIZACIÓN NECESARIA

El código en `market_manager.py` necesita actualizarse para:
1. Acceder a `instruments` como lista
2. Extraer payout de la posición [5]
3. Filtrar por payout ≥ 80%

---

**✅ Payouts disponibles en pyquotex - Estructura identificada correctamente**
