
import os
import dotenv

dotenv.load_dotenv()

def getGeminiApiKey():
    return os.environ.get("GEMINI_API_KEY")

def getClient():
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(model="gemini-3-flash-preview", api_key=getGeminiApiKey())


class MockRedisClient:
    """Mock Redis client that doesn't fail when Redis is unavailable."""
    def ping(self): return True
    def hset(self, *args, **kwargs): return True
    def hgetall(self, *args, **kwargs): return {}
    def set(self, *args, **kwargs): return True
    def get(self, *args, **kwargs): return None

def getRedisClient():
    import redis
    try:
        # Try environment variable first
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            return redis.from_url(redis_url)
        else:
            # Default to local Redis (docker-compose setup)
            return redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    except Exception as e:
        print(f"Redis connection error: {e}")
        # Return a mock client that doesn't fail
        return MockRedisClient()

