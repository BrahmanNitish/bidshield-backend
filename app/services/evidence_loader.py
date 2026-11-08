import pypdf
from app.services.embedding import generate_embedding


def chunk_text(text: str, chunk_size: int = 600, overlap: int = 100) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def process_policy_pdf(file_path: str, category: str, base_title: str) -> list[dict]:
    reader = pypdf.PdfReader(file_path)
    full_text = []
    for page in reader.pages:
        txt = page.extract_text()
        if txt:
            full_text.append(txt)

    merged_text = "\n\n".join(full_text)
    text_chunks = chunk_text(merged_text)

    records = []
    for i, chunk in enumerate(text_chunks):
        embedding = generate_embedding(chunk)
        records.append({
            "title": f"{base_title} (Part {i+1})",
            "category": category,
            "content": chunk,
            "embedding": embedding,
        })
    return records