
@bp.route("/que-es")
def que_es():
    return render_template("que_es.html")

@bp.route("/vista-previa")
def vista_previa():
    return render_template("vista_previa.html")

@bp.route("/incluye")
def incluye():
    return render_template("incluye.html")

@bp.route("/preguntas")
def preguntas():
    return render_template("preguntas.html")

@bp.route("/resenas")
def resenas_page():
    reales_rows = database.list_resenas_aprobadas_todas()

    resenas_reales = []
    for r in reales_rows:
        resenas_reales.append(dict(r))

    total_count, avg = database.resumen_resenas_aprobadas()

    return render_template(
        "resenas.html",
        resenas_aprobadas=resenas_reales,
        total_count=total_count,
        avg=avg,
    )
