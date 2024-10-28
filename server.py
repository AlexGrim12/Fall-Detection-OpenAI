from flask import Flask, request, jsonify
import os
from datetime import datetime
import base64
from openai import OpenAI
from pymongo import MongoClient
from dotenv import load_dotenv
import certifi
import cloudinary
import cloudinary.uploader
import cloudinary.api
from bson import ObjectId

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)

# Configuración de MongoDB Atlas
MONGO_URI = "mongodb+srv://AlexGrim:Alexgrim612@asterionsecurity.kqftf.mongodb.net/?retryWrites=true&w=majority&appName=AsterionSecurity"

# Configuración de Cloudinary y OpenAI (mantenido igual)
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# Variables globales para MongoDB
mongo_client = None
falls_collection = None


def init_mongodb():
    global mongo_client, falls_collection
    try:
        mongo_client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
        mongo_client.admin.command("ping")
        print("¡Conexión exitosa a MongoDB!")
        db = mongo_client.fall_detection
        falls_collection = db.falls
    except Exception as e:
        print(f"Error conectando a MongoDB Atlas: {e}")
        raise e


# Inicializar MongoDB
init_mongodb()


# Funciones auxiliares existentes (upload_image_to_cloudinary, analyze_images) se mantienen igual...
def upload_image_to_cloudinary(image, folder, public_id):
    """Sube una imagen a Cloudinary y retorna la URL."""
    try:
        result = cloudinary.uploader.upload(
            image, folder=folder, public_id=public_id, resource_type="image"
        )
        return {"url": result["secure_url"], "public_id": result["public_id"]}
    except Exception as e:
        print(f"Error al subir imagen a Cloudinary: {e}")
        return None


def analyze_images(before_fall_image_url, fall_image_url):
    """Envía las URLs de imágenes a la API de OpenAI para análisis."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Corrected model name
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "These images are screenshots from a fall detection system. Provide a brief description of the causes for the fall.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": before_fall_image_url},
                        },
                        {"type": "image_url", "image_url": {"url": fall_image_url}},
                    ],
                }
            ],
            max_tokens=300,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error en el análisis de OpenAI: {e}")
        return "Error en el análisis de imágenes"


@app.route("/fall_alert", methods=["POST"])
def fall_alert():
    try:
        data = request.form.to_dict()

        if "track_id" not in data:
            return (
                jsonify({"status": "error", "message": "track_id no proporcionado"}),
                400,
            )

        timestamp = datetime.now()
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")

        # Procesamiento de imágenes y análisis OpenAI (mantenido igual)
        images = request.files.getlist("images")
        cloudinary_urls = []

        for i, image in enumerate(images):
            public_id = f"falls/{timestamp_str}/track_{data['track_id']}_frame_{i}"
            upload_result = upload_image_to_cloudinary(
                image, folder="fall_detection", public_id=public_id
            )
            if upload_result:
                cloudinary_urls.append(upload_result["url"])
            else:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": "Error al subir imágenes a Cloudinary",
                        }
                    ),
                    500,
                )

        analysis_response = "No hay suficientes imágenes para análisis."
        if len(cloudinary_urls) >= 2:
            analysis_response = analyze_images(cloudinary_urls[0], cloudinary_urls[1])

        # Nuevo formato de documento para MongoDB que coincide con el frontend
        fall_document = {
            "userId": data.get("userId", "unknown"),
            "userName": data.get("userName", "Usuario Desconocido"),
            "roomNumber": data.get("roomNumber", "Sin Asignar"),
            "title": "Detección de Caída",
            "description": analysis_response,
            "createdAt": timestamp.isoformat(),
            "status": "pending",
            "type": "fall-detection",
            "priority": "high",
            "images": cloudinary_urls,
            "track_id": data["track_id"],
            "additional_data": {
                "original_timestamp": timestamp_str,
                "analysis_details": analysis_response,
            },
        }

        result = falls_collection.insert_one(fall_document)

        return jsonify(
            {
                "status": "success",
                "message": "Alerta procesada y guardada",
                "notification_id": str(result.inserted_id),
                "data": fall_document,
            }
        )

    except Exception as e:
        print(f"Error detallado: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/notifications", methods=["GET"])
def get_notifications():
    try:
        # Obtener parámetros de consulta
        userId = request.args.get("userId")
        type = request.args.get("type")
        priority = request.args.get("priority")
        status = request.args.get("status")

        # Construir el filtro de MongoDB
        query = {}
        if userId:
            query["userId"] = userId
        if type:
            query["type"] = type
        if priority:
            query["priority"] = priority
        if status:
            query["status"] = status

        # Realizar la consulta a MongoDB
        notifications = list(falls_collection.find(query).sort("createdAt", -1))

        # Convertir ObjectId a string para serialización JSON
        for notification in notifications:
            notification["_id"] = str(notification["_id"])

        return jsonify(notifications)

    except Exception as e:
        print(f"Error al obtener notificaciones: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/notifications/<notification_id>", methods=["PUT"])
def update_notification_status(notification_id):
    try:
        data = request.json
        new_status = data.get("status")

        if not new_status:
            return (
                jsonify({"status": "error", "message": "Status no proporcionado"}),
                400,
            )

        result = falls_collection.update_one(
            {"_id": ObjectId(notification_id)}, {"$set": {"status": new_status}}
        )

        if result.modified_count > 0:
            return jsonify({"status": "success", "message": "Estado actualizado"})
        else:
            return (
                jsonify({"status": "error", "message": "Notificación no encontrada"}),
                404,
            )

    except Exception as e:
        print(f"Error al actualizar notificación: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(port=5000, debug=True)
