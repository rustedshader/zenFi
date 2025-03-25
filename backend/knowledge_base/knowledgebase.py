import os
from chromadb import PersistentClient
from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

CHROMA_DB_DIRECTORY = "knowledge_base_db"
DOCUMENT_SOURCE_DIRECTORY = "source_documents"
TARGET_SOURCE_CHUNKS = 4
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
HIDE_SOURCE_DOCUMENTS = False

GEMINI_API_KEY = os.environ.get["GOOGLE_GEMINI_API_KEY"]


class MyKnowledgeBase:
    def __init__(self, pdf_source_folder_path: str) -> None:
        """
        Loads PDFs and creates a knowledge base using the Chroma vector DB.

        Args:
            pdf_source_folder_path (str): The source folder containing all the PDF documents
        """
        self.pdf_source_folder_path = pdf_source_folder_path

    def load_pdfs(self):
        loader = DirectoryLoader(self.pdf_source_folder_path)
        loaded_pdfs = loader.load()
        return loaded_pdfs

    def split_documents(self, loaded_docs):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )
        chunked_docs = splitter.split_documents(loaded_docs)
        return chunked_docs

    def convert_document_to_embeddings(self, chunked_docs, embedder):
        # Create a persistent client for the vector database
        client = PersistentClient(path=CHROMA_DB_DIRECTORY)
        vector_db = Chroma(
            client=client,
            embedding_function=embedder,
        )
        vector_db.add_documents(chunked_docs)
        # Note: persist() is not needed with PersistentClient as it handles persistence automatically
        return vector_db

    def return_retriever_from_persistant_vector_db(self, embedder):
        if not os.path.isdir(CHROMA_DB_DIRECTORY):
            raise NotADirectoryError("Please load your vector database first.")

        # Load the existing vector database using PersistentClient
        client = PersistentClient(path=CHROMA_DB_DIRECTORY)
        vector_db = Chroma(
            client=client,
            embedding_function=embedder,
        )
        return vector_db.as_retriever(search_kwargs={"k": TARGET_SOURCE_CHUNKS})

    def initiate_document_injetion_pipeline(self):
        loaded_pdfs = self.load_pdfs()
        chunked_documents = self.split_documents(loaded_docs=loaded_pdfs)

        print("=> PDF loading and chunking done.")

        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=GEMINI_API_KEY,
        )
        self.convert_document_to_embeddings(
            chunked_docs=chunked_documents, embedder=embeddings
        )

        print("=> Vector DB initialized and created.")
        print("All done")


# Example usage (if run as a script)
if __name__ == "__main__":
    kb = MyKnowledgeBase(DOCUMENT_SOURCE_DIRECTORY)
    kb.initiate_document_injetion_pipeline()
