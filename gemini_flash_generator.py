from .config import get_settings
from .gemini_ai_client import generate_text


def generate_nutrition_tip_with_flash(
    goal: str
) -> str:

    settings = get_settings()

    prompt = f"""
Give one concise, practical nutrition or recovery
tip for a person whose fitness goal is:

{goal}

Keep it general wellness guidance.

Do not provide medical prescriptions.

Avoid:

- calorie targets
- extreme restriction
- supplements
- rapid weight-loss advice

You can mention:

- hydration
- balanced meals
- protein
- fiber
- sleep
- recovery

Maximum 100 words.
"""

    return generate_text(
        prompt,
        settings.tip_model,
        max_output_tokens=250
    )
