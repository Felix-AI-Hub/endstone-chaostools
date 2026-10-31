"""Floating texts. They exist only on the clients; the server simulates no actor for them."""

import math
import time
import uuid

from endstone import ColorFormat, Player
from endstone.plugin import Plugin

from endstone_chaostools import protocol
from endstone_chaostools.store import JsonStore

EYE_HEIGHT = 1.62
SPAWN_HEIGHT = 2.5
REDRAW_DISTANCE = 0.15
JOIN_DELAY_SECONDS = 5.0
PICK_ANGLE = math.radians(10)
MIN_DISTANCE, MAX_DISTANCE = 1.0, 64.0


def clamp_distance(value: float) -> float:
    return max(MIN_DISTANCE, min(MAX_DISTANCE, value))


def eye_position(player: Player) -> tuple[float, float, float]:
    loc = player.location
    return loc.x, loc.y + EYE_HEIGHT, loc.z


class TextManager:
    def __init__(self, plugin: Plugin, store: JsonStore) -> None:
        self.plugin = plugin
        self.store = store
        self.texts = store.data
        self.runtime_ids: dict[str, int] = {}
        self.next_runtime_id = protocol.FIRST_RUNTIME_ID
        self.seen: dict[str, set[str]] = {}  # player name -> text ids on that client
        self.seen_dim: dict[str, str] = {}
        self.joined: dict[str, float] = {}
        self.moving: dict[str, dict] = {}  # player name -> {"id", "dist", "drawn"}

    def _runtime_id(self, text_id: str) -> int:
        if text_id not in self.runtime_ids:
            self.runtime_ids[text_id] = self.next_runtime_id
            self.next_runtime_id += 1
        return self.runtime_ids[text_id]

    def _hide(self, player: Player, text_id: str) -> None:
        payload = protocol.remove_text(self._runtime_id(text_id))
        player.send_packet(protocol.PACKET_REMOVE_ACTOR, payload)

    def _show(self, player: Player, text_id: str) -> None:
        data = self.texts[text_id]
        payload = protocol.add_text(self._runtime_id(text_id), data["text"], data["x"], data["y"], data["z"])
        player.send_packet(protocol.PACKET_ADD_ACTOR, payload)

    def _viewers(self, text_id: str) -> list[Player]:
        return [p for p in self.plugin.server.online_players if text_id in self.seen.get(p.name, set())]

    def _refresh(self, text_id: str) -> None:
        for player in self._viewers(text_id):
            self._hide(player, text_id)
            self._show(player, text_id)

    def _looked_at(self, player: Player) -> str | None:
        ex, ey, ez = eye_position(player)
        d = player.location.direction
        best, best_angle = None, PICK_ANGLE
        for text_id, data in self.texts.items():
            if data["dim"] != player.dimension.name:
                continue
            vx, vy, vz = data["x"] - ex, data["y"] - ey, data["z"] - ez
            length = math.sqrt(vx * vx + vy * vy + vz * vz)
            if length < 0.01:
                continue
            dot = (vx * d.x + vy * d.y + vz * d.z) / length
            angle = math.acos(max(-1.0, min(1.0, dot)))
            if angle < best_angle:
                best, best_angle = text_id, angle
        return best

    def sync(self) -> None:
        """Send every player the texts of their dimension."""
        now = time.monotonic()
        for player in self.plugin.server.online_players:
            name = player.name
            if name not in self.joined or now - self.joined[name] < JOIN_DELAY_SECONDS:
                continue
            seen = self.seen.setdefault(name, set())
            dimension = player.dimension.name
            if self.seen_dim.get(name) != dimension:
                for text_id in seen & set(self.texts):
                    self._hide(player, text_id)
                seen.clear()
                self.seen_dim[name] = dimension
            for text_id, data in self.texts.items():
                if data["dim"] == dimension and text_id not in seen:
                    self._show(player, text_id)
                    seen.add(text_id)

    def tick_moving(self) -> None:
        for name, state in list(self.moving.items()):
            player = self.plugin.server.get_player(name)
            data = self.texts.get(state["id"])
            if player is None or data is None:
                self.moving.pop(name, None)
                continue
            if player.is_sneaking:
                self.moving.pop(name)
                self.store.save()
                player.send_message(f"{ColorFormat.GREEN}Text {state['id']} abgesetzt.")
                continue
            ex, ey, ez = eye_position(player)
            d = player.location.direction
            dist = state["dist"]
            data["x"], data["y"], data["z"] = ex + d.x * dist, ey + d.y * dist, ez + d.z * dist
            data["dim"] = player.dimension.name
            position = (data["x"], data["y"], data["z"])
            if math.dist(position, state.get("drawn", (1e9, 1e9, 1e9))) >= REDRAW_DISTANCE:
                state["drawn"] = position
                self._refresh(state["id"])
            player.send_tip("Duck dich zum Absetzen")

    def on_join(self, player: Player) -> None:
        self.joined[player.name] = time.monotonic()

    def on_quit(self, player: Player) -> None:
        name = player.name
        self.seen.pop(name, None)
        self.seen_dim.pop(name, None)
        self.joined.pop(name, None)
        self.moving.pop(name, None)

    def command(self, player: Player, args: list[str]) -> bool:
        handlers = {
            "create": self._create,
            "list": self._list,
            "drop": self._drop,
            "dist": self._dist,
            "edit": self._edit,
            "move": self._move,
            "remove": self._remove,
        }
        return handlers[args[0]](player, args[1:])

    def _create(self, player: Player, args: list[str]) -> bool:
        if not args:
            player.send_error_message("Bitte einen Text angeben: /ft create <Text>")
            return False
        loc = player.location
        text_id = uuid.uuid4().hex[:6]
        self.texts[text_id] = {
            "text": args[0].replace("|", "\n"),
            "dim": player.dimension.name,
            "x": loc.x,
            "y": loc.y + SPAWN_HEIGHT,
            "z": loc.z,
        }
        self.store.save()
        player.send_message(f"{ColorFormat.GREEN}Text {text_id} erstellt. Mit /ft move bewegen.")
        return True

    def _list(self, player: Player, args: list[str]) -> bool:
        for text_id, data in self.texts.items():
            player.send_message(f"{text_id}: {data['text']!r} ({data['dim']})")
        if not self.texts:
            player.send_message("Keine Texte vorhanden.")
        return True

    def _drop(self, player: Player, args: list[str]) -> bool:
        self.moving.pop(player.name, None)
        self.store.save()
        player.send_message(f"{ColorFormat.GREEN}Abgesetzt.")
        return True

    def _dist(self, player: Player, args: list[str]) -> bool:
        state = self.moving.get(player.name)
        if state is None:
            player.send_error_message("Du bewegst gerade keinen Text.")
            return False
        state["dist"] = clamp_distance(float(args[0]))
        return True

    def _edit(self, player: Player, args: list[str]) -> bool:
        text_id, text = args[0], args[1]
        if text_id not in self.texts:
            player.send_error_message("Unbekannte Text-ID.")
            return False
        self.texts[text_id]["text"] = text.replace("|", "\n")
        self._refresh(text_id)
        self.store.save()
        return True

    def _pick(self, player: Player, args: list[str]) -> str | None:
        text_id = args[0] if args else self._looked_at(player)
        if text_id not in self.texts:
            player.send_error_message("Schau auf einen Text oder gib seine ID an.")
            return None
        return text_id

    def _move(self, player: Player, args: list[str]) -> bool:
        text_id = self._pick(player, args)
        if text_id is None:
            return False
        data = self.texts[text_id]
        dist = math.dist(eye_position(player), (data["x"], data["y"], data["z"]))
        self.moving[player.name] = {"id": text_id, "dist": clamp_distance(dist)}
        player.send_message(f"{ColorFormat.GREEN}Text {text_id} folgt deinem Fadenkreuz.")
        return True

    def _remove(self, player: Player, args: list[str]) -> bool:
        text_id = self._pick(player, args)
        if text_id is None:
            return False
        for viewer in self._viewers(text_id):
            self._hide(viewer, text_id)
            self.seen[viewer.name].discard(text_id)
        del self.texts[text_id]
        self.store.save()
        player.send_message(f"{ColorFormat.GREEN}Text {text_id} entfernt.")
        return True
