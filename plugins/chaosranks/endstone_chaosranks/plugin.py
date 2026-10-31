from endstone import Player
from endstone.command import Command, CommandSender
from endstone.event import PlayerChatEvent, PlayerJoinEvent, PlayerQuitEvent, event_handler
from endstone.plugin import Plugin

from endstone_chaosranks.ranks import RankManager
from endstone_chaosranks.store import JsonStore


class ChaosRanksPlugin(Plugin):
    prefix = "ChaosRanks"
    api_version = "0.11"

    commands = {
        "rank": {
            "description": "Permission groups: create, assign, grant permissions",
            "usages": [
                "/rank (list)<action: RankListAction>",
                "/rank (info|perms)<action: RankLookupAction> [filter: str]",
                "/rank (create|delete|default)<action: RankGroupAction> <rank: str>",
                "/rank (set)<action: RankSetAction> <player: str> <rank: str>",
                "/rank (unset)<action: RankUnsetAction> <player: str>",
                "/rank (perm)<action: RankPermAction> <rank: str> <permission: str> [value: bool]",
                "/rank (unperm)<action: RankUnpermAction> <rank: str> <permission: str>",
                "/rank (inherit)<action: RankInheritAction> <rank: str> <parent: str>",
                "/rank (prefix)<action: RankPrefixAction> <rank: str> [prefix: message]",
            ],
            "permissions": ["chaosranks.command"],
        },
    }
    permissions = {
        "chaosranks.command": {"description": "Manage permission groups", "default": "op"},
    }

    def on_enable(self) -> None:
        self.data_folder.mkdir(parents=True, exist_ok=True)
        self.manager = RankManager(self, JsonStore(self.data_folder / "ranks.json"))
        self.manager.write_known_permissions()
        self.register_events(self)

    def on_disable(self) -> None:
        self.manager.store.save()

    def on_command(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_error_message("Nur Spieler können diesen Befehl nutzen.")
            return False
        return self.manager.command(sender, args)

    @event_handler
    def on_chat(self, event: PlayerChatEvent) -> None:
        self.manager.on_chat(event)

    @event_handler
    def on_join(self, event: PlayerJoinEvent) -> None:
        self.manager.on_join(event.player)

    @event_handler
    def on_quit(self, event: PlayerQuitEvent) -> None:
        self.manager.on_quit(event.player)
