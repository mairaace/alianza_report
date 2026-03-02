#!/usr/bin/env python3
"""
clasificar_instituciones.py

Lee instituciones_normalizadas.csv, clasifica cada institución única
con GPT usando nombre + dominio email + país como contexto, y genera
una copia del CSV original enriquecida con nombre_normalizado y tipo.

Uso:
    OPENAI_API_KEY=sk-... python clasificar_instituciones.py
"""

import os
import sys

import openai
import pandas as pd

from config.config import API_KEY, NORMALIZED_FILE, INPUT_FILE, OUTPUT_FILE
from src.llm import clasificar_instituciones

# ── Correcciones manuales (nombre_normalizado → (tipo, subtipo)) ─────────────
OVERRIDES = {
    "CENIA": (
        "Centro de Investigacion / Laboratorio",
        "Centro nacional de inteligencia artificial, fundación sin fines de lucro "
        "financiada con fondos públicos y privados, articulada con universidades",
    ),
}


def dominio_email(email: str) -> str:
    if pd.isna(email) or "@" not in str(email):
        return ""
    return "@" + str(email).strip().split("@")[-1].lower()


def main():
    if not API_KEY:
        sys.exit("❌  Falta OPENAI_API_KEY (variable de entorno o config/config.py)")
    openai.api_key = API_KEY

    # ── 1. Leer CSV normalizado ──────────────────────────────────────────
    norm = pd.read_csv(NORMALIZED_FILE)
    print(f"Leído {NORMALIZED_FILE}: {len(norm)} filas, {norm['nombre_normalizado'].nunique()} instituciones únicas")

    # ── 2. Obtener mapa de clasificaciones (LLM o caché) ────────────────
    if os.path.exists(OUTPUT_FILE):
        print(f"⚡ '{OUTPUT_FILE}' ya existe — cargando clasificaciones previas (sin llamar al LLM)")
        existing = pd.read_csv(OUTPUT_FILE)
        mapa = {
            row["nombre_normalizado"]: (row["tipo_institucion"], row["subtipo_institucion"])
            for _, row in existing[["nombre_normalizado", "tipo_institucion", "subtipo_institucion"]]
            .drop_duplicates("nombre_normalizado")
            .iterrows()
            if pd.notna(row["nombre_normalizado"])
        }
    else:
        records = []
        for nombre, grp in norm.groupby("nombre_normalizado"):
            dominios = [dominio_email(e) for e in grp["email"] if dominio_email(e) and "gmail" not in str(e)]
            dom = max(set(dominios), key=dominios.count) if dominios else dominio_email(grp["email"].iloc[0])
            pais = grp["pais"].mode().iloc[0] if not grp["pais"].mode().empty else ""
            records.append({"nombre": nombre, "dominio_email": dom, "pais": str(pais)})

        print(f"Instituciones a clasificar: {len(records)}")
        clasificaciones = clasificar_instituciones(records)
        mapa = {
            c["nombre"]: (c.get("tipo", ""), c.get("subtipo", ""))
            for c in clasificaciones
        }

    # ── 3. Aplicar correcciones manuales ────────────────────────────────
    for nombre, valores in OVERRIDES.items():
        mapa[nombre] = valores
        print(f"✏️  Override aplicado: {nombre} → {valores[0]}")

    # ── 4. Leer CSV original y enriquecer ────────────────────────────────
    original = pd.read_csv(INPUT_FILE)
    print(f"Leído {INPUT_FILE}: {len(original)} filas")

    inst_map  = dict(zip(norm["institucion_original"], norm["nombre_normalizado"]))
    pais_map  = dict(zip(norm["institucion_original"], norm["pais"]))

    original["nombre_normalizado"] = original["institucion"].map(
        lambda x: inst_map.get(str(x).strip().strip('"\'´ '), str(x).strip() if pd.notna(x) else "")
    )
    original["pais"] = original["institucion"].map(
        lambda x: pais_map.get(str(x).strip().strip('"\'´ '), "")
    )

    # Filas sin institución → "Independiente"
    sin_inst = original["nombre_normalizado"].isna() | (original["nombre_normalizado"].str.strip() == "")
    original.loc[sin_inst, "nombre_normalizado"] = "Independiente"
    original.loc[sin_inst, "tipo_institucion"]   = "Independiente"
    original.loc[sin_inst, "subtipo_institucion"] = ""

    # Clasificar el resto
    original.loc[~sin_inst, "tipo_institucion"] = original.loc[~sin_inst, "nombre_normalizado"].map(
        lambda x: mapa.get(x, ("", ""))[0]
    )
    original.loc[~sin_inst, "subtipo_institucion"] = original.loc[~sin_inst, "nombre_normalizado"].map(
        lambda x: mapa.get(x, ("", ""))[1]
    )

    # ── 5. Guardar ───────────────────────────────────────────────────────
    original.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"\nGuardado: {OUTPUT_FILE} ({len(original)} filas)")
    print("\nDistribución por tipo:")
    print(original["tipo_institucion"].value_counts().to_string())

    errores = original[original["tipo_institucion"] == "ERROR"]
    if not errores.empty:
        print(f"\n⚠  {len(errores)} filas con error de clasificación")


if __name__ == "__main__":
    main()
