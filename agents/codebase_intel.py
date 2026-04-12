import chromadb
from pathlib import Path

from util import getClient, getChromaClient

client = getClient()  
chroma = getChromaClient() 
    
def index_repo(repo_path: str):
    """Run once, or on file change events."""
    collection = chroma.get_or_create_collection("codebase")
    repo = Path(repo_path)

    for file in repo.rglob("*.py"):  # add *.ts, *.js etc as needed
        content = file.read_text(errors="ignore")
        # Chunk by function/class (simple split for now)
        chunks = [content[i:i+1000] for i in range(0, len(content), 1000)]
        for i, chunk in enumerate(chunks):
            collection.upsert(
                documents=[chunk],
                ids=[f"{file}::{i}"]
            )

def query_context(question: str) -> str:
    """Called by Prep Agent to get relevant codebase context."""
    collection = chroma.get_or_create_collection("codebase")
    results = collection.query(query_texts=[question], n_results=5)
    return "\n\n".join(results["documents"][0])