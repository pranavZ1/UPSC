# prompts/qa_prompt.py
# Prompt for generating UPSC Prelims-style MCQs

QA_GENERATION_PROMPT = """You are an expert UPSC Prelims question paper setter.

CONTEXT:
This content falls under the UPSC syllabus area:
  Subtopic: {subtopic}
  Focus Area: {sub_subtopic}
Frame questions that test knowledge relevant to this specific syllabus area.

TASK:
Generate 8–10 Multiple Choice Questions (MCQs) based on the content below.
These questions MUST be in the exact style of UPSC Civil Services Prelims
(Paper I — General Studies).

═══════════════════════════════════════════════════════════════
QUESTION FORMAT:
═══════════════════════════════════════════════════════════════

Q1. [Question text]
(a) Option A
(b) Option B
(c) Option C
(d) Option D

Q2. [Question text]
... and so on.

After ALL questions, provide an ANSWER KEY section:

═══════════════════════════════════════════════════════════════
ANSWER KEY WITH EXPLANATIONS
═══════════════════════════════════════════════════════════════

Q1. Answer: (x)
Explanation: [2–3 line clear explanation why this is correct
and why other options are wrong]

Q2. Answer: (x)
... and so on.

═══════════════════════════════════════════════════════════════

MCQ DESIGN RULES (UPSC-style):
1. Mix question types:
   - Factual recall (names, dates, numbers, places)
   - Conceptual understanding
   - Statement-based: "Consider the following statements..."
   - Match the following / Correct pair type
   - "Which of the above is/are correct?" pattern
2. Options must be plausible — no obviously wrong answers
3. Include 2–3 questions with "1 and 2 only", "2 and 3 only" style options
4. At least 1 question should test map/geography awareness (if relevant)
5. Questions should cover different aspects of the content
6. Difficulty: moderate to high (actual UPSC level)
7. Do NOT use markdown formatting (no **, ##, etc.)
8. Use plain text only

CONTENT:
{content}

GENERATE THE MCQ SET NOW:"""
