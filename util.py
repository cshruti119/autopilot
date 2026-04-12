
import os
import dotenv

dotenv.load_dotenv()

def getGeminiApiKey():
    return os.environ.get("GEMINI_API_KEY")

def getClient():
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(model="gemini-3-flash-preview", api_key=getGeminiApiKey())

def getChromaClient():
    import chromadb
    return chromadb.HttpClient(host="localhost", port=8001)

