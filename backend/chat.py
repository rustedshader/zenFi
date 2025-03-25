from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from app.chat_provider.service.chat_service import ChatService
import os

load_dotenv()


GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Main execution block
if __name__ == "__main__":
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-pro-exp-02-05",
        api_key=GEMINI_API_KEY,
    )
    chat_service = ChatService(llm)
    print("Chatbot ready! Type 'quit', 'exit', or 'bye' to stop.")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["quit", "exit", "bye"]:
            print("Assistant: Goodbye!")
            break
        response = chat_service.process_input(user_input)
        print("Assistant:", response)
