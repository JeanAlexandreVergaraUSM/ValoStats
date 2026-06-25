# ValoStats

ValoStats es un proyecto de **minería de datos aplicado a estadísticas de jugadores de Valorant**.

El objetivo del proyecto es analizar partidas competitivas recientes de un jugador, construir métricas de rendimiento, detectar su estilo de juego, comparar su desempeño con jugadores similares y entregar recomendaciones personalizadas.

La aplicación final incluye:

* extracción de partidas recientes mediante scraper;
* análisis de rendimiento individual;
* predicción de estilo de juego;
* análisis de tendencia competitiva;
* comparación con jugadores de referencia;
* sistema de recomendación basado en similitud;
* dashboard web para visualizar los resultados;
* demo pública en GitHub Pages con un jugador precargado.

---

## Integrantes

| Nombre | Nickname | ROL USM | Correo USM |
|---|---|---:|---|
| Lorenzo Gonzalez | Lorenx003 | 202230550-9 | lorenzo.gonzalez@usm.cl |
| Fernando Zamora |  | 202230 | fernando.zamorav@usm.cl |
| Jean Alexandre | JeanAlexandreVergaraUSM | 202230562-2 | jean.alexandre@usm.cl |

---

## Descripción del proyecto

Este proyecto toma estadísticas de jugadores de Valorant y construye un pipeline completo de minería de datos para transformar datos de partidas en información interpretable.

El sistema permite:

* obtener partidas recientes desde Tracker.gg;
* limpiar y preparar los datos;
* generar variables derivadas;
* analizar rendimiento reciente;
* detectar estilo de juego;
* estimar tendencia competitiva;
* buscar jugadores similares;
* generar recomendaciones personalizadas;
* mostrar los resultados en una página web.

La idea principal no es solo mostrar estadísticas aisladas, sino convertirlas en una lectura comprensible del desempeño y estilo de juego de un jugador.

---

## Objetivo

El proyecto busca responder preguntas como:

* ¿Qué tipo de jugador es una persona según sus estadísticas recientes?
* ¿Su estilo es más ofensivo, táctico o de alto impacto?
* ¿Está teniendo una tendencia positiva, negativa o estable?
* ¿Cómo se compara con jugadores de lobbies similares?
* ¿Qué aspectos debería mejorar?
* ¿Qué recomendaciones se pueden entregar según su perfil?

---

## Funcionamiento general

El flujo principal del sistema es el siguiente:

```text
Riot ID del jugador
        ↓
Scraper de Tracker.gg
        ↓
Partidas competitivas recientes
        ↓
Generación de métricas
        ↓
Predicción de rendimiento
        ↓
Predicción de estilo de juego
        ↓
Análisis de tendencia
        ↓
Búsqueda de jugadores similares
        ↓
Recomendaciones personalizadas
        ↓
Dashboard web
```

Para la demo pública se utiliza un jugador previamente analizado, ya que GitHub Pages solo permite publicar archivos estáticos y no ejecuta procesos de backend en Python.

---

## Perfiles de jugador

El modelo trabaja con tres perfiles principales.

### 1. Alto impacto

Jugador que destaca por generar diferencia en rondas clave.
Suele tener mayor presencia en entradas, duelos importantes, jugadas decisivas o partidas donde su rendimiento individual marca diferencia.

### 2. Apoyo táctico

Jugador que aporta al equipo mediante utilidad, asistencias, participación en rondas y juego colectivo.
No necesariamente lidera siempre en agresividad, pero entrega valor estratégico y mantiene buena participación.

### 3. Ofensivo consistente

Jugador que mantiene un rendimiento ofensivo estable.
Se caracteriza por eficiencia, regularidad y presión sostenida, más que por jugadas explosivas aisladas.

> Estos perfiles no son etiquetas humanas del dataset. Fueron construidos mediante clustering y luego interpretados a partir de métricas promedio, centroides y comportamiento estadístico de los jugadores.

---

## Metodología utilizada

El proyecto se desarrolló en varias etapas.

### 1. Preprocesamiento

Se cargan los datos y se limpian valores faltantes, tipos de datos, duplicados y columnas numéricas.

### 2. Feature engineering

Se construyen variables nuevas para representar mejor el estilo del jugador, por ejemplo:

* agresividad;
* precisión;
* impacto;
* soporte;
* eficiencia;
* entry power;
* consistencia;
* K/D;
* ACS;
* ADR;
* KAST;
* first kills;
* first deaths;
* entry success.

### 3. Clustering

Se agrupan jugadores según similitud estadística para descubrir perfiles de juego.

El clustering permite identificar grupos de jugadores con comportamientos parecidos sin depender de etiquetas manuales.

### 4. Interpretación de clusters

Cada cluster se analiza según sus métricas promedio.
A partir de esa comparación se asignan nombres interpretables:

