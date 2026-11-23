import json
import os
import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import streamlit as st

# ------------------------------------------------------------------ Configuración de página
st.set_page_config(
    page_title="Dashboard TMDB · Películas Más Votadas",
    page_icon="🎬",
    layout="wide",
)

URL = "https://api.themoviedb.org/3/discover/movie"
ARCHIVO_RESPUESTA = "respuesta.json"
ARCHIVO_TOKEN = "token.txt"
PAGINAS = 15  # 20 películas por página -> 300 registros

# Paleta del curso
GRIS = "#B9C3D1"
AZUL = "#1C4C9A"

GENEROS = {
    28: "Acción",
    12: "Aventura",
    16: "Animación",
    35: "Comedia",
    80: "Crimen",
    99: "Documental",
    18: "Drama",
    10751: "Familia",
    14: "Fantasía",
    36: "Historia",
    27: "Terror",
    10402: "Música",
    9648: "Misterio",
    10749: "Romance",
    878: "Ciencia ficción",
    10770: "Película de TV",
    53: "Suspense",
    10752: "Bélica",
    37: "Western",
}


# ------------------------------------------------------------------ Extracción y Limpieza
def leer_token():
    # 1. Buscar en secrets de Streamlit (útil si despliegas en Streamlit Cloud)
    try:
        if "TMDB_TOKEN" in st.secrets:
            return st.secrets["TMDB_TOKEN"].strip()
    except Exception:
        pass

    # 2. Variable de entorno o archivo local
    token = os.environ.get("TMDB_TOKEN", "").strip()
    if not token and os.path.exists(ARCHIVO_TOKEN):
        with open(ARCHIVO_TOKEN, encoding="utf-8") as f:
            token = f.read().strip()
    return token


