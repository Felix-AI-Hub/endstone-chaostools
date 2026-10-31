import json
import math
import struct
import time
import uuid

from endstone import ColorFormat, Player
from endstone.command import Command, CommandSender
from endstone.event import (
    PlayerInteractEvent,
    PlayerJoinEvent,
    PlayerQuitEvent,
    event_handler,
)
from endstone.level import Location
from endstone.plugin import Plugin

TAG_PREFIX = "ft_"
EYE_HEIGHT = 1.62
TEXT_OFFSET = 0.0
SPAWN_HEIGHT = 2.5
REDRAW_DISTANCE = 0.15
JOIN_DELAY_SECONDS = 5.0

# Texts are client-side only: the server never simulates an actor for them.
PACKET_ADD_ACTOR = 13
PACKET_REMOVE_ACTOR = 14
FIRST_RUNTIME_ID = 0x7F000000
FLAG_NO_AI = 16
AIR_BLOCK_HASH = -604749536
DATA_FLAGS = 0
DATA_VARIANT = 2
DATA_NAMETAG = 4
DATA_SCALE = 38
DATA_BOX_WIDTH = 53
DATA_BOX_HEIGHT = 54
DATA_ALWAYS_SHOW = 81
TYPE_BYTE, TYPE_INT, TYPE_FLOAT, TYPE_STRING, TYPE_LONG = 0, 2, 3, 4, 7
PICK_ANGLE = math.radians(10)
COOLDOWN_SECONDS = 3.0


def _uvarint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def _zigzag(value: int) -> bytes:
    return _uvarint((value << 1) ^ (value >> 63))


def _string(value: str) -> bytes:
    raw = value.encode("utf-8")
    return _uvarint(len(raw)) + raw


def _entry(key: int, value_type: int) -> bytes:
    # Since 26.60 the value type is written twice.
    return _uvarint(key) + _uvarint(value_type) + _uvarint(value_type)


def _add_actor(runtime_id: int, data: dict) -> bytes:
    flags = 1 << FLAG_NO_AI
    metadata = [
        _entry(DATA_FLAGS, TYPE_LONG) + _zigzag(flags),
        _entry(DATA_NAMETAG, TYPE_STRING) + _string(data["text"]),
        _entry(DATA_VARIANT, TYPE_INT) + _zigzag(AIR_BLOCK_HASH),
        _entry(DATA_SCALE, TYPE_FLOAT) + struct.pack("<f", 0.01),
        _entry(DATA_BOX_WIDTH, TYPE_FLOAT) + struct.pack("<f", 0.0),
        _entry(DATA_BOX_HEIGHT, TYPE_FLOAT) + struct.pack("<f", 0.0),
        _entry(DATA_ALWAYS_SHOW, TYPE_BYTE) + bytes([1]),
    ]
    return (
        _zigzag(runtime_id)
        + _uvarint(runtime_id)
        + _string("minecraft:falling_block")
        + struct.pack("<3f", data["x"], data["y"], data["z"])
        + struct.pack("<3f", 0.0, 0.0, 0.0)
        + struct.pack("<4f", 0.0, 0.0, 0.0, 0.0)
        + _uvarint(0)  # attributes
        + _uvarint(len(metadata))
        + b"".join(metadata)
        + _uvarint(0)  # synced int properties
        + _uvarint(0)  # synced float properties
        + _uvarint(0)  # links
        + bytes(1)  # no passenger-of-block entry
    )


