"""Permission groups with inheritance, a default group and name prefixes."""

from endstone import ColorFormat, Player
from endstone.event import PlayerChatEvent
from endstone.plugin import Plugin

from endstone_chaosranks.store import JsonStore

DEFAULT_GROUP = "spieler"
KNOWN_PERMISSIONS_FILE = "known-permissions.txt"
MAX_LISTED_PERMISSIONS = 40


class RankManager:
    def __init__(self, plugin: Plugin, store: JsonStore) -> None:
        self.plugin = plugin
        self.store = store
        self.data = store.data
        self.data.setdefault("default", DEFAULT_GROUP)
        self.data.setdefault("groups", {DEFAULT_GROUP: {"inherit": [], "perms": {}, "prefix": ""}})
        self.data.setdefault("players", {})
        self.attachments: dict[str, object] = {}

    @property
    def groups(self) -> dict[str, dict]:
        return self.data["groups"]

    @property
    def players(self) -> dict[str, str]:
        return self.data["players"]

    def write_known_permissions(self) -> None:
        names = sorted(p.name for p in self.plugin.server.plugin_manager.permissions)
        path = self.plugin.data_folder / KNOWN_PERMISSIONS_FILE
        path.write_text("\n".join(names) + "\n", encoding="utf-8")

    def group_of(self, name: str) -> str:
        group = self.players.get(name.lower(), self.data["default"])
        return group if group in self.groups else self.data["default"]

    def resolved_permissions(self, group: str) -> dict[str, bool]:
        """Merge a group with its parents; a child overrides its parents."""
        merged: dict[str, bool] = {}
        visited: set[str] = set()

        def visit(name: str) -> None:
            if name in visited or name not in self.groups:
                return
            visited.add(name)
            for parent in self.groups[name]["inherit"]:
                visit(parent)
            merged.update(self.groups[name]["perms"])

        visit(group)
        return merged

    def _prefix(self, name: str) -> str:
        return self.groups[self.group_of(name)]["prefix"]

    def apply(self, player: Player) -> None:
        previous = self.attachments.pop(player.name, None)
        if previous is not None:
            player.remove_attachment(previous)
        attachment = player.add_attachment(self.plugin)
        for permission, value in self.resolved_permissions(self.group_of(player.name)).items():
            attachment.set_permission(permission, value)
        self.attachments[player.name] = attachment
        player.recalculate_permissions()
        player.update_commands()
        prefix = self._prefix(player.name)
        player.name_tag = f"{prefix} {player.name}" if prefix else player.name

    def assign(self, name: str, group: str) -> None:
        self.players[name.lower()] = group
        self.store.save()
        self._apply_all()

    def _apply_all(self) -> None:
        for player in self.plugin.server.online_players:
            self.apply(player)

    def on_join(self, player: Player) -> None:
        self.apply(player)

    def on_quit(self, player: Player) -> None:
        self.attachments.pop(player.name, None)

    def on_chat(self, event: PlayerChatEvent) -> None:
        prefix = self._prefix(event.player.name)
        if prefix and not event.cancelled:
            event.cancelled = True
            self.plugin.server.broadcast_message(f"{prefix} <{event.player.name}> {event.message}")

    def command(self, player: Player, args: list[str]) -> bool:
        handlers = {
            "list": self._list,
            "info": self._info,
            "perms": self._known,
            "create": self._create,
            "delete": self._delete,
            "default": self._default,
            "set": self._set,
            "unset": self._unset,
            "perm": self._perm,
            "unperm": self._unperm,
            "inherit": self._inherit,
            "prefix": self._set_prefix,
        }
        return handlers[args[0]](player, args[1:])

    def _changed(self, player: Player, message: str) -> bool:
        self.store.save()
        self._apply_all()
        player.send_message(f"{ColorFormat.GREEN}{message}")
        return True

    def _require_group(self, player: Player, group: str) -> bool:
        if group in self.groups:
            return True
        player.send_error_message(f"Unbekannter Rang: {group}")
        return False

    def _list(self, player: Player, args: list[str]) -> bool:
        for name, group in self.groups.items():
            marker = " (Standard)" if name == self.data["default"] else ""
            player.send_message(f"{name}{marker}: erbt {group['inherit']}, {len(group['perms'])} Rechte")
        return True

    def _info(self, player: Player, args: list[str]) -> bool:
        name = args[0] if args else player.name
        group = self.group_of(name)
        player.send_message(f"{name}: Rang {group}")
        for permission, value in sorted(self.resolved_permissions(group).items()):
            player.send_message(f"  {permission} = {value}")
        return True

    def _known(self, player: Player, args: list[str]) -> bool:
        needle = args[0].lower() if args else ""
        names = sorted(p.name for p in self.plugin.server.plugin_manager.permissions if needle in p.name.lower())
        for name in names[:MAX_LISTED_PERMISSIONS]:
            player.send_message(name)
        if len(names) > MAX_LISTED_PERMISSIONS:
            player.send_message(f"... und {len(names) - MAX_LISTED_PERMISSIONS} weitere. Filter genauer angeben.")
        return True

    def _create(self, player: Player, args: list[str]) -> bool:
        group = args[0].lower()
        if group in self.groups:
            player.send_error_message("Diesen Rang gibt es schon.")
            return False
        self.groups[group] = {"inherit": [], "perms": {}, "prefix": ""}
        return self._changed(player, f"Rang {group} erstellt.")

    def _delete(self, player: Player, args: list[str]) -> bool:
        group = args[0].lower()
        if not self._require_group(player, group):
            return False
        if group == self.data["default"]:
            player.send_error_message("Der Standard-Rang kann nicht gelöscht werden.")
            return False
        del self.groups[group]
        for other in self.groups.values():
            other["inherit"] = [parent for parent in other["inherit"] if parent != group]
        for name in [name for name, value in self.players.items() if value == group]:
            del self.players[name]
        return self._changed(player, f"Rang {group} gelöscht.")

    def _default(self, player: Player, args: list[str]) -> bool:
        group = args[0].lower()
        if not self._require_group(player, group):
            return False
        self.data["default"] = group
        return self._changed(player, f"Standard-Rang ist jetzt {group}.")

    def _set(self, player: Player, args: list[str]) -> bool:
        group = args[1].lower()
        if not self._require_group(player, group):
            return False
        self.players[args[0].lower()] = group
        return self._changed(player, f"{args[0]} hat jetzt den Rang {group}.")

    def _unset(self, player: Player, args: list[str]) -> bool:
        self.players.pop(args[0].lower(), None)
        return self._changed(player, f"{args[0]} hat wieder den Standard-Rang.")

    def _perm(self, player: Player, args: list[str]) -> bool:
        group = args[0].lower()
        if not self._require_group(player, group):
            return False
        value = len(args) < 3 or args[2].lower() != "false"
        self.groups[group]["perms"][args[1]] = value
        return self._changed(player, f"{group}: {args[1]} = {value}")

    def _unperm(self, player: Player, args: list[str]) -> bool:
        group = args[0].lower()
        if not self._require_group(player, group):
            return False
        self.groups[group]["perms"].pop(args[1], None)
        return self._changed(player, f"{group}: {args[1]} entfernt.")

    def _inherit(self, player: Player, args: list[str]) -> bool:
        group, parent = args[0].lower(), args[1].lower()
        if not self._require_group(player, group) or not self._require_group(player, parent):
            return False
        if parent not in self.groups[group]["inherit"]:
            self.groups[group]["inherit"].append(parent)
        return self._changed(player, f"{group} erbt jetzt von {parent}.")

    def _set_prefix(self, player: Player, args: list[str]) -> bool:
        group = args[0].lower()
        if not self._require_group(player, group):
            return False
        self.groups[group]["prefix"] = args[1] if len(args) > 1 else ""
        return self._changed(player, f"Präfix von {group} geändert.")
