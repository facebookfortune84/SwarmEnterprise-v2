"""
tests/test_ollama_client.py
=============================
Comprehensive coverage for backend/llm/ollama_client.py

Covers all public methods of OllamaClient:
- generate
- generate_stream
- chat
- embeddings
- list_models
- pull_model
- health_check
- get_model_info
- context manager (__aenter__/__aexit__)
- convenience functions: generate_code, analyze_code, generate_tests
"""

import os

os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET_KEY", "ci-test-secret-key-do-not-use-in-production-64chars00")
os.environ.setdefault("SECRET_KEY", "ci-test-secret-key-do-not-use-in-production-64chars01")

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.llm.ollama_client import OllamaClient, OllamaConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_httpx_client():
    """Patch httpx.AsyncClient used internally."""
    mock = AsyncMock()
    return mock


@pytest.fixture()
def client_and_http(mock_httpx_client):
    config = OllamaConfig(base_url="http://localhost:11434", model="llama3", timeout=30)
    with patch("httpx.AsyncClient") as mock_cls:
        mock_cls.return_value = mock_httpx_client
        c = OllamaClient(config)
        c.client = mock_httpx_client
    return c, mock_httpx_client


# ---------------------------------------------------------------------------
# Tests: OllamaConfig defaults
# ---------------------------------------------------------------------------


class TestOllamaConfig:
    def test_default_config_from_env(self):
        with (
            patch.dict(os.environ, {"OLLAMA_URL": "http://myhost:11434", "OLLAMA_MODEL": "mistral"}),
            patch("httpx.AsyncClient"),
        ):
            c = OllamaClient()
        assert c.config.base_url == "http://myhost:11434"
        assert c.config.model == "mistral"

    def test_explicit_config(self):
        with patch("httpx.AsyncClient"):
            cfg = OllamaConfig(base_url="http://custom:9999", model="phi-2")
            c = OllamaClient(cfg)
        assert c.config.model == "phi-2"


# ---------------------------------------------------------------------------
# Tests: generate
# ---------------------------------------------------------------------------


class TestGenerate:
    @pytest.mark.asyncio
    async def test_generate_success(self, client_and_http):
        c, http = client_and_http
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"response": "Hello, world!"}
        http.post = AsyncMock(return_value=mock_resp)

        result = await c.generate("Say hello")
        assert result == "Hello, world!"
        http.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_system_and_options(self, client_and_http):
        c, http = client_and_http
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"response": "def foo(): pass"}
        http.post = AsyncMock(return_value=mock_resp)

        result = await c.generate(
            "Write a function",
            system="You are a coder",
            temperature=0.5,
            max_tokens=100,
            stop=["END"],
        )
        assert "foo" in result
        call_kwargs = http.post.call_args
        payload = call_kwargs[1]["json"]
        assert payload["system"] == "You are a coder"
        assert payload["options"]["num_predict"] == 100
        assert payload["options"]["stop"] == ["END"]

    @pytest.mark.asyncio
    async def test_generate_http_error(self, client_and_http):
        c, http = client_and_http
        http.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with pytest.raises(httpx.ConnectError):
            await c.generate("Hello")

    @pytest.mark.asyncio
    async def test_generate_generic_error(self, client_and_http):
        c, http = client_and_http
        http.post = AsyncMock(side_effect=RuntimeError("Unexpected"))

        with pytest.raises(RuntimeError):
            await c.generate("Hello")


# ---------------------------------------------------------------------------
# Tests: generate_stream
# ---------------------------------------------------------------------------


class TestGenerateStream:
    @pytest.mark.asyncio
    async def test_stream_yields_chunks(self, client_and_http):
        c, http = client_and_http

        lines = [
            json.dumps({"response": "Hello"}),
            json.dumps({"response": " world"}),
            "",  # empty line should be skipped
            json.dumps({"done": True}),  # no 'response' key, skipped
        ]

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=None)
        mock_stream.raise_for_status = MagicMock()

        async def _aiter_lines():
            for line in lines:
                yield line

        mock_stream.aiter_lines = _aiter_lines
        http.stream = MagicMock(return_value=mock_stream)

        chunks = []
        async for chunk in c.generate_stream("Say hello"):
            chunks.append(chunk)

        assert chunks == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_stream_http_error(self, client_and_http):
        c, http = client_and_http

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_stream.__aexit__ = AsyncMock(return_value=None)
        http.stream = MagicMock(return_value=mock_stream)

        with pytest.raises(httpx.ConnectError):
            async for _ in c.generate_stream("Hello"):
                pass

    @pytest.mark.asyncio
    async def test_stream_invalid_json_skipped(self, client_and_http):
        c, http = client_and_http

        lines = ["not-json", json.dumps({"response": "ok"})]

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=None)
        mock_stream.raise_for_status = MagicMock()

        async def _aiter_lines():
            for line in lines:
                yield line

        mock_stream.aiter_lines = _aiter_lines
        http.stream = MagicMock(return_value=mock_stream)

        chunks = []
        async for chunk in c.generate_stream("Hello"):
            chunks.append(chunk)

        assert chunks == ["ok"]

    @pytest.mark.asyncio
    async def test_stream_with_system(self, client_and_http):
        c, http = client_and_http

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=None)
        mock_stream.raise_for_status = MagicMock()

        async def _aiter_lines():
            yield json.dumps({"response": "Hello"})

        mock_stream.aiter_lines = _aiter_lines
        http.stream = MagicMock(return_value=mock_stream)

        chunks = []
        async for chunk in c.generate_stream("Hello", system="You are helpful", temperature=0.3):
            chunks.append(chunk)

        assert chunks == ["Hello"]
        call_args = http.stream.call_args
        payload = call_args[1]["json"]
        assert payload["system"] == "You are helpful"


