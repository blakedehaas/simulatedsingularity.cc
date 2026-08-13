"""Documentation Server with RAG via FastAPI and Chroma."""

import logging
import os
import pathlib
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
from dotenv import load_dotenv

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

# Load environment variables (for GOOGLE_API_KEY)
load_dotenv()

logger = logging.getLogger(__name__)

# Constants
DB_DIR = pathlib.Path.cwd() / ".chroma_db"
PROJECT_ROOT = pathlib.Path.cwd()
DOCS_HTML_PATH = PROJECT_ROOT / "docs.html"

# Global state
vector_store = None
llm = None


def ingest_codebase() -> Chroma:
    """Ingest all .py and .md files into ChromaDB."""
    logger.info("Initializing vector store from codebase...")
    
    # We will use Gemini embeddings
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

    # If the DB already exists, we load it instead of re-ingesting every time
    if DB_DIR.exists():
        logger.info("Loading existing Chroma vector store from %s", DB_DIR)
        store = Chroma(persist_directory=str(DB_DIR), embedding_function=embeddings)
        try:
            if store._collection.count() > 0:
                return store
            logger.info("Existing vector store is empty. Rebuilding...")
        except Exception as e:
            logger.warning("Error checking vector store size. Rebuilding: %s", e)

    logger.info("No existing vector store found. Crawling codebase and indexing...")
    
    docs = []
    # Only parse Python files in src/ and the main README
    targets = list((PROJECT_ROOT / "src").rglob("*.py"))
    if (PROJECT_ROOT / "README.md").exists():
        targets.append(PROJECT_ROOT / "README.md")

    for file_path in targets:
        try:
            content = file_path.read_text(encoding="utf-8")
            docs.append(Document(page_content=content, metadata={"source": str(file_path)}))
        except Exception as e:
            logger.warning("Failed to load %s: %s", file_path, e)

    # Chunk the documents
    # Larger chunk sizes significantly reduce the total number of chunks,
    # keeping us under the 100 requests-per-minute free tier quota for embeddings.
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=4000,
        chunk_overlap=400,
        length_function=len,
    )
    chunks = text_splitter.split_documents(docs)
    logger.info("Split %d files into %d chunks. Generating embeddings...", len(docs), len(chunks))

    # Create empty Chroma store and batch insert to avoid API rate limits
    store = Chroma(embedding_function=embeddings, persist_directory=str(DB_DIR))
    
    batch_size = 15
    import time
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        
        # Retry loop for rate limits
        retries = 0
        while True:
            try:
                store.add_documents(batch)
                break
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    retries += 1
                    sleep_time = 30 * retries
                    logger.warning("Rate limit hit. Sleeping %ds before retry...", sleep_time)
                    time.sleep(sleep_time)
                else:
                    raise e
                    
        logger.info("Indexed %d / %d chunks...", min(i + batch_size, len(chunks)), len(chunks))
        if i + batch_size < len(chunks):
            time.sleep(10)  # Gentle pacing between batches
            
    logger.info("Vector store initialization complete.")
    return store



