"""
AgentricAI - Skills System
Agent skills for specialized capabilities and workflows.
"""
import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field


@dataclass
class SkillParameter:
    """A parameter for a skill."""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None


@dataclass
class Skill:
    """A skill that can be assigned to agents."""
    id: str
    name: str
    description: str
    category: str
    parameters: List[SkillParameter] = field(default_factory=list)
    handler: Optional[Callable] = None
    prompt_template: str = ""
    tools_required: List[str] = field(default_factory=list)
    examples: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert skill to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'parameters': [
                {'name': p.name, 'type': p.type, 'description': p.description, 
                 'required': p.required, 'default': p.default}
                for p in self.parameters
            ],
            'prompt_template': self.prompt_template,
            'tools_required': self.tools_required,
            'examples': self.examples
        }
    
    def generate_prompt(self, **kwargs) -> str:
        """Generate a prompt for this skill."""
        prompt = self.prompt_template
        for key, value in kwargs.items():
            prompt = prompt.replace(f"{{{key}}}", str(value))
        return prompt


class SkillRegistry:
    """Registry of all available skills."""
    
    def __init__(self, skills_dir: str = None):
        self.skills: Dict[str, Skill] = {}
        self.categories: Dict[str, List[str]] = {}
        self.skills_dir = Path(skills_dir) if skills_dir else Path(__file__).parent / 'skills'
        
        # Register built-in skills
        self._register_builtin_skills()
        
        # Load skills from directory
        self.load_skills()
    
    def _register_builtin_skills(self):
        """Register built-in skills."""
        
        # Code Generation Skill
        self.register_skill(Skill(
            id='code_generation',
            name='Code Generation',
            description='Generate code based on requirements',
            category='coding',
            parameters=[
                SkillParameter('language', 'string', 'Programming language', True),
                SkillParameter('requirements', 'string', 'Code requirements', True),
                SkillParameter('style', 'string', 'Code style preferences', False, 'clean')
            ],
            prompt_template="""Generate {language} code that meets these requirements:
{requirements}

Style: {style}

Provide clean, well-documented code with error handling.""",
            tools_required=['code_execute'],
            examples=[
                {'language': 'python', 'requirements': 'A function to calculate fibonacci numbers'}
            ]
        ))
        
        # Code Review Skill
        self.register_skill(Skill(
            id='code_review',
            name='Code Review',
            description='Review code for quality, bugs, and improvements',
            category='coding',
            parameters=[
                SkillParameter('code', 'string', 'Code to review', True),
                SkillParameter('focus', 'string', 'Review focus area', False, 'general')
            ],
            prompt_template="""Review the following code for {focus}:

```
{code}
```

Provide:
1. Issues found
2. Suggestions for improvement
3. Best practices recommendations""",
            tools_required=['code_execute'],
            examples=[
                {'code': 'def add(a,b): return a+b', 'focus': 'error handling'}
            ]
        ))
        
        # Data Analysis Skill
        self.register_skill(Skill(
            id='data_analysis',
            name='Data Analysis',
            description='Analyze data and generate insights',
            category='data',
            parameters=[
                SkillParameter('data', 'string', 'Data to analyze', True),
                SkillParameter('analysis_type', 'string', 'Type of analysis', True)
            ],
            prompt_template="""Analyze the following data for {analysis_type}:

{data}

Provide:
1. Key findings
2. Statistical insights
3. Recommendations""",
            tools_required=['code_execute'],
            examples=[
                {'data': 'sales.csv content', 'analysis_type': 'trend analysis'}
            ]
        ))
        
        # Document Generation Skill
        self.register_skill(Skill(
            id='document_generation',
            name='Document Generation',
            description='Generate documentation',
            category='documentation',
            parameters=[
                SkillParameter('content', 'string', 'Content to document', True),
                SkillParameter('doc_type', 'string', 'Type of documentation', True),
                SkillParameter('format', 'string', 'Output format', False, 'markdown')
            ],
            prompt_template="""Generate {doc_type} documentation in {format} format for:

{content}

Include:
1. Overview
2. Details
3. Examples
4. References""",
            tools_required=['file_write'],
            examples=[
                {'content': 'API endpoints', 'doc_type': 'API reference', 'format': 'markdown'}
            ]
        ))
        
        # Research Skill
        self.register_skill(Skill(
            id='research',
            name='Research',
            description='Research a topic and compile findings',
            category='research',
            parameters=[
                SkillParameter('topic', 'string', 'Topic to research', True),
                SkillParameter('depth', 'string', 'Research depth', False, 'comprehensive')
            ],
            prompt_template="""Research the topic: {topic}

Depth: {depth}

Provide:
1. Overview
2. Key findings
3. Sources
4. Recommendations""",
            tools_required=['web_search'],
            examples=[
                {'topic': 'LLM architectures', 'depth': 'technical'}
            ]
        ))
        
        # Problem Solving Skill
        self.register_skill(Skill(
            id='problem_solving',
            name='Problem Solving',
            description='Analyze and solve complex problems',
            category='reasoning',
            parameters=[
                SkillParameter('problem', 'string', 'Problem description', True),
                SkillParameter('constraints', 'string', 'Constraints to consider', False, '')
            ],
            prompt_template="""Analyze and solve the following problem:

{problem}

Constraints: {constraints}

Provide:
1. Problem analysis
2. Possible solutions
3. Recommended approach
4. Implementation steps""",
            tools_required=['code_execute', 'memory_store'],
            examples=[
                {'problem': 'Optimize database queries', 'constraints': 'Must maintain ACID compliance'}
            ]
        ))
        
        # Memory Management Skill
        self.register_skill(Skill(
            id='memory_management',
            name='Memory Management',
            description='Manage agent memory and context',
            category='memory',
            parameters=[
                SkillParameter('action', 'string', 'Memory action (store/retrieve/summarize)', True),
                SkillParameter('content', 'string', 'Content to store/retrieve', False, '')
            ],
            prompt_template="""Perform memory action: {action}

Content: {content}

Process the memory operation appropriately.""",
            tools_required=['memory_store', 'memory_retrieve'],
            examples=[
                {'action': 'store', 'content': 'User prefers dark theme'}
            ]
        ))
    
    def register_skill(self, skill: Skill):
        """Register a skill."""
        self.skills[skill.id] = skill
        
        # Add to category
        if skill.category not in self.categories:
            self.categories[skill.category] = []
        self.categories[skill.category].append(skill.id)
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Get a skill by ID."""
        return self.skills.get(skill_id)
    
    def list_skills(self, category: str = None) -> List[Dict]:
        """List all skills, optionally filtered by category."""
        skills = []
        for skill in self.skills.values():
            if category is None or skill.category == category:
                skills.append(skill.to_dict())
        return skills
    
    def get_categories(self) -> List[str]:
        """Get all skill categories."""
        return list(self.categories.keys())
    
    def load_skills(self):
        """Load skills from directory."""
        if not self.skills_dir.exists():
            self.skills_dir.mkdir(parents=True, exist_ok=True)
            return
        
        for file in self.skills_dir.glob('*.json'):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                
                skill = Skill(
                    id=data.get('id', file.stem),
                    name=data.get('name', file.stem),
                    description=data.get('description', ''),
                    category=data.get('category', 'custom'),
                    parameters=[
                        SkillParameter(**p) for p in data.get('parameters', [])
                    ],
                    prompt_template=data.get('prompt_template', ''),
                    tools_required=data.get('tools_required', []),
                    examples=data.get('examples', [])
                )
                
                self.register_skill(skill)
                
            except Exception as e:
                print(f"Error loading skill {file}: {e}")


# Global skill registry instance
_skill_registry = None

def get_skill_registry() -> SkillRegistry:
    """Get the global skill registry instance."""
    global _skill_registry
    if _skill_registry is None:
        _skill_registry = SkillRegistry()
    return _skill_registry
