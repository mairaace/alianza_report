# Alianza Report

Pipeline de **normalización, clasificación y análisis** de las instituciones que contribuyeron preguntas al benchmark de LatamGPT.  
A partir de las respuestas crudas de un formulario, el proyecto:

1. **Normaliza** nombres de instituciones (fusiona variantes, siglas y duplicados).  
2. **Clasifica** cada institución por tipo usando un LLM (GPT-4o-mini).  
3. **Genera un reporte visual** con distribuciones por país, tipo de institución y cruces entre ambos.

---

## Estructura del proyecto

```
alianza_report/
├── config/
│   └── config.py                 # Rutas de archivos, API key, modelo y categorías
├── src/
│   └── llm.py                    # Wrapper de OpenAI para clasificar instituciones
├── data/
│   ├── Benchmark Manual LatamGPT (Responses) - Form responses 1.csv   # Datos crudos del formulario
│   ├── instituciones_normalizadas.csv       # Salida del paso 1
│   └── instituciones_clasificadas_ok.csv    # Salida del paso 2 (revisada)
├── notebooks/
│   └── reporte.ipynb             # Notebook de análisis y visualización (Plotly)
├── normalizar_instituciones.py   # Paso 1: normalización
├── clasificar_instituciones.py   # Paso 2: clasificación con LLM
└── README.md
```

---

## Pipeline

### Paso 1 — Normalización (`normalizar_instituciones.py`)

Lee el CSV crudo del formulario y unifica nombres de instituciones que refieren a la misma entidad, usando dos reglas:

| Regla | Descripción |
|-------|-------------|
| **Dominio de email** | Si dos registros comparten un dominio de email no genérico (e.g. `@uchile.cl`), se unifican. |
| **Sigla + país** | Si dos nombres del mismo país son uno la sigla del otro (e.g. "UNAM" ↔ "Universidad Nacional Autónoma de México"), se unifican. |

Internamente utiliza una estructura **Union-Find** que conserva siempre el nombre más largo (completo) como representante canónico.

**Entrada:** `Benchmark Manual LatamGPT (Responses) - Form responses 1.csv`  
**Salida:** `instituciones_normalizadas.csv` con columnas `(institucion_original, pais, nombre_normalizado, email)`

```bash
python normalizar_instituciones.py
```

### Paso 2 — Clasificación (`clasificar_instituciones.py`)

Toma el CSV normalizado y clasifica cada institución única en una de las siguientes categorías usando GPT-4o-mini (con web search habilitado):

- Universidad / IES  
- Centro de Investigación / Laboratorio  
- Hospital / Clínica  
- Empresa / Industria  
- Organismo Gubernamental  
- ONG / Fundación  
- Instituto Técnico / Tecnológico  
- Asociación / Sociedad Científica  
- Otra  

El prompt le entrega al modelo el **nombre**, **dominio de email** y **país** de cada institución como pistas. Las llamadas se ejecutan en paralelo con un `ThreadPoolExecutor` (configurable en `config.py`).

También soporta **correcciones manuales** (diccionario `OVERRIDES` en el script) para instituciones que requieren una clasificación específica.

Si el archivo de salida ya existe, reutiliza las clasificaciones previas sin volver a llamar al LLM.

**Entrada:** `instituciones_normalizadas.csv`  
**Salida:** `instituciones_clasificadas.csv` (CSV original enriquecido con `nombre_normalizado`, `tipo_institucion`, `subtipo_institucion`)

```bash
OPENAI_API_KEY=sk-... python clasificar_instituciones.py
```

### Paso 3 — Reporte visual (`notebooks/reporte.ipynb`)

Notebook con visualizaciones interactivas en **Plotly** que genera:

| Gráfico | Descripción |
|---------|-------------|
| Barras horizontales | Total de respuestas por país |
| Barras horizontales | Instituciones distintas por tipo |
| Barras horizontales | Total de preguntas aportadas por tipo de institución |
| Gráfico de dona | Distribución porcentual de preguntas por tipo (top 5 + otros) |
| Mapa coroplético | Instituciones distintas por país en América Latina (con rangos de color) |
| Heatmap | Cruce de preguntas por país × tipo de institución |

---

## Configuración

Las variables principales se encuentran en `config/config.py`:

| Variable | Descripción |
|----------|-------------|
| `API_KEY` | Clave de API de OpenAI (lee de `OPENAI_API_KEY`) |
| `MODEL` | Modelo a usar (por defecto `gpt-4o-mini`) |
| `MAX_WORKERS` | Hilos concurrentes para llamadas al LLM |
| `CATEGORIAS` | Lista de tipos de institución válidos |

---

## Requisitos

- Python 3.10+
- `openai`
- `pandas`
- `unidecode`
- `tqdm`
- `plotly` (para el notebook)

---

## Uso rápido

```bash
# 1. Normalizar instituciones
python normalizar_instituciones.py

# 2. Clasificar con LLM
OPENAI_API_KEY=sk-... python clasificar_instituciones.py

# 3. Abrir el notebook de reporte
jupyter notebook notebooks/reporte.ipynb
```