async def heartbeat_monitor():
    import os
    import time
    import asyncio
    await asyncio.sleep(10)
    while True:
        if not os.getenv("DOCS_SERVER_PERSISTENT"):
            if time.time() - last_ping_time > 5:
                logger.info("No heartbeat received from UI. Exiting gracefully...")
                os._exit(0)
        await asyncio.sleep(1)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle hook to initialize RAG and DB components on startup."""
    global llm
    try:
        from singularity.memory_vault.database import init_database
        await init_database()
    except Exception as e:
        logger.error("Failed to initialize database: %s", e)

    try:
        llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0)
    except Exception as e:
        logger.error("Failed to initialize LLM: %s", e)
        
    def init_rag():
        global vector_store
        try:
            vector_store = ingest_codebase()
        except Exception as e:
            logger.error("Failed to initialize RAG pipeline: %s", e)

    import asyncio
    asyncio.create_task(asyncio.to_thread(init_rag))
    asyncio.create_task(heartbeat_monitor())
    yield
    # Shutdown logic if necessary


from fastapi.staticfiles import StaticFiles

app = FastAPI(lifespan=lifespan)
SENSORIUM_DIR = PROJECT_ROOT / "sensorium"

if SENSORIUM_DIR.exists():
    app.mount("/sensorium/static", StaticFiles(directory=str(SENSORIUM_DIR)), name="sensorium_static")

@app.get("/", response_class=HTMLResponse)
async def serve_docs():
    """Serve the static docs.html file."""
    if not DOCS_HTML_PATH.exists():
        return HTMLResponse(content="<h1>docs.html not found!</h1><p>Run `singularity -h` to generate it.</p>", status_code=404)
    return HTMLResponse(content=DOCS_HTML_PATH.read_text(encoding="utf-8"))

@app.get("/sensorium", response_class=HTMLResponse)
async def serve_sensorium():
    """Serve the C2 Sensorium Dashboard visual substrate."""
    sensorium_html = SENSORIUM_DIR / "index.html"
    if not sensorium_html.exists():
        return HTMLResponse(content="<h1>Sensorium dashboard not found!</h1>", status_code=404)
    html_content = sensorium_html.read_text(encoding="utf-8")
    # Fix relative css/js path if needed
    html_content = html_content.replace('href="style.css"', 'href="/sensorium/static/style.css"')
    html_content = html_content.replace('src="app.js"', 'src="/sensorium/static/app.js"')
    return HTMLResponse(content=html_content)


@app.post("/chat")
async def chat_endpoint(request: Request):
    """Handle RAG queries from the documentation UI."""
    data = await request.json()
    query = data.get("query", "")
    
    if not query:
        return JSONResponse(content={"error": "Empty query"}, status_code=400)
        
    if not vector_store or not llm:
        return JSONResponse(
            content={"response": "The RAG pipeline is not initialized properly. Is your GOOGLE_API_KEY set?"},
            status_code=500
        )

    try:
        # Retrieve context
        retriever = vector_store.as_retriever(search_kwargs={"k": 5})
        docs = retriever.invoke(query)
        context = "\n\n".join(doc.page_content for doc in docs)
        
        # Build prompt
        prompt = ChatPromptTemplate.from_template(
            "You are the Simulated Singularity Architect LLM. You are helping a developer understand the project.\n"
            "Use the following pieces of retrieved codebase context to answer the question. "
            "If you don't know the answer, just say that you don't know. "
            "Keep the answer concise and use markdown formatting.\n\n"
            "Context:\n{context}\n\n"
            "Question: {question}\n\n"
            "Answer:"
        )
        
        chain = prompt | llm
        response = await chain.ainvoke({"context": context, "question": query})
        
        response_content = response.content
        if isinstance(response_content, list):
            # If it's a list of blocks, extract text
            texts = []
            for block in response_content:
                if isinstance(block, dict) and "text" in block:
                    texts.append(block["text"])
                elif isinstance(block, str):
                    texts.append(block)
            response_content = "".join(texts)
        elif not isinstance(response_content, str):
            response_content = str(response_content)
            
        return JSONResponse(content={"response": response_content})
    except Exception as e:
        logger.error("RAG Error: %s", e)
        return JSONResponse(content={"response": f"An error occurred during retrieval: {e}"}, status_code=500)

import time

last_ping_time = time.time()

@app.post("/ping")
async def ping_endpoint():
    """Heartbeat endpoint to keep the server alive."""
    global last_ping_time
    last_ping_time = time.time()
    return JSONResponse(content={"status": "ok"})


@app.post("/api/heartbeat")
async def triadic_heartbeat_api(request: Request):
    """Broadcast a timestamped heartbeat prompt to all 3 triadic agents."""
    from datetime import datetime, timezone
    from singularity.neural_core.node_registry import initialize_constellation, get_all_agents
    from singularity.scheduler.heartbeat import HeartbeatScheduler
    import singularity.cognitive_nodes

    agents = get_all_agents()
    if not agents:
        initialize_constellation()

    scheduler = HeartbeatScheduler()
    frames = await scheduler.broadcast_triadic_heartbeat()
    
    timestamp_iso = datetime.now(timezone.utc).isoformat()

    return JSONResponse(content={
        "timestamp": timestamp_iso,
        "sequence_number": scheduler.sequence_number,
        "frames": [
            {
                "node_id": f.node_id,
                "status": f.status.value,
                "metrics": f.metrics,
                "message": f.message,
                "timestamp": f.timestamp.isoformat(),
            }
            for f in frames
        ]
    })


@app.post("/api/prompt")
async def agent_prompt_api(request: Request):
    """Route a prompt to the triadic architecture graph."""
    data = await request.json()
    message = data.get("message", "")
    if not message:
        return JSONResponse(content={"error": "Empty message"}, status_code=400)

    try:
        from singularity.ground_control.handlers import handle_triadic_prompt
        state, formatted_resp = await handle_triadic_prompt(message)
        return JSONResponse(content={
            "response": formatted_resp,
            "security_verdict": state.get("security_verdict", "CLEAR"),
            "route_decision": state.get("route_decision", "self_handle"),
            "synthesis_output": state.get("synthesis_output", ""),
            "proposed_actions": [
                {
                    "action_type": a.action_type,
                    "description": a.description,
                    "risk_level": a.risk_level.value,
                }
                for a in state.get("proposed_actions", [])
            ]
        })
    except Exception as e:
        logger.exception("Failed to execute triadic prompt: %s", e)
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/shutdown")
async def shutdown_endpoint():
    """Graceful shutdown triggered by the UI closing."""
    logger.info("Shutdown signal received from UI. Exiting...")
    
    async def suicide():
        import asyncio
        import os
        await asyncio.sleep(0.5)
        os._exit(0)
        
    import asyncio
    asyncio.create_task(suicide())
    return JSONResponse(content={"status": "shutting down"})

def start_server():
    """Start the docs server on port 8080."""
    # We initialize the model variable correctly here
    global llm
    llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0)
    
    logger.info("Starting Simulated Singularity Docs Server...")
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="warning")

if __name__ == "__main__":
    start_server()
