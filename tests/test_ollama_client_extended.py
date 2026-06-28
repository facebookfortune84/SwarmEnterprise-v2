"""
Extended tests for backend/llm/ollama_client.py
Covers generate_stream, embeddings, pull_model, health_check, generate_code, analyze_code, generate_tests.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import httpx

from backend.llm.ollama_client import OllamaClient, OllamaConfig


def _make_client(max_retries: int = 1) -> OllamaClient:
    config = OllamaConfig(
        base_url="http://localhost:11434",
        model="llama3",
        max_retries=max_retries,
    )
    return OllamaClient(config)


def _mock_response(json_data: dict = None, status_code: int = 200):
    """Create a synchronous-method mock for httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=json_data or {})
    return resp


class TestGenerate:
    @pytest.mark.asyncio
    async def test_generate_success(self):
        client = _make_client()
        resp = _mock_response({"response": "Hello world"})
        client.client = AsyncMock()
        client.client.post = AsyncMock(return_value=resp)

        result = await client.generate("say hello")
        assert result == "Hello world"
        await client.close()

    @pytest.mark.asyncio
    async def test_generate_with_system_and_stop(self):
        client = _make_client()
        resp = _mock_response({"response": "sys prompt response"})
        client.client = AsyncMock()
        client.client.post = AsyncMock(return_value=resp)

        result = await client.generate(
            "prompt", system="system msg", max_tokens=100, stop=["END"]
        )
        assert result == "sys prompt response"
        await client.close()

    @pytest.mark.asyncio
    async def test_generate_http_error(self):
        client = _make_client()
        resp = MagicMock()
        resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())
        )
        client.client = AsyncMock()
        client.client.post = AsyncMock(return_value=resp)

        with pytest.raises(Exception):
            await client.generate("test")
        await client.close()

    @pytest.mark.asyncio
    async def test_generate_generic_exception(self):
        client = _make_client()
        client.client = AsyncMock()
        client.client.post = AsyncMock(side_effect=Exception("generic error"))

        with pytest.raises(Exception):
            await client.generate("test")
        await client.close()


def _make_stream_client() -> OllamaClient:
    """Create a client where client.client is an AsyncMock (aclose is awaitable)."""
    c = _make_client()
    c.client = AsyncMock()
    c.client.aclose = AsyncMock()
    return c


class TestGenerateStream:
    @pytest.mark.asyncio
    async def test_generate_stream_yields_chunks(self):
        import json as json_mod
        client = _make_stream_client()

        lines = [
            json_mod.dumps({"response": "Hello "}),
            json_mod.dumps({"response": "world"}),
            json_mod.dumps({"done": True}),
        ]

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        async def aiter_lines():
            for line in lines:
                yield line

        mock_response.aiter_lines = aiter_lines

        class MockStream:
            async def __aenter__(self_inner):
                return mock_response

            async def __aexit__(self_inner, *args):
                pass

        client.client.stream = MagicMock(return_value=MockStream())

        chunks = []
        async for chunk in client.generate_stream("test prompt"):
            chunks.append(chunk)

        assert chunks == ["Hello ", "world"]
        await client.close()

    @pytest.mark.asyncio
    async def test_generate_stream_invalid_json_skipped(self):
        client = _make_stream_client()

        async def aiter_lines():
            yield "not-valid-json"
            yield '{"response": "valid"}'

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = aiter_lines

        class MockStream:
            async def __aenter__(self_inner):
                return mock_response

            async def __aexit__(self_inner, *args):
                pass

        client.client.stream = MagicMock(return_value=MockStream())

        chunks = []
        async for chunk in client.generate_stream("test"):
            chunks.append(chunk)

        assert chunks == ["valid"]
        await client.close()

    @pytest.mark.asyncio
    async def test_generate_stream_with_system(self):
        import json as json_mod
        client = _make_stream_client()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        async def aiter_lines():
            yield json_mod.dumps({"response": "streamed"})

        mock_response.aiter_lines = aiter_lines

        class MockStream:
            async def __aenter__(self_inner):
                return mock_response

            async def __aexit__(self_inner, *args):
                pass

        client.client.stream = MagicMock(return_value=MockStream())

        chunks = []
        async for chunk in client.generate_stream("prompt", system="sys", temperature=0.5):
            chunks.append(chunk)
        assert "streamed" in chunks
        await client.close()

    @pytest.mark.asyncio
    async def test_generate_stream_http_error(self):
        client = _make_stream_client()

        class MockStream:
            async def __aenter__(self_inner):
                raise httpx.HTTPStatusError(
                    "500", request=MagicMock(), response=MagicMock()
                )

            async def __aexit__(self_inner, *args):
                pass

        client.client.stream = MagicMock(return_value=MockStream())

        with pytest.raises(httpx.HTTPError):
            async for _ in client.generate_stream("fail"):
                pass
        await client.close()


