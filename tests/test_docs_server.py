import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
import pathlib
import json

from singularity.docs_server import app, serve_docs, chat_endpoint, start_server, ingest_codebase, lifespan
import singularity.docs_server

client = TestClient(app)

def test_serve_docs_not_found(tmp_path):
    with patch("singularity.docs_server.DOCS_HTML_PATH", tmp_path / "missing.html"):
        response = client.get("/")
        assert response.status_code == 404
        assert "not found" in response.text

def test_serve_docs_found(tmp_path):
    docs_file = tmp_path / "docs.html"
    docs_file.write_text("<h1>Mock Docs</h1>", encoding="utf-8")
    with patch("singularity.docs_server.DOCS_HTML_PATH", docs_file):
        response = client.get("/")
        assert response.status_code == 200
        assert "Mock Docs" in response.text

def test_chat_empty_query():
    response = client.post("/chat", json={"query": ""})
    assert response.status_code == 400

def test_chat_uninitialized():
    with patch("singularity.docs_server.vector_store", None):
        response = client.post("/chat", json={"query": "test"})
        assert response.status_code == 500
        assert "not initialized" in response.text

@pytest.mark.asyncio
async def test_chat_success():
    mock_store = MagicMock()
    mock_retriever = MagicMock()
    mock_doc = MagicMock()
    mock_doc.page_content = "context text"
    mock_retriever.invoke.return_value = [mock_doc]
    mock_store.as_retriever.return_value = mock_retriever
    
    mock_llm = MagicMock()
    mock_resp = MagicMock()
    mock_resp.content = "answer text"
    
    async def mock_ainvoke(*args, **kwargs):
        return mock_resp
        
    with patch("singularity.docs_server.vector_store", mock_store), \
         patch("singularity.docs_server.llm", mock_llm), \
         patch("singularity.docs_server.ChatPromptTemplate.from_template") as mock_prompt:
         
        mock_chain = MagicMock()
        mock_chain.ainvoke = mock_ainvoke
        mock_prompt.return_value.__or__.return_value = mock_chain
        
        mock_request = AsyncMock()
        mock_request.json.return_value = {"query": "hello"}
        
        from fastapi.responses import JSONResponse
        res = await chat_endpoint(mock_request)
        assert isinstance(res, JSONResponse)
        body = json.loads(res.body)
        assert body["response"] == "answer text"

@pytest.mark.asyncio
async def test_chat_success_list_content():
    mock_store = MagicMock()
    mock_retriever = MagicMock()
    mock_doc = MagicMock()
    mock_doc.page_content = "context text"
    mock_retriever.invoke.return_value = [mock_doc]
    mock_store.as_retriever.return_value = mock_retriever
    
    mock_llm = MagicMock()
    mock_resp = MagicMock()
    # Test complex object content that caused [object Object]
    mock_resp.content = [{"text": "part1"}, "part2", {"ignore": "this"}]
    
    async def mock_ainvoke(*args, **kwargs):
        return mock_resp
        
    with patch("singularity.docs_server.vector_store", mock_store), \
         patch("singularity.docs_server.llm", mock_llm), \
         patch("singularity.docs_server.ChatPromptTemplate.from_template") as mock_prompt:
         
        mock_chain = MagicMock()
        mock_chain.ainvoke = mock_ainvoke
        mock_prompt.return_value.__or__.return_value = mock_chain
        
        mock_request = AsyncMock()
        mock_request.json.return_value = {"query": "hello"}
        
        from fastapi.responses import JSONResponse
        res = await chat_endpoint(mock_request)
        assert isinstance(res, JSONResponse)
        body = json.loads(res.body)
        assert body["response"] == "part1part2"

@pytest.mark.asyncio
async def test_chat_success_non_string():
    mock_store = MagicMock()
    mock_retriever = MagicMock()
    mock_doc = MagicMock()
    mock_doc.page_content = "context"
    mock_retriever.invoke.return_value = [mock_doc]
    mock_store.as_retriever.return_value = mock_retriever
    
    mock_llm = MagicMock()
    mock_resp = MagicMock()
    # Test integer content just to hit the 'else' fallback
    mock_resp.content = 42
    
    async def mock_ainvoke(*args, **kwargs):
        return mock_resp
        
    with patch("singularity.docs_server.vector_store", mock_store), \
         patch("singularity.docs_server.llm", mock_llm), \
         patch("singularity.docs_server.ChatPromptTemplate.from_template") as mock_prompt:
         
        mock_chain = MagicMock()
        mock_chain.ainvoke = mock_ainvoke
        mock_prompt.return_value.__or__.return_value = mock_chain
        
        mock_request = AsyncMock()
        mock_request.json.return_value = {"query": "hello"}
        
        from fastapi.responses import JSONResponse
        res = await chat_endpoint(mock_request)
        assert json.loads(res.body)["response"] == "42"

