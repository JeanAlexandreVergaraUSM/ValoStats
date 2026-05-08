import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from sklearn.preprocessing import MinMaxScaler


def plot_k_metrics(k_results):
    fig = px.line(
        k_results,
        x="k",
        y=["silhouette", "davies_bouldin"],
        markers=True,
        template="plotly_dark",
        title="Comparación de métricas de clustering por K"
    )

    return fig


def plot_elbow(k_results):
    fig = px.line(
        k_results,
        x="k",
        y="inertia",
        markers=True,
        template="plotly_dark",
        title="Método del codo usando inercia"
    )

    return fig


def plot_pca_clusters(feature_df):
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
            "win_percent"
        ],
        template="plotly_dark",
        title="Clusters de jugadores visualizados con PCA"
    )

    fig.update_traces(marker=dict(size=7, opacity=0.75))

    return fig


def build_profile_summary(feature_df):
    radar_features = [
        "agresividad",
        "precision",
        "impacto",
        "soporte",
        "eficiencia",
        "entry_power",
        "consistencia"
    ]

    return feature_df.groupby("player_type")[radar_features].mean()


def plot_radar_profiles(feature_df):
    radar_features = [
        "agresividad",
        "precision",
        "impacto",
        "soporte",
        "eficiencia",
        "entry_power",
        "consistencia"
    ]

    profile_summary = feature_df.groupby("player_type")[radar_features].mean()

    scaler = MinMaxScaler()

    profile_summary_scaled = pd.DataFrame(
        scaler.fit_transform(profile_summary),
        columns=profile_summary.columns,
        index=profile_summary.index
    )

    fig = go.Figure()

    for player_type in profile_summary_scaled.index:
        fig.add_trace(
            go.Scatterpolar(
                r=profile_summary_scaled.loc[player_type].values,
                theta=radar_features,
                fill="toself",
                name=player_type
            )
        )

    fig.update_layout(
        template="plotly_dark",
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            )
        ),
        showlegend=True,
        title="Radar chart normalizado por perfil"
    )

    return fig, profile_summary


def plot_feature_importance(feature_importance):
    fig = px.bar(
        feature_importance,
        x="importance",
        y="feature",
        orientation="h",
        template="plotly_dark",
        title="Importancia de variables en Random Forest"
    )

    fig.update_layout(
        yaxis=dict(autorange="reversed")
    )

    return fig