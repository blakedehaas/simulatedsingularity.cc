import pytest
import datetime
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from singularity.neural_core.models import GemmaChatModel

class TestGemmaChatModel:
    @pytest.mark.asyncio
    async def test_generate_mock(self):
        """Test the mocked generate method for Gemma model."""
        model = GemmaChatModel(node_role="core", model_name="gemma-2b")
        
        # We need to mock the API call so it returns '[timestamp] mock'
        mock_response = MagicMock()
        mock_response.content = f"[{datetime.datetime.now().isoformat()}] mock"
        
        # Replace the internal llm with a mock to avoid Pydantic validation errors when mocking methods
        model._llm = MagicMock()
        model._llm.ainvoke = AsyncMock(return_value=mock_response)
        
        response = await model.generate("Hello Gemma")
        assert "mock" in response
        # Ensure timestamp is included (ISO format contains 'T')
        assert "T" in response

    def test_generate_sync_mock(self):
        """Test the mocked synchronous generate method for Gemma model."""
        model = GemmaChatModel(node_role="core", model_name="gemma-2b")
        
        mock_response = MagicMock()
        mock_response.content = f"[{datetime.datetime.now().isoformat()}] mock"
        
        model._llm = MagicMock()
        model._llm.invoke = MagicMock(return_value=mock_response)
        
        response = model.generate_sync("Hello Gemma")
        assert "mock" in response
        assert "T" in response