* Alto impacto;
* Apoyo táctico;
* Ofensivo consistente.

### 5. Clasificación

Se entrena un modelo supervisado para predecir el perfil detectado por clustering.
Esto permite clasificar nuevas partidas o nuevos jugadores según los patrones aprendidos.

### 6. Predicción de rendimiento

El sistema clasifica el rendimiento de las partidas recientes en niveles como:

* Bajo;
* Medio;
* Alto;
* Destacado.

Luego se genera una lectura global del desempeño reciente del jugador.

### 7. Análisis de tendencia

Se comparan las partidas más recientes contra las anteriores para estimar si el jugador presenta:

* progreso positivo;
* estabilidad;
* riesgo de bajar;
* subida probable.

Esta tendencia se calcula a partir de cambios en métricas como winrate, ACS, K/D, KAST y estilo predominante.

### 8. Sistema de recomendación

El sistema compara al jugador contra una base de referencia de jugadores reales.
La comparación se realiza usando métricas agregadas y similitud entre vectores de características.

Esto permite encontrar jugadores con comportamiento parecido y generar recomendaciones más contextualizadas.

### 9. Visualización web

Los resultados se exportan a archivos JSON que son utilizados por una web estática en HTML, CSS y JavaScript.

---

## Scraper y análisis en vivo

El proyecto incluye un scraper implementado en Python usando Playwright.

Este scraper permite ingresar un Riot ID, por ejemplo:

```text
PoloGB#LAS
```

y extraer sus últimas partidas competitivas desde Tracker.gg.

### Ejecutar scraper localmente

Desde la raíz del proyecto:

```powershell
python data/tracker/scraper_valorant.py "PoloGB#LAS"
```

Esto genera o actualiza el archivo:

```text
data/recent_matches.csv
```

Ese archivo contiene las partidas recientes extraídas para el jugador objetivo.

### Ejecutar análisis completo local

Después de ejecutar el scraper, se corre el pipeline completo:

```powershell
python src/run_full_analysis.py "PoloGB#LAS" --skip-scraper
```

Se usa `--skip-scraper` porque las partidas ya fueron descargadas previamente en `data/recent_matches.csv`.

El pipeline genera:

```text
outputs/recent_features/recent_features.json
outputs/recent_predictions/performance_predictions.json
outputs/recent_predictions/style_predictions.json
outputs/recent_predictions/trend_predictions.json
outputs/recent_predictions/similar_players.json
outputs/recent_predictions/final_player_analysis.json
docs/final_player_analysis.json
```

---

## Demo pública en GitHub Pages

La versión publicada en GitHub Pages funciona como una **demo estática**.

Esto significa que la página pública no ejecuta el scraper en vivo directamente. En su lugar, utiliza archivos JSON previamente generados, especialmente:

```text
docs/web_data.json
docs/final_player_analysis.json
```

En la demo pública se puede cargar un jugador precargado, por ejemplo:

```text
PoloGB#LAS
```

La página lee el archivo:

```text
docs/final_player_analysis.json
```

y muestra el análisis ya generado.

### Motivo de esta decisión

GitHub Pages solo permite servir archivos estáticos como:

* HTML;
* CSS;
* JavaScript;
* JSON;
* imágenes.

No permite ejecutar un backend en Python ni correr procesos como scraping, Playwright o modelos de machine learning en el servidor.

También se probó desplegar el backend en Render para ejecutar el scraper online, pero el flujo completo requiere abrir Chromium con Playwright, procesar datos con pandas y ejecutar modelos de machine learning. En el plan gratuito el servicio superó el límite de memoria.

Por esta razón, para mantener el proyecto sin costo, se decidió:

```text
Web pública:
- muestra el dashboard;
- usa datos ya generados;
- carga un jugador precargado.

Ejecución local:
- ejecuta el scraper en vivo;
- actualiza las partidas recientes;
- corre el pipeline completo;
- genera nuevos archivos para la web.
```

---

## Estructura del proyecto