class TestChat:
    @pytest.mark.asyncio
    async def test_chat_success(self):
        client = _make_client()
        resp = _mock_response({"message": {"content": "assistant reply"}})
        client.client = AsyncMock()
        client.client.post = AsyncMock(return_value=resp)

        result = await client.chat([{"role": "user", "content": "hi"}])
        assert result == "assistant reply"
        await client.close()

    @pytest.mark.asyncio
    async def test_chat_with_max_tokens(self):
        client = _make_client()
        resp = _mock_response({"message": {"content": "short"}})
        client.client = AsyncMock()
        client.client.post = AsyncMock(return_value=resp)

        result = await client.chat([{"role": "user", "content": "hi"}], max_tokens=50)
        assert result == "short"
        await client.close()

    @pytest.mark.asyncio
    async def test_chat_http_error(self):
        client = _make_client()
        resp = MagicMock()
        resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())
        )
        client.client = AsyncMock()
        client.client.post = AsyncMock(return_value=resp)

        with pytest.raises(Exception):
            await client.chat([{"role": "user", "content": "hi"}])
        await client.close()


class TestEmbeddings:
    @pytest.mark.asyncio
    async def test_embeddings_success(self):
        client = _make_client()
        resp = _mock_response({"embedding": [0.1, 0.2, 0.3]})
        client.client = AsyncMock()
        client.client.post = AsyncMock(return_value=resp)

        result = await client.embeddings("some text")
        assert result == [0.1, 0.2, 0.3]
        await client.close()

    @pytest.mark.asyncio
    async def test_embeddings_http_error(self):
        client = _make_client()
        resp = MagicMock()
        resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())
        )
        client.client = AsyncMock()
        client.client.post = AsyncMock(return_value=resp)

        with pytest.raises(Exception):
            await client.embeddings("fail text")
        await client.close()


class TestListModels:
    @pytest.mark.asyncio
    async def test_list_models_success(self):
        client = _make_client()
        resp = _mock_response({"models": [{"name": "llama3"}, {"name": "codellama"}]})
        client.client = AsyncMock()
        client.client.get = AsyncMock(return_value=resp)

        models = await client.list_models()
        assert len(models) == 2
        await client.close()

    @pytest.mark.asyncio
    async def test_list_models_empty(self):
        client = _make_client()
        resp = _mock_response({})
        client.client = AsyncMock()
        client.client.get = AsyncMock(return_value=resp)

        models = await client.list_models()
        assert models == []
        await client.close()

    @pytest.mark.asyncio
    async def test_list_models_http_error(self):
        client = _make_client()
        resp = MagicMock()
        resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())
        )
        client.client = AsyncMock()
        client.client.get = AsyncMock(return_value=resp)

        with pytest.raises(Exception):
            await client.list_models()
        await client.close()


