import os

# ── Archivos ─────────────────────────────────
INPUT_FILE      = "Benchmark Manual LatamGPT (Responses) - Form responses 1.csv"
NORMALIZED_FILE = "instituciones_normalizadas.csv"
OUTPUT_FILE     = "instituciones_clasificadas.csv"

# ── API OpenAI ────────────────────────────────
API_KEY     = os.getenv("OPENAI_API_KEY", "")
MODEL       = "gpt-4o-mini"
MAX_TOKENS  = 4096
MAX_WORKERS = 10

# ── Categorías de clasificación ───────────────
CATEGORIAS = [
    "Universidad / IES",
    "Centro de Investigacion / Laboratorio",
    "Hospital / Clinica",
    "Empresa / Industria",
    "Organismo Gubernamental",
    "ONG / Fundacion",
    "Instituto Tecnico / Tecnologico",
    "Asociacion / Sociedad Cientifica",
    "Otra",
]
