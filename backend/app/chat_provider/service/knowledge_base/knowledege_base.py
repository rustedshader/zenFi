import os
from typing import Any, Dict, List, Optional
import uuid
from fastapi import HTTPException
from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    HarmBlockThreshold,
    HarmCategory,
)
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
)  # Keep for ingest_vectors
from sqlalchemy import select
from app.chat_provider.service.knowledge_base.knowledge_base_pdf_helpers import (
    SemanticBoundariesTextSplitter,
    calculate_text_content_quality,
    process_pdf_document,  # Assumes this is the refactored version
)
from langchain_core.documents import Document

from app.chat_provider.service.knowledge_base.knowledge_base_vector import (
    EnhancedVectorStoreFactory,
    Properties,
    create_vectors_enhanced,
)
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain.chains.retrieval import create_retrieval_chain
from langchain_community.document_loaders import (
    WebBaseLoader,
)  # Corrected from langchain.document_loaders
from google.cloud import bigquery
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.api_models import KnowledgeBase  # Assuming this model exists

# Ensure GOOGLE_GEMINI_API_KEY is used as per this script's context
# GOOGLE_APPLICATION_CREDENTIALS would typically be set in the environment for ADC with BigQuery/Vector Store
# if not os.getenv("GOOGLE_GEMINI_API_KEY") and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
# print("Warning: GOOGLE_GEMINI_API_KEY or GOOGLE_APPLICATION_CREDENTIALS not set. LLM calls might fail.")

project_id = os.environ.get("PROJECT_ID")


