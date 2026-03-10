# prompts/content_prompt.py
# Prompt for generating detailed UPSC Prelims content per the content structure

CONTENT_GENERATION_PROMPT = """You are an expert UPSC Prelims content creator.

CONTEXT:
This content falls under the UPSC syllabus area:
  Subtopic: {subtopic}
  Focus Area: {sub_subtopic}
Keep this syllabus context in mind when generating the notes — emphasize
angles and facts that are most relevant to this specific area.

TASK:
Generate detailed study-notes content from the given input text following
the EXACT structure below. Every section MUST be present. If the input
does not have enough information for a section, write "Not applicable for
this content." under that section.

═══════════════════════════════════════════════════════════════
STRUCTURE (follow this order exactly):
═══════════════════════════════════════════════════════════════

Title: <Clear descriptive title in your own words>
Source: <Extract or infer date and source>
Tags: <GS paper number + syllabus keywords>

A. Core Information
   • Reproduce the core factual content from the input faithfully.
   • Preserve all facts, figures, names, dates.
   • Clean up language but do NOT omit any information.
   • Organize the information logically.

B. Significance & Impact
   • 5–8 lines covering: the event + its significance + what changed
   • Be specific and UPSC-oriented.
   • Connect to syllabus relevance.

C. Background & Timeline
   • Previous policy/history related to this topic
   • Earlier attempts / committees / court judgments (if any)
   • Relevant Constitution Articles (if applicable)
   • Timeline: 3–6 bullet milestones
   • Institutions involved + their roles

D. Key Concepts & Definitions
   • 5–10 key terms with 1–2 line definitions each
   • Link to static content from standard UPSC books (Laxmikanth, Spectrum, etc.)

E. Prelims-Ready Facts
   • Names, dates, targets, numbers that can be asked directly
   • Geography/mapping points (if any)
   • International bodies: HQ, members, mandate (only if relevant)

F. Advantages & Opportunities
   • 5–8 bullet points

G. Challenges & Risks
   • 5–8 bullet points covering implementation, governance, tech, rights, ecology

═══════════════════════════════════════════════════════════════

RULES:
- Use simple, precise UPSC language
- No fluff, no filler
- Every fact from the input must appear somewhere
- If a section truly does not apply, write "Not applicable for this content."
- Do NOT use markdown formatting (no **, ##, etc.)
- Use plain text with clear section headers exactly as shown (A. Core Information, etc.)
- Start with "Title:" on the first line

INPUT CONTENT:
{content}

GENERATE THE COMPLETE STUDY NOTES NOW:"""
