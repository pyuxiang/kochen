class TestHi:

    def test_nested_import(self):
        from boiler import pathutil
        pathutil.get_list_of_files