@pytest.mark.asyncio
async def test_chat_exception():
    mock_store = MagicMock()
    mock_store.as_retriever.side_effect = Exception("test error")
    
    with patch("singularity.docs_server.vector_store", mock_store), \
         patch("singularity.docs_server.llm", MagicMock()):
         
        mock_request = AsyncMock()
        mock_request.json.return_value = {"query": "hello"}
        
        res = await chat_endpoint(mock_request)
        assert res.status_code == 500

@patch("singularity.docs_server.Chroma")
def test_ingest_codebase_existing_db(mock_chroma, tmp_path):
    db_dir = tmp_path / "db"
    db_dir.mkdir()
    
    mock_store = MagicMock()
    # Explicitly make count return an integer to avoid TypeError on comparison
    mock_store._collection.count = MagicMock(return_value=10)
    mock_chroma.return_value = mock_store
    
    with patch("singularity.docs_server.DB_DIR", db_dir):
        store = ingest_codebase()
        assert store == mock_store
        mock_chroma.assert_called_once()

@patch("singularity.docs_server.Chroma")
def test_ingest_codebase_existing_db_empty(mock_chroma, tmp_path):
    db_dir = tmp_path / "empty_db"
    db_dir.mkdir()
    
    mock_store = MagicMock()
    mock_store._collection.count.return_value = 0
    mock_chroma.return_value = mock_store
    
    with patch("singularity.docs_server.DB_DIR", db_dir), \
         patch("singularity.docs_server.PROJECT_ROOT", tmp_path):
        store = ingest_codebase()
        assert store == mock_store
        # One call to load the existing DB, one call to create the new one in the logic
        assert mock_chroma.call_count == 2
        mock_store.add_documents.assert_not_called()

@patch("singularity.docs_server.Chroma")
def test_ingest_codebase_existing_db_error(mock_chroma, tmp_path):
    db_dir = tmp_path / "err_db"
    db_dir.mkdir()
    
    mock_store = MagicMock()
    # Mock the property to raise an AttributeError when accessed to hit lines 47-48
    type(mock_store)._collection = property(lambda self: (_ for _ in ()).throw(Exception("db error")))
    mock_chroma.return_value = mock_store
    
    with patch("singularity.docs_server.DB_DIR", db_dir), \
         patch("singularity.docs_server.PROJECT_ROOT", tmp_path):
        store = ingest_codebase()
        assert store == mock_store
        assert mock_chroma.call_count == 2
        mock_store.add_documents.assert_not_called()

@patch("time.sleep")
@patch("singularity.docs_server.Chroma")
def test_ingest_codebase_new_db(mock_chroma, mock_sleep, tmp_path):
    db_dir = tmp_path / "new_db"
    
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "test.py").write_text("print('test')")
    (tmp_path / "README.md").write_text("Hello")
    
    mock_store = MagicMock()
    mock_chroma.return_value = mock_store
    
    with patch("singularity.docs_server.DB_DIR", db_dir), \
         patch("singularity.docs_server.PROJECT_ROOT", tmp_path), \
         patch("singularity.docs_server.RecursiveCharacterTextSplitter.split_documents") as mock_split:
        
        # We just need more than 15 chunks to trigger batching and sleep. 
        mock_split.return_value = ["chunk" + str(i) for i in range(16)]
        
        store = ingest_codebase()
        assert store == mock_store
        mock_chroma.assert_called_once()
        assert mock_store.add_documents.call_count == 2
        mock_sleep.assert_called_once_with(10)

@patch("time.sleep")
@patch("singularity.docs_server.Chroma")
def test_ingest_codebase_rate_limit_retry(mock_chroma, mock_sleep, tmp_path):
    db_dir = tmp_path / "new_db_retry"
    
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "test.py").write_text("print('test')")
    
    mock_store = MagicMock()
    # Raise 429 on first call, succeed on second
    mock_store.add_documents.side_effect = [Exception("429 RESOURCE_EXHAUSTED"), None]
    mock_chroma.return_value = mock_store
    
    with patch("singularity.docs_server.DB_DIR", db_dir), \
         patch("singularity.docs_server.PROJECT_ROOT", tmp_path), \
         patch("singularity.docs_server.RecursiveCharacterTextSplitter.split_documents") as mock_split:
        
        mock_split.return_value = ["chunk1"]
        
        store = ingest_codebase()
        assert store == mock_store
        assert mock_store.add_documents.call_count == 2
        mock_sleep.assert_called_once_with(30)

