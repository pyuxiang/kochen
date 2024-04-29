class TestHi:

    def test_nested_import(self):
        from scribbles import pathutil
        pathutil.get_list_of_files