from src.adapter import build_responses_request, to_chat_completions


def test_build_responses_request_maps_tokens_and_model():
    payload = {
        "model": "old-model",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 123,
        "stream": False,
    }
    result = build_responses_request(payload, {"old-model": "new-model"})

    assert result["model"] == "new-model"
    assert result["max_output_tokens"] == 123
    assert result["input"][0]["content"] == "hi"


def test_to_chat_completions_extracts_text():
    response = {
        "id": "resp-1",
        "output": [
            {
                "content": [
                    {"type": "output_text", "text": "hello"},
                    {"type": "output_text", "text": " world"},
                ]
            }
        ],
        "usage": {"input_tokens": 1, "output_tokens": 2},
    }

    result = to_chat_completions(response)
    assert result["choices"][0]["message"]["content"] == "hello world"
    assert result["usage"]["total_tokens"] == 3