@patch("singularity.docs_server.Chroma")
def test_ingest_codebase_generic_error(mock_chroma, tmp_path):
    db_dir = tmp_path / "new_db_generic_err"
    
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "test.py").write_text("print('test')")
    
    mock_store = MagicMock()
    # Raise a generic exception
    mock_store.add_documents.side_effect = Exception("Some generic error")
    mock_chroma.return_value = mock_store
    
    with patch("singularity.docs_server.DB_DIR", db_dir), \
         patch("singularity.docs_server.PROJECT_ROOT", tmp_path), \
         patch("singularity.docs_server.RecursiveCharacterTextSplitter.split_documents") as mock_split:
        
        mock_split.return_value = ["chunk1"]
        
        with pytest.raises(Exception, match="Some generic error"):
            ingest_codebase()
        assert mock_store.add_documents.call_count == 1

@patch("singularity.docs_server.Chroma")
def test_ingest_codebase_load_error(mock_chroma, tmp_path):
    db_dir = tmp_path / "new_db_err"
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "test.py").write_text("print('test')")
    
    mock_store = MagicMock()
    mock_chroma.return_value = mock_store
    
    with patch("singularity.docs_server.DB_DIR", db_dir), \
         patch("singularity.docs_server.PROJECT_ROOT", tmp_path), \
         patch("pathlib.Path.read_text", side_effect=Exception("load error")):
        store = ingest_codebase()
        mock_chroma.assert_called_once()
        mock_store.add_documents.assert_not_called()

@pytest.mark.asyncio
async def test_shutdown_endpoint():
    # Mock os._exit so it doesn't kill the test suite!
    with patch("os._exit") as mock_exit:
        from singularity.docs_server import shutdown_endpoint
        res = await shutdown_endpoint()
        
        # Let the event loop run the background task
        import asyncio
        import json
        await asyncio.sleep(0.6)
        
        mock_exit.assert_called_once_with(0)
        assert json.loads(res.body)["status"] == "shutting down"

@pytest.mark.asyncio
async def test_lifespan():
    from singularity.docs_server import lifespan
    from singularity.docs_server import app
    with patch("singularity.docs_server.ingest_codebase") as mock_ingest, \
         patch("singularity.docs_server.ChatGoogleGenerativeAI") as mock_llm:
        async with lifespan(app):
            pass
        import asyncio
        await asyncio.sleep(0.1)
        mock_ingest.assert_called_once()
        mock_llm.assert_called_once()

@pytest.mark.asyncio
async def test_lifespan_error():
    with patch("singularity.docs_server.ingest_codebase", side_effect=Exception("init err")):
        async with lifespan(app):
            pass
        import asyncio
        await asyncio.sleep(0.1)

@pytest.mark.asyncio
async def test_lifespan_llm_error():
    with patch("singularity.docs_server.ChatGoogleGenerativeAI", side_effect=Exception("llm err")):
        async with lifespan(app):
            pass

@patch("uvicorn.run")
@patch("singularity.docs_server.ChatGoogleGenerativeAI")
def test_start_server(mock_llm, mock_run):
    from singularity.docs_server import start_server, app
    start_server()
    mock_run.assert_called_once_with(app, host="127.0.0.1", port=8080, log_level="warning")

def test_ping_endpoint():
    from singularity.docs_server import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.post("/ping")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

@pytest.mark.asyncio
async def test_heartbeat_monitor():
    from singularity.docs_server import heartbeat_monitor
    
    # We will raise StopAsyncIteration to cleanly break the while True loop
    async def mock_sleep(seconds):
        import time
        import singularity.docs_server
        if seconds == 10:
            # First startup sleep, fast-forward time to simulate missing pings
            singularity.docs_server.last_ping_time = time.time() - 6.0
            return
            
        # Break loop on subsequent sleeps
        raise StopAsyncIteration()
        
    with patch("os._exit") as mock_exit, \
         patch("asyncio.sleep", side_effect=mock_sleep):
        
        try:
            await heartbeat_monitor()
        except StopAsyncIteration:
            pass
            
        mock_exit.assert_called_once_with(0)

@patch("uvicorn.run")
@patch("singularity.docs_server.ChatGoogleGenerativeAI")
def test_main_execution(mock_llm, mock_run):
    import runpy
    from pathlib import Path
    server_path = Path(__file__).resolve().parent.parent / "src" / "singularity" / "docs_server.py"
    runpy.run_path(str(server_path), run_name="__main__")
    mock_run.assert_called_once()

