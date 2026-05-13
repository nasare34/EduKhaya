import os
from dotenv import load_dotenv

load_dotenv()

SUPPORTED_LLMS = {
    "groq": {
        "name": "Groq (LLaMA 3)",
        "model": "llama-3.3-70b-versatile",
        "requires_key": "GROQ_API_KEY",
        "available": bool(os.getenv("GROQ_API_KEY"))
    },
    "claude": {
        "name": "Claude (Anthropic)",
        "model": "claude-3-5-sonnet-20241022",
        "requires_key": "ANTHROPIC_API_KEY",
        "available": bool(os.getenv("ANTHROPIC_API_KEY"))
    },
    "chatgpt": {
        "name": "ChatGPT (OpenAI)",
        "model": "gpt-4o",
        "requires_key": "OPENAI_API_KEY",
        "available": bool(os.getenv("OPENAI_API_KEY"))
    },
    "gemini": {
        "name": "Gemini (Google)",
        "model": "gemini-1.5-pro",
        "requires_key": "GEMINI_API_KEY",
        "available": bool(os.getenv("GEMINI_API_KEY"))
    }
}

def build_educational_prompt(generation_type: str, topic: str, grade_level: str, subject: str, context: str, extra: str = "") -> str:
    base = f"""You are an expert educational assistant helping Ghanaian primary and junior high school teachers.
Subject: {subject}
Grade Level: {grade_level}
Topic: {topic}
{f'Additional Instructions: {extra}' if extra else ''}

Use the following uploaded educational content as your primary knowledge base:
--- KNOWLEDGE BASE START ---
{context if context else 'No specific content uploaded. Use your general knowledge.'}
--- KNOWLEDGE BASE END ---
"""
    type_prompts = {
        "lesson_plan": f"""{base}
Generate a detailed lesson plan for the topic above. Include:
1. Learning Objectives (3-5 clear objectives)
2. Required Materials
3. Introduction/Hook Activity (5 mins)
4. Main Teaching Steps (step by step, 30 mins)
5. Practice Activity (10 mins)
6. Assessment/Evaluation
7. Homework Assignment
8. Teacher Notes

Format clearly with headers. Make it practical for a Ghanaian classroom context.""",

        "exam_questions": f"""{base}
Generate a comprehensive set of exam questions for the topic above. Include:
1. Section A: Multiple Choice Questions (10 questions with options A-D and answers)
2. Section B: Short Answer Questions (5 questions with model answers)
3. Section C: Essay/Long Answer Questions (2 questions with marking scheme)

Label difficulty: Easy / Medium / Hard. Align with Ghana Education Service standards.""",

        "examples": f"""{base}
Generate clear, practical examples and illustrations for the topic above. Include:
1. 5 Worked Examples (step-by-step solutions where applicable)
2. 5 Practice Problems for students
3. Real-life applications relevant to Ghanaian students
4. Common misconceptions to avoid
5. Memory aids or mnemonics if applicable""",

        "explanation": f"""{base}
Write a clear, engaging explanation of the topic for the grade level above. Include:
1. Simple introduction suitable for the age group
2. Key concepts explained in plain language
3. Diagrams or visual descriptions where helpful
4. Connections to everyday life in Ghana
5. Summary of key points
6. Check-for-understanding questions"""
    }
    return type_prompts.get(generation_type, f"{base}\nRespond helpfully to assist the teacher.")

def generate_with_groq(prompt: str) -> str:
    from groq import Groq
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model=SUPPORTED_LLMS["groq"]["model"],
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4000,
        temperature=0.7
    )
    return response.choices[0].message.content

def generate_with_claude(prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    message = client.messages.create(
        model=SUPPORTED_LLMS["claude"]["model"],
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

def generate_with_openai(prompt: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=SUPPORTED_LLMS["chatgpt"]["model"],
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4000,
        temperature=0.7
    )
    return response.choices[0].message.content

def generate_with_gemini(prompt: str) -> str:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel(SUPPORTED_LLMS["gemini"]["model"])
    response = model.generate_content(prompt)
    return response.text

def generate_response(prompt: str, llm_choice: str = "groq") -> str:
    """Route generation to the selected LLM."""
    generators = {
        "groq": generate_with_groq,
        "claude": generate_with_claude,
        "chatgpt": generate_with_openai,
        "gemini": generate_with_gemini
    }
    fn = generators.get(llm_choice, generate_with_groq)
    if not SUPPORTED_LLMS.get(llm_choice, {}).get("available"):
        if SUPPORTED_LLMS["groq"]["available"]:
            fn = generate_with_groq
        else:
            raise ValueError("No LLM API key configured. Please add your GROQ_API_KEY to .env")
    return fn(prompt)
