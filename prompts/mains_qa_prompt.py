# prompts/mains_qa_prompt.py
# Prompt for generating UPSC Mains-style questions with structured answers

MAINS_QA_PROMPT = """You are an expert UPSC Mains question paper setter and answer writer.

CONTEXT:
This content falls under the UPSC Mains syllabus area:
  Paper: {paper}
  Subtopic: {subtopic}
  Focus Area: {sub_subtopic}
Frame questions that test analytical ability relevant to this specific area.

TASK:
Generate 4-5 UPSC Mains-style questions based on the content below.
Each question MUST be followed IMMEDIATELY by a model answer.

═══════════════════════════════════════════════════════════════
FORMAT FOR EACH QUESTION:
═══════════════════════════════════════════════════════════════

Q1. [Question text] (Word limit: 150/250 words)

Answer:

Introduction:
[2-3 lines: definition + context + why in news]

Body:

[Heading 1]
- Point 1
- Point 2
- Point 3

[Heading 2]
- Point 1
- Point 2
- Point 3

[Heading 3 — if applicable]
- Point 1
- Point 2

Way Forward:
- Recommendation 1
- Recommendation 2
- Recommendation 3
- Recommendation 4

Conclusion:
[2-3 lines: balanced, reform-focused, optimistic wrap-up]

────────────────────────────────────────────────────────────

Q2. [Next question]
... and so on.

═══════════════════════════════════════════════════════════════

QUESTION DESIGN RULES (UPSC Mains style):
1. Mix question TYPES from these patterns:
   - "Discuss" (broad understanding + relevance)
   - "Analyze" (break into parts: causes → effects → linkages)
   - "Examine" / "Critically examine" (check validity, show both sides)
   - "Evaluate" (judge performance, criteria-based)
   - "Comment" (take a position with balance)
   - "Suggest measures" (solution-heavy)
   - "Compare and contrast" (two approaches)

2. ANSWER STRUCTURE RULES:
   - Introduction: Short context (why in news / definition)
   - Body: 3-5 headings with bullet points under each
   - Headings should represent different analytical dimensions
   - Way Forward: 4-6 specific, actionable recommendations
   - Conclusion: Balanced, reform-focused, 2-3 lines
   - Each answer should be 150-250 words

3. Do NOT use markdown formatting (no **, ##, etc.)
4. Use plain text with clear structure
5. Each question should test a DIFFERENT aspect of the content
6. Answers must be analytical, not just descriptive
7. Use a thin separator (────) between questions

CONTENT:
{content}

GENERATE THE MAINS QUESTIONS WITH IMMEDIATE ANSWERS NOW:"""
