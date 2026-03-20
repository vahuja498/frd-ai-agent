"""
app/services/ingestion.py
Document ingestion service — cleans and chunks input text documents.
"""
from typing import List
from app.models.schemas import DocumentChunk
from app.utils.file_loader import clean_text, chunk_text


class IngestionService:
    """
    Takes raw text inputs (transcript, MoM, SOW),
    cleans them, and produces DocumentChunks ready for embedding.
    """

    CHUNK_SIZE = 400
    OVERLAP = 40

    def ingest(
        self,
        transcript: str,
        mom: str,
        sow: str,
    ) -> List[DocumentChunk]:
        """
        Clean and chunk all three input documents.
        Returns a flat list of DocumentChunk objects.
        """
        sources = {
            "transcript": transcript,
            "mom": mom,
            "sow": sow,
        }

        all_chunks: List[DocumentChunk] = []

        for source_name, raw_text in sources.items():
            cleaned = clean_text(raw_text)
            chunks = chunk_text(cleaned, chunk_size=self.CHUNK_SIZE, overlap=self.OVERLAP)

            for i, chunk_text_item in enumerate(chunks):
                all_chunks.append(
                    DocumentChunk(
                        text=chunk_text_item,
                        source=source_name,
                        chunk_index=i,
                    )
                )

        return all_chunks

    def combine_for_prompt(
        self,
        transcript: str,
        mom: str,
        sow: str,
    ) -> str:
        """
        Combine all three documents into a single cleaned string
        for direct inclusion in the LLM prompt.
        """
        parts = [
            f"=== MEETING TRANSCRIPT ===\n{clean_text(transcript)}",
            f"\n=== MINUTES OF MEETING (MoM) ===\n{clean_text(mom)}",
            f"\n=== STATEMENT OF WORK (SOW) ===\n{clean_text(sow)}",
        ]
        return "\n\n".join(parts)
