# Prototipo antiguo.
# La versión final del proyecto se encuentra en docs/ y backend/api.py.

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import MinMaxScaler

from src.preprocessing import (
    load_data,
    clean_data,
    create_features,
    select_model_data,
    scale_data,
)


st.set_page_config(
    page_title="Valostats",
    page_icon="V",
    layout="wide",
    initial_sidebar_state="collapsed",
)


st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Rajdhani', sans-serif;
    }

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(255,70,85,0.22), transparent 28%),
            radial-gradient(circle at top right, rgba(90,90,255,0.22), transparent 28%),
            linear-gradient(135deg, #080b12 0%, #101827 45%, #090b10 100%);
        color: #f5f7fb;
    }

    section[data-testid="stSidebar"] {
        background: #0b111d;
        border-right: 1px solid rgba(255,255,255,0.08);
    }

    .hero {
        padding: 42px 46px;
        border-radius: 28px;
        background:
            linear-gradient(135deg, rgba(255,70,85,0.92), rgba(89,45,125,0.75)),
            url("https://images.contentstack.io/v3/assets/bltb6530b271fddd0b1/blt8f8f541c7b5416ea/5eb26f54402b8b4d13a56656/agent-background-generic.JPG");
        background-size: cover;
        background-position: center;
        box-shadow: 0 18px 50px rgba(0,0,0,0.45);
        margin-bottom: 24px;
    }

    .hero h1 {
        font-size: 72px;
        font-weight: 700;
        margin: 0;
        letter-spacing: 2px;
        color: white;
    }

    .hero p {
        font-size: 24px;
        max-width: 850px;
        color: #e7e9f2;
        margin-top: 8px;
    }

    .badge {
        display: inline-block;
        background: rgba(0,0,0,0.35);
        border: 1px solid rgba(255,255,255,0.18);
        border-radius: 999px;
        padding: 8px 16px;
        margin-bottom: 14px;
        font-weight: 700;
        color: #ffffff;
    }

    .card {
        background: rgba(13, 19, 32, 0.88);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 22px;
        padding: 22px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.35);
        min-height: 132px;
    }

    .card h3 {
        color: #9aa7bd;
        font-size: 18px;
        margin-bottom: 8px;
    }

    .big-number {
        font-size: 42px;
        font-weight: 700;
        color: #ffffff;
    }

    .accent {
        color: #ff4655;
        font-weight: 700;
    }

    .recommendation {
        background: linear-gradient(135deg, rgba(255,70,85,0.95), rgba(118,58,186,0.95));
        border-radius: 22px;
        padding: 24px;
        font-size: 22px;
        font-weight: 600;
        color: white;
        box-shadow: 0 12px 34px rgba(255,70,85,0.22);
    }

    .section-title {
        font-size: 34px;
        font-weight: 700;
        margin-top: 28px;
        margin-bottom: 12px;
        color: white;
    }

    div[data-testid="stMetric"] {
        background: rgba(13, 19, 32, 0.82);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 18px;
        padding: 18px;
        box-shadow: 0 10px 24px rgba(0,0,0,0.22);
    }

    div[data-testid="stMetricValue"] {
        color: #ffffff;
        font-size: 30px;
    }

    div[data-testid="stMetricLabel"] {
        color: #a7b1c5;
        font-size: 16px;
    }

    .stSelectbox label, .stRadio label {
        color: #dbe4ff !important;
        font-size: 18px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def prepare_data():
    raw_df = load_data(str(PROJECT_ROOT / "data" / "val_stats.csv"))
    clean_df = clean_data(raw_df)
    feature_df = create_features(clean_df)

    model_df = select_model_data(feature_df)
    scaled_df, scaler = scale_data(model_df)

    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(scaled_df)

    feature_df["cluster"] = clusters

    cluster_names = {
        0: "Soporte",
        1: "Agresivo",
        2: "Táctico",
    }

    feature_df["player_type"] = feature_df["cluster"].map(cluster_names)

    pca = PCA(n_components=2)
    pca_result = pca.fit_transform(scaled_df)

    feature_df["pca_1"] = pca_result[:, 0]
    feature_df["pca_2"] = pca_result[:, 1]

    X = scaled_df
    y = feature_df["player_type"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    model = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
    )

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    return feature_df, model_df, scaled_df, scaler, model, accuracy


def generate_recommendation(row):
    player_type = row["player_type"]
    precision = row["precision"]
    agresividad = row["agresividad"]
    impacto = row["impacto"]
    soporte = row["soporte"]

    if player_type == "Agresivo":
        if precision < 24:
            return "Perfil agresivo detectado. Tienes alta capacidad ofensiva, pero podrías mejorar precisión, control de recoil y selección de duelos."
        return "Perfil agresivo sólido. Tu estilo destaca por presión ofensiva, precisión y eficiencia en combate."

    if player_type == "Soporte":
        if soporte < 0.35:
            return "Perfil de soporte detectado, pero con margen para participar más en asistencias y utilidad de equipo."
        return "Perfil de soporte claro. Tu aporte se orienta al juego cooperativo, asistencias y acompañamiento del equipo."

    if player_type == "Táctico":
        if impacto < 80:
            return "Perfil táctico detectado. Se recomienda aumentar impacto en rondas clave mediante clutches, first bloods o mejores decisiones de rotación."
        return "Perfil táctico de alto impacto. Tu estilo destaca por influencia en rondas decisivas y buena lectura del juego."

    return "Perfil no identificado."


feature_df, model_df, scaled_df, scaler, model, accuracy = prepare_data()
feature_df["recommendation"] = feature_df.apply(generate_recommendation, axis=1)


st.markdown(
    """
    <div class="hero">
        <div class="badge">VALORANT DATA MINING PROJECT · TEL354</div>
        <h1>VALOSTATS</h1>
        <p>
        Plataforma de análisis de jugadores de Valorant basada en clustering,
        clasificación y recomendaciones personalizadas.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


menu = st.sidebar.radio(
    "Navegación",
    [
        "Home",
        "Buscar jugador",
        "Clusters",
        "Perfiles",
        "Dataset",
    ],
)


if menu == "Home":
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Jugadores analizados", f"{len(feature_df):,}")

    with col2:
        st.metric("Variables usadas", model_df.shape[1])

    with col3:
        st.metric("Perfiles detectados", feature_df["player_type"].nunique())

    with col4:
        st.metric("Accuracy demo", f"{accuracy:.2%}")

    st.markdown('<div class="section-title">Resumen de perfiles</div>', unsafe_allow_html=True)

    profile_counts = feature_df["player_type"].value_counts().reset_index()
    profile_counts.columns = ["Perfil", "Cantidad"]

    fig = px.bar(
        profile_counts,
        x="Perfil",
        y="Cantidad",
        color="Perfil",
        template="plotly_dark",
        title="Distribución de perfiles detectados",
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-title">¿Qué hace Valostats?</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(
            """
            <div class="card">
                <h3>1. Descubre perfiles</h3>
                <div class="big-number">Clustering</div>
                <p>Agrupa jugadores según estadísticas reales de rendimiento.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            """
            <div class="card">
                <h3>2. Predice estilos</h3>
                <div class="big-number">Random Forest</div>
                <p>Clasifica jugadores según los perfiles encontrados.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            """
            <div class="card">
                <h3>3. Recomienda mejoras</h3>
                <div class="big-number">Feedback</div>
                <p>Entrega sugerencias personalizadas por tipo de jugador.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


elif menu == "Buscar jugador":
    st.markdown('<div class="section-title">Buscar jugador</div>', unsafe_allow_html=True)

    names = sorted(feature_df["name"].dropna().astype(str).unique())

    selected_player = st.selectbox(
        "Selecciona un jugador del dataset",
        names,
    )

    player_row = feature_df[feature_df["name"].astype(str) == selected_player].iloc[0]

    st.markdown(
        f"""
        <div class="card">
            <h3>PLAYER PROFILE</h3>
            <div class="big-number">{selected_player}</div>
            <p>Perfil detectado: <span class="accent">{player_row["player_type"]}</span></p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Kills", int(player_row["kills"]))

    with col2:
        st.metric("Deaths", int(player_row["deaths"]))

    with col3:
        st.metric("K/D", f"{player_row['kd_ratio']:.2f}")

    with col4:
        st.metric("Headshot %", f"{player_row['headshot_percent']:.1f}%")

    st.markdown('<div class="section-title">Recomendación personalizada</div>', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="recommendation">
            {player_row["recommendation"]}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">Estadísticas del jugador</div>', unsafe_allow_html=True)

    player_stats = pd.DataFrame(
        {
            "Métrica": ["Agresividad", "Precisión", "Impacto", "Soporte", "Eficiencia"],
            "Valor": [
                player_row["agresividad"],
                player_row["precision"],
                player_row["impacto"],
                player_row["soporte"],
                player_row["eficiencia"],
            ],
        }
    )

    fig = px.bar(
        player_stats,
        x="Métrica",
        y="Valor",
        color="Métrica",
        template="plotly_dark",
        title="Perfil individual",
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
    )

    st.plotly_chart(fig, use_container_width=True)


elif menu == "Clusters":
    st.markdown('<div class="section-title">Clusters visualizados con PCA</div>', unsafe_allow_html=True)

    fig = px.scatter(
        feature_df,
        x="pca_1",
        y="pca_2",
        color="player_type",
        hover_data=[
            "name",
            "kills",
            "deaths",
            "assists",
            "headshot_percent",
            "kd_ratio",
        ],
        template="plotly_dark",
        title="Proyección PCA de jugadores por perfil",
    )

    fig.update_traces(marker=dict(size=7, opacity=0.75))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
    )

    st.plotly_chart(fig, use_container_width=True)

    st.info(
        "PCA reduce las variables numéricas del dataset a dos dimensiones para visualizar los grupos encontrados por clustering."
    )


elif menu == "Perfiles":
    st.markdown('<div class="section-title">Comparación de perfiles</div>', unsafe_allow_html=True)

    radar_features = [
        "agresividad",
        "precision",
        "impacto",
        "soporte",
        "eficiencia",
    ]

    profile_summary = feature_df.groupby("player_type")[radar_features].mean()

    scaler_radar = MinMaxScaler()

    profile_summary_scaled = pd.DataFrame(
        scaler_radar.fit_transform(profile_summary),
        columns=profile_summary.columns,
        index=profile_summary.index,
    )

    fig = go.Figure()

    for player_type in profile_summary_scaled.index:
        fig.add_trace(
            go.Scatterpolar(
                r=profile_summary_scaled.loc[player_type].values,
                theta=radar_features,
                fill="toself",
                name=player_type,
            )
        )

    fig.update_layout(
        template="plotly_dark",
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                visible=True,
                range=[0, 1],
            ),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        showlegend=True,
        title="Radar chart normalizado por perfil",
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-title">Valores reales promedio</div>', unsafe_allow_html=True)
    st.dataframe(profile_summary)


elif menu == "Dataset":
    st.markdown('<div class="section-title">Dataset procesado</div>', unsafe_allow_html=True)

    st.write("Primeras 200 filas del dataset enriquecido:")
    st.dataframe(feature_df.head(200))

    st.markdown('<div class="section-title">Variables usadas por el modelo</div>', unsafe_allow_html=True)
    st.write(model_df.columns.tolist())