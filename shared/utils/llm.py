import os
import re
from pathlib import Path
from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=_env_path, override=True)

SUPPORTED_LLMS = {
    "groq": {
        "name": "Groq (LLaMA 3)",
        "model": "llama-3.3-70b-versatile",
        "requires_key": "GROQ_API_KEY",
        "available": True,
    },
    "claude": {
        "name": "Claude (Anthropic)",
        "model": "claude-3-5-sonnet-20241022",
        "requires_key": "ANTHROPIC_API_KEY",
        "available": False,
    },
    "chatgpt": {
        "name": "ChatGPT (OpenAI)",
        "model": "gpt-4o",
        "requires_key": "OPENAI_API_KEY",
        "available": False,
    },
    "gemini": {
        "name": "Gemini (Google)",
        "model": "gemini-1.5-pro",
        "requires_key": "GEMINI_API_KEY",
        "available": False,
    }
}

def is_llm_available(llm_choice: str) -> bool:
    key_map = {
        "groq":    "GROQ_API_KEY",
        "claude":  "ANTHROPIC_API_KEY",
        "chatgpt": "OPENAI_API_KEY",
        "gemini":  "GEMINI_API_KEY",
    }
    return bool(os.getenv(key_map.get(llm_choice, ""), "").strip())


def clean_response(text: str) -> str:
    """
    Remove markdown stars/bold/italic and clean up the LLM output.
    Keeps numbered lists, section headers, and paragraph structure intact.
    """
    # Remove bold (**text** or __text__)
    text = re.sub(r'\*{2,3}(.+?)\*{2,3}', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'_{2,3}(.+?)_{2,3}', r'\1', text, flags=re.DOTALL)
    # Remove italic (*text* or _text_) — single star/underscore
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\1', text)
    text = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'\1', text)
    # Remove any remaining lone stars
    text = re.sub(r'\*+', '', text)
    # Remove markdown headers (### Title → Title)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Remove horizontal rules
    text = re.sub(r'^[-_=]{3,}\s*$', '', text, flags=re.MULTILINE)
    # Collapse 3+ consecutive blank lines into 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ── FORMATTING INSTRUCTION appended to every prompt ───────────────────────────
FORMAT_RULES = """

CRITICAL FORMATTING RULES — follow these exactly:
- Do NOT use markdown stars (*) for bold or italic — ever
- Do NOT use # hashtags for headers
- Use PLAIN TEXT only
- For section headings, write them in CAPITAL LETTERS followed by a colon, e.g. LEARNING OBJECTIVES:
- For numbered items, use: 1. 2. 3. etc.
- For sub-items, use: a) b) c) or indented dashes (-)
- Separate sections with a blank line
- No markdown formatting whatsoever — the output will be displayed as plain text
"""


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
Generate a detailed lesson plan for the topic above. Structure it exactly like this:

LESSON PLAN: [Topic]
Subject: {subject} | Grade: {grade_level} | Duration: 60 minutes

LEARNING OBJECTIVES:
1. [Objective 1]
2. [Objective 2]
3. [Objective 3]

REQUIRED MATERIALS:
- [Material 1]
- [Material 2]

INTRODUCTION (5 minutes):
[Describe the hook activity]

MAIN TEACHING STEPS (30 minutes):
1. [Step 1 - include time estimate]
2. [Step 2 - include time estimate]
3. [Step 3 - include time estimate]

PRACTICE ACTIVITY (10 minutes):
[Describe the activity]

ASSESSMENT AND EVALUATION:
[How will you assess student understanding]

HOMEWORK:
[Assignment description]

TEACHER NOTES:
[Any additional notes or tips]

{FORMAT_RULES}""",

        "exam_questions": f"""{base}
Generate exam questions for the topic above. Structure it exactly like this:

EXAMINATION QUESTIONS
Subject: {subject} | Grade: {grade_level} | Topic: {topic}

SECTION A: MULTIPLE CHOICE (10 marks)
Choose the correct answer from the options given.

