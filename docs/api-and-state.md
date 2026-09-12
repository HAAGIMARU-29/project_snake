# HTTP API and game state

[Documentation index](README.md)

This page documents the server and payload subset used by this repository. It is not a complete specification of every Battlesnake ruleset or API extension.

## Routes

| Method and path | Handler | Successful response |
|---|---|---|
| `GET /` | `main.info()` | JSON metadata with `apiversion`, `author`, `color`, `head`, `tail` |
| `POST /start` | `main.start(game_state)` | Text `ok` |
| `POST /move` | `main.move(game_state)` | JSON such as `{"move":"up"}` |
| `POST /end` | `main.end(game_state)` | Text `ok` |

Successful route calls use HTTP 200. POST requests must send JSON with an appropriate content type. Every response passing through the app's `after_request` hook gets the `server` header value `battlesnake/github/starter-snake-python`.

`start` logs a start message without initializing persistent game state. `end` logs survival or elimination evidence. Each call to `move` independently reads the complete request. `info` can be customized in `main.py` without touching the move algorithm.

## Coordinate and body conventions

Cells arrive as dictionaries such as `{"x":5,"y":6}`. Internally, `to_pos` converts them to tuples such as `(5, 6)` for set membership and dictionary keys.

| Direction | Delta |
|---|---|
| `up` | `(0, 1)` |
| `down` | `(0, -1)` |
| `left` | `(-1, 0)` |
| `right` | `(1, 0)` |

Valid coordinates satisfy `0 <= x < width` and `0 <= y < height`. A snake's body is ordered head first, tail last. The logic uses `body[0]` as the head and `len(body)` as length; the separate incoming `head` and `length` fields do not override those values. Repeated tail coordinates can represent stacked growth, so a set of cells alone is insufficient to decide whether a tail cell becomes empty.

## Fields used by the bot

| Path | Purpose / default |
|---|---|
| `board.width`, `board.height` | Required dimensions |
| `board.snakes` | Current snakes, including us; drives occupancy, head threats, and player count |
| `board.food` | Food cells; absent list treated as empty |
| `board.hazards` | Hazard cells; absent list treated as empty |
| `you.id` | Our identity; opponents are identified by inequality, not hardcoded IDs |
| `you.body` | Nonempty ordered body |
| `you.health` | Health; many helpers default to 100 when omitted |
| Each enemy's `id`, `body` | Identity, head, length, body occupancy |
| `game.ruleset.name` | Exact `royale` activates hazard logic; otherwise hazard-specific helpers are inactive |
| `game.ruleset.settings.hazardDamagePerTurn` | Default 14, clamped to at least zero |
| `game.timeout` | Request timeout in milliseconds; default 500 |
| `game.id`, `turn` | Telemetry identifiers; turn also increments in simulation |

`shrinkEveryNTurns` may be present in Royale requests, but the evaluator does not predict future shrink events from it. Maps with wrapping, squads, constrictor growth, or stacked hazard semantics are not implemented as separate modes. The validated strategy scope is Standard and ordinary Royale; solo can be used for practice.

## Runnable request fixture

Generate an example JSON request from the project's fixture helper:

```bash
.venv/bin/python - <<'PY' > /tmp/battlesnake-request.json
import json
from tests.fixtures import make_state
print(json.dumps(make_state(food=[{"x": 6, "y": 5}])))
PY
```

Then send it to a running local server:

```bash
curl -sS -H 'Content-Type: application/json' \
  --data-binary @/tmp/battlesnake-request.json \
  http://localhost:8000/move
```

The fixture has an 11×11 board, one three-segment snake, and the supplied food. For a standalone client, the essential structure is:

```json
{
  "game": {
    "id": "example-game",
    "ruleset": {"name": "standard", "settings": {}},
    "timeout": 500
  },
  "turn": 0,
  "board": {
    "width": 11,
    "height": 11,
    "food": [{"x": 6, "y": 5}],
    "hazards": [],
    "snakes": [{
      "id": "you", "health": 100,
      "body": [{"x": 5, "y": 5}, {"x": 5, "y": 4}, {"x": 5, "y": 3}]
    }]
  },
  "you": {
    "id": "you", "health": 100,
    "body": [{"x": 5, "y": 5}, {"x": 5, "y": 4}, {"x": 5, "y": 3}]
  }
}
```

## Errors and return guarantees

For a valid game state, even a completely trapped snake receives a dictionary containing a valid move direction. That fallback does not imply the move can survive.

The server calls `request.get_json()` and passes the result directly to the handler. It does not validate all fields or catch arbitrary strategy exceptions. Missing bodies, inconsistent identities, invalid directions passed directly to helpers, or a malformed request can therefore raise errors. Do not interpret the valid-state regression tests as validation of arbitrary user input.

## End-of-game evidence

`death_reason` first examines `you.elimination_event.cause`, falling back to `you.eliminatedCause`. Recognized causes map to WALL, BODY, HEAD_TO_HEAD, STARVATION, HAZARD, TIMEOUT, or TRAPPED. Without explicit metadata, it can infer an out-of-bounds head or health exhaustion; otherwise it returns UNKNOWN.

`end` decides `survived` by whether our ID is still in `board.snakes`. Survival is not a separately computed tournament placement. The practice runner extracts explicit engine causes from CLI logs for more reliable loss analysis; see [Operations](operations.md).
