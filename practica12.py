"""
Práctica 12 · Tu API — Herramientas de Visualización (UPQ)
API: TMDB (The Movie Database) — películas más votadas
Docs: https://developer.themoviedb.org/docs/getting-started

Uso:
  1) Crea cuenta gratis en https://www.themoviedb.org/signup
  2) Settings > API > pide la llave (tipo Developer) y copia el "API Read Access Token".
  3) Pégalo en token.txt (una sola línea) o en la variable de entorno TMDB_TOKEN.
  4) python practica12_tmdb.py
  La primera vez consulta la API y guarda respuesta.json; las siguientes lee el archivo.
  Para forzar una nueva consulta, borra respuesta.json.
"""

import json
import os
import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests

# ------------------------------------------------------------------ Configuración
URL = "https://api.themoviedb.org/3/discover/movie"
ARCHIVO_RESPUESTA = "respuesta.json"
ARCHIVO_TOKEN = "token.txt"
PAGINAS = 15            # 20 películas por página -> 300 registros

# Paleta del curso
GRIS = "#B9C3D1"
AZUL = "#1C4C9A"

# Códigos de género de TMDB -> nombre (mapeo explícito)
GENEROS = {
    28: "Acción", 12: "Aventura", 16: "Animación", 35: "Comedia", 80: "Crimen",
    99: "Documental", 18: "Drama", 10751: "Familia", 14: "Fantasía", 36: "Historia",
    27: "Terror", 10402: "Música", 9648: "Misterio", 10749: "Romance",
    878: "Ciencia ficción", 10770: "Película de TV", 53: "Suspense",
    10752: "Bélica", 37: "Western",
}


# ------------------------------------------------------------------ 1. Token fuera del código
def leer_token():
    token = os.environ.get("TMDB_TOKEN", "").strip()
    origen = "variable de entorno TMDB_TOKEN"
    if not token and os.path.exists(ARCHIVO_TOKEN):
        with open(ARCHIVO_TOKEN, encoding="utf-8") as f:
            token = f.read().strip()
        origen = ARCHIVO_TOKEN
    if not token:
        print(f"ERROR: no encontré el token. Pégalo en {ARCHIVO_TOKEN} o define TMDB_TOKEN.")
        raise SystemExit(1)
    if len(token) < 100 or " " in token or not token.startswith("eyJ"):
        print(f"ERROR: el token de {origen} parece incompleto o no es el 'API Read Access Token' "
              f"(longitud {len(token)}). Ese token es largo y empieza con 'eyJ'. "
              "No uses la API Key corta de 32 caracteres.")
        raise SystemExit(1)
    print(f"Token leído desde {origen} ({len(token)} caracteres).")
    return token


# ------------------------------------------------------------------ 2 y 3. Estado y tipo de contenido
MENSAJES_ESTADO = {
    400: "400: la petición está mal hecha (revisa los parámetros).",
    401: "401: el token no sirve (inválido, incompleto o con espacios).",
    404: "404: el endpoint no existe (revisa la URL).",
    422: "422: algún parámetro tiene un valor no válido.",
    429: "429: te pasaste del límite de peticiones. Espera unos segundos y reintenta.",
}


def consultar_pagina(token, pagina):
    cabeceras = {"Authorization": f"Bearer {token}", "accept": "application/json"}
    params = {
        "sort_by": "vote_count.desc",
        "include_adult": "false",
        "language": "es-MX",
        "page": pagina,
    }
    try:
        r = requests.get(URL, headers=cabeceras, params=params, timeout=30)
    except requests.RequestException as e:
        print(f"ERROR de red: {e}")
        raise SystemExit(1)

    if r.status_code != 200:
        print(MENSAJES_ESTADO.get(r.status_code, f"Código inesperado: {r.status_code}"))
        print(r.text[:300])
        raise SystemExit(1)

    if "json" not in (r.headers.get("Content-Type") or ""):
        print(r.text[:300])
        raise SystemExit(1)

    return r.json()


