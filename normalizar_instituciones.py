#!/usr/bin/env python3
"""
normalizar_instituciones.py

Normaliza nombres de instituciones con dos reglas:
  1. Mismo dominio de email no genérico → misma institución.
  2. Mismo país + una es sigla de la otra → misma institución.
En ambos casos se conserva el nombre más largo (no la abreviación).

Salida: CSV con (institucion_original, pais, nombre_normalizado, email).
"""

import pandas as pd
from unidecode import unidecode
from collections import defaultdict

# ── Configuración ────────────────────────────────────────────────────────

INPUT  = "Benchmark Manual LatamGPT (Responses) - Form responses 1.csv"
OUTPUT = "instituciones_normalizadas.csv"

GENERIC_DOMAINS = {
    "gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "yahoo.es",
    "live.com", "icloud.com", "protonmail.com", "mail.com", "hotmail.es",
}

STOP = {
    "de", "del", "la", "las", "los", "en", "y", "e", "o",
    "el", "al", "a", "por", "para", "con", "un", "una",
}

# ── Funciones auxiliares ─────────────────────────────────────────────────

def limpiar(t):
    """Quita espacios y comillas/apóstrofes sueltos."""
    if pd.isna(t):
        return ""
    return str(t).strip().strip('"\'´ ')


def norm(t):
    """Minúsculas sin acentos (para comparación)."""
    return unidecode(t.lower())


def dominio(email):
    if pd.isna(email) or "@" not in str(email):
        return ""
    return str(email).strip().split("@")[-1].lower()


def es_sigla(corta, larga):
    """True si 'corta' es la sigla formada por primeras letras de 'larga'."""
    c, l = norm(corta), norm(larga)
    if not c or len(c) >= len(l) or len(c) > 10:
        return False
    iniciales = "".join(w[0] for w in l.split() if w not in STOP)
    return c == iniciales


# ── Union-Find (conserva el nombre más largo como raíz) ─────────────────

class UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]  # path compression
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            # el más largo queda como raíz (nombre completo > sigla)
            if len(ra) < len(rb):
                ra, rb = rb, ra
            self.p[rb] = ra


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    df = pd.read_csv(INPUT)
    df["_inst"] = df["institucion"].apply(limpiar)
    df["pais_final"] = df["País"].where(df["País"].notna() & (df["País"].str.strip() != ""), df["País de Origen"])
    df["_pais"] = df["pais_final"].apply(lambda x: norm(limpiar(x)))
    df["_dom"]  = df["Email address"].apply(dominio)
    df = df[df["_inst"] != ""].copy()

    uf = UF()

    # Paso 0 – unir textos idénticos tras normalizar (case + acentos)
    norm_groups = defaultdict(list)
    for inst in df["_inst"].unique():
        norm_groups[norm(inst)].append(inst)
    for forms in norm_groups.values():
        for f in forms[1:]:
            uf.union(forms[0], f)

    # Regla 1 – mismo dominio no genérico → unir
    dom_groups = defaultdict(set)
    for _, row in df.iterrows():
        d = row["_dom"]
        if d and d not in GENERIC_DOMAINS:
            dom_groups[d].add(row["_inst"])
    for insts in dom_groups.values():
        insts = list(insts)
        for i in insts[1:]:
            uf.union(insts[0], i)

    # Regla 2 – mismo país + sigla → unir
    pais_groups = defaultdict(set)
    for _, row in df.iterrows():
        pais_groups[row["_pais"]].add(row["_inst"])
    for insts in pais_groups.values():
        insts = list(insts)
        for i in range(len(insts)):
            for j in range(i + 1, len(insts)):
                if es_sigla(insts[i], insts[j]) or es_sigla(insts[j], insts[i]):
                    uf.union(insts[i], insts[j])

    # Aplicar normalización
    df["nombre_normalizado"] = df["_inst"].apply(uf.find)

    out = df[["institucion", "pais_final", "nombre_normalizado", "Email address"]].copy()
    out.columns = ["institucion_original", "pais", "nombre_normalizado", "email"]
    out.to_csv(OUTPUT, index=False)

    n_before = df["_inst"].nunique()
    n_after  = out["nombre_normalizado"].nunique()
    print(f"Instituciones únicas: {n_before} → {n_after}")
    print(f"Guardado en {OUTPUT}")

    # Mostrar las fusiones realizadas
    merged = {}
    for inst in df["_inst"].unique():
        canon = uf.find(inst)
        if canon != inst:
            merged.setdefault(canon, []).append(inst)
    if merged:
        print(f"\nFusiones ({len(merged)} grupos):")
        for canon, miembros in sorted(merged.items(), key=lambda x: -len(x[1])):
            print(f"  ✓ {canon}")
            for m in sorted(miembros, key=len):
                print(f"      ← {m}")


if __name__ == "__main__":
    main()
