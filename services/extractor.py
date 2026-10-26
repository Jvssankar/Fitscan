import io

def extract_text(file_storage) -> str:
    filename = (file_storage.filename or "").lower()
    data = file_storage.read()
    if filename.endswith(".txt"):
        return _decode(data)
    if filename.endswith(".pdf"):
        return _pdf(data)
    if filename.endswith(".docx"):
        return _docx(data)
    raise ValueError("Unsupported file type. Upload PDF, DOCX, or TXT.")

def _decode(data):
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return data.decode(enc).strip()
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace").strip()

def _pdf(data):
    import pdfplumber
    lines = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                lines.append(t)
    result = "\n".join(lines).strip()
    if not result:
        raise ValueError("Could not extract text from PDF. Try a text-based PDF, DOCX, or TXT.")
    return result

def _docx(data):
    from docx import Document
    doc = Document(io.BytesIO(data))
    paras = [p.text for p in doc.paragraphs if p.text.strip()]
    result = "\n".join(paras).strip()
    if not result:
        raise ValueError("Could not extract text from DOCX.")
    return result
