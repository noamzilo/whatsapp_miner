# src/doppler_bootstrap.py

import os
import subprocess
def inject_doppler_secrets():
	if "GREEN_API_INSTANCE_ID" in os.environ and "GREEN_API_INSTANCE_API_TOKEN" in os.environ:
		print("doppler secrets already present")
		return  # Already present, skip
	else:
		print("doppler secrets not present yet, injecting...")
	try:
		output = subprocess.check_output(
			[
				"doppler", "secrets", "download",
				"--no-file", "--format", "env"
			],
			text=True,
			stderr=subprocess.STDOUT  # ensure errors are caught
		)

		for line in output.strip().splitlines():
			if "=" in line:
				key, value = line.split("=", 1)
				os.environ[key] = value
				print(f"Injected secret from doppler: {key}")

	except FileNotFoundError:
		raise RuntimeError("❌ Doppler CLI not found. Please install it.")
	except subprocess.CalledProcessError as e:
		raise RuntimeError(f"❌ Failed to load Doppler secrets:\n{e.output.strip()}") from e

if __name__ == "__main__":
	inject_doppler_secrets()