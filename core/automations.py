"""
AgentricAI Automation System.
Provides automation rules and triggers for automated actions.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import re


class TriggerType(Enum):
    """Types of automation triggers."""
    SCHEDULE = "schedule"
    EVENT = "event"
    WEBHOOK = "webhook"
    CONDITION = "condition"
    MANUAL = "manual"


class ActionType(Enum):
    """Types of automation actions."""
    CHAT = "chat"
    TOOL = "tool"
    WORKFLOW = "workflow"
    WEBHOOK = "webhook"
    NOTIFICATION = "notification"
    LOG = "log"


@dataclass
class Trigger:
    """Automation trigger definition."""
    type: TriggerType
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class Action:
    """Automation action definition."""
    type: ActionType
    config: Dict[str, Any] = field(default_factory=dict)
    order: int = 0


@dataclass
class AutomationRule:
    """
    An automation rule with triggers and actions.
    
    Attributes:
        id: Unique rule identifier
        name: Human-readable name
        description: Rule description
        triggers: List of triggers that can activate this rule
        actions: List of actions to execute
        enabled: Whether the rule is active
        conditions: Optional conditions that must be met
    """
    id: str = field(default_factory=lambda: str(__import__('uuid').uuid4()))
    name: str = ""
    description: str = ""
    triggers: List[Trigger] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    enabled: bool = True
    conditions: List[Callable] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0


@dataclass
class AutomationExecution:
    """Record of an automation execution."""
    id: str
    rule_id: str
    triggered_at: datetime
    trigger_type: TriggerType
    trigger_data: Dict[str, Any]
    actions_executed: List[Dict[str, Any]]
    status: str
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class AutomationEngine:
    """
    Engine for managing and executing automation rules.
    
    Features:
    - Multiple trigger types (schedule, event, webhook, condition)
    - Action chaining
    - Condition evaluation
    - Execution history
    - Rule management
    """
    
    def __init__(self):
        """Initialize the automation engine."""
        self._rules: Dict[str, AutomationRule] = {}
        self._executions: List[AutomationExecution] = []
        self._schedulers: Dict[str, asyncio.Task] = {}
        self._event_handlers: Dict[str, List[str]] = {}  # event_type -> rule_ids
        self._running = False
    
    def create_rule(
        self,
        name: str,
        description: str = "",
        triggers: List[Trigger] = None,
        actions: List[Action] = None,
        conditions: List[Callable] = None,
        enabled: bool = True
    ) -> AutomationRule:
        """
        Create a new automation rule.
        
        Args:
            name: Rule name
            description: Rule description
            triggers: List of triggers
            actions: List of actions
            conditions: Optional conditions
            enabled: Whether rule is active
            
        Returns:
            The created rule
        """
        rule = AutomationRule(
            name=name,
            description=description,
            triggers=triggers or [],
            actions=actions or [],
            conditions=conditions or [],
            enabled=enabled
        )
        
        self._rules[rule.id] = rule
        self._register_rule_triggers(rule)
        
        return rule
    
    def _register_rule_triggers(self, rule: AutomationRule) -> None:
        """Register trigger handlers for a rule."""
        for trigger in rule.triggers:
            if trigger.type == TriggerType.EVENT:
                event_type = trigger.config.get("event_type", "*")
                if event_type not in self._event_handlers:
                    self._event_handlers[event_type] = []
                self._event_handlers[event_type].append(rule.id)
    
    def update_rule(self, rule_id: str, **kwargs) -> Optional[AutomationRule]:
        """
        Update an existing rule.
        
        Args:
            rule_id: Rule to update
            **kwargs: Fields to update
            
        Returns:
            Updated rule or None if not found
        """
        if rule_id not in self._rules:
            return None
        
        rule = self._rules[rule_id]
        
        for key, value in kwargs.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        
        rule.updated_at = datetime.now()
        return rule
    
    def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule."""
        if rule_id in self._rules:
            # Unregister triggers
            rule = self._rules[rule_id]
            for trigger in rule.triggers:
                if trigger.type == TriggerType.EVENT:
                    event_type = trigger.config.get("event_type", "*")
                    if event_type in self._event_handlers:
                        self._event_handlers[event_type] = [
                            r for r in self._event_handlers[event_type] 
                            if r != rule_id
                        ]
            
            # Cancel any scheduled tasks
            if rule_id in self._schedulers:
                self._schedulers[rule_id].cancel()
                del self._schedulers[rule_id]
            
            del self._rules[rule_id]
            return True
        return False
    
    def get_rule(self, rule_id: str) -> Optional[AutomationRule]:
        """Get a rule by ID."""
        return self._rules.get(rule_id)
    
    def list_rules(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """List all rules."""
        rules = list(self._rules.values())
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        
        return [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "enabled": r.enabled,
                "trigger_count": len(r.triggers),
                "action_count": len(r.actions),
                "last_triggered": r.last_triggered.isoformat() if r.last_triggered else None,
                "trigger_count_total": r.trigger_count
            }
            for r in rules
        ]
    
    async def evaluate_conditions(
        self,
        rule: AutomationRule,
        context: Dict[str, Any]
    ) -> bool:
        """
        Evaluate rule conditions.
        
        Args:
            rule: The rule to evaluate
            context: Evaluation context
            
        Returns:
            True if all conditions pass
        """
        for condition in rule.conditions:
            try:
                if callable(condition):
                    result = condition(context)
                    if asyncio.iscoroutine(result):
                        result = await result
                    if not result:
                        return False
            except Exception as e:
                print(f"[Automation] Condition evaluation error: {e}")
                return False
        
        return True
    
    async def execute_actions(
        self,
        rule: AutomationRule,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Execute rule actions.
        
        Args:
            rule: The rule to execute
            context: Execution context
            
        Returns:
            List of action results
        """
        results = []
        
        # Sort actions by order
        sorted_actions = sorted(rule.actions, key=lambda a: a.order)
        
        for action in sorted_actions:
            try:
                result = await self._execute_action(action, context)
                results.append({
                    "action_type": action.type.value,
                    "status": "success",
                    "result": result
                })
                
                # Update context with result
                context["last_action_result"] = result
                
            except Exception as e:
                results.append({
                    "action_type": action.type.value,
                    "status": "error",
                    "error": str(e)
                })
                break  # Stop on error
        
        return results
    
    async def _execute_action(
        self,
        action: Action,
        context: Dict[str, Any]
    ) -> Any:
        """Execute a single action."""
        if action.type == ActionType.CHAT:
            return await self._execute_chat_action(action, context)
        elif action.type == ActionType.TOOL:
            return await self._execute_tool_action(action, context)
        elif action.type == ActionType.WORKFLOW:
            return await self._execute_workflow_action(action, context)
        elif action.type == ActionType.LOG:
            return await self._execute_log_action(action, context)
        else:
            raise ValueError(f"Unknown action type: {action.type}")
    
    async def _execute_chat_action(self, action: Action, context: Dict[str, Any]) -> Any:
        """Execute a chat action."""
        from core.agent_loader import AgentLoader
        from core.memory_router import MemoryRouter
        
        agent_id = action.config.get("agent_id", "lacy")
        message = action.config.get("message", "")
        
        # Interpolate variables
        for key, value in context.items():
            message = message.replace(f"{{{key}}}", str(value))
        
        # Get agent and generate response
        loader = AgentLoader()
        memory_router = MemoryRouter()
        
        agent = loader.get_agent(agent_id)
        memory_context = memory_router.read_memory(
            context.get("resource", "default"),
            context.get("thread", "default")
        )
        
        return await agent.generate_response_async(
            text=message,
            memory_context=memory_context,
            resource=context.get("resource", "default"),
            thread=context.get("thread", "default")
        )
    
    async def _execute_tool_action(self, action: Action, context: Dict[str, Any]) -> Any:
        """Execute a tool action."""
        from core.tool_loader import ToolLoader
        
        tool_id = action.config.get("tool_id")
        parameters = action.config.get("parameters", {})
        
        # Interpolate variables in parameters
        for key, value in parameters.items():
            if isinstance(value, str):
                for ctx_key, ctx_value in context.items():
                    value = value.replace(f"{{{ctx_key}}}", str(ctx_value))
                parameters[key] = value
        
        loader = ToolLoader()
        return loader.execute_tool(tool_id, parameters)
    
    async def _execute_workflow_action(self, action: Action, context: Dict[str, Any]) -> Any:
        """Execute a workflow action."""
        from core.workflows import get_workflow_engine
        
        workflow_id = action.config.get("workflow_id")
        engine = get_workflow_engine()
        
        return await engine.execute(workflow_id)
    
    async def _execute_log_action(self, action: Action, context: Dict[str, Any]) -> Any:
        """Execute a log action."""
        message = action.config.get("message", "")
        level = action.config.get("level", "info")
        
        # Interpolate variables
        for key, value in context.items():
            message = message.replace(f"{{{key}}}", str(value))
        
        print(f"[Automation] [{level.upper()}] {message}")
        return {"logged": True, "message": message}
    
    async def trigger(
        self,
        trigger_type: TriggerType,
        trigger_data: Dict[str, Any] = None,
        context: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Trigger automation rules.
        
        Args:
            trigger_type: Type of trigger
            trigger_data: Data from the trigger
            context: Additional context
            
        Returns:
            List of execution results
        """
        results = []
        trigger_data = trigger_data or {}
        context = context or {}
        context.update(trigger_data)
        
        # Find matching rules
        matching_rules = []
        
        for rule in self._rules.values():
            if not rule.enabled:
                continue
            
            for trigger in rule.triggers:
                if trigger.type == trigger_type:
                    if await self._matches_trigger(trigger, trigger_data):
                        matching_rules.append(rule)
                        break
        
        # Execute matching rules
        for rule in matching_rules:
            try:
                # Evaluate conditions
                if not await self.evaluate_conditions(rule, context):
                    continue
                
                # Execute actions
                action_results = await self.execute_actions(rule, context)
                
                # Update rule stats
                rule.last_triggered = datetime.now()
                rule.trigger_count += 1
                
                # Record execution
                execution = AutomationExecution(
                    id=str(__import__('uuid').uuid4()),
                    rule_id=rule.id,
                    triggered_at=datetime.now(),
                    trigger_type=trigger_type,
                    trigger_data=trigger_data,
                    actions_executed=action_results,
                    status="completed",
                    completed_at=datetime.now()
                )
                self._executions.append(execution)
                
                results.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "status": "success",
                    "actions": action_results
                })
                
            except Exception as e:
                results.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "status": "error",
                    "error": str(e)
                })
        
        return results
    
    async def _matches_trigger(
        self,
        trigger: Trigger,
        trigger_data: Dict[str, Any]
    ) -> bool:
        """Check if trigger matches the data."""
        if trigger.type == TriggerType.EVENT:
            event_type = trigger.config.get("event_type", "*")
            if event_type != "*":
                if trigger_data.get("event_type") != event_type:
                    return False
            
            # Check pattern matching
            pattern = trigger.config.get("pattern")
            if pattern:
                data_str = str(trigger_data)
                if not re.search(pattern, data_str):
                    return False
        
        elif trigger.type == TriggerType.CONDITION:
            condition_fn = trigger.config.get("condition")
            if condition_fn and callable(condition_fn):
                if not condition_fn(trigger_data):
                    return False
        
        return True
    
    async def start(self) -> None:
        """Start the automation engine."""
        self._running = True
        
        # Start scheduled triggers
        for rule in self._rules.values():
            await self._schedule_rule(rule)
    
    async def stop(self) -> None:
        """Stop the automation engine."""
        self._running = False
        
        # Cancel all schedulers
        for task in self._schedulers.values():
            task.cancel()
        
        self._schedulers.clear()
    
    async def _schedule_rule(self, rule: AutomationRule) -> None:
        """Schedule a rule's time-based triggers."""
        for trigger in rule.triggers:
            if trigger.type == TriggerType.SCHEDULE:
                interval = trigger.config.get("interval_seconds", 60)
                
                async def run_scheduled():
                    while self._running:
                        await asyncio.sleep(interval)
                        await self.trigger(
                            TriggerType.SCHEDULE,
                            {"rule_id": rule.id}
                        )
                
                self._schedulers[rule.id] = asyncio.create_task(run_scheduled())
    
    def get_executions(self, rule_id: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get execution history."""
        executions = self._executions
        
        if rule_id:
            executions = [e for e in executions if e.rule_id == rule_id]
        
        return [
            {
                "id": e.id,
                "rule_id": e.rule_id,
                "triggered_at": e.triggered_at.isoformat(),
                "trigger_type": e.trigger_type.value,
                "status": e.status,
                "actions_count": len(e.actions_executed),
                "error": e.error
            }
            for e in executions[-limit:]
        ]


# Global automation engine
_automation_engine: Optional[AutomationEngine] = None


def get_automation_engine() -> AutomationEngine:
    """Get the global automation engine instance."""
    global _automation_engine
    if _automation_engine is None:
        _automation_engine = AutomationEngine()
    return _automation_engine
