from flask import Flask, request, jsonify
import os
from datetime import datetime

app = Flask(__name__)

# Directorio base donde se guardarán todas las carpetas de caídas
BASE_IMAGES_FOLDER = "fall_images"
if not os.path.exists(BASE_IMAGES_FOLDER):
    os.makedirs(BASE_IMAGES_FOLDER)


@app.route("/fall_alert", methods=["POST"])
def fall_alert():
    try:
        # Recibe los datos de la caída desde el formulario
        data = request.form.to_dict()

        if "track_id" not in data:
            return (
                jsonify({"status": "error", "message": "track_id no proporcionado"}),
                400,
            )

        # Genera una carpeta con la fecha y hora exacta de la caída
        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )  # Fecha y hora en formato AñoMesDía_HoraMinutoSegundo
        fall_folder = os.path.join(
            BASE_IMAGES_FOLDER, timestamp
        )  # Crea la ruta de la carpeta de esta caída
        os.makedirs(fall_folder, exist_ok=True)  # Crea la carpeta si no existe

        # Guardar las imágenes dentro de la carpeta creada
        images = request.files.getlist("images")
        image_paths = []

        for i, image in enumerate(images):
            image_name = f"track_{data['track_id']}_frame_{i}.png"  # Nombrar cada imagen por el ID del track y un índice
            image_path = os.path.join(
                fall_folder, image_name
            )  # Ruta completa donde se guardará la imagen
            image.save(image_path)  # Guarda la imagen en el disco
            image_paths.append(image_path)  # Guarda la ruta para el log

        print(f"Imágenes guardadas en: {image_paths}")

        # Retorna una respuesta indicando éxito
        return jsonify(
            {
                "status": "success",
                "message": "Alerta e imágenes recibidas y guardadas",
                "image_folder": fall_folder,
                "image_paths": image_paths,
            }
        )

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(port=5000, debug=True)
