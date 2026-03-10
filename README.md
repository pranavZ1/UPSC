# UPSC Prelims Engine

A complete pipeline to process UPSC Prelims study material — automatically generates **Content Notes**, **Revision Summaries**, and **MCQ Practice Papers** as clean PDFs.

---

## How It Works

```
Input (PDF / TXT / Image)
         │
         ▼
   Extract Text (OCR / pypdf)
         │
         ▼
   Zero-Loss Compression
         │
         ▼
   Semantic Chunking (by topic)
         │
         ▼
   ┌─────┴─────┐
   │  For each  │
   │   chunk:   │
   └─────┬─────┘
         │
    Classify Topic ──→ History / Polity / Economy / ...
         │
    ┌────┼────┐
    ▼    ▼    ▼
Content Summary MCQs
 (A-H)  (A-E)  (Q+Ans)
    │    │    │
    ▼    ▼    ▼
   HTML → PDF (per topic)
```

---

## Output Structure

```
output/
├── content/          ← Detailed study notes (TXT)
├── summary/          ← Revision summaries (TXT)
├── questions/        ← MCQ papers (TXT)
├── html/
│   ├── content/      ← HTML for content
│   ├── summary/      ← HTML for summary
│   └── questions/    ← HTML for Q&A
├── pdf/
│   ├── content/      ← 📄 Content PDFs (e.g., current_affairs_content.pdf)
│   ├── summary/      ← 📄 Summary PDFs (e.g., history_summary.pdf)
│   └── questions/    ← 📄 Q&A PDFs (e.g., polity_governance_questions.pdf)
└── debug/            ← Intermediate files for debugging
```

---

## Topics Covered

From `Prelims topics.txt` — **Paper I (GS)**:

| # | Topic | File Prefix |
|---|-------|-------------|
| 1 | Current Affairs | `current_affairs` |
| 2 | History | `history` |
| 3 | Geography | `geography` |
| 4 | Polity & Governance | `polity_governance` |
| 5 | Economy | `economy` |
| 6 | Science & Technology | `science_technology` |
| 7 | Environment & Ecology | `environment_ecology` |
| 8 | Art & Culture | `art_culture` |

---

## Content Structure (per topic)

### Content PDF (sections A–H)
- A. Header (title, date, source, tags)
- B. Content As-Is
- C. What Happened + Why It Matters
- D. Background & Timeline
- E. Concepts / Definitions / Static Linkage
- F. Key Facts (Prelims-ready)
- G. Pros / Opportunities
- H. Cons / Risks / Challenges

### Summary PDF (sections A–E)
- A. 1-liner
- B. Why Important
- C. Must-Remember Points (8–12 bullets)
- D. Prelims Nuggets (5 bullets)
- E. Mains Hook

### Q&A PDF
- 8–10 UPSC-style MCQs
- Answer Key with detailed explanations at the end

---

## Key Feature: Append Mode

When you process new input:
- If the topic **already has** a PDF → new content is **appended** (not overwritten)
- If it's a **new topic** → a new file is created
- All files stay within the 8 predefined topics from the Prelims syllabus

---

## Setup

```bash
cd upsc_prelims_engine

# Create virtual environment
python -m venv env
source env/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Set your Gemini API key in .env
# GEMINI_API_KEY=your_key_here
```

---

## Usage

```bash
# Process a PDF
python pipeline.py input/your_material.pdf

# Process a text file
python pipeline.py input/news_article.txt

# Or just place file(s) in input/ and run:
python pipeline.py
```

---

## Project Structure

```
upsc_prelims_engine/
├── pipeline.py              ← Main orchestrator
├── config.py                ← Configuration & paths
├── .env                     ← API key (not committed)
├── requirements.txt
├── README.md
├── chunking/
│   └── text_chunker.py      ← Text splitting logic
├── llm/
│   ├── gemini_client.py     ← Gemini API wrapper
│   ├── topic_classifier.py  ← Classify text → topic
│   ├── content_generator.py ← Generate content (A–H)
│   ├── summary_generator.py ← Generate summary (A–E)
│   ├── qa_generator.py      ← Generate MCQs
│   ├── html_formatter.py    ← Text → HTML conversion
│   └── text_cleaner.py      ← Clean & compress text
├── ocr/
│   ├── pdf_loader.py        ← PDF text extraction
│   └── image_loader.py      ← Image OCR
├── prompts/
│   ├── content_prompt.py    ← Content generation prompt
│   ├── summary_prompt.py    ← Summary generation prompt
│   └── qa_prompt.py         ← MCQ generation prompt
├── topics/
│   └── topic_list.py        ← Full topic hierarchy
├── utils/
│   ├── file_manager.py      ← TXT file append/create
│   └── pdf_creator.py       ← HTML → PDF generation
├── input/                   ← Drop your input files here
└── output/                  ← All generated output
```
