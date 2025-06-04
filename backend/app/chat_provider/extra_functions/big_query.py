import os
import statistics
from typing import List, Any, Optional, Dict
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    HarmBlockThreshold,
    HarmCategory,
)
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain
from langchain_google_vertexai import VertexAIEmbeddings
from app.chat_provider.extra_functions.bigquery_vector import (
    create_vectors as bq_create_vectors,
    search_by_text as bq_search_by_text,
)

from app.chat_provider.extra_functions.pdf_parser import (
    IntelligentTextSplitter,
    calculate_content_quality,
    process_document,
    process_document_enhanced,
)
from app.chat_provider.extra_functions.bigquery_vector_search import (
    BigQueryVectorSearchLocal,
)
from langchain_community.vectorstores.utils import DistanceStrategy


safety_settings = {
    HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
}
from google.cloud import bigquery

GEMINI_API_KEY = os.environ.get("GOOGLE_GEMINI_API_KEY", "")


quicksearch_llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-lite",
    api_key=GEMINI_API_KEY,
    safety_settings=safety_settings,
)

PROJECT_ID = "gdg-on-campus-challenge"
REGION = "EU"
DATASET = "zenf_dataset"
TABLE = "doc_and_vectors"

LLM = quicksearch_llm


class BigQueryRetriever(BaseRetriever):
    project_id: str
    region: str
    dataset: str
    table: str
    filter: Optional[Dict[str, Any]] = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.project_id = kwargs["project_id"]
        self.region = kwargs["region"]
        self.dataset = kwargs["dataset"]
        self.table = kwargs["table"]
        self.filter = kwargs["filter"]

    def get_relevant_documents(self, query: str) -> List[Document]:
        return bq_search_by_text(
            project_id=self.project_id,
            region=self.region,
            dataset=self.dataset,
            table=self.table,
            filter=self.filter,
            query=query,
        )


# 6. ENHANCED RETRIEVER WITH BETTER RANKING


# 7. ENHANCED SEARCH WITH BETTER PROMPTING


# Keep existing utility classes


# Keep your existing functions that are still needed
def extract_text_custom(page):
    # Your existing implementation
    chars = page.chars
    if not chars:
        return ""
    chars.sort(key=lambda c: -c["y0"])
    lines = []
    current_line = [chars[0]]
    for char in chars[1:]:
        if abs(char["y0"] - current_line[-1]["y0"]) < 2:
            current_line.append(char)
        else:
            lines.append(current_line)
            current_line = [char]
    if current_line:
        lines.append(current_line)
    margin = 50
    h = page.height
    lines = [line for line in lines if margin < line[0]["y0"] < h - margin]
    for line in lines:
        line.sort(key=lambda c: c["x0"])
    text = ""
    for line in lines:
        if len(line) > 1:
            spaces = [line[i + 1]["x0"] - line[i]["x1"] for i in range(len(line) - 1)]
            median_space = statistics.median(spaces) if spaces else 0
            space_threshold = median_space * 1.5 if median_space > 0 else 1
        else:
            space_threshold = 1
        text_line = line[0]["text"]
        for i in range(1, len(line)):
            if spaces[i - 1] > space_threshold:
                text_line += " "
            text_line += line[i]["text"]
        text += text_line + "\n"
    return text


def search(query, filter, table_id):
    prompt = ChatPromptTemplate.from_template("""
    You are a financial document analyst. Answer the question based on the provided context from bank statements and financial documents.                                         
    Answer the following question based only on the provided context:

    <context>
    {context}
    </context>

    Question: {input}""")

    document_chain = create_stuff_documents_chain(LLM, prompt)
    retriever = BigQueryRetriever(
        project_id=PROJECT_ID,
        region=REGION,
        dataset=DATASET,
        table=table_id,
        filter=filter,
    )
    retrieval_chain = create_retrieval_chain(retriever, document_chain)
    response = retrieval_chain.invoke({"input": query})

    # Convert Document objects to dictionaries
    sources = [
        {"content": doc.page_content, "metadata": doc.metadata}
        for doc in response.get("context", [])
    ]

    return {"answer": response["answer"], "sources": sources}
