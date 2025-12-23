import datetime as dt
import time


from kochen.datautil import filecache, datacache


def test_filecache_decorator_call():
    @filecache
    def f(x):
        return x**2


def test_filecache_result(tmp_path):
    cache_path = tmp_path / "test_filecache_basic"

    @filecache(path=cache_path)
    def f(x):
        return x**2

    expected_16 = f(4)
    assert expected_16 == 16
    assert expected_16 == f(4)

    # Share same cache path
    @filecache(path=cache_path)
    def g():
        return 2

    assert g() == 2
    assert expected_16 == f(4)  # override


def test_filecache_cache(tmp_path):
    cache_path = tmp_path / "test_filecache_cache"

    @filecache(path=cache_path)
    def f(x):  # pyright: ignore[reportRedeclaration]
        return dt.datetime.now()

    expected_date1 = f(1)
    time.sleep(0.01)
    expected_date2 = f(2)
    assert expected_date1 == f(1)
    assert expected_date2 == f(2)
    assert expected_date1 < expected_date2

    # Same function name => cached
    @filecache(path=cache_path)
    def f(x):
        return dt.datetime.now()

    assert expected_date1 == f(1)

    # Different function name => no cache
    @filecache(path=cache_path)
    def g(x):
        return dt.datetime.now()

    assert expected_date1 != g(1)


def test_filecache_data(tmp_path):
    cache_path = tmp_path / "test_filecache_data"

    if data := datacache(path=cache_path):
        assert False  # should not have anything in cache

    assert data is None
    data = dt.datetime.now()
    datacache(data, path=cache_path)

    # Second retrieval
    if (_data := datacache(path=cache_path)) is None:
        assert False  # should already be cached

    assert data == _data