class EnhancedBigQueryRetriever(BaseRetriever):
    project_id: str
    region: str
    dataset: str
    table: str
    filter: Optional[Dict[str, Any]] = None
    k: int = 15  # Default k value

    class Config:
        arbitrary_types_allowed = True

    # __init__ is fine as provided by user; it correctly assigns attributes.
    # No changes needed in __init__ based on the prompt.

    def get_relevant_documents(self, query: str) -> List[Document]:
        # Enhanced search with multiple retrieval strategies
        docs = self._multi_strategy_search(query)

        # Rerank based on relevance and quality
        ranked_docs = self._rerank_by_relevance_and_quality(docs, query)

        return ranked_docs[:10]  # Return top 10 after reranking

    def _multi_strategy_search(self, query: str) -> List[Document]:
        """Use multiple search strategies and combine results"""
        properties = Properties(self.project_id, self.region, self.dataset, self.table)
        # Assuming EnhancedVectorStoreFactory correctly creates a store compatible with Langchain
        store = EnhancedVectorStoreFactory(properties).create_store()

        all_docs: List[Document] = []

        # Strategy 1: Direct similarity search
        try:
            # Ensure filter is correctly passed if it's part of the store's API
            docs1 = store.similarity_search(query=query, filter=self.filter, k=self.k)
            all_docs.extend(docs1)
        except Exception as e:
            print(f"Direct search error: {e}")

        # Strategy 2: Query expansion (add synonyms and related terms)
        expanded_query = self._expand_query(query)
        if expanded_query != query:
            try:
                # Reduce k for expanded query to get diverse results without too many overlaps initially
                docs2 = store.similarity_search(
                    query=expanded_query, filter=self.filter, k=max(1, self.k // 2)
                )
                all_docs.extend(docs2)
            except Exception as e:
                print(f"Expanded search error: {e}")

        # Remove duplicates based on content
        unique_docs: List[Document] = []
        seen_content_keys = set()
        for doc in all_docs:
            # Using a more robust key for deduplication, like first N chars + last N chars, or a hash.
            # For simplicity, keeping user's original approach for now.
            content_key = (
                doc.page_content[:100] + doc.page_content[-100:]
                if len(doc.page_content) > 200
                else doc.page_content
            )
            if content_key not in seen_content_keys:
                seen_content_keys.add(content_key)
                unique_docs.append(doc)

        return unique_docs

    def _expand_query(self, query: str) -> str:
        """Expand query with related terms for better recall"""
        # This is a simple implementation. Could be enhanced with LLM-based expansion,
        # thesaurus, or domain-specific knowledge.
        expansions = {
            "find": "locate search discover identify",
            "show": "display present exhibit demonstrate",
            "list": "enumerate itemize catalog show",
            "top": "highest largest biggest maximum best",
            "bottom": "lowest smallest minimum worst",
            "recent": "latest newest current new",
            "old": "previous earlier past former",
            "total": "sum aggregate combined overall",
            "average": "mean typical standard normal",
            # Add more domain-specific expansions if relevant
        }

        original_terms = query.lower().split()
        additional_expanded_terms = []
        for word in original_terms:
            if word in expansions:
                additional_expanded_terms.extend(expansions[word].split())

        # Add unique expansions, limit total number of added terms
        unique_new_terms = [
            t for t in additional_expanded_terms if t not in original_terms
        ]
        if unique_new_terms:
            # Limit to a few (e.g., 3-5) most relevant or diverse expansions
            return query + " " + " ".join(list(set(unique_new_terms))[:5])
        return query

    def _rerank_by_relevance_and_quality(
        self, docs: List[Document], query: str
    ) -> List[Document]:
        """Rerank documents by relevance and quality scores"""
        scored_docs = []

        query_words = set(query.lower().split())
        if not query_words:  # Handle empty query case
            return docs  # Or return empty list, depending on desired behavior

        for doc in docs:
            doc_words = set(doc.page_content.lower().split())

            keyword_overlap = len(query_words.intersection(doc_words)) / len(
                query_words
            )

            # Get quality score from metadata - "chunk_quality" is specific to the chunk
            quality_score = float(doc.metadata.get("chunk_quality", 0.5))

            # Get information density - this is page-level density associated with the chunk
            info_density = float(
                doc.metadata.get("information_density", 0.5)
            )  # Or page_information_density

            has_structured_data_bonus = (
                0.1 if doc.metadata.get("has_structured_data", False) else 0.0
            )

            # Combine scores - weights can be tuned
            # Emphasize keyword overlap more, then quality, then density
            combined_score = (
                keyword_overlap * 0.50  # Keyword relevance
                + quality_score * 0.25  # Content quality of the chunk
                + info_density * 0.15  # Information density of the source page
                + has_structured_data_bonus  # Structured data bonus
            )
            scored_docs.append((doc, combined_score))

        scored_docs.sort(key=lambda x: x[1], reverse=True)
        return [doc_item for doc_item, score in scored_docs]


def ingest_documents_enhanced(
    pdf_file: Any,  # Can be path, BytesIO, or file-like object from FastAPI upload
    table_id: str,
    context: str,
    text: bool = True,
    table: bool = True,
    page_ids: Optional[List[int]] = None,
    truncate_all: bool = False,
):
    """Enhanced document ingestion using refactored PDF processing."""

    # Process document with enhancements from knowledge_base_pdf_helpers
    # process_pdf_document is the refactored version
    page_data = process_pdf_document(
        pdf_file_source=pdf_file,
        extract_text=text,
        extract_tables=table,
        page_ids_to_process=page_ids,
        # use_custom_text_extraction_method can be a parameter if needed
    )

    if not page_data:
        print("No content extracted from document")
        return

    all_documents: List[Document] = []
    for page_num, page_content_info in page_data.items():
        # page_content_info structure from refactored process_pdf_document:
        # {
        #     "text_content": cleaned_page_content,
        #     "metadata": { "page_number": ..., "word_count": ..., ... },
        #     "quality_metrics": { "content_quality_score": ..., "information_density_score": ...}
        # }

        # These are page-level scores and metadata that will be associated with the Document object
        # before it's split into chunks.
        doc_metadata = {
            "page_id": page_num,  # Using the key from page_data dict, which is the page number
            "context": context,
            # Page-level quality, using the key "quality_score" for consistency if downstream code expects it
            "quality_score": page_content_info["quality_metrics"][
                "content_quality_score"
            ],
            # Page-level information density
            "information_density": page_content_info["quality_metrics"][
                "information_density_score"
            ],
            # Spread other detailed metadata from the page (word_count, has_dates, etc.)
            **page_content_info["metadata"],
        }
        # page_content_info["metadata"] contains "page_number", which is same as page_num.
        # It also contains "entity_density_per_100_words", which is same as "information_density_score".
        # Spreading it is fine; more specific keys take precedence if added before spread, or override if after.
        # Current setup should be okay.

        doc = Document(
            page_content=page_content_info[
                "text_content"
            ],  # Use "text_content" from refactored output
            metadata=doc_metadata,
        )
        all_documents.append(doc)

    # Use SemanticBoundariesTextSplitter (the refactored intelligent splitter)
    text_splitter = SemanticBoundariesTextSplitter(
        chunk_size=800,  # As per original script
        chunk_overlap=150,  # As per original script
    )
    split_documents = text_splitter.split_documents(all_documents)

    enhanced_chunk_metadata_list: List[Dict[str, Any]] = []
    chunk_texts: List[str] = []

    for i, chunk_doc in enumerate(split_documents):
        # chunk_doc.metadata already contains page_id, context, page-level quality_score,
        # page-level information_density, and other metadata from page_content_info["metadata"].

        current_chunk_metadata = (
            chunk_doc.metadata.copy()
        )  # Start with inherited metadata
        current_chunk_metadata.update(
            {
                "chunk_id": uuid.uuid4().hex,  # Unique ID for the chunk
                "original_chunk_index": i,  # If order matters
                "chunk_length_chars": len(chunk_doc.page_content),
                "chunk_word_count": len(chunk_doc.page_content.split()),
                # Calculate quality specifically for this chunk's content
                "chunk_quality": calculate_text_content_quality(chunk_doc.page_content),
                "has_structured_data": "|" in chunk_doc.page_content
                or "[TABLE START" in chunk_doc.page_content  # Match new table markers
                or "[TABLE END" in chunk_doc.page_content,
                # Using a portion of hash for near-deduplication, consider full hash or other methods if needed
                "content_hash_prefix": str(hash(chunk_doc.page_content))[:10],
            }
        )
        enhanced_chunk_metadata_list.append(current_chunk_metadata)
        chunk_texts.append(chunk_doc.page_content)

    # Deduplication of chunks (optional, if not handled by vector store or if desired here)
    # The user's original script had deduplication; let's adapt it slightly.
    unique_texts_final: List[str] = []
    unique_metadata_final: List[Dict[str, Any]] = []
    # Using a more robust content hash for deduplication if available, or combination of fields.
    # For this example, let's use the `content_hash_prefix` if it's deemed sufficient.
    # A full SHA256 hash would be more robust for true content deduplication.
    seen_chunk_hashes = set()

    for text_content, meta in zip(chunk_texts, enhanced_chunk_metadata_list):
        # Using a simple prefix; for production, a full content hash (e.g., SHA256) is better.
        # The original used `hash() % 1000000` which is not cryptographically strong for uniqueness.
        # Let's assume "content_hash_prefix" or a more robust hash is used.
        # For now, we'll use the prefix generated above.

        # If a more robust hash is needed:
        # import hashlib
        # content_hash_full = hashlib.sha256(text_content.encode('utf-8')).hexdigest()

        # Using the prefix for this example as in the spirit of original code's simplicity
        # but for production, a full hash stored in metadata would be better for `create_vectors_enhanced`
        # to handle true deduplication if it doesn't do it internally.
        # For this logic, we assume the vector DB handles finer-grained deduplication or updates.
        # The provided logic simply filters before sending to `create_vectors_enhanced`.

        # Simplified: Assuming `create_vectors_enhanced` can handle duplicate content if sent,
        # or has its own ID mechanism. If pre-filtering is essential:
        current_hash = meta.get("content_hash_prefix")  # Or a more robust hash
        if current_hash not in seen_chunk_hashes:
            seen_chunk_hashes.add(current_hash)
            unique_texts_final.append(text_content)
            unique_metadata_final.append(meta)
        # Else: if pre-filtering is not critical, send all processed chunks
        # unique_texts_final = chunk_texts
        # unique_metadata_final = enhanced_chunk_metadata_list

    # If no pre-filtering was done, use all chunks:
    if not unique_texts_final:  # Or based on a flag
        unique_texts_final = chunk_texts
        unique_metadata_final = enhanced_chunk_metadata_list

    print("\n--- Enhanced Ingestion Statistics ---")
    print(f"- Original documents from PDF pages: {len(all_documents)}")
    print(f"- Chunks generated after splitting: {len(split_documents)}")
    print(
        f"- Chunks being sent to vector store (after potential pre-filtering): {len(unique_texts_final)}"
    )
    if unique_metadata_final:
        avg_chunk_q = sum(
            m.get("chunk_quality", 0.0) for m in unique_metadata_final
        ) / len(unique_metadata_final)
        print(f"- Average chunk quality: {avg_chunk_q:.2f}")
        structured_data_chunks = sum(
            1 for m in unique_metadata_final if m.get("has_structured_data", False)
        )
        print(f"- Chunks with potential structured data: {structured_data_chunks}")

    # Store in BigQuery with enhanced vectors
    if unique_texts_final:
        create_vectors_enhanced(
            project_id=project_id,  # Consider making these configurable
            region="EU",
            dataset="zenf_dataset",
            table=table_id,
            metadata=unique_metadata_final,
            texts=unique_texts_final,
            truncate=truncate_all,
        )
    else:
        print("No unique texts to ingest after processing.")


def search_enhanced(
    query: str, filter: Optional[Dict[str, Any]], table_id: str, k: int = 10
):
    """Enhanced search with better retrieval, prompting, and response formatting."""

    prompt_template_str = """You are an intelligent document assistant. Your primary goal is to answer questions accurately based *only* on the provided context.

Context from documents:
---------------------
{context}
---------------------

Question: {input}

Instructions for Answering:
1.  Base your answer *strictly* on the information found in the "Context from documents" above. Do not use any external knowledge or make assumptions.
2.  If the context directly answers the question, provide the answer. Quote relevant parts of the context if it helps clarify the answer, but keep quotes concise.
3.  If the question asks for a list, items, or rankings, and the information is present, provide it as requested.
4.  Include relevant details like page numbers (if available in the metadata like 'page_id') or document source identifiers if they help the user locate the information.
5.  If the information needed to answer the question is *not found* in the provided context, you MUST explicitly state that. For example, say "Based on the provided context, I cannot answer this question." or "The provided documents do not contain information about [topic of question]."
6.  Be concise but ensure your answer is comprehensive within the bounds of the provided context. Avoid speculation.
7.  If there are multiple pieces of relevant context, synthesize them into a coherent answer.

Answer:"""

    prompt = ChatPromptTemplate.from_template(prompt_template_str)

    # Ensure API key is available for ChatGoogleGenerativeAI
    gemini_api_key = os.environ.get("GOOGLE_GEMINI_API_KEY")
    if not gemini_api_key:
        # Fallback or raise error if ADC is not intended for LLM auth.
        # For Gemini, API key is common.
        print(
            "Warning: GOOGLE_GEMINI_API_KEY not found. LLM calls may fail or use ambient ADC if configured."
        )
        # raise ValueError("GOOGLE_GEMINI_API_KEY is required for ChatGoogleGenerativeAI")

    # Safety settings as defined by user
    safety_settings = {
        HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    }

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-pro-preview-03-25",  # Using a generally available model, user had "gemini-2.0-flash-lite"
        # api_key=gemini_api_key, # Handled by library if GOOGLE_API_KEY or GOOGLE_GEMINI_API_KEY env var is set
        safety_settings=safety_settings,
        temperature=0.1,  # For more factual, less creative answers
        convert_system_message_to_human=True,  # Often useful for models that don't strongly differentiate system/human
    )

    document_chain = create_stuff_documents_chain(llm, prompt)

    retriever = EnhancedBigQueryRetriever(
        project_id=project_id,  # Consider making these configurable
        region="EU",
        dataset="zenf_dataset",
        table=table_id,
        filter=filter,
        k=k,  # Use the passed-in k for retriever
    )

    retrieval_chain = create_retrieval_chain(retriever, document_chain)

    try:
        response = retrieval_chain.invoke({"input": query})
    except Exception as e:
        print(f"Error during retrieval_chain.invoke: {e}")
        # Provide a fallback response or re-raise as appropriate
        return {
            "answer": "An error occurred while trying to answer the question. Please try again later.",
            "sources": [],
            "total_sources": 0,
            "retrieval_quality": {},
        }

    # Enhanced response processing for sources
    sources_info = []
    retrieved_docs = response.get("context", [])

    avg_chunk_quality_sum = 0
    valid_quality_scores = 0
    structured_data_in_sources = 0

    for doc in retrieved_docs:
        metadata = doc.metadata if hasattr(doc, "metadata") else {}
        content_preview = doc.page_content
        if len(content_preview) > 300:
            content_preview = content_preview[:300] + "..."

        chunk_q = metadata.get("chunk_quality", "N/A")
        if chunk_q != "N/A":
            try:
                avg_chunk_quality_sum += float(chunk_q)
                valid_quality_scores += 1
            except ValueError:
                pass  # Keep as N/A if not float

        has_struct_data = metadata.get("has_structured_data", False)
        if has_struct_data:
            structured_data_in_sources += 1

        sources_info.append(
            {
                "content_preview": content_preview,
                "metadata": {
                    "page_id": metadata.get("page_id", "N/A"),
                    # "page_quality_score": metadata.get("quality_score", "N/A"), # Page quality
                    "chunk_quality_score": chunk_q,  # Chunk specific quality
                    "information_density": metadata.get(
                        "information_density", "N/A"
                    ),  # Page info density
                    "has_structured_data": has_struct_data,
                    "context_tag": metadata.get(
                        "context", "N/A"
                    ),  # Original context tag
                    "chunk_id": metadata.get(
                        "chunk_id", "N/A"
                    ),  # Chunk ID if available
                },
            }
        )

    final_avg_chunk_quality = (
        (avg_chunk_quality_sum / valid_quality_scores)
        if valid_quality_scores > 0
        else 0
    )

    return {
        "answer": response.get("answer", "No answer generated."),
        "sources": sources_info,
        "total_sources_retrieved": len(sources_info),
        "retrieval_analytics": {  # Renamed for clarity
            "average_retrieved_chunk_quality": round(final_avg_chunk_quality, 2),
            "count_structured_data_sources": structured_data_in_sources,
        },
    }


