import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv() 

def main():
    """Main entry point for the Hello Python application."""
    print("Hello, World!")
    model = ChatGoogleGenerativeAI(model="gemini-3.1-pro-preview", api_key=os.environ.get("GEMINI_API_KEY"))
    model_response = model.invoke("What is tamagachi? Give a concise answer in 2 sentences.")
    print("Model response:", model_response.text)

if __name__ == "__main__":
    main()