import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)


def train_random_forest(X, y, test_size=0.2, random_state=42):
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        random_state=random_state,
        class_weight="balanced"
    )

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)

    feature_importance = pd.DataFrame({
        "feature": X.columns,
        "importance": model.feature_importances_
    }).sort_values(
        by="importance",
        ascending=False
    )

    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "classification_report": classification_report(y_test, y_pred),
        "confusion_matrix": confusion_matrix(y_test, y_pred),
        "classes": model.classes_,
        "probabilities": y_proba,
        "feature_importance": feature_importance
    }

    return model, X_train, X_test, y_train, y_test, y_pred, metrics


def predict_player_profile(model, player_scaled_row):
    prediction = model.predict(player_scaled_row)[0]
    probabilities = model.predict_proba(player_scaled_row)[0]

    confidence = probabilities.max()
    classes = model.classes_

    probability_by_class = {
        cls: prob
        for cls, prob in zip(classes, probabilities)
    }

    return prediction, confidence, probability_by_class