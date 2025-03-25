from langchain_google_community import GoogleSearchAPIWrapper
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from app.chat_provider.service.chat_service import ChatService
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import AsyncGenerator
import json
from langchain_google_genai import HarmBlockThreshold, HarmCategory
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.tools import BraveSearch
from dotenv import load_dotenv
import os


load_dotenv()

app = FastAPI()

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust to your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic model for chat input
class ChatInput(BaseModel):
    message: str


# Pydantic model for chat response
class ChatResponse(BaseModel):
    message: str
    sources: list = []


safety_settings = {
    HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
}


GEMINI_API_KEY = os.environ.get["GOOGLE_GEMINI_API_KEY"]
BRAVE_API_KEY = os.environ.get("BRAVE_SEARCH_API_KEY")
GOOGLE_SEARCH_API_KEY = os.environ.get("GOOGLE_SEARCH_API_KEY")
TAVILY_SEARCH_API_KEY = os.environ.get("TAVILY_API_KEY")
GOOGLE_CSE_ID = os.environ.get("GOOGLE_SEACH_ENGINE_ID")

# Initialize the language model
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-pro-exp-02-05",
    api_key=GEMINI_API_KEY,
    safety_settings=safety_settings,
)

search = GoogleSearchAPIWrapper(
    google_api_key=GOOGLE_SEARCH_API_KEY,
    google_cse_id=GOOGLE_CSE_ID,
)
tavily_tool = TavilySearchResults(tavily_api_key=TAVILY_SEARCH_API_KEY)

google_embedings = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004",
    google_api_key=GEMINI_API_KEY,
)

brave_search = (
    BraveSearch.from_api_key(api_key=BRAVE_API_KEY, search_kwargs={"count": 3}),
)


# ChatServiceManager with streaming method
class ChatServiceManager:
    def __init__(self):
        self.chat_service = ChatService(
            llm=llm,
            google_search_wrapper=search,
            google_embedings=google_embedings,
            tavily_tool=tavily_tool,
            brave_search=brave_search,
        )

    async def process_message(self, message: str) -> ChatResponse:
        """Process a message synchronously for the /chat endpoint."""
        try:
            response = await self.chat_service.process_input(message)
            return ChatResponse(message=response, sources=[])
        except Exception as e:
            return ChatResponse(message=f"An error occurred: {str(e)}", sources=[])

    async def stream_message(self, message: str) -> AsyncGenerator[str, None]:
        """Stream message tokens for the HTTP streaming endpoint."""
        async for token in self.chat_service.stream_input(message):
            yield token


# Singleton instance
chat_service_manager = ChatServiceManager()


@app.post("/chat")
async def send_message(input_data: ChatInput):
    """Synchronous chat endpoint."""
    response = await chat_service_manager.process_message(input_data.message)
    return response


@app.post("/chat/stream_http")
async def stream_chat(input_data: ChatInput):
    """HTTP streaming endpoint for chat responses."""

    async def stream_generator():
        try:
            # Use the stream_input method from ChatService
            async for chunk in chat_service_manager.stream_message(input_data.message):
                # Ensure chunk is not None and not an empty string
                if chunk and chunk.strip():
                    # Send data event with the chunk
                    yield f"data: {json.dumps({'content': chunk})}\n\n"

            # Send stop event when streaming is complete
            yield 'data: {"finishReason":"stop"}\n\n'

        except Exception as e:
            # Send error event if something goes wrong
            yield f'data: {{"finishReason":"error","error":{json.dumps(str(e))}}}\n\n'

    # Create StreamingResponse with the generator
    response = StreamingResponse(stream_generator(), media_type="text/event-stream")
    response.headers["Content-Type"] = "text/event-stream"
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    return response


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
