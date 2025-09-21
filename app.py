from fastapi import FastAPI, Query, UploadFile, File, HTTPException,APIRouter
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from opensearchpy import OpenSearch
from typing import List
from mangum import Mangum
import os
import json
import boto3
import re

router = APIRouter()
app = FastAPI()

origins = [
    "http://127.0.0.1:5500",  # your frontend URL
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # or ["http://127.0.0.1:5500"] if using Live Server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Serve static files from the current folder
app.mount("/static", StaticFiles(directory="."), name="static")

# Serve main HTML page
@app.get("/")
def main_page():
    return FileResponse("knowledge_search.html")

# OpenSearch config
OPENSEARCH_HOST = "search-risingstars-l4yuatyouvcbjbbf4c47pk3ium.us-east-1.es.amazonaws.com"
INDEX_NAME = "knowledge_base"
OPENSEARCH_USER = os.getenv("risingstar") or "risingstar"
OPENSEARCH_PASSWORD = os.getenv("12345678Aa!") or "12345678Aa!"

client = OpenSearch(
    hosts=[{"host": "search-risingstars-l4yuatyouvcbjbbf4c47pk3ium.us-east-1.es.amazonaws.com", "port": 443}],
    http_auth=("risingstar", "12345678Aa!"),
    use_ssl=True,
    verify_certs=True
)
def create_index_if_not_exists():
    if not client.indices.exists(index=INDEX_NAME):
        client.indices.create(
            index=INDEX_NAME,
            body={
                "mappings": {
                    "properties": {
                        "title": {"type": "text"},
                        "content": {"type": "text"}
                    }
                }
            }
        )
create_index_if_not_exists()


def extract_txt_text(file_path: str):
    """Read plain .txt files"""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def chunk_text(text, chunk_size=150):
    """Split text into chunks of ~chunk_size words"""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunks.append(" ".join(words[i:i+chunk_size]))
    return chunks

def split_into_sentences(text: str):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


# Upload folder
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload_documents/")
async def upload_documents(files: List[UploadFile] = File(...)):
    documents = []

    # ✅ Clear old docs before uploading new
    client.delete_by_query(index=INDEX_NAME, body={"query": {"match_all": {}}})

    for file in files:
        try:
            text = (await file.read()).decode("utf-8")  # read txt content
            chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]  # chunking

            for idx, chunk in enumerate(chunks):
                doc_id = f"{file.filename}_chunk_{idx}"
                doc = {"title": file.filename, "content": chunk}
                client.index(index=INDEX_NAME, id=doc_id, body=doc)
                documents.append(doc)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to process {file.filename}: {str(e)}")

    return {"message": "Documents uploaded & indexed successfully", "documents": documents}


@app.get("/search/")
def search_documents(query: str = Query(..., min_length=1)):
    try:
        response = client.search(
            index=INDEX_NAME,
            body={
                "query": {
                    "bool": {
                        "should": [
                            {"match": {"content": {"query": query, "fuzziness": "AUTO"}}},
                            {"match": {"title": {"query": query, "fuzziness": "AUTO"}}}
                        ]
                    }
                },
                "size": 1
            }
        )

        hits = []
        lower_query = query.lower()

        for hit in response.get("hits", {}).get("hits", []):
            content = hit["_source"].get("content", "")
            sentences = split_into_sentences(content)

            # find sentences containing the query (case-insensitive)
            relevant = [s for s in sentences if lower_query in s.lower()]

            # fallback: first 3 sentences if none matched
            if not relevant:
                relevant = sentences[:3]

            # join up to 3 sentences into one clean answer
            answer_text = " ".join(relevant[:3])

            hits.append({
                "title": hit["_source"].get("title", "Untitled"),
                "content": answer_text
            })

        return {"results": hits} if hits else {"results": []}

    except Exception as e:
        return JSONResponse({"error": str(e)})


@app.get("/test_opensearch/")
def test_opensearch():
    try:
        # Create a test document
        test_doc = {
            "title": "Test Document",
            "content": "This is a test content for OpenSearch integration.",
            "media_url": None
        }
        # Index the test document
        client.index(index=INDEX_NAME, id="test_doc_1", body=test_doc)

        # Search for the test word
        response = client.search(
            index=INDEX_NAME,
            query={"match": {"content": "test"}},
            size=3
        )

        hits = [hit["_source"] for hit in response["hits"]["hits"]]

        return {"indexed_document": test_doc, "search_hits": hits}
    except Exception as e:
        return {"error": str(e)}