class ChaosToolsPlugin(Plugin):
    prefix = "ChaosTools"
    api_version = "0.11"

    commands = {
        "ft": {
            "description": "Floating texts: create, move with the crosshair, edit, remove",
            "usages": [
                "/ft (create)<action: FtCreateAction> <text: message>",
                "/ft (edit)<action: FtEditAction> <id: str> <text: message>",
                "/ft (dist)<action: FtDistAction> <blocks: float>",
                "/ft (list|drop)<action: FtSimpleAction>",
                "/ft (move|remove)<action: FtPickAction> [id: str]",
            ],
            "permissions": ["chaostools.command"],
        },
        "portal": {
            "description": "Portals and signs that teleport players or send them to another server",
            "usages": [
                "/portal (create)<action: PortalCreateAction> <name: str> [radius: float]",
                "/portal (sign|target|remove)<action: PortalNameAction> <name: str>",
                "/portal (server)<action: PortalServerAction> <name: str> <host: str> [port: int]",
                "/portal (list)<action: PortalListAction>",
            ],
            "permissions": ["chaostools.command"],
        },
    }
    permissions = {
        "chaostools.command": {"description": "Manage floating texts and portals", "default": "op"},
    }

    def on_enable(self) -> None:
        self.data_folder.mkdir(parents=True, exist_ok=True)
        self.texts: dict[str, dict] = self._load("texts.json")
        self.portals: dict[str, dict] = self._load("portals.json")
        self.runtime_ids: dict[str, int] = {}
        self.next_runtime_id = FIRST_RUNTIME_ID
        self.seen: dict[str, set[str]] = {}  # player name -> text ids on that client
        self.seen_dim: dict[str, str] = {}
        self.joined: dict[str, float] = {}
        self.moving: dict[str, dict] = {}  # player name -> {"id", "dist"}
        self.arming: dict[str, str] = {}  # player name -> portal waiting for a sign click
        self.cooldown: dict[str, float] = {}
        self.inside: dict[str, str] = {}
        self.register_events(self)
        self.server.scheduler.run_task(self, self._tick_moving, delay=1, period=1)
        self.server.scheduler.run_task(self, self._sync_texts, delay=20, period=20)
        self.server.scheduler.run_task(self, self._tick_portals, delay=5, period=5)

    def on_disable(self) -> None:
        self._save("texts.json", self.texts)
        self._save("portals.json", self.portals)

    def _load(self, name: str) -> dict:
        path = self.data_folder / name
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def _save(self, name: str, data: dict) -> None:
        (self.data_folder / name).write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _console(self, line: str) -> None:
        self.server.dispatch_command(self.server.command_sender, line)

    # Floating texts

    def _runtime_id(self, text_id: str) -> int:
        if text_id not in self.runtime_ids:
            self.runtime_ids[text_id] = self.next_runtime_id
            self.next_runtime_id += 1
        return self.runtime_ids[text_id]

    def _hide(self, player: Player, text_id: str) -> None:
        player.send_packet(PACKET_REMOVE_ACTOR, _zigzag(self._runtime_id(text_id)))

    def _show(self, player: Player, text_id: str) -> None:
        player.send_packet(PACKET_ADD_ACTOR, _add_actor(self._runtime_id(text_id), self.texts[text_id]))

    def _sync_texts(self) -> None:
        now = time.monotonic()
        for actor in self.server.level.actors:  # NPCs left over from version 0.1
            if any(tag.startswith(TAG_PREFIX) for tag in actor.scoreboard_tags):
                actor.remove()
        for player in self.server.online_players:
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

    def _refresh(self, text_id: str) -> None:
        for player in self.server.online_players:
            if text_id in self.seen.get(player.name, set()):
                self._hide(player, text_id)
                self._show(player, text_id)

    @staticmethod
    def _eye(player: Player) -> tuple[float, float, float]:
        loc = player.location
        return loc.x, loc.y + EYE_HEIGHT, loc.z

    def _looked_at(self, player: Player) -> str | None:
        ex, ey, ez = self._eye(player)
        d = player.location.direction
        best, best_angle = None, PICK_ANGLE
        for text_id, data in self.texts.items():
            if data["dim"] != player.dimension.name:
                continue
            vx, vy, vz = data["x"] - ex, data["y"] + TEXT_OFFSET - ey, data["z"] - ez
            length = math.sqrt(vx * vx + vy * vy + vz * vz)
            if length < 0.01:
                continue
            dot = (vx * d.x + vy * d.y + vz * d.z) / length
            angle = math.acos(max(-1.0, min(1.0, dot)))
            if angle < best_angle:
                best, best_angle = text_id, angle
        return best

    def _tick_moving(self) -> None:
        for name, state in list(self.moving.items()):
            player = self.server.get_player(name)
            data = self.texts.get(state["id"])
            if player is None or data is None:
                self.moving.pop(name, None)
                continue
            if player.is_sneaking:
                self.moving.pop(name)
                self._save("texts.json", self.texts)
                player.send_message(f"{ColorFormat.GREEN}Text {state['id']} abgesetzt.")
                continue
            ex, ey, ez = self._eye(player)
            d = player.location.direction
            dist = state["dist"]
            data["x"], data["z"] = ex + d.x * dist, ez + d.z * dist
            data["y"] = ey + d.y * dist - TEXT_OFFSET
            data["dim"] = player.dimension.name
            position = (data["x"], data["y"], data["z"])
            if math.dist(position, state.get("drawn", (1e9, 1e9, 1e9))) >= REDRAW_DISTANCE:
                state["drawn"] = position
                self._refresh(state["id"])
            player.send_tip("Duck dich zum Absetzen")

    def _ft(self, player: Player, args: list[str]) -> bool:
        action = args[0]
        name = player.name
        if action == "create":
            if len(args) < 2:
                player.send_error_message("Bitte einen Text angeben: /ft create <Text>")
                return False
            loc = player.location
            text_id = uuid.uuid4().hex[:6]
            self.texts[text_id] = {
                "text": args[1].replace("|", "\n"),
                "dim": player.dimension.name,
                "x": loc.x,
                "y": loc.y + SPAWN_HEIGHT,
                "z": loc.z,
            }
            self._save("texts.json", self.texts)
            player.send_message(f"{ColorFormat.GREEN}Text {text_id} erstellt. Mit /ft move bewegen.")
        elif action == "list":
            for text_id, data in self.texts.items():
                player.send_message(f"{text_id}: {data['text']!r} ({data['dim']})")
            if not self.texts:
                player.send_message("Keine Texte vorhanden.")
        elif action == "drop":
            self.moving.pop(name, None)
            self._save("texts.json", self.texts)
            player.send_message(f"{ColorFormat.GREEN}Abgesetzt.")
        elif action == "dist":
            state = self.moving.get(name)
            if state is None:
                player.send_error_message("Du bewegst gerade keinen Text.")
                return False
            state["dist"] = max(1.0, min(64.0, float(args[1])))
        elif action == "edit":
            if args[1] not in self.texts:
                player.send_error_message("Unbekannte Text-ID.")
                return False
            self.texts[args[1]]["text"] = args[2].replace("|", "\n")
            self._refresh(args[1])
            self._save("texts.json", self.texts)
        elif action in ("move", "remove"):
            text_id = args[1] if len(args) > 1 else self._looked_at(player)
            if text_id not in self.texts:
                player.send_error_message("Schau auf einen Text oder gib seine ID an.")
                return False
            if action == "move":
                ex, ey, ez = self._eye(player)
                data = self.texts[text_id]
                dist = math.dist((ex, ey, ez), (data["x"], data["y"] + TEXT_OFFSET, data["z"]))
                self.moving[name] = {"id": text_id, "dist": max(1.0, min(64.0, dist))}
                player.send_message(f"{ColorFormat.GREEN}Text {text_id} folgt deinem Fadenkreuz.")
            else:
                for viewer in self.server.online_players:
                    if text_id in self.seen.get(viewer.name, set()):
                        self._hide(viewer, text_id)
                        self.seen[viewer.name].discard(text_id)
                del self.texts[text_id]
                self._save("texts.json", self.texts)
                player.send_message(f"{ColorFormat.GREEN}Text {text_id} entfernt.")
        return True

    # Portals

    def _use_portal(self, player: Player, name: str) -> None:
        now = time.monotonic()
        if now - self.cooldown.get(player.name, 0.0) < COOLDOWN_SECONDS:
            return
        target = self.portals[name].get("target")
        if target is None:
            player.send_error_message(f"Portal {name} hat noch kein Ziel.")
            self.cooldown[player.name] = now
            return
        self.cooldown[player.name] = now
        if target["type"] == "server":
            player.transfer(target["host"], target["port"])
            return
        dimension = self.server.level.get_dimension(target["dim"])
        player.teleport(
            Location(dimension, target["x"], target["y"], target["z"], target["pitch"], target["yaw"])
        )

    def _tick_portals(self) -> None:
        for player in self.server.online_players:
            loc = player.location
            hit = None
            for name, portal in self.portals.items():
                region = portal.get("region")
                if region is None or region["dim"] != player.dimension.name:
                    continue
                dx, dz = loc.x - region["x"], loc.z - region["z"]
                if dx * dx + dz * dz <= region["radius"] ** 2 and 0 <= loc.y - region["y"] < 3:
                    hit = name
                    break
            previous = self.inside.get(player.name)
            if hit is None:
                self.inside.pop(player.name, None)
            elif hit != previous:
                self.inside[player.name] = hit
                self._use_portal(player, hit)

    @event_handler
    def on_interact(self, event: PlayerInteractEvent) -> None:
        if event.action != PlayerInteractEvent.Action.RIGHT_CLICK_BLOCK or not event.has_block:
            return
        player, block = event.player, event.block
        key = f"{block.dimension.name}:{block.x}:{block.y}:{block.z}"
        armed = self.arming.pop(player.name, None)
        if armed is not None:
            self.portals[armed].setdefault("signs", []).append(key)
            self._save("portals.json", self.portals)
            event.cancelled = True
            player.send_message(f"{ColorFormat.GREEN}Block mit Portal {armed} verknuepft.")
            self.cooldown[player.name] = time.monotonic()
            return
        for name, portal in self.portals.items():
            if key in portal.get("signs", []):
                event.cancelled = True
                self._use_portal(player, name)
                return

    @event_handler
    def on_join(self, event: PlayerJoinEvent) -> None:
        self.joined[event.player.name] = time.monotonic()

    @event_handler
    def on_quit(self, event: PlayerQuitEvent) -> None:
        name = event.player.name
        self.seen.pop(name, None)
        self.seen_dim.pop(name, None)
        self.joined.pop(name, None)
        self.moving.pop(name, None)
        self.arming.pop(name, None)
        self.inside.pop(name, None)

    def _portal(self, player: Player, args: list[str]) -> bool:
        action = args[0]
        if action == "list":
            for name, portal in self.portals.items():
                player.send_message(
                    f"{name}: Ziel {portal.get('target')}, "
                    f"Bereich {portal.get('region') is not None}, {len(portal.get('signs', []))} Schilder"
                )
            if not self.portals:
                player.send_message("Keine Portale vorhanden.")
            return True
        name = args[1]
        loc = player.location
        if action == "create":
            radius = float(args[2]) if len(args) > 2 else 1.5
            portal = self.portals.setdefault(name, {})
            portal["region"] = {
                "dim": player.dimension.name, "x": loc.x, "y": loc.y, "z": loc.z, "radius": radius,
            }
            self.inside[player.name] = name
            player.send_message(f"{ColorFormat.GREEN}Portal {name} steht hier. Jetzt /portal target oder server.")
        elif name not in self.portals and action != "sign":
            player.send_error_message("Unbekanntes Portal.")
            return False
        elif action == "sign":
            self.portals.setdefault(name, {})
            self.arming[player.name] = name
            player.send_message("Klicke jetzt mit Rechtsklick auf das Schild.")
        elif action == "target":
            self.portals[name]["target"] = {
                "type": "tp", "dim": player.dimension.name, "x": loc.x, "y": loc.y, "z": loc.z,
                "pitch": loc.pitch, "yaw": loc.yaw,
            }
            player.send_message(f"{ColorFormat.GREEN}Ziel von {name} ist jetzt dein Standort.")
        elif action == "server":
            port = int(args[3]) if len(args) > 3 else 19132
            self.portals[name]["target"] = {"type": "server", "host": args[2], "port": port}
            player.send_message(f"{ColorFormat.GREEN}{name} fuehrt jetzt zu {args[2]}:{port}.")
        elif action == "remove":
            del self.portals[name]
            player.send_message(f"{ColorFormat.GREEN}Portal {name} entfernt.")
        self._save("portals.json", self.portals)
        return True

    def on_command(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_error_message("Nur Spieler koennen diesen Befehl nutzen.")
            return False
        if command.name == "ft":
            return self._ft(sender, args)
        return self._portal(sender, args)