```text
ValoStats/
│
├── backend/
│   └── api.py                         # Backend FastAPI para ejecución local
│
├── data/
│   ├── tracker/
│   │   ├── scraper_valorant.py         # Scraper principal para un jugador
│   │   └── scraper_reference_batch.py  # Scraper para jugadores de referencia
│   │
│   ├── recent_matches.csv              # Últimas partidas del jugador objetivo
│   ├── reference_players.csv           # Lista de jugadores de referencia
│   ├── rank_reference_matches.csv      # Partidas extraídas de jugadores de referencia
│   ├── rank_reference_profiles.csv     # Perfiles agregados de referencia
│   └── val_stats.csv                   # Dataset base del proyecto
│
├── docs/
│   ├── assets/
│   │   ├── favicon.png
│   │   └── logo.png
│   │
│   ├── index.html                      # Web pública
│   ├── styles.css                      # Estilos de la web
│   ├── app.js                          # Lógica del dashboard
│   ├── web_data.json                   # Datos procesados para la web
│   └── final_player_analysis.json      # Jugador precargado para demo pública
│
├── models/                             # Modelos entrenados o artefactos del pipeline
│
├── notebooks/
│   ├── 01_clustering_perfiles_valostats.ipynb
│   └── 02_pipeline_predicciones_valostats.ipynb
│
├── outputs/
│   ├── figures/
│   ├── metrics/
│   ├── rank_reference/
│   │   └── rank_reference_summary.json
│   ├── recent_features/
│   │   └── recent_features.json
│   └── recent_predictions/
│       ├── performance_predictions.json
│       ├── style_predictions.json
│       ├── trend_predictions.json
│       ├── similar_players.json
│       └── final_player_analysis.json
│
├── scripts/
│   └── export_web_data.py              # Exporta datos procesados a docs/web_data.json
│
├── src/
│   ├── preprocessing.py
│   ├── clustering.py
│   ├── classification.py
│   ├── recommendation.py
│   ├── visualization.py
│   ├── recent_features.py
│   ├── performance_prediction.py
│   ├── recent_style_prediction.py
│   ├── trend_analysis.py
│   ├── similar_players.py
│   ├── final_player_analysis.py
│   ├── rank_reference_features.py
│   └── run_full_analysis.py
│
├── requirements.txt
├── Dockerfile
├── .gitignore
└── README.md
```

---

## Requisitos

Antes de ejecutar el proyecto, asegúrate de tener instalado:

* Python 3.10 o superior;
* pip;
* Git;
* un navegador web moderno;
* Google Chrome o Chromium;
* Playwright.

Dependencias principales:

* pandas;
* numpy;
* matplotlib;
* seaborn;
* scikit-learn;
* plotly;
* jupyter;
* nbformat;
* ipykernel;
* fastapi;
* uvicorn;
* playwright;
* beautifulsoup4;
* requests.

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/JeanAlexandreVergaraUSM/ValoStats.git
cd ValoStats
```

### 2. Crear un entorno virtual

En PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

En Git Bash:

```bash
python -m venv .venv
source .venv/Scripts/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Instalar navegadores de Playwright

```bash
python -m playwright install chromium
```

---

## Uso local del proyecto

### Opción 1: ejecutar scraper y pipeline por comandos

Primero se descarga la información reciente del jugador:

```powershell
python data/tracker/scraper_valorant.py "PoloGB#LAS"
```

Luego se ejecuta el análisis completo usando el CSV generado:

```powershell
python src/run_full_analysis.py "PoloGB#LAS" --skip-scraper
```

Finalmente se exportan los datos para la web:

```powershell
python scripts/export_web_data.py
```

### Opción 2: ejecutar backend local

El proyecto incluye un backend con FastAPI para ejecutar el análisis desde la web local.

```powershell
uvicorn backend.api:app --reload
```

Luego abrir en el navegador:

```text
http://localhost:8000
```

En esta versión local, al ingresar un Riot ID con formato:

```text
Nombre#TAG
```

el sistema puede ejecutar el análisis completo desde el backend.

---

## Generar datos para la web

Para actualizar la demo pública se recomienda seguir este orden.

### 1. Descargar partidas recientes del jugador objetivo

```powershell
python data/tracker/scraper_valorant.py "PoloGB#LAS"
```

Esto actualiza:

```text
data/recent_matches.csv
```

### 2. Generar perfiles de referencia

Si ya existe `data/rank_reference_matches.csv`, ejecutar:

```powershell
python src/rank_reference_features.py
```

Esto genera:

```text
data/rank_reference_profiles.csv
outputs/rank_reference/rank_reference_summary.json
```

### 3. Ejecutar análisis completo

```powershell
python src/run_full_analysis.py "PoloGB#LAS" --skip-scraper
```

Esto genera el análisis final del jugador:

```text
outputs/recent_predictions/final_player_analysis.json
docs/final_player_analysis.json
```

### 4. Exportar datos generales de la web

```powershell
python scripts/export_web_data.py
```

Esto actualiza:

```text
docs/web_data.json
```

---

## Notas importantes

### 1. Sobre GitHub Pages

GitHub Pages no ejecuta Python.
Por eso la versión pública funciona con archivos JSON previamente generados.

### 2. Sobre el scraper

El scraper sí está implementado y funciona localmente.
Permite descargar partidas recientes desde Tracker.gg usando Playwright.

### 3. Sobre el backend online

Se probó ejecutar el backend online con Render, pero el scraping en vivo requiere más memoria que la disponible en el plan gratuito.
Por eso la versión pública se dejó como demo estática y el análisis en vivo se mantiene en ejecución local.

