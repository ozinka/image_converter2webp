from version import __version__

version_tuple = tuple(map(int, __version__.split(".")))
version_str = __version__

with open("version_info.txt", "r", encoding="utf-8") as template:
    data = template.read()

data = data.replace("__VERSION_TUPLE__", str(version_tuple))
data = data.replace("__VERSION_STRING__", version_str)

with open("version_generated.txt", "w", encoding="utf-8") as f:
    f.write(data)