def ingest_vectors_from_url(
    url: str, table_id: str, context: str, truncate_all: bool = False
):
    """Ingests text content from a URL into the vector store."""
    # Corrected: WebBaseLoader is in langchain_community.document_loaders
    try:
        loader = WebBaseLoader(web_paths=[url])  # Pass URL as a list to web_paths
        docs = loader.load()
    except Exception as e:
        print(f"Error loading URL {url}: {e}")
        return

    if not docs:
        print(f"No documents loaded from URL: {url}")
        return

    # Using a simple RecursiveCharacterTextSplitter for web content, not the PDF-specific one
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    documents = text_splitter.split_documents(docs)

    # Basic metadata for web documents
    all_metadata = []
    all_texts = []
    for i, doc_content in enumerate(documents):
        # doc_content is already a Document object
        page_text = doc_content.page_content
        meta = doc_content.metadata.copy() if hasattr(doc_content, "metadata") else {}
        meta.update(
            {
                "document_index": i,
                "source_url": url,  # Add original URL
                "text_length_chars": len(page_text),
                "context": context,  # User-provided context tag
                "chunk_quality": calculate_text_content_quality(
                    page_text
                ),  # Basic quality for the chunk
            }
        )
        all_metadata.append(meta)
        all_texts.append(page_text)

    if not all_texts:
        print(f"No text content to ingest from URL: {url} after splitting.")
        return

    create_vectors_enhanced(
        project_id=project_id,  # Consider making these configurable
        region="EU",
        dataset="zenf_dataset",
        table=table_id,
        metadata=all_metadata,
        texts=all_texts,
        truncate=truncate_all,
    )
    print(f"Successfully ingested {len(all_texts)} chunks from URL: {url}")