# ------------------------------------------------------------------ 4. Guardar y reutilizar respuesta
def obtener_datos():
    if os.path.exists(ARCHIVO_RESPUESTA):
        print(f"Leyendo {ARCHIVO_RESPUESTA} (sin gastar peticiones).")
        with open(ARCHIVO_RESPUESTA, encoding="utf-8") as f:
            return json.load(f)

    token = leer_token()
    paginas = []
    for n in range(1, PAGINAS + 1):
        print(f"Consultando página {n}/{PAGINAS}...")
        paginas.append(consultar_pagina(token, n))
        time.sleep(0.3)

    # TMDB no devuelve el token en la respuesta (va en el encabezado), pero se
    # comprueba antes de guardar para no entregarlo por accidente.
    # Se guarda en una línea por página para que el archivo no sea larguísimo.
    texto = "[\n" + ",\n".join(json.dumps(p, ensure_ascii=False) for p in paginas) + "\n]"
    if token in texto:
        print("ERROR: el token apareció en la respuesta; no se guardó el archivo.")
        raise SystemExit(1)
    with open(ARCHIVO_RESPUESTA, "w", encoding="utf-8") as f:
        f.write(texto)
    print(f"Respuesta guardada en {ARCHIVO_RESPUESTA} ({len(paginas)} páginas, una por línea; sigue siendo un JSON válido).")
    return paginas


# ------------------------------------------------------------------ 5. Limpieza documentada
def aplanar(paginas):
    filas = []
    for pagina in paginas:
        for peli in pagina["results"]:
            ids = peli.get("genre_ids") or []
            filas.append({
                "id": peli.get("id"),
                "titulo": peli.get("title"),
                "fecha_estreno": peli.get("release_date"),
                "calificacion": peli.get("vote_average"),
                "votos": peli.get("vote_count"),
                "popularidad": peli.get("popularity"),
                "idioma": peli.get("original_language"),
                "genero": GENEROS.get(ids[0], "Otro") if ids else "Sin género",
            })
    return pd.DataFrame(filas)


