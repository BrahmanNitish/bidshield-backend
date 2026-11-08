import instructor
from openai import OpenAI
from app.config import settings

groq_client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=settings.GROQ_API_KEY,
)

instructor_client = instructor.from_openai(
    groq_client,
    mode=instructor.Mode.JSON,
)

GROQ_MODEL = "openai/gpt-oss-20b"