# ---------------------------------------------------------------------------
# Tests: chat
# ---------------------------------------------------------------------------


class TestChat:
    @pytest.mark.asyncio
    async def test_chat_success(self, client_and_http):
        c, http = client_and_http
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"message": {"content": "I am an AI"}}
        http.post = AsyncMock(return_value=mock_resp)

        messages = [{"role": "user", "content": "What are you?"}]
        result = await c.chat(messages)
        assert result == "I am an AI"

    @pytest.mark.asyncio
    async def test_chat_with_temperature_and_max_tokens(self, client_and_http):
        c, http = client_and_http
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"message": {"content": "Sure"}}
        http.post = AsyncMock(return_value=mock_resp)

        await c.chat([{"role": "user", "content": "Help"}], temperature=0.1, max_tokens=50)
        payload = http.post.call_args[1]["json"]
        assert payload["options"]["num_predict"] == 50

    @pytest.mark.asyncio
    async def test_chat_http_error(self, client_and_http):
        c, http = client_and_http
        http.post = AsyncMock(side_effect=httpx.ReadTimeout("timeout"))

        with pytest.raises(httpx.ReadTimeout):
            await c.chat([{"role": "user", "content": "Hi"}])


# ---------------------------------------------------------------------------
# Tests: embeddings
# ---------------------------------------------------------------------------


class TestEmbeddings:
    @pytest.mark.asyncio
    async def test_embeddings_success(self, client_and_http):
        c, http = client_and_http
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"embedding": [0.1, 0.2, 0.3]}
        http.post = AsyncMock(return_value=mock_resp)

        result = await c.embeddings("Hello world")
        assert result == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_embeddings_http_error(self, client_and_http):
        c, http = client_and_http
        http.post = AsyncMock(side_effect=httpx.ConnectError("refused"))

        with pytest.raises(httpx.ConnectError):
            await c.embeddings("test")


# ---------------------------------------------------------------------------
# Tests: list_models
# ---------------------------------------------------------------------------


class TestListModels:
    @pytest.mark.asyncio
    async def test_list_models_success(self, client_and_http):
        c, http = client_and_http
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"models": [{"name": "llama3"}, {"name": "codellama"}]}
        http.get = AsyncMock(return_value=mock_resp)

        result = await c.list_models()
        assert len(result) == 2
        assert result[0]["name"] == "llama3"

    @pytest.mark.asyncio
    async def test_list_models_empty(self, client_and_http):
        c, http = client_and_http
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {}
        http.get = AsyncMock(return_value=mock_resp)

        result = await c.list_models()
        assert result == []

    @pytest.mark.asyncio
    async def test_list_models_http_error(self, client_and_http):
        c, http = client_and_http
        http.get = AsyncMock(side_effect=httpx.ConnectError("refused"))

        with pytest.raises(httpx.ConnectError):
            await c.list_models()


# ---------------------------------------------------------------------------
# Tests: pull_model
# ---------------------------------------------------------------------------


class TestPullModel:
    @pytest.mark.asyncio
    async def test_pull_model_success(self, client_and_http):
        c, http = client_and_http
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        http.post = AsyncMock(return_value=mock_resp)

        result = await c.pull_model("llama3")
        assert result is True

    @pytest.mark.asyncio
    async def test_pull_model_http_error(self, client_and_http):
        c, http = client_and_http
        http.post = AsyncMock(side_effect=httpx.ConnectError("refused"))

        result = await c.pull_model("llama3")
        assert result is False


