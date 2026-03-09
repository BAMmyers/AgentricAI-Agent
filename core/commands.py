"""
AgentricAI Command System.
Provides a command palette and keyboard shortcut infrastructure.
"""
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Any
from enum import Enum
import json


class CommandCategory(Enum):
    """Categories for organizing commands."""
    NAVIGATION = "navigation"
    EDITING = "editing"
    CHAT = "chat"
    AGENT = "agent"
    TOOLS = "tools"
    MEMORY = "memory"
    SYSTEM = "system"
    HELP = "help"


@dataclass
class Command:
    """
    Represents a command that can be executed.
    
    Attributes:
        id: Unique command identifier
        name: Human-readable name
        description: What the command does
        category: Command category for grouping
        shortcut: Keyboard shortcut (e.g., "Ctrl+K")
        icon: Icon identifier for UI
        action: Callable to execute
        enabled: Whether the command is currently available
    """
    id: str
    name: str
    description: str
    category: CommandCategory
    shortcut: Optional[str] = None
    icon: Optional[str] = None
    action: Optional[Callable] = None
    enabled: bool = True
    aliases: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category.value,
            'shortcut': self.shortcut,
            'icon': self.icon,
            'enabled': self.enabled,
            'aliases': self.aliases
        }


class CommandRegistry:
    """
    Registry for all available commands.
    
    Features:
    - Command registration with metadata
    - Keyboard shortcut mapping
    - Command search and filtering
    - Category organization
    """
    
    def __init__(self):
        """Initialize the command registry."""
        self._commands: Dict[str, Command] = {}
        self._shortcuts: Dict[str, str] = {}  # shortcut -> command_id
        self._aliases: Dict[str, str] = {}    # alias -> command_id
        self._register_default_commands()
    
    def register(self, command: Command) -> None:
        """
        Register a command.
        
        Args:
            command: The command to register
        """
        self._commands[command.id] = command
        
        if command.shortcut:
            self._shortcuts[command.shortcut.lower()] = command.id
        
        for alias in command.aliases:
            self._aliases[alias.lower()] = command.id
    
    def unregister(self, command_id: str) -> bool:
        """
        Unregister a command.
        
        Args:
            command_id: The command ID to remove
            
        Returns:
            True if command was removed
        """
        if command_id in self._commands:
            cmd = self._commands[command_id]
            if cmd.shortcut:
                self._shortcuts.pop(cmd.shortcut.lower(), None)
            for alias in cmd.aliases:
                self._aliases.pop(alias.lower(), None)
            del self._commands[command_id]
            return True
        return False
    
    def get(self, command_id: str) -> Optional[Command]:
        """Get a command by ID."""
        return self._commands.get(command_id)
    
    def get_by_shortcut(self, shortcut: str) -> Optional[Command]:
        """Get a command by keyboard shortcut."""
        cmd_id = self._shortcuts.get(shortcut.lower())
        return self._commands.get(cmd_id) if cmd_id else None
    
    def get_by_alias(self, alias: str) -> Optional[Command]:
        """Get a command by alias."""
        cmd_id = self._aliases.get(alias.lower())
        return self._commands.get(cmd_id) if cmd_id else None
    
    def search(self, query: str, limit: int = 10) -> List[Command]:
        """
        Search commands by name or description.
        
        Args:
            query: Search query
            limit: Maximum results to return
            
        Returns:
            List of matching commands
        """
        query = query.lower()
        results = []
        
        for cmd in self._commands.values():
            if not cmd.enabled:
                continue
            
            score = 0
            if query in cmd.name.lower():
                score = 3
            elif query in cmd.description.lower():
                score = 2
            elif query in cmd.id.lower():
                score = 1
            
            if score > 0:
                results.append((score, cmd))
        
        results.sort(key=lambda x: (-x[0], x[1].name))
        return [cmd for _, cmd in results[:limit]]
    
    def list_by_category(self, category: CommandCategory) -> List[Command]:
        """List all commands in a category."""
        return [cmd for cmd in self._commands.values() 
                if cmd.category == category and cmd.enabled]
    
    def list_all(self) -> List[Command]:
        """List all registered commands."""
        return list(self._commands.values())
    
    def execute(self, command_id: str, *args, **kwargs) -> Any:
        """
        Execute a command by ID.
        
        Args:
            command_id: The command to execute
            *args, **kwargs: Arguments to pass to the command
            
        Returns:
            Command execution result
        """
        cmd = self.get(command_id)
        if cmd and cmd.enabled and cmd.action:
            return cmd.action(*args, **kwargs)
        return None
    
    def execute_shortcut(self, shortcut: str, *args, **kwargs) -> Any:
        """Execute a command by keyboard shortcut."""
        cmd = self.get_by_shortcut(shortcut)
        if cmd:
            return self.execute(cmd.id, *args, **kwargs)
        return None
    
    def _register_default_commands(self):
        """Register default system commands."""
        default_commands = [
            # Navigation
            Command(
                id="nav.home",
                name="Go to Home",
                description="Navigate to the home page",
                category=CommandCategory.NAVIGATION,
                shortcut="Ctrl+H",
                icon="home"
            ),
            Command(
                id="nav.chat",
                name="Go to Chat",
                description="Open the chat interface",
                category=CommandCategory.NAVIGATION,
                shortcut="Ctrl+Shift+C",
                icon="message"
            ),
            Command(
                id="nav.settings",
                name="Open Settings",
                description="Open the settings panel",
                category=CommandCategory.NAVIGATION,
                shortcut="Ctrl+,",
                icon="settings"
            ),
            
            # Chat commands
            Command(
                id="chat.new",
                name="New Conversation",
                description="Start a new conversation",
                category=CommandCategory.CHAT,
                shortcut="Ctrl+N",
                icon="plus"
            ),
            Command(
                id="chat.clear",
                name="Clear Conversation",
                description="Clear the current conversation",
                category=CommandCategory.CHAT,
                shortcut="Ctrl+L",
                icon="trash"
            ),
            Command(
                id="chat.export",
                name="Export Conversation",
                description="Export the conversation to a file",
                category=CommandCategory.CHAT,
                shortcut="Ctrl+E",
                icon="download"
            ),
            Command(
                id="chat.search",
                name="Search Conversations",
                description="Search through conversation history",
                category=CommandCategory.CHAT,
                shortcut="Ctrl+F",
                icon="search"
            ),
            
            # Agent commands
            Command(
                id="agent.select",
                name="Select Agent",
                description="Choose an agent to chat with",
                category=CommandCategory.AGENT,
                shortcut="Ctrl+Shift+A",
                icon="bot",
                aliases=["switch agent", "change agent"]
            ),
            Command(
                id="agent.info",
                name="Agent Info",
                description="Show current agent information",
                category=CommandCategory.AGENT,
                icon="info"
            ),
            
            # System commands
            Command(
                id="system.command_palette",
                name="Command Palette",
                description="Open the command palette",
                category=CommandCategory.SYSTEM,
                shortcut="Ctrl+K",
                icon="terminal",
                aliases=["commands", "palette"]
            ),
            Command(
                id="system.theme",
                name="Toggle Theme",
                description="Switch between light and dark theme",
                category=CommandCategory.SYSTEM,
                shortcut="Ctrl+T",
                icon="moon"
            ),
            Command(
                id="system.help",
                name="Show Help",
                description="Display help and keyboard shortcuts",
                category=CommandCategory.HELP,
                shortcut="F1",
                icon="help"
            ),
        ]
        
        for cmd in default_commands:
            self.register(cmd)