class TestPullModel:
    @pytest.mark.asyncio
    async def test_pull_model_success(self):
        client = _make_client()
        resp = _mock_response({})
        client.client = AsyncMock()
        client.client.post = AsyncMock(return_value=resp)

        result = await client.pull_model("llama3")
        assert result is True
        await client.close()

    @pytest.mark.asyncio
    async def test_pull_model_http_error_returns_false(self):
        client = _make_client()
        resp = MagicMock()
        resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("404", request=MagicMock(), response=MagicMock())
        )
        client.client = AsyncMock()
        client.client.post = AsyncMock(return_value=resp)

        result = await client.pull_model("nonexistent")
        assert result is False
        await client.close()


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        client = _make_client()
        resp = MagicMock()
        resp.status_code = 200
        client.client = AsyncMock()
        client.client.get = AsyncMock(return_value=resp)

        result = await client.health_check()
        assert result is True
        await client.close()

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):
        client = _make_client()
        resp = MagicMock()
        resp.status_code = 503
        client.client = AsyncMock()
        client.client.get = AsyncMock(return_value=resp)

        result = await client.health_check()
        assert result is False
        await client.close()

    @pytest.mark.asyncio
    async def test_health_check_exception(self):
        client = _make_client()
        client.client = AsyncMock()
        client.client.get = AsyncMock(side_effect=Exception("connection refused"))

        result = await client.health_check()
        assert result is False
        await client.close()


class TestGetModelInfo:
    @pytest.mark.asyncio
    async def test_get_model_info_success(self):
        client = _make_client()
        resp = _mock_response({"name": "llama3", "parameters": "8B"})
        client.client = AsyncMock()
        client.client.post = AsyncMock(return_value=resp)

        result = await client.get_model_info("llama3")
        assert result["name"] == "llama3"
        await client.close()

    @pytest.mark.asyncio
    async def test_get_model_info_default_model(self):
        client = _make_client()
        resp = _mock_response({"name": "llama3"})
        client.client = AsyncMock()
        client.client.post = AsyncMock(return_value=resp)

        result = await client.get_model_info()
        assert "name" in result
        await client.close()

    @pytest.mark.asyncio
    async def test_get_model_info_http_error(self):
        client = _make_client()
        resp = MagicMock()
        resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("404", request=MagicMock(), response=MagicMock())
        )
        client.client = AsyncMock()
        client.client.post = AsyncMock(return_value=resp)

        with pytest.raises(Exception):
            await client.get_model_info("missing")
        await client.close()


class TestAsyncContextManager:
    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        config = OllamaConfig(base_url="http://localhost:11434", model="llama3")
        async with OllamaClient(config) as ollama_client:
            assert isinstance(ollama_client, OllamaClient)


class TestConvenienceFunctions:
    @pytest.mark.asyncio
    async def test_generate_code_with_existing_client(self):
        from backend.llm.ollama_client import generate_code

        client = _make_client()
        resp = _mock_response({"response": "def foo(): pass"})
        client.client = AsyncMock()
        client.client.post = AsyncMock(return_value=resp)

        result = await generate_code("write a function", client=client)
        assert "def foo" in result

    @pytest.mark.asyncio
    async def test_analyze_code_with_client(self):
        from backend.llm.ollama_client import analyze_code

        client = _make_client()
        resp = _mock_response({"response": "code looks good"})
        client.client = AsyncMock()
        client.client.post = AsyncMock(return_value=resp)

        result = await analyze_code("def foo(): pass", task="review", client=client)
        assert "good" in result

    @pytest.mark.asyncio
    async def test_generate_tests_with_client(self):
        from backend.llm.ollama_client import generate_tests

        client = _make_client()
        resp = _mock_response({"response": "def test_foo(): assert True"})
        client.client = AsyncMock()
        client.client.post = AsyncMock(return_value=resp)

        result = await generate_tests("def foo(): pass", client=client)
        assert "test_foo" in result

    @pytest.mark.asyncio
    async def test_analyze_code_unknown_task(self):
        from backend.llm.ollama_client import analyze_code

        client = _make_client()
        resp = _mock_response({"response": "analysis"})
        client.client = AsyncMock()
        client.client.post = AsyncMock(return_value=resp)

        result = await analyze_code("code", task="custom_unknown_task", client=client)
        assert isinstance(result, str)
