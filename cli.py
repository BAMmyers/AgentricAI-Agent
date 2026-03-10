"""
AgentricAI Command Line Interface
"""
import asyncio
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import json

from agentricai_sdk import AgentricAI, AgentricAIClient


console = Console()


@click.group()
def cli():
    """AgentricAI Command Line Interface"""
    pass


@cli.command()
@click.option("--agent", default="lacy", help="Agent to use")
@click.option("--resource", default="default", help="Resource ID")
@click.option("--thread", default="cli", help="Thread ID")
def chat(agent, resource, thread):
    """Interactive chat with an agent."""
    client = AgentricAI()
    
    console.print(Panel(f"Chat with {agent}", style="bold blue"))
    console.print("Type 'exit' or 'quit' to exit\n")
    
    try:
        while True:
            try:
                user_input = console.input("[bold cyan]You:[/] ")
                
                if user_input.lower() in ("exit", "quit"):
                    console.print("[yellow]Goodbye![/]")
                    break
                
                if not user_input.strip():
                    continue
                
                console.print(f"[bold green]{agent}:[/] ", end="", flush=True)
                
                response = client.chat(user_input, agent, resource, thread)
                console.print(response)
                console.print()
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted[/]")
                break
    finally:
        client.close()


@cli.command()
@click.option("--format", type=click.Choice(["json", "table", "text"]), default="table")
def list_agents(format):
    """List available agents."""
    client = AgentricAI()
    
    try:
        agents = client.list_agents()
        
        if format == "json":
            console.print_json(data=agents)
        elif format == "table":
            table = Table(title="Available Agents", show_header=True, header_style="bold")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Model", style="yellow")
            table.add_column("Version", style="magenta")
            
            for agent in agents:
                table.add_row(
                    agent.get("id", "unknown"),
                    agent.get("name", "unknown"),
                    agent.get("model", "unknown"),
                    agent.get("version", "1.0.0")
                )
            
            console.print(table)
        else:
            for agent in agents:
                console.print(f"• {agent.get('name', agent.get('id'))}")
    finally:
        client.close()


@cli.command()
@click.option("--format", type=click.Choice(["json", "table"]), default="table")
def list_tools(format):
    """List available tools."""
    client = AgentricAI()
    
    try:
        tools = client.list_tools()
        
        if format == "json":
            console.print_json(data=tools)
        else:
            table = Table(title="Available Tools", show_header=True, header_style="bold")
            table.add_column("ID", style="cyan")
            table.add_column("Category", style="green")
            table.add_column("Status", style="yellow")
            
            for tool in tools:
                status = "✓" if tool.get("validated") else "✗"
                table.add_row(
                    tool.get("id", "unknown"),
                    tool.get("category", "general"),
                    status
                )
            
            console.print(table)
    finally:
        client.close()


@cli.command()
@click.argument("agent_id")
@click.argument("message")
@click.option("--thread", default="cli", help="Thread ID")
@click.option("--resource", default="default", help="Resource ID")
def send(agent_id, message, thread, resource):
    """Send a single message to an agent."""
    client = AgentricAI()
    
    try:
        console.print(f"[bold cyan]Sending to {agent_id}...[/]")
        response = client.chat(message, agent_id, resource, thread)
        console.print(f"\n[bold green]{agent_id}:[/]\n{response}")
    finally:
        client.close()


@cli.command()
@click.option("--resource", default="default", help="Resource ID")
@click.option("--thread", default="cli", help="Thread ID")
@click.option("--limit", default=10, help="Number of messages to show")
def history(resource, thread, limit):
    """Show conversation history."""
    client = AgentricAI()
    
    try:
        messages = client.get_memory(resource, thread)
        
        if not messages:
            console.print("[yellow]No conversation history found[/]")
            return
        
        console.print(Panel(f"Conversation History ({resource}/{thread})", style="bold blue"))
        
        for msg in messages[-limit:]:
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")
            
            if role == "USER":
                console.print(f"\n[bold cyan]{role}:[/] {content}")
            else:
                console.print(f"\n[bold green]{role}:[/] {content[:200]}...")
    finally:
        client.close()


@cli.command()
def health():
    """Check server health."""
    async def check():
        async with AgentricAIClient() as client:
            try:
                health_data = await client.get_health()
                
                table = Table(title="Server Health", show_header=True, header_style="bold")
                table.add_column("Component", style="cyan")
                table.add_column("Status", style="green")
                
                for component, status in health_data.get("components", {}).items():
                    table.add_row(component, status)
                
                console.print(table)
            except Exception as e:
                console.print(f"[red]Error: {e}[/]")
    
    asyncio.run(check())


@cli.command()
def models():
    """List available models."""
    async def list_models():
        async with AgentricAIClient() as client:
            try:
                models_list = await client.get_models()
                
                table = Table(title="Available Models", show_header=True, header_style="bold")
                table.add_column("Model", style="cyan")
                
                for model in models_list:
                    table.add_row(model)
                
                console.print(table)
            except Exception as e:
                console.print(f"[red]Error: {e}[/]")
    
    asyncio.run(list_models())


@cli.command()
@click.option("--resource", default="default", help="Resource ID")
@click.option("--thread", default="cli", help="Thread ID")
@click.option("--query", prompt=True, help="Search query")
def search_memory(resource, thread, query):
    """Search conversation memory."""
    async def search():
        async with AgentricAIClient() as client:
            try:
                results = await client.search_memory(query, "resource", resource)
                
                if not results:
                    console.print("[yellow]No results found[/]")
                    return
                
                console.print(Panel(f"Search Results for '{query}'", style="bold blue"))
                
                for i, result in enumerate(results, 1):
                    console.print(f"\n[bold]{i}. {result.get('key')}[/]")
                    console.print(f"   Value: {result.get('value')[:100]}...")
            except Exception as e:
                console.print(f"[red]Error: {e}[/]")
    
    asyncio.run(search())


@cli.command()
def config():
    """Show configuration."""
    async def show_config():
        async with AgentricAIClient() as client:
            try:
                health_data = await client.get_detailed_health()
                
                if "config" in health_data:
                    console.print_json(data=health_data["config"])
                else:
                    console.print("[yellow]No config available[/]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/]")
    
    asyncio.run(show_config())


@cli.command()
@click.option("--url", default="http://127.0.0.1:3939", help="API URL")
def info(url):
    """Get server information."""
    async def get_info():
        async with AgentricAIClient(base_url=url) as client:
            try:
                health = await client.get_health()
                models = await client.get_models()
                agents = await client.list_agents()
                tools = await client.list_tools()
                
                console.print(Panel("AgentricAI Server Information", style="bold blue"))
                console.print(f"URL: {url}")
                console.print(f"Status: {health.get('status', 'unknown')}")
                console.print(f"Version: {health.get('version', 'unknown')}")
                console.print(f"\nAgents: {len(agents)}")
                console.print(f"Tools: {len(tools)}")
                console.print(f"Models: {len(models)}")
            except Exception as e:
                console.print(f"[red]Error connecting to {url}: {e}[/]")
    
    asyncio.run(get_info())


if __name__ == "__main__":
    cli()
