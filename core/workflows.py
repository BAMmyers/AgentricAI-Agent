"""
AgentricAI Workflow System.
Defines and executes multi-step workflows.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from enum import Enum
import asyncio
import uuid


class WorkflowStatus(Enum):
    """Status of a workflow."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    """Status of a workflow step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    id: str
    name: str
    action: Callable
    dependencies: List[str] = field(default_factory=list)
    condition: Optional[Callable] = None
    timeout: int = 300
    retry_count: int = 0
    max_retries: int = 3
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class Workflow:
    """
    A workflow definition.
    
    Attributes:
        id: Unique workflow identifier
        name: Human-readable name
        description: Workflow description
        steps: List of workflow steps
        variables: Workflow-level variables
        status: Current workflow status
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    steps: List[WorkflowStep] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_step: Optional[str] = None
    results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class WorkflowEngine:
    """
    Engine for executing workflows.
    
    Features:
    - Step dependencies
    - Conditional execution
    - Retry logic
    - Timeout handling
    - Variable passing between steps
    """
    
    def __init__(self):
        """Initialize the workflow engine."""
        self._workflows: Dict[str, Workflow] = {}
        self._running: Dict[str, asyncio.Task] = {}
    
    def create_workflow(
        self,
        name: str,
        description: str = "",
        steps: List[WorkflowStep] = None,
        variables: Dict[str, Any] = None
    ) -> Workflow:
        """
        Create a new workflow.
        
        Args:
            name: Workflow name
            description: Workflow description
            steps: List of workflow steps
            variables: Initial variables
            
        Returns:
            The created workflow
        """
        workflow = Workflow(
            name=name,
            description=description,
            steps=steps or [],
            variables=variables or {}
        )
        self._workflows[workflow.id] = workflow
        return workflow
    
    def add_step(
        self,
        workflow: Workflow,
        step_id: str,
        name: str,
        action: Callable,
        dependencies: List[str] = None,
        condition: Callable = None,
        timeout: int = 300,
        max_retries: int = 3
    ) -> WorkflowStep:
        """
        Add a step to a workflow.
        
        Args:
            workflow: The workflow to add to
            step_id: Unique step identifier
            name: Step name
            action: Async callable to execute
            dependencies: List of step IDs that must complete first
            condition: Optional condition function
            timeout: Step timeout in seconds
            max_retries: Maximum retry attempts
            
        Returns:
            The created step
        """
        step = WorkflowStep(
            id=step_id,
            name=name,
            action=action,
            dependencies=dependencies or [],
            condition=condition,
            timeout=timeout,
            max_retries=max_retries
        )
        workflow.steps.append(step)
        return step
    
    def _get_ready_steps(self, workflow: Workflow) -> List[WorkflowStep]:
        """Get steps that are ready to execute."""
        ready = []
        completed_ids = {
            s.id for s in workflow.steps 
            if s.status == StepStatus.COMPLETED
        }
        
        for step in workflow.steps:
            if step.status != StepStatus.PENDING:
                continue
            
            # Check dependencies
            if not all(dep in completed_ids for dep in step.dependencies):
                continue
            
            # Check condition
            if step.condition and not step.condition(workflow.variables):
                step.status = StepStatus.SKIPPED
                continue
            
            ready.append(step)
        
        return ready
    
    async def _execute_step(self, workflow: Workflow, step: WorkflowStep) -> bool:
        """
        Execute a single step.
        
        Returns:
            True if step completed successfully
        """
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now()
        workflow.current_step = step.id
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                step.action(workflow.variables),
                timeout=step.timeout
            )
            
            step.result = result
            step.status = StepStatus.COMPLETED
            step.completed_at = datetime.now()
            
            # Store result in workflow
            workflow.results[step.id] = result
            
            # Update variables if result is a dict
            if isinstance(result, dict):
                workflow.variables.update(result)
            
            return True
            
        except asyncio.TimeoutError:
            step.error = f"Step timed out after {step.timeout} seconds"
            step.status = StepStatus.FAILED
            return False
            
        except Exception as e:
            step.error = str(e)
            step.retry_count += 1
            
            if step.retry_count < step.max_retries:
                # Retry
                step.status = StepStatus.PENDING
                return await self._execute_step(workflow, step)
            
            step.status = StepStatus.FAILED
            return False
    
    async def execute(self, workflow_id: str) -> Dict[str, Any]:
        """
        Execute a workflow.
        
        Args:
            workflow_id: The workflow to execute
            
        Returns:
            Execution results
        """
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.now()
        
        try:
            while True:
                # Get ready steps
                ready_steps = self._get_ready_steps(workflow)
                
                if not ready_steps:
                    # Check if all steps are done
                    all_done = all(
                        s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED, StepStatus.FAILED)
                        for s in workflow.steps
                    )
                    
                    if all_done:
                        break
                    
                    # Wait and check again
                    await asyncio.sleep(0.1)
                    continue
                
                # Execute ready steps (can be parallelized)
                for step in ready_steps:
                    success = await self._execute_step(workflow, step)
                    
                    if not success and step.status == StepStatus.FAILED:
                        workflow.errors.append(f"Step {step.id} failed: {step.error}")
            
            # Determine final status
            failed_steps = [s for s in workflow.steps if s.status == StepStatus.FAILED]
            
            if failed_steps:
                workflow.status = WorkflowStatus.FAILED
            else:
                workflow.status = WorkflowStatus.COMPLETED
            
            workflow.completed_at = datetime.now()
            workflow.current_step = None
            
            return {
                "workflow_id": workflow.id,
                "status": workflow.status.value,
                "results": workflow.results,
                "errors": workflow.errors,
                "duration": (
                    workflow.completed_at - workflow.started_at
                ).total_seconds() if workflow.completed_at and workflow.started_at else 0
            }
            
        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.errors.append(str(e))
            raise
    
    async def execute_async(self, workflow_id: str) -> asyncio.Task:
        """Execute a workflow in the background."""
        task = asyncio.create_task(self.execute(workflow_id))
        self._running[workflow_id] = task
        return task
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow by ID."""
        return self._workflows.get(workflow_id)
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all workflows."""
        return [
            {
                "id": w.id,
                "name": w.name,
                "status": w.status.value,
                "step_count": len(w.steps),
                "created_at": w.created_at.isoformat()
            }
            for w in self._workflows.values()
        ]
    
    def cancel(self, workflow_id: str) -> bool:
        """Cancel a running workflow."""
        if workflow_id in self._running:
            self._running[workflow_id].cancel()
            workflow = self._workflows.get(workflow_id)
            if workflow:
                workflow.status = WorkflowStatus.CANCELLED
            return True
        return False


# Predefined workflow templates
def create_chat_workflow(engine: WorkflowEngine, agent_id: str, message: str) -> Workflow:
    """Create a standard chat workflow."""
    workflow = engine.create_workflow(
        name="Chat Workflow",
        description="Standard chat processing workflow"
    )
    
    workflow.variables["agent_id"] = agent_id
    workflow.variables["message"] = message
    
    return workflow


# Global workflow engine
_workflow_engine: Optional[WorkflowEngine] = None


def get_workflow_engine() -> WorkflowEngine:
    """Get the global workflow engine instance."""
    global _workflow_engine
    if _workflow_engine is None:
        _workflow_engine = WorkflowEngine()
    return _workflow_engine
