# Deployment checklist

[Documentation index](README.md) · [Getting started](getting-started.md) · [Operations](operations.md)

The tournament engine calls the bot over HTTP. The deployed service must expose the Battlesnake API root and move routes through a stable public URL. The official [Quickstart](https://docs.battlesnake.com/quickstart) describes the same flow: deploy a web server, verify its root response, then register that URL. Hosting can be Replit, a container host, a cloud VM, or another provider; the [hosting guide](https://docs.battlesnake.com/guides/hosting-suggestions) emphasizes public reachability and latency.

## Container contract

This repository is already containerized:

    docker build -t seds-battlesnake:latest .
    docker run --rm -p 8000:8000 \
      -e BATTLESNAKE_SEARCH=1 \
      -e BATTLESNAKE_MAX_DEPTH=2 \
      seds-battlesnake:latest

The server binds 0.0.0.0 and reads the hosting provider's PORT variable. Do not hardcode localhost in a hosted launch command. The .dockerignore keeps tests, replays, virtual environments, and documentation out of the image context.

## Render deployment

The repository includes `render.yaml` for a Docker web service. Render assigns a public HTTPS hostname after deployment; the exact hostname is account-specific and cannot be generated locally.

1. Push this repository to GitHub.
2. In Render, create a Blueprint and select the repository and the `starter-snake-python/render.yaml` file.
3. Deploy the `seds-battlesnake` service and wait for its health check on `/` to pass.
4. Copy the service's `https://...onrender.com` URL into the Battlesnake registration form.
5. Ping the registered snake and send one four-snake Standard rehearsal before the hackathon.

Render's first request after an idle period may include a cold-start delay on free hosting. Use an always-on plan or another nearby container host if the tournament's timeout is strict.

Before publishing an image, run:

    docker run -d --name seds-snake -p 8000:8000 seds-battlesnake:latest
    curl -fsS http://127.0.0.1:8000/
    curl -fsS -X POST -H 'Content-Type: application/json' \
      --data-binary @/tmp/battlesnake-request.json \
      http://127.0.0.1:8000/move
    docker rm -f seds-snake

The move request fixture is documented in [API and state](api-and-state.md). A successful move response must be a JSON object containing one of up, down, left, or right.

## Hackathon launch checklist

1. Pin the Git commit used for the tournament image.
2. Build the image from starter-snake-python/, not the workspace parent.
3. Set PORT using the provider's runtime configuration; the default is 8000 locally.
4. Keep BATTLESNAKE_SEARCH=1 and BATTLESNAKE_MAX_DEPTH=2 for the normal four-snake tournament profile. Set depth to 1 only if the host has materially slower CPU or high network latency.
5. Keep BATTLESNAKE_LOG=0 in production unless short telemetry logs are required; logs are useful during a rehearsal but add I/O.
6. Confirm GET / returns the bot metadata and POST /move returns within the tournament timeout.
7. Register the public HTTPS URL in the Battlesnake dashboard or the hackathon's tournament console and use its Ping/health check.
8. Run one four-snake Standard rehearsal and one Royale rehearsal against the deployed URL before qualifying.
9. Record the deployment region and measured /move latency. Battlesnake supports engine-region selection, so choose the region closest to the service when the tournament configuration allows it.

## Tunnel rehearsal

For a short rehearsal from a laptop, a port-forwarding service such as ngrok can expose port 8000. This is suitable for connectivity checks, but the official hosting guidance warns that local hosting and Wi-Fi can add round-trip latency. Use a managed host or cloud deployment for the actual tournament when possible.

    .venv/bin/python main.py
    ngrok http 8000

Register the generated HTTPS forwarding URL temporarily, run a Ping, then remove it after testing. Never commit tunnel credentials.

## Failure checks

- Root URL fails: inspect provider logs and verify the process uses python main.py.
- Port mismatch: confirm the provider's PORT is passed into the container or process.
- Move timeout: set BATTLESNAKE_MAX_DEPTH=1, disable logging, and compare remote latency with the local benchmark.
- HTTP 5xx: replay the captured request locally and run the full pytest suite against the same commit.
- Wrong appearance: restart the service and Ping the registered snake so the dashboard refreshes /.

The service is stateless: each request carries the full game state, so horizontal replicas do not share match memory. Keep one stable deployment URL during a tournament and avoid autoscaling cold starts on the move path.
