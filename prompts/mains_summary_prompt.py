# prompts/mains_summary_prompt.py
# Prompt for generating Mains revision summary

MAINS_SUMMARY_PROMPT = """You are a UPSC Mains Revision Note Generator.

CONTEXT:
This content falls under the UPSC Mains syllabus area:
  Paper: {paper}
  Subtopic: {subtopic}
  Focus Area: {sub_subtopic}

TASK:
Generate a MAINS-ORIENTED REVISION SUMMARY from the detailed content below.
This summary should help a candidate quickly revise key analytical points
and answer structures in 2-3 minutes.

═══════════════════════════════════════════════════════════════
FORMAT (STRICT — follow this order exactly):
═══════════════════════════════════════════════════════════════

A. One-liner Context
   • What is this about and why it matters (1-2 lines)

B. Multi-dimensional Summary (6-8 bullets)
   • Political/governance angle
   • Economic angle
   • Social angle
   • Environmental angle (if applicable)
   • Key facts and figures

C. Key Arguments (For vs Against)
   • 3-4 strongest arguments FOR
   • 3-4 strongest arguments AGAINST

D. Way Forward Highlights (5-6 points)
   • Most impactful recommendations
   • Ready to use in Mains answers

E. Answer-Ready Phrases
   • 4-5 lines that can be directly used in Mains answers
   • Include intro-ready line, body-ready points, conclusion line
   • These should sound polished and analytical

═══════════════════════════════════════════════════════════════

RULES:
- Analytical, NOT just factual
- Each bullet must be answer-ready
- Way Forward points should be specific
- Do NOT use markdown formatting (no **, ##, etc.)
- Use plain text with clear section headers exactly as shown

DETAILED CONTENT:
{content}

GENERATE THE MAINS REVISION SUMMARY NOW:"""
