# ValoStats

ValoStats es un proyecto de **minería de datos aplicado a estadísticas de jugadores de Valorant**.  
El objetivo del proyecto es **analizar el estilo de juego de un jugador**, asignarle un **perfil principal**, un **perfil secundario**, generar una **interpretación de su forma de jugar** y entregar una **recomendación personalizada** basada en sus estadísticas.

La aplicación final incluye:

- análisis de perfiles de jugadores;
- clustering para descubrir estilos de juego;
- clasificación para predecir el perfil detectado;
- recomendaciones personalizadas;
- una web pública hecha para consultar jugadores de forma visual.

---

## Tabla de contenido

1. [Descripción del proyecto](#descripción-del-proyecto)
2. [Objetivo](#objetivo)
3. [Perfiles de jugador](#perfiles-de-jugador)
4. [Metodología utilizada](#metodología-utilizada)
5. [Estructura del proyecto](#estructura-del-proyecto)
6. [Requisitos](#requisitos)
7. [Instalación](#instalación)
8. [Uso del proyecto](#uso-del-proyecto)
9. [Generar la web](#generar-la-web)
10. [Publicar en GitHub Pages](#publicar-en-github-pages)
11. [Notas importantes](#notas-importantes)

---

## Descripción del proyecto

Este proyecto toma un dataset de estadísticas de jugadores de Valorant y construye un pipeline de análisis para:

- limpiar y preparar los datos;
- crear variables derivadas relevantes;
- descubrir perfiles de jugadores usando clustering;
- interpretar esos perfiles;
- entrenar un clasificador supervisado para predecir el perfil detectado;
- exportar los resultados a una web estática para consulta visual.

La idea principal no es solo mostrar números, sino **transformar estadísticas en una lectura comprensible del estilo de juego de cada jugador**.

---

## Objetivo

El proyecto busca responder preguntas como:

- ¿Qué tipo de jugador es una persona según sus estadísticas?
- ¿Su estilo es más ofensivo, táctico o de alto impacto?
- ¿Qué rasgos secundarios también presenta?
- ¿Qué aspectos debería mejorar?
- ¿Qué tipo de agentes encajan mejor con su perfil?

---

## Perfiles de jugador

El modelo trabaja con tres perfiles principales:

### 1. Alto impacto
Jugador que destaca por generar diferencia en rondas clave.  
Suele tener mayor presencia en jugadas importantes, entradas, clutch o momentos decisivos.

### 2. Apoyo táctico
Jugador que aporta más al equipo mediante apoyo, utilidad, asistencias y juego colectivo.  
No necesariamente lidera en agresividad, pero sí en valor estratégico para el equipo.

### 3. Ofensivo consistente
Jugador que mantiene un rendimiento ofensivo estable.  
Se caracteriza por eficiencia, consistencia y presión sostenida, más que por jugadas explosivas aisladas.

> Importante: estos perfiles no son etiquetas humanas reales entregadas por el dataset.  
> Fueron descubiertos mediante clustering y luego interpretados a partir de sus centroides y métricas promedio.

---

## Metodología utilizada

El proyecto se desarrolló en varias etapas.

### 1. Preprocesamiento
Se cargan los datos y se limpian valores faltantes, tipos de datos, duplicados y columnas numéricas.

### 2. Feature engineering
Se construyen variables nuevas para representar mejor el estilo del jugador, por ejemplo:

- agresividad
- precisión
- impacto
- soporte
- eficiencia
- entry power
- consistencia

### 3. Clustering
Se agrupan jugadores según similitud estadística para descubrir perfiles de juego.

### 4. Interpretación de clusters
Cada cluster se analiza según sus métricas promedio y se le asigna un nombre interpretable.

### 5. Clasificación
Se entrena un modelo supervisado para predecir el perfil detectado por clustering.

### 6. Recomendación
Se generan sugerencias personalizadas según el perfil principal y secundario del jugador.

### 7. Visualización web
Se exportan los datos procesados a una web estática para consultar jugadores y mostrar su análisis.

---

## Estructura del proyecto

```text
ValoStats/
│
├── data/                  # Dataset original
├── docs/                  # Web estática para GitHub Pages
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   └── web_data.json
│
├── notebooks/
│   └── analisis.ipynb     # Notebook principal del proyecto
│
├── outputs/
│   ├── figures/           # Figuras generadas
│   └── metrics/           # Métricas exportadas
│
├── scripts/
│   └── export_web_data.py # Exporta datos procesados a docs/web_data.json
│
├── src/
│   ├── preprocessing.py
│   ├── clustering.py
│   ├── classification.py
│   ├── recommendation.py
│   └── visualization.py
│
├── web/
│   └── app.py             # Versión alternativa / prototipo web en Python
│
├── requirements.txt
├── .gitignore
└── README.md
````

---

## Requisitos

Antes de ejecutar el proyecto, asegúrate de tener instalado:

* Python 3.10 o superior
* pip
* Git, si quieres clonar el repositorio
* Un navegador web moderno para visualizar la página

Dependencias principales del proyecto:

* pandas
* numpy
* matplotlib
* seaborn
* scikit-learn
* plotly
* streamlit
* jupyter
* nbformat
* ipykernel

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/JeanAlexandreVergaraUSM/ValoStats.git
cd ValoStats
```

### 2. Crear un entorno virtual

#### En Git Bash

```bash
python -m venv .venv
source .venv/Scripts/activate
```

#### En PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

Si llegara a faltar alguna dependencia, también puedes instalar manualmente:

```bash
pip install pandas numpy matplotlib seaborn scikit-learn plotly streamlit jupyter nbformat ipykernel
```

---

## Uso del proyecto

El proyecto puede usarse de dos formas principales.

### 1. Análisis en notebook

Para revisar el pipeline completo, el preprocesamiento, clustering, clasificación y visualizaciones, abre Jupyter:

```bash
jupyter notebook
```

Luego entra al archivo:

```text
notebooks/analisis.ipynb
```

### 2. Exportar los datos para la web

Para generar los datos que utiliza la página web:

```bash
python scripts/export_web_data.py
```

Esto creará o actualizará el archivo:

```text
docs/web_data.json
```

Ese archivo contiene la información procesada que luego se muestra en la web.

---

## Generar la web

La web final del proyecto está en la carpeta `docs/`.

### 1. Generar los datos

Primero asegúrate de exportar los datos actualizados:

```bash
python scripts/export_web_data.py
```

### 2. Levantar un servidor local

Desde la carpeta `docs`:

```bash
cd docs
python -m http.server 5500
```

### 3. Abrir la página

En tu navegador entra a:

```text
http://localhost:5500
```

### 4. Qué permite hacer la web

La web permite:

* buscar un jugador por nombre o tag que esté en la base de datos;
* ver su perfil principal;
* ver su perfil secundario;
* ver una interpretación de su estilo de juego;
* ver estadísticas principales;
* comparar sus atributos con el promedio global;
* comparar sus atributos con el promedio de su perfil;
* revisar tops por perfil;
* obtener una recomendación personalizada.

---

## Notas importantes

### 1. Sobre la clasificación

La clasificación supervisada predice los perfiles generados previamente por clustering.
Eso significa que el clasificador **aprende a reproducir los perfiles descubiertos**, no una verdad absoluta entregada por una etiqueta humana externa.

### 2. Sobre los perfiles secundarios

Un jugador no siempre pertenece de forma completamente rígida a una sola categoría.
Por eso el proyecto también muestra un **perfil secundario**, para reflejar estilos híbridos.

### 3. Sobre los rankings web

Los tops muestran solo jugadores con muestra suficiente, para evitar sesgos por jugadores con muy pocas partidas o estadísticas poco representativas.

### 4. Sobre la interpretación

El sistema no pretende reemplazar el análisis experto del juego, sino entregar una interpretación estadística útil, clara y visual.

---

## Tecnologías utilizadas

* Python
* Pandas
* NumPy
* Matplotlib
* Seaborn
* Scikit-learn
* Plotly
* Jupyter Notebook
* HTML
* CSS
* JavaScript
* GitHub Pages

---

## Ejecución rápida

Si alguien quiere probar el proyecto lo más rápido posible:

```bash
git clone https://github.com/JeanAlexandreVergaraUSM/ValoStats.git
cd ValoStats
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
python scripts/export_web_data.py
cd docs
python -m http.server 5500
```

Después abrir:

```text
http://localhost:5500
```

---

## Estado del proyecto

Proyecto funcional con:

* pipeline de datos implementado;
* clustering interpretado;
* clasificación operativa;
* recomendaciones personalizadas;
* web estática lista para despliegue.

```
