# Dashboard TMDB · Películas Más Votadas (Streamlit)

Aplicación web interactiva desarrollada con **Python** y **Streamlit** para la materia de **Herramientas de Visualización (UPQ)**. El proyecto integra el consumo de la API de **The Movie Database (TMDB)**, el procesamiento y limpieza de datos con **Pandas**, y la visualización dinámica de métricas y gráficas analíticas.

---

## Características principales

- **Extracción con caché local:** Consulta las 15 páginas de películas más votadas en TMDB (300 registros en total) y almacena la respuesta en `respuesta.json` para evitar peticiones innecesarias a la API.
- **Limpieza y transformación de datos:** Normalización de tipos numéricos y fechas, eliminación de duplicados, filtrado de registros inválidos y agrupación de géneros principales.
- **Filtros interactivos en tiempo real:**
  - Selección múltiple por grupo de género principal.
  - Rango dinámico por año de estreno.
  - Filtro de calificación mínima.
- **Indicadores clave (KPIs):** Total de películas filtradas, calificación mediana, promedio de votos y conteo de películas con calificación $\ge 8.0$.
- **Visualizaciones analíticas:**
  1. **Distribución de calificaciones:** Histograma destacando las películas sobresalientes ($\ge 8.0$).
  2. **Comparación por género:** Calificación mediana por grupo de género principal.
  3. **Relación entre votos y calificación:** Diagrama de dispersión en escala logarítmica con coeficiente de correlación de Spearman.
  4. **Evolución por década:** Tendencia de la calificación mediana a lo largo de las décadas.
- **Catálogo explorable:** Tabla interactiva ordenada por cantidad de votos.

---

## Estructura del repositorio

```text
├── app.py              # Aplicación principal del dashboard en Streamlit
├── practica12.py       # Script base de extracción, limpieza y generación de gráficas estáticas
├── respuesta.json      # Caché local con los registros obtenidos de la API de TMDB
├── requirements.txt    # Dependencias del proyecto
├── .gitignore          # Exclusión de archivos sensibles (token.txt) y temporales
└── README.md           # Documentación del proyecto