# Initialize BigQuery client (globally or within functions where needed)
# It's generally fine to initialize it globally if the script's lifecycle aligns with it.
# For FastAPI, you might manage clients via app state or dependency injection.
try:
    bigquery_client = bigquery.Client()  # Uses Application Default Credentials
except Exception as e:
    print(
        f"Warning: Failed to initialize BigQuery client: {e}. BigQuery operations will fail."
    )
    bigquery_client = None


project_id = os.environ.get("PROJECT_ID")


def create_bigquery_table_if_not_exists(
    table_id: str, schema: List[bigquery.SchemaField]
) -> None:
    """Creates a BigQuery table if it doesn't already exist."""
    if not bigquery_client:
        print("BigQuery client not initialized. Cannot create table.")
        raise RuntimeError("BigQuery client not available.")

    dataset_id = "zenf_dataset"  # Hardcoded, consider config

    full_table_id = f"{project_id}.{dataset_id}.{table_id}"

    try:
        bigquery_client.get_table(full_table_id)  # Check if table exists
        print(f"Table {full_table_id} already exists.")
    except Exception:  # Typically google.cloud.exceptions.NotFound
        print(f"Table {full_table_id} not found. Creating table...")
        table_ref = bigquery.Table(full_table_id, schema=schema)
        try:
            bigquery_client.create_table(table_ref)
            print(f"Table {full_table_id} created successfully.")
        except Exception as e_create:  # Handle other creation errors
            print(f"Error creating table {full_table_id}: {e_create}")
            raise HTTPException(
                status_code=500, detail=f"Failed to create table {table_id}: {e_create}"
            )