class KeyboardShortcutManager:
    """
    Manages keyboard shortcuts and their bindings.
    
    Features:
    - Platform-specific shortcut handling
    - Conflict detection
    - Shortcut customization
    """
    
    def __init__(self, registry: CommandRegistry):
        """Initialize with a command registry."""
        self.registry = registry
        self._platform = "windows"  # Could be detected
    
    def get_shortcuts_for_display(self) -> Dict[str, str]:
        """
        Get all shortcuts formatted for display.
        
        Returns:
            Dict mapping command names to shortcut strings
        """
        shortcuts = {}
        for cmd in self.registry.list_all():
            if cmd.shortcut:
                shortcuts[cmd.name] = self._format_shortcut(cmd.shortcut)
        return shortcuts
    
    def _format_shortcut(self, shortcut: str) -> str:
        """Format a shortcut for the current platform."""
        if self._platform == "mac":
            return shortcut.replace("Ctrl", "⌘").replace("Alt", "⌥").replace("Shift", "⇧")
        return shortcut
    
    def handle_key_event(self, key_event: Dict) -> Optional[Any]:
        """
        Handle a keyboard event.
        
        Args:
            key_event: Dict with 'ctrl', 'alt', 'shift', 'key' fields
            
        Returns:
            Command execution result if shortcut matched
        """
        parts = []
        if key_event.get('ctrl'):
            parts.append('Ctrl')
        if key_event.get('alt'):
            parts.append('Alt')
        if key_event.get('shift'):
            parts.append('Shift')
        if key_event.get('key'):
            parts.append(key_event['key'].upper())
        
        shortcut = '+'.join(parts)
        return self.registry.execute_shortcut(shortcut)


# Global command registry
_command_registry: Optional[CommandRegistry] = None


def get_command_registry() -> CommandRegistry:
    """Get the global command registry."""
    global _command_registry
    if _command_registry is None:
        _command_registry = CommandRegistry()
    return _command_registry
