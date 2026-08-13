- never run code without first asking the user for permission.
- never run automatically on production or prd or prod environments.
- when running code, prefix it with `uv run` (never `pip`/`poetry`)
- when running anything that needs secrets, use `doppler run --project whatsapp_miner_backend --config dev`. Also add that to shell scripts
- All imports should be from the `src` directory and top of file. No relative imports and no inline imports.
- Be careful of n+1 queries when writing sql queries or using sqlalchemy.
- Dont run commands directly, we have make commands for everything.

* EC2 is stopped to save cost (~$15/mo). To bring it back:
- The instance has NO Elastic IP, so stopping it RELEASES its public IP. It comes
  back with a different address every time it is started.
- After every start, read the new address and update `AWS_EC2_HOST_ADDRESS` in Doppler
  for all three configs (dev, stg, prd). Nothing that SSHes or deploys will work
  until you do — the Makefile remote targets and the GitHub deploy both read it.
- Get the new address with:
  `aws ec2 describe-instances --instance-ids i-0adeaebf9f64d7233 --query 'Reservations[].Instances[].PublicDnsName' --output text`
- Set it with:
  `doppler secrets set AWS_EC2_HOST_ADDRESS=<new-dns> --project whatsapp_miner_backend --config <dev|stg|prd>`
- Attach an Elastic IP instead if the stop/start cycle becomes frequent (~$3.6/mo
  while the instance is stopped, free while it is running and attached).
- The 20GB EBS volume survives stop/start, so everything on disk is preserved.
  Only terminating the instance destroys it.

* versions of things:
- Scripts are run from Windows 11 (git-bash), not WSL. The WSL checkout is a stale archive.
- Docker Compose version v2.38.2-desktop.1
- Docker version 28.3.2
- Python 3.11.15 (provisioned by uv)
- uv 0.12.3 (NOT poetry — poetry was removed)
- GNU Make 4.4.1 (ezwinports, run from git-bash)
- act version 0.2.79
- sqlalchemy Version: 2.0.41
- PostgreSQL 17.6 on aarch64-unknown-linux-gnu, compiled by gcc (GCC) 13.2.0, 64-bit on Supabase

* variables names that exist in doppler (more may be added later):
AWS_EC2_HOST_ADDRESS, AWS_EC2_PEM_CHATBOT_SA_B64, AWS_EC2_REGION, AWS_EC2_USERNAME, AWS_EC2_WORKING_DIRECTORY_WHATSAPP_MINER, AWS_IAM_WHATSAPP_MINER_ACCESS_KEY, AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID, BUILD_TARGET, DOCKER_COMPOSE_SERVICES, DOCKER_CONTAINER_NAME_WHATSAPP_CLASSIFIER, DOCKER_CONTAINER_NAME_WHATSAPP_MINER, DOCKER_IMAGE_NAME_WHATSAPP_CLASSIFIER, DOCKER_IMAGE_NAME_WHATSAPP_MINER, ENV_NAME, GREEN_API_INSTANCE_API_TOKEN, GREEN_API_INSTANCE_ID, GROQ_API_KEY, MESSAGE_CLASSIFIER_RUN_EVERY_SECONDS, SUPABASE_DATABASE_CONNECTION_STRING, SUPABASE_DATABASE_CONNECTION_STRING_DIRECT, SUPABASE_DATABASE_CONNECTION_STRING_SESSION_POOLER, SUPABASE_DATABASE_PASSWORD, SUPABASE_PSQL_COMMAND
Also SUPABASE_DATABASE_CONNECTION_STRING_SESSION_POOLER_EXTERNAL (required by
src/env_var_injection.py, and missing from the .env the deploy workflow writes —
that is why the prd deploy fails at the migrate step).

For the db connection strings, use SUPABASE_DATABASE_CONNECTION_STRING_SESSION_POOLER
*from inside a container*. From Windows/host use the _EXTERNAL one: the plain
SESSION_POOLER value points at host `db`, which only resolves on the docker network,
and dev's _EXTERNAL points at localhost:55432 (a tunnel that is not running).
Only stg and prd are reachable from the host.
