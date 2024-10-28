from flask import Flask, request, jsonify
import os
from datetime import datetime
import base64
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configuración de OpenAI

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# Directorio base donde se guardarán todas las carpetas de caídas
BASE_IMAGES_FOLDER = "fall_images"
if not os.path.exists(BASE_IMAGES_FOLDER):
    os.makedirs(BASE_IMAGES_FOLDER)


def encode_image_to_base64(image_path):
    """Convierte la imagen en la ruta proporcionada a base64."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def analyze_images(before_fall_image_base64, fall_image_base64):
    """Envía las imágenes a la API de OpenAI para análisis."""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "¿Estas imágenes muestran una caída? Proporciona contexto sobre la situación.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{before_fall_image_base64}"
                        },
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{fall_image_base64}"
                        },
                    },
                ],
            }
        ],
        max_tokens=300,
    )
    # print(before_fall_image_base64)
    # print(fall_image_base64)
    print(response)
    return response.choices[0].message["content"]  # Devuelve la respuesta de OpenAI


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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fall_folder = os.path.join(BASE_IMAGES_FOLDER, timestamp)
        os.makedirs(fall_folder, exist_ok=True)

        # Guardar las imágenes dentro de la carpeta creada
        images = request.files.getlist("images")
        image_paths = []

        for i, image in enumerate(images):
            image_name = f"track_{data['track_id']}_frame_{i}.png"
            image_path = os.path.join(fall_folder, image_name)
            image.save(image_path)
            image_paths.append(image_path)

        # Convertir las dos primeras imágenes a base64 para análisis
        if len(image_paths) >= 2:
            before_fall_image_base64 = encode_image_to_base64(image_paths[0])
            fall_image_base64 = encode_image_to_base64(image_paths[1])
            # Analizar imágenes con OpenAI
            analysis_response = analyze_images(
                before_fall_image_base64, fall_image_base64
            )
            print("Respuesta de la API de OpenAI:", analysis_response)
        else:
            analysis_response = "No hay suficientes imágenes para análisis."

        # Retorna una respuesta indicando éxito
        return jsonify(
            {
                "status": "success",
                "message": "Alerta e imágenes recibidas y guardadas",
                "image_folder": fall_folder,
                "image_paths": image_paths,
                "openai_analysis": analysis_response,
            }
        )

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(port=5000, debug=True)