### 4. Sobre la clasificación

La clasificación supervisada predice los perfiles generados previamente por clustering.
Eso significa que el clasificador aprende a reproducir los perfiles descubiertos, no una verdad absoluta entregada por etiquetas humanas externas.

### 5. Sobre los perfiles secundarios

Un jugador no siempre pertenece de forma completamente rígida a una sola categoría.
Por eso el proyecto también muestra un perfil secundario para reflejar estilos híbridos.

### 6. Sobre los jugadores similares

La comparación de jugadores similares se realiza contra una base de referencia construida con partidas reales.
El sistema filtra jugadores por grupo de rango de lobby y luego compara métricas de rendimiento.

### 7. Sobre la interpretación

El sistema no pretende reemplazar el análisis experto del juego, sino entregar una interpretación estadística útil, clara y visual.

---

## Datasets utilizados

El proyecto utiliza distintas fuentes de datos, separadas según su propósito dentro del pipeline.

### 1. Dataset histórico base


```md
data/val_stats.csv
```

Este dataset contiene estadísticas históricas de jugadores de Valorant. Se utiliza principalmente para:

* construir variables derivadas;
* aplicar clustering;
* descubrir perfiles de jugador;
* entrenar clasificadores supervisados;
* generar los datos generales de la web.

### 2. Partidas recientes del jugador objetivo

Archivo:

```text
data/recent_matches.csv
```

Este archivo contiene las últimas partidas competitivas extraídas mediante el scraper para un jugador específico. En la demo pública se utiliza el jugador:

```text
PoloGB#LAS
```

Estas partidas se usan para generar:

* resumen reciente del jugador;
* predicción de rendimiento;
* predicción de estilo;
* análisis de tendencia;
* recomendaciones personalizadas.

### 3. Jugadores de referencia

Archivos:

```text
data/reference_players.csv
data/rank_reference_matches.csv
data/rank_reference_profiles.csv
```

Estos archivos se utilizan para construir una base de comparación. El sistema extrae partidas de jugadores de referencia, calcula perfiles agregados y luego compara al jugador objetivo con referentes de lobbies similares.

### 4. Archivos generados para la web

Archivos:

```text
docs/web_data.json
docs/final_player_analysis.json
```

Estos archivos permiten que la versión pública en GitHub Pages funcione como demo estática, sin necesidad de ejecutar Python en el servidor.

---

## Resultados principales

La versión actual del proyecto permite analizar un jugador de Valorant a partir de sus partidas competitivas recientes.

Para el caso de prueba `PoloGB#LAS`, el sistema generó los siguientes resultados:

* partidas recientes analizadas: 20;
* rendimiento global detectado: Alto;
* estilo principal detectado: Apoyo táctico;
* estilo secundario detectado: Alto impacto;
* tendencia competitiva reciente: Subida probable;
* comparación contra jugadores de lobbies similares;
* generación de recomendaciones personalizadas.

Además, la base de referencia utilizada para comparar jugadores incluye:

* 128 jugadores de referencia;
* 2560 partidas de referencia;
* 20 partidas por jugador de referencia.

En la etapa de modelado se aplicaron técnicas de minería de datos como:

* clustering con K-Means;
* evaluación mediante silhouette score y Davies-Bouldin;
* clasificación con Random Forest;
* análisis temporal de rendimiento;
* búsqueda de jugadores similares mediante Nearest Neighbors con similitud coseno.

Estos resultados se integran en el dashboard web, donde se muestran métricas, gráficos, perfiles, brechas frente al grupo similar, predicción por partida y recomendaciones.

---

## Reproducción rápida del análisis de demo

Para reproducir el análisis usado en la demo pública, ejecutar:

```powershell
python data/tracker/scraper_valorant.py "PoloGB#LAS"
python src/rank_reference_features.py
python src/run_full_analysis.py "PoloGB#LAS" --skip-scraper
python scripts/export_web_data.py
```

Luego iniciar la versión local con backend:

```powershell
uvicorn backend.api:app --reload
```

Abrir en el navegador:

```text
http://localhost:8000
```

También se puede revisar la versión pública en GitHub Pages, que utiliza los JSON previamente generados:

```text
https://jeanalexandrevergarausm.github.io/ValoStats/
```

---

## Estado del proyecto

El proyecto se encuentra funcional con:

* scraper local implementado;
* pipeline completo de minería de datos;
* limpieza y transformación de datos;
* generación de variables derivadas;
* clustering interpretado;
* clasificación supervisada;
* análisis de tendencia competitiva;
* comparación con jugadores similares;
* recomendaciones personalizadas;
* backend local con FastAPI;
* demo pública en GitHub Pages con jugador precargado.

La versión pública permite visualizar el análisis ya generado.
La versión local permite ejecutar el flujo completo con scraping en vivo.



