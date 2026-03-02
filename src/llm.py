"""
Clasificación de instituciones con OpenAI.

clasificar_instituciones: recibe una lista de dicts {nombre, dominio_email, pais}
y devuelve la misma lista enriquecida con 'tipo' y 'subtipo'.
"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed

import openai
from tqdm import tqdm

from config.config import CATEGORIAS, MAX_TOKENS, MAX_WORKERS, MODEL

LISTA_CATS = "\n".join(f"- {c}" for c in CATEGORIAS)


def _parse_json(raw: str):
    raw = raw.strip()
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def _call(prompt: str) -> str:
    resp = openai.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        tools=[{"type": "web_search_preview"}],
        max_tokens=MAX_TOKENS,
    )
    return resp.choices[0].message.content.strip()


def _make_prompt(nombre: str, dominio: str, pais: str) -> str:
    return f"""Clasifica la siguiente institución en una de las categorías listadas.

CATEGORÍAS:
{LISTA_CATS}

INSTITUCIÓN: {nombre}
DOMINIO EMAIL: {dominio}
PAÍS: {pais}

Usa el nombre, el dominio de email y el país como pistas para inferir el tipo.
Por ejemplo, un dominio .edu.xx sugiere universidad; .gob.xx sugiere gobierno.

Responde ÚNICAMENTE con un JSON object (sin markdown, sin texto extra):
{{
  "nombre": "{nombre}",
  "tipo": "categoría exacta de la lista",
  "subtipo": "descripción breve más específica (ej: 'Universidad pública', 'Ministerio de ciencia')"
}}"""


def clasificar_instituciones(items: list[dict]) -> list[dict]:
    """
    Recibe lista de dicts con keys: nombre, dominio_email, pais.
    Retorna lista de dicts con keys: nombre, tipo, subtipo.
    """
    prompts = [_make_prompt(it["nombre"], it["dominio_email"], it["pais"]) for it in items]
    results = [None] * len(prompts)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(_call, p): i for i, p in enumerate(prompts)
        }
        with tqdm(total=len(prompts), desc="Clasificando", unit="inst") as pbar:
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    results[idx] = future.result()
                except Exception as exc:
                    results[idx] = f"[ERROR: {exc}]"
                pbar.update(1)

    parsed = []
    for item, raw in zip(items, results):
        if raw.startswith("[ERROR"):
            parsed.append({"nombre": item["nombre"], "tipo": "ERROR", "subtipo": raw})
        else:
            try:
                parsed.append(_parse_json(raw))
            except Exception:
                parsed.append({"nombre": item["nombre"], "tipo": "ERROR", "subtipo": raw})
    return parsed