1. [Question]
   A) [Option]
   B) [Option]
   C) [Option]
   D) [Option]
   Answer: [Letter]

[Continue for all 10 questions]

SECTION B: SHORT ANSWER QUESTIONS (20 marks)

1. [Question] (2 marks)
   Model Answer: [Answer]

[Continue for 5 questions]

SECTION C: ESSAY QUESTIONS (20 marks)

1. [Question] (10 marks)
   Marking Scheme:
   - [Point 1] (2 marks)
   - [Point 2] (2 marks)
   - [Point 3] (2 marks)

{FORMAT_RULES}""",

        "examples": f"""{base}
Generate examples and exercises for the topic above. Structure it exactly like this:

EXAMPLES AND EXERCISES
Subject: {subject} | Grade: {grade_level} | Topic: {topic}

WORKED EXAMPLES:

Example 1: [Title]
[Step-by-step solution]

Example 2: [Title]
[Step-by-step solution]

Example 3: [Title]
[Step-by-step solution]

PRACTICE PROBLEMS FOR STUDENTS:

1. [Problem]
2. [Problem]
3. [Problem]
4. [Problem]
5. [Problem]

REAL-LIFE APPLICATIONS (Ghana Context):
[How this topic applies to everyday life in Ghana]

COMMON MISTAKES TO AVOID:
1. [Mistake and how to correct it]
2. [Mistake and how to correct it]

MEMORY AIDS:
[Mnemonic or memory trick if applicable]

{FORMAT_RULES}""",

        "explanation": f"""{base}
Write a clear explanation of the topic for the grade level above. Structure it exactly like this:

TOPIC EXPLANATION: {topic}
Subject: {subject} | Grade: {grade_level}

INTRODUCTION:
[Simple, age-appropriate introduction to the topic]

KEY CONCEPTS:

1. [Concept name]
[Clear explanation]

2. [Concept name]
[Clear explanation]

3. [Concept name]
[Clear explanation]

REAL-LIFE CONNECTIONS (Ghana Context):
[How this connects to students' everyday lives in Ghana]

SUMMARY OF KEY POINTS:
1. [Key point 1]
2. [Key point 2]
3. [Key point 3]

CHECK YOUR UNDERSTANDING:
1. [Question to test comprehension]
2. [Question to test comprehension]
3. [Question to test comprehension]

{FORMAT_RULES}"""
    }
    return type_prompts.get(generation_type, f"{base}\nRespond helpfully to assist the teacher.\n{FORMAT_RULES}")


def generate_with_groq(prompt: str) -> str:
    from groq import Groq
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set in your .env file.")
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=SUPPORTED_LLMS["groq"]["model"],
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4000,
        temperature=0.7
    )
    return clean_response(response.choices[0].message.content)


def generate_with_claude(prompt: str) -> str:
    import anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set in your .env file.")
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=SUPPORTED_LLMS["claude"]["model"],
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )
    return clean_response(message.content[0].text)


def generate_with_openai(prompt: str) -> str:
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set in your .env file.")
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=SUPPORTED_LLMS["chatgpt"]["model"],
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4000,
        temperature=0.7
    )
    return clean_response(response.choices[0].message.content)


def generate_with_gemini(prompt: str) -> str:
    import google.generativeai as genai
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in your .env file.")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(SUPPORTED_LLMS["gemini"]["model"])
    response = model.generate_content(prompt)
    return clean_response(response.text)


def generate_response(prompt: str, llm_choice: str = "groq") -> str:
    generators = {
        "groq":    generate_with_groq,
        "claude":  generate_with_claude,
        "chatgpt": generate_with_openai,
        "gemini":  generate_with_gemini,
    }
    if is_llm_available(llm_choice):
        return generators[llm_choice](prompt)
    if llm_choice != "groq" and is_llm_available("groq"):
        return generate_with_groq(prompt)
    raise ValueError(
        f"No API key found for '{llm_choice}'. "
        f"Please add {SUPPORTED_LLMS.get(llm_choice, {}).get('requires_key', 'the API key')} "
        f"to your .env file."
    )
