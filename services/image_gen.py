import requests
from config import Config

# Stable Diffusion XL produces high quality images and works perfectly on the free tier!
API_URL = "https://router.huggingface.co/hf-inference/models/stabilityai/stable-diffusion-xl-base-1.0"

def generate_image_bytes(prompt: str) -> bytes:
    """
    Sends a prompt to Hugging Face and returns the generated image as raw bytes.
    """
    if not Config.IMAGE_GEN_KEY or "sk_" in Config.IMAGE_GEN_KEY:
        raise Exception("Invalid or missing Hugging Face API Key!")

    headers = {
        "Authorization": f"Bearer {Config.IMAGE_GEN_KEY}"
    }
    payload = {
        "inputs": prompt
    }
    
    # We use a 60 second timeout because image generation can take 10-20 seconds
    response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
    
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"Image API Error {response.status_code}: {response.text}")