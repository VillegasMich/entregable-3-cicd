"""Aplicación Flask que expone una calculadora web simple."""

from flask import Flask, render_template, request
from .calculadora import sumar, restar, multiplicar, dividir

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-insecure-key")


OPERACIONES = {
    "sumar": sumar,
    "restar": restar,
    "multiplicar": multiplicar,
    "dividir": dividir,
}


@app.route("/", methods=["GET"])
def index():
    """Renderiza el formulario vacío de la calculadora."""
    return render_template("index.html", resultado=None)


@app.route("/", methods=["POST"])
def calcular():
    """Calcula el resultado de la operación enviada mediante el formulario."""
    try:
        num1 = float(request.form["num1"])
        num2 = float(request.form["num2"])
        operacion = request.form["operacion"]

        operador = OPERACIONES.get(operacion)
        if operador is None:
            resultado = "Operación no válida"
        else:
            resultado = operador(num1, num2)
    except ValueError:
        resultado = "Error: Introduce números válidos"
    except ZeroDivisionError:
        resultado = "Error: No se puede dividir por cero"

    return render_template("index.html", resultado=resultado)


@app.route("/health")
def health():
    return "OK", 200


if __name__ == "__main__":  # pragma: no cover
    app_port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, port=app_port, host="127.0.0.1")
