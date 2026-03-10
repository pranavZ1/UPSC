# prompts/mains_content_prompt.py
# Prompt for generating detailed UPSC Mains content

MAINS_CONTENT_PROMPT = """You are an expert UPSC Mains content creator.

CONTEXT:
This content falls under the UPSC Mains syllabus area:
  Paper: {paper}
  Subtopic: {subtopic}
  Focus Area: {sub_subtopic}
Keep this syllabus context in mind — emphasize analytical depth, multiple
dimensions, and governance angles relevant to Mains answers.

TASK:
Generate detailed MAINS-oriented study notes from the given input text.
Mains requires analytical depth, multi-dimensional coverage, and answer-ready
content — NOT just factual recall like Prelims.

═══════════════════════════════════════════════════════════════
STRUCTURE (follow this order exactly):
═══════════════════════════════════════════════════════════════

Title: <Clear descriptive title in your own words>
Source: <Extract or infer date and source>
Tags: <GS paper number + syllabus keywords>

A. Core Analysis
   • What is the issue/topic about (2-3 lines context)
   • Present the core content with analytical framing
   • Preserve all facts, figures, names, dates
   • Organize by sub-themes or dimensions

B. Multiple Dimensions
   • Political dimension
   • Economic dimension
   • Social dimension
   • Environmental/Ethical dimension (if applicable)
   • International/Comparative dimension (if applicable)
   • Each dimension: 2-4 bullet points

C. Background & Evolution
   • Historical context and policy evolution
   • Key committees/commissions/court judgments
   • Constitution Articles, laws, schemes involved
   • Timeline: 4-6 milestones
   • Institutional framework

D. Arguments For & Against
   • Advantages / arguments supporting (5-6 points)
   • Challenges / arguments against (5-6 points)
   • Present both sides — UPSC rewards balanced analysis

E. Government Initiatives & Institutional Response
   • Key schemes, policies, programs related to this topic
   • Budget allocations, targets, implementation status
   • Role of different agencies/ministries

F. Way Forward
   • 8-10 specific, actionable, governance-oriented recommendations
   • Mix of short-term and long-term measures
   • Include institutional reforms, policy suggestions, technology use
   • Each recommendation should be specific enough to use in a Mains answer

G. Mains Keywords & Concepts
   • 8-12 important terms with 1-2 line definitions
   • These should be usable as vocabulary in Mains answers
   • Link to broader governance/constitutional/policy concepts

═══════════════════════════════════════════════════════════════

RULES:
- Use analytical, nuanced language suitable for Mains answers
- Every fact from the input must appear somewhere
- Multi-dimensional analysis is MANDATORY
- Way Forward must be specific and governance-oriented
- If a section truly does not apply, write "Not applicable for this content."
- Do NOT use markdown formatting (no **, ##, etc.)
- Use plain text with clear section headers exactly as shown
- Start with "Title:" on the first line

INPUT CONTENT:
{content}

GENERATE THE COMPLETE MAINS STUDY NOTES NOW:"""
