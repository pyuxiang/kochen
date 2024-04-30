all:
	@true

# Upload package to PyPI
# This legacy method will be deprecated once GitHub build + sign workflows is up
publish:
	rm -rf dist
	python3 -m build
	python3 -m twine upload dist/*
