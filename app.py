from flask import Flask, request, send_file, render_template_string, flash, redirect, url_for, session
from PIL import Image
import io
import zipfile
from PyPDF2 import PdfReader, PdfWriter
import fitz  # PyMuPDF
from flask_session import Session

app = Flask(__name__)
app.secret_key = "convertDMCsecret"
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Página principal
HTML_PAGE = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>ConvertDMC</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body { background: #f8f9fa; }
.card { max-width: 700px; margin: 50px auto; padding: 30px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);}
h1 { font-weight: bold; color: #0072ff; margin-bottom: 20px; }
.btn-primary { font-weight: bold; }
</style>
</head>
<body>
<div class="card text-center">
  <h1>🌀 ConvertDMC</h1>
  <p>Sube tu archivo y selecciona la operación:</p>
  
  {% with messages = get_flashed_messages() %}
    {% if messages %}
      <div class="alert alert-info" role="alert">
        {% for msg in messages %}
          {{ msg }}<br>
        {% endfor %}
      </div>
    {% endif %}
  {% endwith %}
  
  <form action="/convert" method="post" enctype="multipart/form-data">
    <div class="mb-3">
      <select class="form-select" name="option" required>
        <option value="JPG a TIF">JPG a TIF</option>
        <option value="TIF a PDF">TIF a PDF (multipágina)</option>
        <option value="TIF a JPG">TIF a JPG</option>
        <option value="PDF a TIF">PDF a TIF (multipágina)</option>
        <option value="Separar PDF">Separar PDF</option>
        <option value="ZIP de imágenes a PDF">ZIP de imágenes a PDF</option>
      </select>
    </div>
    <div class="mb-3">
      <input class="form-control" type="file" name="file" required>
    </div>
    <button class="btn btn-primary btn-lg" type="submit">Convertir</button>
  </form>
  
  <hr>
  <p>📊 Conversiones realizadas en esta sesión: {{ session.get('contador', 0) }}</p>
  <p>🌐 Desarrollado por Daniel Chumbipuma - <strong>ConvertDMC</strong></p>
</div>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    if "contador" not in session:
        session["contador"] = 0
    return render_template_string(HTML_PAGE)

@app.route("/convert", methods=["POST"])
def convert():
    option = request.form["option"]
    uploaded_file = request.files["file"]

    if "contador" not in session:
        session["contador"] = 0

    try:
        if option == "JPG a TIF":
            image = Image.open(uploaded_file)
            buf = io.BytesIO()
            image.save(buf, format="TIFF")
            buf.seek(0)
            session["contador"] += 1
            return send_file(buf, download_name="convertido.tif", as_attachment=True)

        elif option == "TIF a PDF":
            image = Image.open(uploaded_file)
            images = []
            try:
                while True:
                    images.append(image.copy().convert("RGB"))
                    image.seek(image.tell() + 1)
            except EOFError:
                pass
            buf = io.BytesIO()
            images[0].save(buf, format="PDF", save_all=True, append_images=images[1:])
            buf.seek(0)
            session["contador"] += 1
            return send_file(buf, download_name="convertido.pdf", as_attachment=True)

        elif option == "TIF a JPG":
            image = Image.open(uploaded_file).convert("RGB")
            buf = io.BytesIO()
            image.save(buf, format="JPEG")
            buf.seek(0)
            session["contador"] += 1
            return send_file(buf, download_name="convertido.jpg", as_attachment=True)

        elif option == "PDF a TIF":
            doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            images = []
            for page in doc:
                pix = page.get_pixmap(dpi=200)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                images.append(img.convert("RGB"))
            buf = io.BytesIO()
            images[0].save(buf, format="TIFF", save_all=True, append_images=images[1:])
            buf.seek(0)
            session["contador"] += 1
            return send_file(buf, download_name="convertido.tif", as_attachment=True)

        elif option == "Separar PDF":
            reader = PdfReader(uploaded_file)
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zip_file:
                for i, page in enumerate(reader.pages):
                    writer = PdfWriter()
                    writer.add_page(page)
                    page_buf = io.BytesIO()
                    writer.write(page_buf)
                    page_buf.seek(0)
                    zip_file.writestr(f"pagina_{i+1}.pdf", page_buf.read())
            zip_buf.seek(0)
            session["contador"] += 1
            return send_file(zip_buf, download_name="separado.zip", as_attachment=True)

        elif option == "ZIP de imágenes a PDF":
            images = []
            with zipfile.ZipFile(uploaded_file, "r") as archive:
                file_list = sorted(archive.namelist())
                for file in file_list:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                        with archive.open(file) as img_file:
                            img = Image.open(img_file).convert("RGB")
                            images.append(img)
            if images:
                buf = io.BytesIO()
                images[0].save(buf, format="PDF", save_all=True, append_images=images[1:])
                buf.seek(0)
                session["contador"] += 1
                return send_file(buf, download_name="imagenes_convertidas.pdf", as_attachment=True)
            else:
                flash("No se encontraron imágenes válidas en el ZIP")
                return redirect(url_for("index"))
        else:
            flash("Opción no válida")
            return redirect(url_for("index"))

    except Exception as e:
        flash(f"Error: {str(e)}")
        return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

