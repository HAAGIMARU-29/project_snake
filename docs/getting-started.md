# Getting started

[Documentation index](README.md)

## Environment

The bot uses Python standard-library algorithms and Flask. The recorded development environment used Python 3.13.15, Flask 2.3.2, pytest, and a working Battlesnake CLI. The original starter targets Python 3.10+, but the recorded 205-test result is specifically from Python 3.13.15.

The dependency files have different purposes:

| File | Contents | When to use |
|---|---|---|
| [`requirements.txt`](../requirements.txt) | `Flask==2.3.2` | Run the server |
| [`requirements-dev.txt`](../requirements-dev.txt) | Runtime requirements plus `pytest>=8,<10` | Develop and test |

The Battlesnake CLI is an external executable, not a Python dependency. The commands below assume it is already installed and on `PATH`. Check the installed executable with `battlesnake play --help` if its flags differ from the examples.

## Create or use the virtual environment

From the workspace root:

```bash
cd starter-snake-python
```

For an existing environment, use its interpreter directly:

```bash
.venv/bin/python --version
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

For a fresh checkout without `.venv/`:

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
```

An activated environment is optional. Using `.venv/bin/python` avoids accidentally using a system or Conda interpreter. This matters because the original workspace also had a separate Python installation with its own packages.

## Start the server

In terminal 1:

```bash
.venv/bin/python main.py
```

The server binds `0.0.0.0:8000`. Open `http://localhost:8000` or run:

```bash
curl http://localhost:8000/
```

The response describes the snake's current appearance:

```json
{"apiversion":"1","author":"SEDS Hackathon","color":"#2563EB","head":"sunglasses","tail":"bolt"}
```

Stop the foreground server with Ctrl+C. Restart it after code changes; the entry point does not enable Flask's development reloader.

## Play a solo game

In terminal 2, with the server still running:

```bash
battlesnake play -W 11 -H 11 \
  --name 'MySnake' --url http://localhost:8000 \
  -g solo -v
```

Solo is useful for checking HTTP connectivity, walls, bodies, food, and growth. It does not exercise enemy head contests or multiplayer pressure.

## Play multiplayer and Royale

A four-snake self-play Standard game can use the same stateless server for every snake:

```bash
battlesnake play -W 11 -H 11 -g standard \
  --name 'MySnake' --url http://localhost:8000 \
  --name 'Copy2' --url http://localhost:8000 \
  --name 'Copy3' --url http://localhost:8000 \
  --name 'Copy4' --url http://localhost:8000
```

For Royale, change `-g standard` to `-g royale`. For the larger final board, use `-W 19 -H 19`. Supply a different opponent URL to test another bot rather than another copy of this implementation.

For repeated games with replay files and summaries, use the [practice runner](operations.md). It launches its own temporary servers; you do not need to start those manually.

## Runtime configuration

| Setting | Default | Effect |
|---|---|---|
| `PORT` | `8000` | Integer port used by the Flask server |
| `BATTLESNAKE_SEARCH` | `1` | Exact value `0` disables search when `move` has no explicit override |
| `BATTLESNAKE_MAX_DEPTH` | `2` | Iterative-deepening limit; multi-snake MaxN is capped to a safe depth of `1` |
| `BATTLESNAKE_LOG` | `1` | Exact value `0` disables per-move JSON telemetry |

```bash
PORT=8002 .venv/bin/python main.py
BATTLESNAKE_SEARCH=0 .venv/bin/python main.py
BATTLESNAKE_MAX_DEPTH=1 .venv/bin/python main.py
BATTLESNAKE_LOG=0 .venv/bin/python main.py
```

Values such as `false` do not disable the two switches: the code compares the string with `"0"`. The logging switch does not silence Flask startup, `INFO`, `GAME START`, or end-of-game messages. Rule settings such as hazard damage arrive in the game request; they are not environment variables.

## Docker

The existing Dockerfile can build and run the application:

```bash
docker build -t battlesnake .
docker run --rm -p 8000:8000 battlesnake
```

To disable search in the container:

```bash
docker run --rm -p 8000:8000 -e BATTLESNAKE_SEARCH=0 battlesnake
```

The Dockerfile currently uses `python:3.10.6-slim`, installs runtime requirements, and runs `python main.py` from `/usr/app`. It does not install pytest or the Battlesnake CLI. Its Python version differs from the validated local 3.13 environment, and the recorded test result is not a container test result.

The build uses `COPY . /usr/app`, and the repository currently has no `.dockerignore`. Docker does not use `.gitignore` as its build-context filter; a local virtual environment or large practice artifacts can therefore enter the build context. The supplied image also runs the starter's Flask server, not a separately configured production WSGI service.

## Access from a tournament engine

A local URL is reachable only from an engine with access to that host. For a hosted tournament, follow the [deployment checklist](deployment.md) and provide its public HTTPS endpoint. Keep `PORT` aligned with the hosting environment, verify all four [HTTP routes](api-and-state.md), and measure latency from the engine's location. Local compute benchmarks do not include network travel or hosting startup delays.
