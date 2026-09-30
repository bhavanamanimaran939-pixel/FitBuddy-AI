from .config import get_settings
from .gemini_client import generate_text
from .schemas import UserInput


def generate_workout_gemini(
    user: UserInput
) -> str:

    settings = get_settings()

    prompt = f"""
You are FitBuddy, a cautious wellness assistant.

Create a practical 7-day beginner-friendly
fitness plan using the information below.

Name:
{user.name}

Age:
{user.age}

Weight:
{user.weight} kg

Goal:
{user.goal}

Preferred intensity:
{user.intensity}

Requirements:

- Return exactly 7 labeled days.
- Each day must include:
  Focus
  Warm-up
  Main workout
  Cool-down or Recovery
- Include exercise names.
- Include sets/repetitions or time.
- Include sensible rest guidance.
- Include at least one recovery/rest-focused day.
- Keep recommendations age-appropriate.
- Avoid extreme exercise.
- Avoid starvation.
- Avoid rapid weight-loss advice.
- Avoid body-shaming.
- Avoid appearance-based targets.
- Do not diagnose medical conditions.
- Do not prescribe medical treatment.
- If the user may have an injury or health condition,
  recommend professional guidance.
- Keep the plan easy to read.

Return the plan using clear headings and bullet points.
"""

    return generate_text(
        prompt,
        settings.workout_model,
        max_output_tokens=3500
    )