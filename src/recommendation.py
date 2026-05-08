def generate_recommendation(row):
    tipo = row["player_type"]
    precision = row["precision"]
    agresividad = row["agresividad"]
    impacto = row["impacto"]
    soporte = row["soporte"]
    win_percent = row["win_percent"]
    consistencia = row["consistencia"]

    recomendaciones = []

    if tipo == "Ofensivo consistente":
        if precision < 22:
            recomendaciones.append(
                "Mejorar precisión con aim training y control de recoil."
            )

        if agresividad < 60:
            recomendaciones.append(
                "Aumentar presencia ofensiva tomando duelos iniciales favorables."
            )

        if win_percent < 50:
            recomendaciones.append(
                "Convertir mejor la presión ofensiva en rondas ganadas."
            )

        recomendaciones.append(
            "Agentes sugeridos: Jett, Reyna, Neon o Raze."
        )

    elif tipo == "Apoyo táctico":
        if soporte < 60:
            recomendaciones.append(
                "Aumentar asistencias mediante mejor uso de utilidad y apoyo al equipo."
            )

        if precision < 20:
            recomendaciones.append(
                "Mejorar precisión para acompañar mejor las entradas del equipo."
            )

        recomendaciones.append(
            "Agentes sugeridos: Sage, Skye, Breach, Killjoy o Cypher."
        )

    elif tipo == "Alto impacto":
        if impacto < 60:
            recomendaciones.append(
                "Aumentar participación en clutches, first bloods o rondas decisivas."
            )

        if consistencia < 60:
            recomendaciones.append(
                "Mejorar consistencia para sostener el impacto durante más rondas."
            )

        recomendaciones.append(
            "Agentes sugeridos: Sova, Fade, KAY/O, Viper u Omen."
        )

    else:
        recomendaciones.append(
            "Perfil balanceado. Mantener consistencia y revisar estadísticas clave."
        )

    return " | ".join(recomendaciones)


def explain_profile(row):
    tipo = row["player_type"]
    secondary = row.get("secondary_profile", None)

    if tipo == "Ofensivo consistente":
        base = (
            "Predomina un estilo ofensivo consistente: el jugador mantiene buen rendimiento "
            "por ronda, estabilidad general y capacidad de presión ofensiva sin depender solo "
            "de jugadas explosivas."
        )

    elif tipo == "Apoyo táctico":
        base = (
            "Predomina un estilo de apoyo táctico: el jugador aporta valor mediante asistencias, "
            "acompañamiento al equipo y contribución al juego colectivo."
        )

    elif tipo == "Alto impacto":
        base = (
            "Predomina un estilo de alto impacto: el jugador destaca por generar ventaja en rondas "
            "clave mediante agresividad, entry power e intervenciones decisivas."
        )

    else:
        base = (
            "El jugador presenta un perfil balanceado, sin una característica dominante única."
        )

    if secondary and secondary != tipo:
        return f"{base} Como rasgo secundario, también muestra tendencias de {secondary.lower()}."

    return base