# ---------------------------------------------------------------------------
# Tests: health_check
# ---------------------------------------------------------------------------


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, client_and_http):
        c, http = client_and_http
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        http.get = AsyncMock(return_value=mock_resp)

        result = await c.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_status(self, client_and_http):
        c, http = client_and_http
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        http.get = AsyncMock(return_value=mock_resp)

        result = await c.health_check()
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_connection_error(self, client_and_http):
        c, http = client_and_http
        http.get = AsyncMock(side_effect=Exception("Connection refused"))

        result = await c.health_check()
        assert result is False


# ---------------------------------------------------------------------------
# Tests: get_model_info
# ---------------------------------------------------------------------------


class TestGetModelInfo:
    @pytest.mark.asyncio
    async def test_get_model_info_default(self, client_and_http):
        c, http = client_and_http
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"details": {"parameter_size": "8B"}}
        http.post = AsyncMock(return_value=mock_resp)

        result = await c.get_model_info()
        assert "details" in result

    @pytest.mark.asyncio
    async def test_get_model_info_named(self, client_and_http):
        c, http = client_and_http
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"details": {"parameter_size": "7B"}}
        http.post = AsyncMock(return_value=mock_resp)

        result = await c.get_model_info("mistral")
        assert "details" in result
        payload = http.post.call_args[1]["json"]
        assert payload["name"] == "mistral"

    @pytest.mark.asyncio
    async def test_get_model_info_error(self, client_and_http):
        c, http = client_and_http
        http.post = AsyncMock(side_effect=httpx.ConnectError("refused"))

        with pytest.raises(httpx.ConnectError):
            await c.get_model_info()


# ---------------------------------------------------------------------------
# Tests: context manager
# ---------------------------------------------------------------------------


class TestContextManager:
    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_cls.return_value = mock_http
            async with OllamaClient() as c:
                assert c is not None
            mock_http.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_close(self, client_and_http):
        c, http = client_and_http
        http.aclose = AsyncMock()
        await c.close()
        http.aclose.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: convenience functions
# ---------------------------------------------------------------------------


class TestConvenienceFunctions:
    @pytest.mark.asyncio
    async def test_generate_code(self):
        from backend.llm.ollama_client import generate_code

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {"response": "def foo(): pass"}
            mock_http.post = AsyncMock(return_value=mock_resp)
            mock_http.aclose = AsyncMock()
            mock_cls.return_value = mock_http

            result = await generate_code("Write a function")
        assert "foo" in result

    @pytest.mark.asyncio
    async def test_generate_code_with_client(self):
        from backend.llm.ollama_client import generate_code

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {"response": "print('hi')"}
            mock_http.post = AsyncMock(return_value=mock_resp)
            mock_http.aclose = AsyncMock()
            mock_cls.return_value = mock_http

            provided_client = OllamaClient()
            provided_client.client = mock_http
            result = await generate_code("print hello", language="python", client=provided_client)
        assert result is not None

    @pytest.mark.asyncio
    async def test_analyze_code(self):
        from backend.llm.ollama_client import analyze_code

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {"response": "Looks good"}
            mock_http.post = AsyncMock(return_value=mock_resp)
            mock_http.aclose = AsyncMock()
            mock_cls.return_value = mock_http

            result = await analyze_code("def foo(): pass")
        assert result == "Looks good"

    @pytest.mark.asyncio
    async def test_analyze_code_task_types(self):
        from backend.llm.ollama_client import analyze_code

        for task in ("review", "document", "optimize", "security"):
            with patch("httpx.AsyncClient") as mock_cls:
                mock_http = AsyncMock()
                mock_resp = MagicMock()
                mock_resp.raise_for_status = MagicMock()
                mock_resp.json.return_value = {"response": f"task: {task}"}
                mock_http.post = AsyncMock(return_value=mock_resp)
                mock_http.aclose = AsyncMock()
                mock_cls.return_value = mock_http

                result = await analyze_code("x = 1", task=task)
            assert task in result

    @pytest.mark.asyncio
    async def test_analyze_code_unknown_task(self):
        from backend.llm.ollama_client import analyze_code

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {"response": "reviewed"}
            mock_http.post = AsyncMock(return_value=mock_resp)
            mock_http.aclose = AsyncMock()
            mock_cls.return_value = mock_http

            result = await analyze_code("x = 1", task="unknown_task")
        assert result is not None

    @pytest.mark.asyncio
    async def test_generate_tests(self):
        from backend.llm.ollama_client import generate_tests

        with patch("httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {"response": "def test_foo(): assert True"}
            mock_http.post = AsyncMock(return_value=mock_resp)
            mock_http.aclose = AsyncMock()
            mock_cls.return_value = mock_http

            result = await generate_tests("def foo(): pass")
        assert "test" in result.lower()
