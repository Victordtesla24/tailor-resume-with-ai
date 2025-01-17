"""Document handling with minimal optimizations."""

import logging
from typing import Generator, List, Optional, Tuple

from docx import Document
from docx.document import Document as DocumentType

from src.utils import (
    CHUNK_SIZE, MAX_INPUT_SIZE, MAX_MEMORY_MB,
    get_memory_usage, track_performance,
    validate_file_format, validate_input_size
)

logger = logging.getLogger("resume_tailor")


def stream_paragraphs(
    doc: DocumentType, chunk_size: int = CHUNK_SIZE
) -> Generator[str, None, None]:
    """Stream paragraphs to reduce memory usage."""
    current_chunk: List[str] = []
    current_size = 0

    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if not text:  # Skip empty paragraphs
            continue

        text_size = len(text.encode("utf-8"))

        # If single paragraph is too large, truncate it
        if text_size > chunk_size:
            text = text[: chunk_size // 2].strip() + "..."
            text_size = len(text.encode("utf-8"))

        if current_size + text_size > chunk_size:
            yield "\n".join(current_chunk)
            current_chunk = [text]
            current_size = text_size
        else:
            current_chunk.append(text)
            current_size += text_size

    if current_chunk:
        yield "\n".join(current_chunk)


@track_performance("file_upload")
def read_document(file_path: str, max_size: Optional[int] = None) -> Tuple[DocumentType, str]:
    """Read document with streaming for large files."""
    try:
        # Validate file format first
        validation = validate_file_format(file_path)
        if not validation["valid"]:
            raise ValueError(validation["error"])

        start_memory = get_memory_usage()

        # Check file size before loading
        file_size = get_document_size(file_path)
        max_size = max_size or MAX_MEMORY_MB * 1024 * 1024  # Default to MAX_MEMORY_MB in bytes
        if file_size > max_size:
            raise ValueError(f"File too large: {file_size} bytes (max {max_size} bytes)")

        # Use binary streaming to reduce memory usage
        doc = Document(file_path)

        # Stream paragraphs and join only when needed
        chunks: List[str] = []
        total_size = 0

        for chunk in stream_paragraphs(doc):
            chunk_size = len(chunk.encode("utf-8"))

            # Check total size including the new chunk
            if total_size + chunk_size > max_size:
                logger.warning("Document too large, truncating...")
                break

            chunks.append(chunk)
            total_size += chunk_size

            # Check memory usage after each chunk
            current_memory = get_memory_usage() - start_memory
            if current_memory > MAX_MEMORY_MB * 0.8:  # Warning at 80% of limit
                logger.warning("High memory usage during streaming: %.2fMB", current_memory)
                break

        result = "\n".join(chunks)

        # Validate final content size
        content_validation = validate_input_size(result)
        if not content_validation["valid"]:
            logger.warning("Content size warning: %s", content_validation["error"])
            # Truncate if too large
            result = result[:MAX_INPUT_SIZE] + "..."

        end_memory = get_memory_usage()
        memory_used = end_memory - start_memory

        if memory_used > MAX_MEMORY_MB * 0.8:  # Warning at 80% of limit
            logger.warning("High memory usage: %.2fMB", memory_used)

        return doc, result

    except Exception as e:
        logger.error("Document read error: %s", str(e))
        raise ValueError("Failed to read document: %s" % str(e))


def get_document_size(file_path: str) -> int:
    """Get document size without loading it fully."""
    with open(file_path, "rb") as f:
        f.seek(0, 2)  # Seek to end
        return f.tell()
