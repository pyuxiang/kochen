import numpy as np
import random
import pytest

from kochen.datautil import _load


# target = pl.DataFrame(
#     {
#         "a": [1, 2],
#         "b": [2, -4],
#         "c": [3.0, 6e9],
#     }
# )

# Base data with tab delimiters
headers = ["a", "b", "c"]
content_tab = "1\t2\t3\n2\t-4\t6_000_000\n"
target = [
    ["1", "2", "3"],
    ["2", "-4", "6_000_000"],
]
target_parsed = [
    [1, 2, 3],
    [2, -4, 6000000],
]

# Replace tabs with random number of spaces
_tokens = content_tab.split("\t")
_spaces = [" " * random.randint(1, 5) for _ in range(len(_tokens) - 1)]
content_space = "".join(t + s for t, s in zip(_tokens, _spaces)) + _tokens[-1]

# Replace tabs with mix of space and tab
_spaces = [
    random.choice([" ", "\t"]) + random.choice([" ", "\t"])
    for _ in range(len(_tokens) - 1)
]
content_mixed = "".join(t + s for t, s in zip(_tokens, _spaces)) + _tokens[-1]


@pytest.fixture(params=[content_tab, content_space, content_mixed])
def content(request):
    return request.param


@pytest.fixture(params=[content_tab, content_space, content_mixed])
def content_with_headers(request):
    return "\t".join(headers) + "\n" + request.param


def test_load_whitespace(content):
    result = _load(content, headers=headers).to_numpy()
    assert np.all(result == target)
    assert result.dtype == np.dtype(object)


@pytest.fixture(params=[int, float])
def default_type(request):
    return request.param


def test_load_defaults(content, default_type):
    result = _load(content, headers=headers, default=default_type).to_numpy()
    assert np.all(result == target_parsed)
    assert result.dtype == np.dtype(default_type)


def test_load_headers(content_with_headers):
    df = _load(content_with_headers, default=int)
    assert df.columns == headers
    result = df.to_numpy()
    assert np.all(result == target_parsed)
    assert result.dtype == np.dtype(int)
