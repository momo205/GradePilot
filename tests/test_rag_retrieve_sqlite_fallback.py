from __future__ import annotations

import uuid

from _pytest.monkeypatch import MonkeyPatch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, Class, Document, DocumentChunk
from app.services.rag.retrieve import retrieve_chunks


def test_retrieve_chunks_sqlite_fallback_ordering(monkeypatch: MonkeyPatch) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    user_id = uuid.uuid4()
    class_id = uuid.uuid4()

    with SessionLocal() as db:
        db.add(Class(id=class_id, user_id=user_id, title="Test"))
        db.commit()

        doc = Document(
            id=uuid.uuid4(),
            class_id=class_id,
            user_id=user_id,
            filename="a.txt",
            title=None,
            document_type="notes",
            raw_text=None,
            metadata_json={},
        )
        db.add(doc)
        db.commit()

        # embedding stored as JSON on SQLite; retrieval should fall back deterministically.
        db.add_all(
            [
                DocumentChunk(
                    document_id=doc.id,
                    class_id=class_id,
                    user_id=user_id,
                    chunk_index=0,
                    chunk_text="alpha",
                    embedding=[0.0],
                    metadata_json={},
                ),
                DocumentChunk(
                    document_id=doc.id,
                    class_id=class_id,
                    user_id=user_id,
                    chunk_index=1,
                    chunk_text="beta",
                    embedding=[0.0],
                    metadata_json={},
                ),
            ]
        )
        db.commit()

        monkeypatch.setattr(
            "app.services.rag.retrieve.embed_query", lambda *, text: [0.0]
        )

        out = retrieve_chunks(
            db=db,
            user_id=user_id,
            class_id=class_id,
            question="anything",
            k=2,
        )
        assert [c.chunk_index for c in out] == [0, 1]
