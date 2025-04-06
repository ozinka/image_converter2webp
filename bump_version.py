from version import __version__

parts = __version__.split(".")
parts[-1] = str(int(parts[-1]) + 1)
new_version = ".".join(parts)

with open("version.py", "w") as f:
    f.write(f"__version__ = \"{new_version}\"\n")

print(f"Bumped version to: {new_version}")
