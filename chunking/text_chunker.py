# chunking/text_chunker.py — Split large text into topic-coherent chunks

import tiktoken

enc = tiktoken.get_encoding("cl100k_base")


def estimate_tokens(text: str) -> int:
    """Estimate token count for a text string."""
    return len(enc.encode(text))


def chunk_text(text: str, max_tokens: int = 6000) -> list[str]:
    """
    Split text into chunks respecting paragraph boundaries.
    Each chunk stays under max_tokens.
    """
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_tokens = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        para_tokens = estimate_tokens(para)

        # If single paragraph exceeds limit, split by lines
        if para_tokens > max_tokens:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_tokens = 0

            lines = para.split("\n")
            line_chunk = []
            line_tokens = 0
            for line in lines:
                lt = estimate_tokens(line)
                if line_tokens + lt > max_tokens and line_chunk:
                    chunks.append("\n".join(line_chunk))
                    line_chunk = []
                    line_tokens = 0
                line_chunk.append(line)
                line_tokens += lt
            if line_chunk:
                chunks.append("\n".join(line_chunk))
            continue

        if current_tokens + para_tokens > max_tokens:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = []
            current_tokens = 0

        current_chunk.append(para)
        current_tokens += para_tokens

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks


def semantic_split(text: str, llm_call_fn, delimiter: str) -> list[str]:
    """
    Use LLM to split text at semantic (topic) boundaries.
    Returns list of topic-coherent chunks.
    """
    prompt = f"""You are a semantic text splitter for UPSC study material.

TASK:
Split the following text at clear TOPIC boundaries. Each chunk should be
about ONE distinct topic or news item.

Insert the delimiter {delimiter} between different topics.
Do NOT insert delimiter at the very end.
Do NOT remove, paraphrase, or summarize any content.
Return ONLY the modified text with delimiters inserted.

TEXT:
{text}
"""
    output = llm_call_fn(prompt)
    chunks = [c.strip() for c in output.split(delimiter) if c.strip()]
    return chunks