def consultar_pagina(token, pagina):
    cabeceras = {"Authorization": f"Bearer {token}", "accept": "application/json"}
    params = {
        "sort_by": "vote_count.desc",
        "include_adult": "false",
        "language": "es-MX",
        "page": pagina,
    }
    r = requests.get(URL, headers=cabeceras, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


@st.cache_data(show_spinner="Cargando y procesando datos de TMDB...")
def cargar_y_limpiar_datos(forzar_recarga=False):
    if os.path.exists(ARCHIVO_RESPUESTA) and not forzar_recarga:
        with open(ARCHIVO_RESPUESTA, encoding="utf-8") as f:
            paginas = json.load(f)
    else:
        token = leer_token()
        if not token:
            st.error(
                f"No se encontró el token en `{ARCHIVO_TOKEN}` ni en `TMDB_TOKEN`."
            )
            st.stop()
        paginas = []
        barra = st.progress(0, text="Consultando API de TMDB...")
        for n in range(1, PAGINAS + 1):
            paginas.append(consultar_pagina(token, n))
            barra.progress(n / PAGINAS, text=f"Descargando página {n}/{PAGINAS}...")
            time.sleep(0.25)
        barra.empty()

        texto = (
            "[\n"
            + ",\n".join(json.dumps(p, ensure_ascii=False) for p in paginas)
            + "\n]"
        )
        with open(ARCHIVO_RESPUESTA, "w", encoding="utf-8") as f:
            f.write(texto)

    # Aplanar
    filas = []
    for pagina in paginas:
        for peli in pagina.get("results", []):
            ids = peli.get("genre_ids") or []
            filas.append(
                {
                    "id": peli.get("id"),
                    "titulo": peli.get("title"),
                    "fecha_estreno": peli.get("release_date"),
                    "calificacion": peli.get("vote_average"),
                    "votos": peli.get("vote_count"),
                    "popularidad": peli.get("popularity"),
                    "idioma": peli.get("original_language"),
                    "genero": GENEROS.get(ids[0], "Otro") if ids else "Sin género",
                }
            )
    df = pd.DataFrame(filas)

    # Limpieza
    for col in ["calificacion", "votos", "popularidad"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["fecha_estreno"] = pd.to_datetime(df["fecha_estreno"], errors="coerce")
    df = df.drop_duplicates(subset=["id"])
    df = df.dropna(subset=["calificacion", "votos", "fecha_estreno"])
    df = df[(df["votos"] > 0) & (df["calificacion"] > 0)]

    df["anio"] = df["fecha_estreno"].dt.year
    df["decada"] = (df["anio"] // 10) * 10

    top = df["genero"].value_counts().head(5).index
    df["grupo_genero"] = df["genero"].where(df["genero"].isin(top), "Otros")
    return df.reset_index(drop=True)


# ------------------------------------------------------------------ Funciones de Gráficas
def estilo(ax):
    ax.spines[["top", "right"]].set_visible(False)


def fig_distribucion(df):
    c = df["calificacion"]
    n8 = (c >= 8).sum()
    bins = np.arange(np.floor(c.min() * 5) / 5, c.max() + 0.2, 0.2)
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.hist(c[c < 8], bins=bins, color=GRIS)
    ax.hist(c[c >= 8], bins=bins, color=AZUL, label="Calificación ≥ 8")
    ax.set_title(
        f"Calificación típica: {c.median():.1f} ({n8} de {len(c)} llegan a ≥ 8)",
        fontsize=10.5,
    )
    ax.set_xlabel("Calificación promedio (0 a 10)")
    ax.set_ylabel("Número de películas")
    ax.legend(frameon=False)
    estilo(ax)
    fig.tight_layout()
    return fig


def fig_comparacion(df):
    med = df.groupby("grupo_genero")["calificacion"].median().sort_values()
    mejor, peor = med.index[-1], med.index[0]
    colores = [AZUL if g == mejor else GRIS for g in med.index]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.barh(med.index, med.values, color=colores)
    for i, v in enumerate(med.values):
        ax.text(v, i, f" {v:.2f}", va="center", fontsize=9)
    ax.set_xlim(0, 10)
    ax.set_title(
        f"{mejor} lidera en mediana ({med.max():.2f}); {peor} es la más baja ({med.min():.2f})",
        fontsize=10.5,
    )
    ax.set_xlabel("Calificación mediana (0 a 10)")
    ax.set_ylabel("Género principal")
    estilo(ax)
    fig.tight_layout()
    return fig


def fig_relacion(df):
    rho = df["votos"].rank().corr(df["calificacion"].rank())
    if abs(rho) < 0.2:
        hallazgo = f"Más votos casi no cambian la nota (Spearman = {rho:.2f})"
    elif rho > 0:
        hallazgo = f"Más votos tienden a mejor nota (Spearman = {rho:.2f})"
    else:
        hallazgo = f"Más votos tienden a peor nota (Spearman = {rho:.2f})"
    alta = df[df["calificacion"] >= 8]
    resto = df[df["calificacion"] < 8]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.scatter(
        resto["votos"], resto["calificacion"], s=18, color=GRIS, label="Menor a 8"
    )
    ax.scatter(alta["votos"], alta["calificacion"], s=24, color=AZUL, label="8 o más")
    ax.set_xscale("log")
    ax.set_title(hallazgo, fontsize=10.5)
    ax.set_xlabel("Número de votos (escala logarítmica)")
    ax.set_ylabel("Calificación promedio (0 a 10)")
    ax.legend(frameon=False)
    estilo(ax)
    fig.tight_layout()
    return fig


def fig_evolucion(df):
    g = df.groupby("decada")["calificacion"].agg(["median", "size"])
    g = g[g["size"] >= 3]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    if g.empty:
        ax.text(
            0.5,
            0.5,
            "Sin suficientes datos por década con los filtros actuales",
            ha="center",
            va="center",
        )
        return fig
    mejor = g["median"].idxmax()
    etiquetas = [f"{int(d)}s" for d in g.index]
    ax.plot(etiquetas, g["median"].values, color=GRIS, linewidth=2, marker="o")
    pos = list(g.index).index(mejor)
    ax.scatter([etiquetas[pos]], [g["median"].max()], color=AZUL, s=70, zorder=3)
    ax.annotate(
        f"{g['median'].max():.2f}",
        (etiquetas[pos], g["median"].max()),
        textcoords="offset points",
        xytext=(8, 6),
        color=AZUL,
        fontsize=9,
    )
    ax.set_title(
        f"Década de los {int(mejor)}s tiene la mediana más alta ({g['median'].max():.2f})",
        fontsize=10.5,
    )
    ax.set_xlabel("Década de estreno")
    ax.set_ylabel("Calificación mediana (0 a 10)")
    estilo(ax)
    fig.tight_layout()
    return fig


# ------------------------------------------------------------------ Interfaz Streamlit
st.title("🎬 Análisis de Películas Más Votadas (TMDB)")
st.caption("Práctica 12 · Herramientas de Visualización (UPQ) — Dashboard Interactivo")

df_base = cargar_y_limpiar_datos()

# Barra lateral de filtros
st.sidebar.header("Filtros de exploración")

generos_disponibles = sorted(df_base["grupo_genero"].unique())
generos_sel = st.sidebar.multiselect(
    "Grupo de género",
    options=generos_disponibles,
    default=generos_disponibles,
)

anio_min, anio_max = int(df_base["anio"].min()), int(df_base["anio"].max())
rango_anios = st.sidebar.slider(
    "Año de estreno",
    min_value=anio_min,
    max_value=anio_max,
    value=(anio_min, anio_max),
)

calif_min = st.sidebar.slider(
    "Calificación mínima",
    min_value=0.0,
    max_value=9.0,
    value=0.0,
    step=0.5,
)

if st.sidebar.button("🔄 Actualizar datos desde API"):
    st.cache_data.clear()
    df_base = cargar_y_limpiar_datos(forzar_recarga=True)
    st.rerun()

# Aplicar filtros
df_filtrado = df_base[
    (df_base["grupo_genero"].isin(generos_sel))
    & (df_base["anio"].between(rango_anios[0], rango_anios[1]))
    & (df_base["calificacion"] >= calif_min)
]

if df_filtrado.empty:
    st.warning("No hay películas que coincidan con los filtros seleccionados.")
    st.stop()

# KPIs principales
col1, col2, col3, col4 = st.columns(4)
col1.metric("Películas analizadas", f"{len(df_filtrado)}")
col2.metric("Calificación mediana", f"{df_filtrado['calificacion'].median():.2f} / 10")
col3.metric("Promedio de votos", f"{int(df_filtrado['votos'].mean()):,}")
col4.metric("Con nota ≥ 8.0", f"{(df_filtrado['calificacion'] >= 8).sum()}")

st.divider()

# Cuadrícula 2x2 de gráficas
c1, c2 = st.columns(2)
with c1:
    st.subheader("1. Distribución de calificaciones")
    st.pyplot(fig_distribucion(df_filtrado))

with c2:
    st.subheader("2. Comparación por género")
    st.pyplot(fig_comparacion(df_filtrado))

c3, c4 = st.columns(2)
with c3:
    st.subheader("3. Relación entre votos y calificación")
    st.pyplot(fig_relacion(df_filtrado))

with c4:
    st.subheader("4. Evolución por década")
    st.pyplot(fig_evolucion(df_filtrado))

st.divider()

# Tabla de datos explorables
st.subheader("📋 Catálogo filtrado")
columnas_mostrar = [
    "titulo",
    "genero",
    "anio",
    "calificacion",
    "votos",
    "popularidad",
    "idioma",
]
st.dataframe(
    df_filtrado[columnas_mostrar].sort_values(by="votos", ascending=False),
    use_container_width=True,
    hide_index=True,
)