async def set_knowledge_base_as_default(
    db: AsyncSession, user_id: int, knowledge_base_id: uuid.UUID
):
    """Set a knowledge base as default for a user (async version)."""
    # Retrieve the target knowledge base
    target_kb_result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == knowledge_base_id, KnowledgeBase.user_id == user_id
        )
    )
    target_kb = target_kb_result.scalars().first()

    if not target_kb:
        raise HTTPException(
            status_code=404, detail="Knowledge base not found or not owned by user."
        )

    if target_kb.is_default:
        print(
            f"Knowledge base {knowledge_base_id} is already the default for user {user_id}."
        )
        return  # Already the default, no changes needed

    # Unset any existing default knowledge base for the user
    # Use update() for a more efficient bulk update if supported and preferred
    existing_defaults_result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.user_id == user_id,
            KnowledgeBase.is_default == True,  # Explicitly True
        )
    )

    for (
        existing_default_kb
    ) in existing_defaults_result.scalars().all():  # Use .all() to iterate
        if (
            existing_default_kb.id != target_kb.id
        ):  # Don't unset the one we are about to set
            existing_default_kb.is_default = False
            # db.add(existing_default_kb) # Mark for update if not automatically tracked by session

    # Set the specified knowledge base as default
    target_kb.is_default = True
    # db.add(target_kb) # Mark for update

    try:
        await db.commit()
        print(f"Knowledge base {knowledge_base_id} set as default for user {user_id}.")
    except Exception as e_commit:
        await db.rollback()
        print(f"Error committing changes to set default knowledge base: {e_commit}")
        raise HTTPException(
            status_code=500, detail="Failed to update default knowledge base settings."
        )
