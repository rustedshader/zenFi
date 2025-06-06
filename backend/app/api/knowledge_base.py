import uuid
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File
from google.cloud import bigquery
from uuid import uuid4
from typing import List
from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    HarmBlockThreshold,
    HarmCategory,
)
from langchain_google_vertexai import VertexAIEmbeddings
from app.api.api_models import (
    FileUploadResponse,
    KnowledgeBase,
    KnowledgeBaseCreateInput,
    KnowledgeBaseOutput,
    QueryRequest,
    QueryResponse,
    SetDefaultKnowledgeBaseInput,
    User,
)
from app.api.api_functions import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from app.api.api_functions import get_db
from sqlalchemy.future import select
from io import BytesIO

from app.chat_provider.service.knowledge_base.knowledege_base import (
    create_bigquery_table_if_not_exists,
    search_enhanced,
    ingest_vectors_from_url,
    ingest_documents_enhanced,
    set_knowledge_base_as_default,
)
from app.config.config import GEMINI_API_KEY, project_id

# -----------------Prequiste-------------#
# ---------------------------------------#

safety_settings = {
    HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
}

rag_llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-lite",
    api_key=GEMINI_API_KEY,
    safety_settings=safety_settings,
)

dataset_id = "zenf_dataset"
client = bigquery.Client()
embedding_model = VertexAIEmbeddings(
    model_name="text-embedding-005", project=project_id
)

# ---------------------------------------#

knowledge_base_router = APIRouter(prefix="/knowledge_base")


