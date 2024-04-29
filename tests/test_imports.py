class TestHi:

    def test_nested_import(self):
        from kochen import pathutil
        pathutil.get_list_of_files