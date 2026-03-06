"""
Tests for document generation and storage.
"""

import os
import pytest
from pathlib import Path

from src.storage.documents import (
    DocumentStore,
    extract_title_and_body,
    title_from_message,
)


class TestExtractTitleAndBody:
    def test_with_document_title(self):
        text = "DOCUMENT_TITLE: Meet and Confer Letter\nDear Counsel,\nThis is the body."
        title, body = extract_title_and_body(text)
        assert title == "Meet and Confer Letter"
        assert "Dear Counsel" in body

    def test_without_document_title(self):
        text = "Dear Counsel,\nThis is the body."
        title, body = extract_title_and_body(text, fallback="Fallback_Title")
        assert title == "Fallback_Title"
        assert body == text

    def test_title_in_middle(self):
        text = "Preamble\nDOCUMENT_TITLE: Motion to Compel\nBody text here"
        title, body = extract_title_and_body(text)
        assert title == "Motion to Compel"
        assert "Preamble" in body
        assert "Body text here" in body


class TestTitleFromMessage:
    def test_basic_title(self):
        result = title_from_message("Draft a meet and confer letter for Rodriguez case")
        assert "Draft" in result or "Meet" in result
        assert "_" in result

    def test_empty_message(self):
        result = title_from_message("")
        assert result == "Legal_Document"


class TestDocumentStore:
    def test_build_docx(self, tmp_path):
        store = DocumentStore()
        # Override local dir for test
        from src.storage import documents
        original_dir = documents.LOCAL_DIR
        documents.LOCAL_DIR = tmp_path

        try:
            filename, local_path = store.build_docx(
                "Test_Document",
                "# Heading\n\nThis is **bold** text.\n\nRegular paragraph.",
            )
            assert filename.endswith(".docx")
            assert Path(local_path).exists()
            assert Path(local_path).stat().st_size > 0
        finally:
            documents.LOCAL_DIR = original_dir

    def test_build_docx_with_org_id(self, tmp_path):
        store = DocumentStore()
        from src.storage import documents
        original_dir = documents.LOCAL_DIR
        documents.LOCAL_DIR = tmp_path

        try:
            filename, local_path = store.build_docx(
                "Org_Document",
                "Body text.",
                org_id="test-org-123",
            )
            assert "test-org-123" in local_path
            assert Path(local_path).exists()
        finally:
            documents.LOCAL_DIR = original_dir
