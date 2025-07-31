import os
for var in os.environ:
	print(f"{var}: {os.environ[var]}")