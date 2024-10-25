from openai import OpenAI
import base64
import os

api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)


def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def analyze_images(before_fall_image_base64, fall_image_base64):
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

    return response.choices[0]


def main():
    # URLs a las imágenes (puedes subir tus imágenes a un servidor o usar imágenes públicas)
    before_fall_image_path = (
        "./fall_images/20241024_021419/track_2_frame_0.png"  # Cambia esta ruta
    )
    fall_image_path = (
        "./fall_images/20241024_021419/track_2_frame_1.png"  # Cambia esta ruta
    )

    # Convertir imágenes a base64
    before_fall_image_base64 = encode_image_to_base64(before_fall_image_path)
    fall_image_base64 = encode_image_to_base64(fall_image_path)

    # Analizar imágenes
    analysis_response = analyze_images(before_fall_image_base64, fall_image_base64)

    # Mostrar la respuesta
    print("Respuesta de la API de OpenAI:")
    print(analysis_response)


if __name__ == "__main__":
    main()