def limpiar(df):
    print("\n=== TIPOS DE DATO AL CARGAR ===")
    print(df.dtypes)
    print(f"\nRegistros crudos: {len(df)}")

    for col in ["calificacion", "votos", "popularidad"]:
        antes = df[col].notna().sum()
        df[col] = pd.to_numeric(df[col], errors="coerce")
        perdidos = antes - df[col].notna().sum()
        print(f"Conversión a número de '{col}': {perdidos} valores perdidos")

    antes = (df["fecha_estreno"].fillna("") != "").sum()
    df["fecha_estreno"] = pd.to_datetime(df["fecha_estreno"], errors="coerce")
    print(f"Conversión a fecha de 'fecha_estreno': {antes - df['fecha_estreno'].notna().sum()} valores perdidos")

    print("\n=== FALTANTES POR COLUMNA ===")
    print(df.isna().sum())

    duplicados = df.duplicated(subset=["id"]).sum()
    df = df.drop_duplicates(subset=["id"])
    print(f"\nDuplicados (mismo id de película) eliminados: {duplicados}")

    n0 = len(df)
    df = df.dropna(subset=["calificacion", "votos", "fecha_estreno"])
    df = df[(df["votos"] > 0) & (df["calificacion"] > 0)]
    print(f"Registros descartados por faltantes o valores no válidos: {n0 - len(df)}")
    print(f"REGISTROS UTILIZABLES: {len(df)}")

    df["anio"] = df["fecha_estreno"].dt.year
    df["decada"] = (df["anio"] // 10) * 10

    # Género principal: los 5 más frecuentes y el resto agrupado -> 6 grupos
    top = df["genero"].value_counts().head(5).index
    df["grupo_genero"] = df["genero"].where(df["genero"].isin(top), "Otros")
    print("\nRegistros por grupo de género:")
    print(df["grupo_genero"].value_counts())
    return df.reset_index(drop=True)


# ------------------------------------------------------------------ 4 gráficas
def estilo(ax):
    ax.spines[["top", "right"]].set_visible(False)


def grafica_distribucion(df):
    c = df["calificacion"]
    n8 = (c >= 8).sum()
    bins = np.arange(np.floor(c.min() * 5) / 5, c.max() + 0.2, 0.2)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(c[c < 8], bins=bins, color=GRIS)
    ax.hist(c[c >= 8], bins=bins, color=AZUL, label="Calificación de 8 o más")
    ax.set_title(f"La calificación típica es {c.median():.1f}: solo {n8} de {len(c)} "
                 "películas llegan a 8 o más", fontsize=11)
    ax.set_xlabel("Calificación promedio de los usuarios (0 a 10)")
    ax.set_ylabel("Número de películas")
    ax.legend(frameon=False)
    estilo(ax)
    fig.tight_layout()
    plt.savefig("grafica1_distribucion.png", dpi=150)
    plt.show()


def grafica_comparacion(df):
    med = df.groupby("grupo_genero")["calificacion"].median().sort_values()
    mejor, peor = med.index[-1], med.index[0]
    colores = [AZUL if g == mejor else GRIS for g in med.index]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(med.index, med.values, color=colores)
    for i, v in enumerate(med.values):
        ax.text(v, i, f" {v:.2f}", va="center", fontsize=9)
    ax.set_xlim(0, 10)
    ax.set_title(f"{mejor} tiene la calificación mediana más alta ({med.max():.2f});\n"
                 f"{peor} la más baja ({med.min():.2f})", fontsize=11)
    ax.set_xlabel("Calificación mediana (0 a 10)")
    ax.set_ylabel("Género principal")
    estilo(ax)
    fig.tight_layout()
    plt.savefig("grafica2_comparacion.png", dpi=150)
    plt.show()


def grafica_relacion(df):
    rho = df["votos"].rank().corr(df["calificacion"].rank())   # Spearman sin scipy
    if abs(rho) < 0.2:
        hallazgo = f"Tener más votos casi no cambia la nota (Spearman = {rho:.2f})"
    elif rho > 0:
        hallazgo = f"Las películas con más votos tienden a tener mejor nota (Spearman = {rho:.2f})"
    else:
        hallazgo = f"Las películas con más votos tienden a tener peor nota (Spearman = {rho:.2f})"
    alta = df[df["calificacion"] >= 8]
    resto = df[df["calificacion"] < 8]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(resto["votos"], resto["calificacion"], s=16, color=GRIS, label="Calificación menor a 8")
    ax.scatter(alta["votos"], alta["calificacion"], s=22, color=AZUL, label="Calificación de 8 o más")
    ax.set_xscale("log")
    ax.set_title(hallazgo, fontsize=11)
    ax.set_xlabel("Número de votos (escala logarítmica)")
    ax.set_ylabel("Calificación promedio (0 a 10)")
    ax.legend(frameon=False)
    estilo(ax)
    fig.tight_layout()
    plt.savefig("grafica3_relacion.png", dpi=150)
    plt.show()


def grafica_evolucion(df):
    g = df.groupby("decada")["calificacion"].agg(["median", "size"])
    g = g[g["size"] >= 5]
    mejor = g["median"].idxmax()
    etiquetas = [f"{int(d)}s" for d in g.index]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(etiquetas, g["median"].values, color=GRIS, linewidth=2, marker="o")
    pos = list(g.index).index(mejor)
    ax.scatter([etiquetas[pos]], [g["median"].max()], color=AZUL, s=70, zorder=3)
    ax.annotate(f"{g['median'].max():.2f}", (etiquetas[pos], g["median"].max()),
                textcoords="offset points", xytext=(8, 6), color=AZUL, fontsize=9)
    ax.set_title(f"Las películas de los {int(mejor)}s tienen la mediana más alta "
                 f"({g['median'].max():.2f});\nla de las más recientes es {g['median'].iloc[-1]:.2f}",
                 fontsize=11)
    ax.set_xlabel("Década de estreno (solo décadas con 5 o más películas)")
    ax.set_ylabel("Calificación mediana (0 a 10)")
    estilo(ax)
    fig.tight_layout()
    plt.savefig("grafica4_evolucion.png", dpi=150)
    plt.show()


# ------------------------------------------------------------------ Principal
def main():
    paginas = obtener_datos()
    df = aplanar(paginas)
    df = limpiar(df)
    grafica_distribucion(df)
    grafica_comparacion(df)
    grafica_relacion(df)
    grafica_evolucion(df)
    print("\nListo: 4 gráficas guardadas como grafica1..4_*.png")


if __name__ == "__main__":
    main()
