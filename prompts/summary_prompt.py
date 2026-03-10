# prompts/summary_prompt.py
# Prompt for generating revision summary per Prelims summary structure

SUMMARY_GENERATION_PROMPT = """You are a UPSC Revision Note Generator.

CONTEXT:
This content falls under the UPSC syllabus area:
  Subtopic: {subtopic}
  Focus Area: {sub_subtopic}

TASK:
Generate a FAST-REVISION SUMMARY from the detailed content below.
This summary should allow revision in 60–90 seconds.

═══════════════════════════════════════════════════════════════
FORMAT (STRICT — follow this order exactly):
═══════════════════════════════════════════════════════════════

A. Quick Summary
   • What happened (1 line only)

B. UPSC Relevance
   • Why UPSC cares — link to syllabus (2 lines max)

C. Key Points to Remember (8–12 bullets)
   • Key features / provisions / targets
   • 2–3 important numbers
   • 2 keywords/definitions
   • 1 map/location point (if any)
   • 1 stakeholder impact point

D. Prelims-Ready Nuggets (5 bullets max)
   • Straight factual MCQ-friendly points
   • Each bullet = one potential MCQ fact

E. Mains Connection
   • One ready-made line usable in essay intro or conclusion

═══════════════════════════════════════════════════════════════

RULES:
- NO fluff, NO repetition
- Use simple UPSC language
- Bullet points must be crisp and exam-ready
- Do NOT use markdown formatting (no **, ##, etc.)
- Use plain text with clear section headers exactly as shown (A. Quick Summary, etc.)

DETAILED CONTENT:
{content}

GENERATE THE REVISION SUMMARY NOW:"""
