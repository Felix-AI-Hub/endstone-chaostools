from endstone import Player
from endstone.command import Command, CommandSender
from endstone.event import PlayerJoinEvent, PlayerQuitEvent, event_handler
from endstone.plugin import Plugin

from endstone_chaostexts.texts import TextManager
from endstone_chaostexts.store import JsonStore


class ChaosTextsPlugin(Plugin):
    prefix = "ChaosTexts"
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
            "permissions": ["chaostexts.command"],
        },
    }
    permissions = {
        "chaostexts.command": {"description": "Manage floating texts", "default": "op"},
    }

    def on_enable(self) -> None:
        self.data_folder.mkdir(parents=True, exist_ok=True)
        self.manager = TextManager(self, JsonStore(self.data_folder / "texts.json"))
        self.server.scheduler.run_task(self, self.manager.tick_moving, delay=1, period=1)
        self.server.scheduler.run_task(self, self.manager.sync, delay=20, period=20)
        self.register_events(self)

    def on_disable(self) -> None:
        self.manager.store.save()

    def on_command(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_error_message("Nur Spieler können diesen Befehl nutzen.")
            return False
        return self.manager.command(sender, args)

    @event_handler
    def on_join(self, event: PlayerJoinEvent) -> None:
        self.manager.on_join(event.player)

    @event_handler
    def on_quit(self, event: PlayerQuitEvent) -> None:
        self.manager.on_quit(event.player)
