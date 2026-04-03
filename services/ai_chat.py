import base64
from groq import AsyncGroq
from config import Config
from utils.logger import get_logger

logger = get_logger(__name__)

# Enhanced System Instruction for "Varsity Level" reasoning, math, and code.
# Forbids LaTeX for Telegram clarity.
SYSTEM_INSTRUCTION = (
    "You are a 'Varsity Level' AI assistant specializing in advanced logic, mathematics, and complex programming. "
    "When solving problems: "
    "1. Show your step-by-step thinking for math and logic. "
    "2. Provide clean, efficient code for programming tasks. "
    "3. Format all responses as clean, readable plain text for Telegram. "
    "4. CRITICAL: Do NOT use LaTeX notations like \\frac, \\sqrt, or $ symbols. "
    "   Instead, use human-readable symbols: / for division, * for multiplication, ^ for powers. "
    "   Example: Use (x + 1) / (y - 2) instead of \\frac{x+1}{y-2}. "
    "5. Do NOT use markdown symbols like **, __, ##, or bullet dashes. "
    "6. Use emojis to organise sections instead. "
    "7. Keep responses concise but intellectually rigorous."
)

# Initialize the Groq client
client = AsyncGroq(api_key=Config.GROQ_API_KEY)

async def get_ai_response(prompt: str, image_bytes: bytes = None) -> str:
    """Gets AI response from Llama 4 Scout (Multimodal) on Groq."""
    try:
        if not Config.GROQ_API_KEY:
            return "🔧 Error: GROQ_API_KEY is not set in environment variables."

        messages = [
            {"role": "system", "content": SYSTEM_INSTRUCTION}
        ]

        # In 2026, Groq's high-end multimodal model is Llama 4 Scout
        model_id = "meta-llama/llama-4-scout-17b-16e-instruct"

        if image_bytes:
            # Encode image as base64 for Groq Vision
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                        },
                    },
                ],
            })
        else:
            messages.append({"role": "user", "content": prompt})

        # Call the Groq chat completions API
        response = await client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
        )

        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"Groq API Error: {e}")
        return f"🔧 Error: {str(e)}"