"""
Conservatory Timber Roof Calculator — Flask Application
"""

import io
import os
import traceback

from flask import Flask, render_template, request, send_file, jsonify

from utils.calculations import ConservatoryRoof
from utils.pdf_generator import generate_pdf

app = Flask(__name__)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/calculate", methods=["POST"])
def calculate():
    errors = []

    def _float(name, default=None, label=None):
        raw = request.form.get(name, "").strip()
        if not raw:
            if default is not None:
                return default
            errors.append(f"{label or name} is required.")
            return None
        try:
            return float(raw)
        except ValueError:
            errors.append(f"{label or name} must be a number.")
            return None

    length   = _float("length",   label="Conservatory length")
    width    = _float("width",    label="Conservatory width")
    pitch    = _float("pitch",    default=30.0,  label="Roof pitch")
    overhang = _float("overhang", default=300.0, label="Overhang")
    spacing  = _float("spacing",  default=600.0, label="Rafter spacing")

    if errors:
        return render_template("index.html", errors=errors,
                               form=request.form)

    try:
        roof = ConservatoryRoof(
            length_m=length,
            width_m=width,
            pitch_deg=pitch,
            overhang_mm=overhang,
            rafter_spacing_mm=spacing,
        )
        results = roof.calculate()
        # Store spacing for diagram helper
        results["spacing_mm"] = spacing
    except ValueError as e:
        errors.append(str(e))
        return render_template("index.html", errors=errors,
                               form=request.form)
    except Exception:
        errors.append("An unexpected error occurred. Please check your inputs.")
        traceback.print_exc()
        return render_template("index.html", errors=errors,
                               form=request.form)

    return render_template("results.html", r=results,
                           length=length, width=width,
                           pitch=pitch, overhang=overhang, spacing=spacing)


@app.route("/download-pdf", methods=["POST"])
def download_pdf():
    errors = []

    def _float(name, default=None):
        raw = request.form.get(name, "").strip()
        if not raw:
            return default
        try:
            return float(raw)
        except ValueError:
            return default

    length   = _float("length")
    width    = _float("width")
    pitch    = _float("pitch",    default=30.0)
    overhang = _float("overhang", default=300.0)
    spacing  = _float("spacing",  default=600.0)

    if not length or not width:
        return "Missing dimensions", 400

    try:
        roof = ConservatoryRoof(
            length_m=length,
            width_m=width,
            pitch_deg=pitch,
            overhang_mm=overhang,
            rafter_spacing_mm=spacing,
        )
        results = roof.calculate()
        results["spacing_mm"] = spacing
        pdf_bytes = generate_pdf(results)
    except Exception:
        traceback.print_exc()
        return "Error generating PDF. Please try again.", 500

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=(
            f"conservatory_roof_{int(length*100)}x{int(width*100)}_"
            f"{int(pitch)}deg.pdf"
        ),
    )


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, port=5000)
