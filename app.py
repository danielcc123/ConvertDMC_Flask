from flask import Flask, request, send_file, render_template_string
from PIL import Image
import io
import zipfile
from PyPDF2 import PdfReader, PdfWriter
import fitz  # PyMuPDF

app = Flask(__name__)

# Página principal
HTML_PAGE = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>ConvertDMC</title>
<style>
body { font-family: Arial, sans-serif; text-align: center; margin: 50px; }
h1 { color: #0072ff; }
button { padding: 10px 20px; font-size: 16px; margin-top: 10px; }
</style>
</head>
<body>
<h1>🌀 ConvertDMC</h1>
<p>Sube tu archivo y selecciona la operación:</p>
<form action="/convert" method="post" enctype="multipart/form-data">
<select name="option">
<option value="JPG a TIF">JPG a TIF</option>
<option value="TIF a PDF">TIF a PDF</option>
<option value="TIF a JPG">TIF a JPG</option>
<option value="PDF a TIF">PDF a TIF</option>
<option value="Separar PDF">Separar PDF</option>
<option value="ZIP de imágenes a PDF">ZIP de imágenes a PDF</option>
</select><br><br>
<input type="file" name="file" required><br><br>
<button type="submit">Convertir</button>
</form>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_PAGE)

@app.route("/convert", methods=["POST"])
def convert():
    option = request.form["option"]
    uploaded_file = request.files["file"]
    
    if option == "JPG a TIF":
        image = Image.open(uploaded_file)
        buf = io.BytesIO()
        image.save(buf, format="TIFF")
        buf.seek(0)
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
        return send_file(buf, download_name="convertido.pdf", as_attachment=True)
    
    elif option == "TIF a JPG":
        image = Image.open(uploaded_file).convert("RGB")
        buf = io.BytesIO()
        image.save(buf, format="JPEG")
        buf.seek(0)
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
            return send_file(buf, download_name="imagenes_convertidas.pdf", as_attachment=True)
        else:
            return "No se encontraron imágenes válidas en el ZIP", 400
    
    return "Opción no válida", 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