@knowledge_base_router.post("/new", response_model=KnowledgeBaseOutput)
async def create_knowledge_base(
    request: KnowledgeBaseCreateInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    knowledge_base_id = uuid4()
    table_id = f"kb_{str(knowledge_base_id).replace('-', '_')}"

    schema = [
        bigquery.SchemaField("doc_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("content", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("embedding", "FLOAT64", mode="REPEATED"),
        bigquery.SchemaField("metadata", "JSON", mode="NULLABLE"),
    ]
    stmt = select(KnowledgeBase).where(
        KnowledgeBase.user_id == current_user.id, KnowledgeBase.name == request.name
    )

    result = await db.execute(stmt)
    existing_kb = result.scalars().first()
    if existing_kb:
        raise HTTPException(
            status_code=400, detail=f"Knowledge base '{request.name}' already exists."
        )

    try:
        create_bigquery_table_if_not_exists(table_id=table_id, schema=schema)

        print(
            f"Table {table_id} created. Vector index will be created when data is added."
        )

        kb = KnowledgeBase(
            id=knowledge_base_id,
            user_id=current_user.id,
            name=request.name,
            description=request.description,
            meta_data=request.meta_data,
            table_id=table_id,
            is_default=False,
        )
        db.add(kb)
        await db.commit()
        await db.refresh(kb)

        if request.is_default:
            await set_knowledge_base_as_default(db, current_user.id, knowledge_base_id)

        return kb
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to create knowledge base: {str(e)}"
        )


@knowledge_base_router.post(
    "/{knowledge_base_id}/upload", response_model=FileUploadResponse
)
async def upload_file_to_knowledge_base(
    knowledge_base_id: str,
    file: UploadFile = File(None),
    url: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload and process a file or URL into the knowledge base"""

    try:
        kb_uuid = uuid.UUID(knowledge_base_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid knowledge base ID format")

    stmt = select(KnowledgeBase).where(
        KnowledgeBase.id == kb_uuid, KnowledgeBase.user_id == current_user.id
    )
    result = await db.execute(stmt)
    kb = result.scalars().first()
    if not kb:
        raise HTTPException(
            status_code=404, detail="Knowledge base not found or access denied"
        )

    if (file is None and url is None) or (file is not None and url is not None):
        raise HTTPException(
            status_code=400, detail="Provide either a file or a URL, but not both"
        )

    try:
        if file:
            if not file.filename.lower().endswith(".pdf"):
                raise HTTPException(
                    status_code=400, detail="Only PDF files are supported"
                )

            pdf_data = await file.read()
            pdf_file = BytesIO(pdf_data)

            try:
                print("Trying yo ingest vector to table id", kb.table_id)
                ingest_documents_enhanced(
                    pdf_file=pdf_file,
                    context="some_context",
                    table_id=kb.table_id,
                    text=True,
                    table=True,
                    page_ids=None,
                    truncate_all=False,
                )
                response = FileUploadResponse(
                    message="PDF processed successfully",
                    file_name=file.filename,
                    status="success",
                )
            except Exception as e:
                print(e)

        else:
            ingest_vectors_from_url(
                url=url,
                context=f"Uploaded URL: {url}",
                truncate_all=False,
                table_id=kb.table_id,
            )
            response = FileUploadResponse(
                message="URL processed successfully",
                file_name=url,
                status="success",
            )

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing input: {str(e)}")


@knowledge_base_router.post("/{knowledge_base_id}/query", response_model=QueryResponse)
async def query_knowledge_base(
    knowledge_base_id: str,
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query the knowledge base using RAG (Retrieval Augmented Generation)"""

    try:
        kb_uuid = uuid.UUID(knowledge_base_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid knowledge base ID format")

    stmt = select(KnowledgeBase).where(
        KnowledgeBase.id == kb_uuid, KnowledgeBase.user_id == current_user.id
    )
    result = await db.execute(stmt)
    kb = result.scalars().first()

    if not kb:
        raise HTTPException(
            status_code=404, detail="Knowledge base not found or access denied"
        )
    if not kb.table_id:
        raise HTTPException(
            status_code=500, detail="Knowledge base has no table_id set"
        )

    count_query = f"""
    SELECT COUNT(*) as doc_count
    FROM `{project_id}.{dataset_id}.{kb.table_id}`
    """

    try:
        count_result = client.query(count_query).result()
        doc_count = list(count_result)[0].doc_count

        if doc_count == 0:
            raise HTTPException(
                status_code=400,
                detail="Knowledge base is empty. Please upload documents first.",
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error checking knowledge base: {str(e)}"
        )

    print("LOG: Trying Rag Query for knowledge Base")

    try:
        rag_result = search_enhanced(
            table_id=kb.table_id,
            query=request.query,
            filter={"context": "some_context"},
        )
        return QueryResponse(
            answer=rag_result["answer"],
            sources=rag_result["sources"],
            query=request.query,
            knowledge_base_id=knowledge_base_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to process query: {str(e)}"
        )


@knowledge_base_router.get("/list", response_model=List[KnowledgeBaseOutput])
async def get_user_knowledge_base(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    stmt = select(KnowledgeBase).where(KnowledgeBase.user_id == current_user.id)
    result = await db.execute(stmt)
    knowledge_bases = result.scalars().all()
    return knowledge_bases


@knowledge_base_router.post(
    "/set_default_knowledge_base",
    response_model=List[KnowledgeBaseOutput],
)
async def set_default_knowledge_base(
    knowledge_base: SetDefaultKnowledgeBaseInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # First, unset any existing default knowledge base
    await db.execute(
        update(KnowledgeBase).where(KnowledgeBase.is_default).values(is_default=False)
    )

    kb_uuid = uuid.UUID(knowledge_base.knowledge_base_id)

    # Set the specified knowledge base as default
    await db.execute(
        update(KnowledgeBase).where(KnowledgeBase.id == kb_uuid).values(is_default=True)
    )

    # Commit the changes
    await db.commit()

    # Fetch all knowledge bases to return
    result = await db.execute(select(KnowledgeBase))
    knowledge_bases = result.scalars().all()

    return knowledge_bases


@knowledge_base_router.get("/{knowledge_base_id}/info")
async def get_knowledge_base_info(
    knowledge_base_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(KnowledgeBase).where(KnowledgeBase.id == uuid.UUID(knowledge_base_id))

    result = await db.execute(stmt)
    kb_data = result.scalar_one_or_none()
    return kb_data
