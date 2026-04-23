from pydantic import BaseModel

class AIQuestion(BaseModel):
    user_id: str
    question: str

class AIResponse(AIQuestion):
    answer: str