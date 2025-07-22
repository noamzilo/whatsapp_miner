# src/doppler_bootstrap.py

import os
import subprocess
def inject_doppler_secrets():
	if "GREEN_API_INSTANCE_ID" in os.environ and "GREEN_API_INSTANCE_API_TOKEN" in os.environ:
		return  # Already present, skip

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

	except FileNotFoundError:
		raise RuntimeError("❌ Doppler CLI not found. Please install it.")
	except subprocess.CalledProcessError as e:
		raise RuntimeError(f"❌ Failed to load Doppler secrets:\n{e.output.strip()}") from e
