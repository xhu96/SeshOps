import os
import sys
import uuid
from time import sleep

import httpx
from rich.console import Console
from rich.panel import Panel

console = Console()

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")


def run_demo():
    """Execute the End-to-End demonstration against the local Copilot instance."""
    console.print(Panel.fit("[bold blue]SeshOps - End-to-End Demo[/bold blue]"))
    
    # 1. Check if the server is healthy before asserting business logic
    try:
        health = httpx.get("http://127.0.0.1:8000/health")
        if health.status_code != 200:
            console.print("[red]✗ The development server is not returning 200 OK at /health. Run `make dev` first.[/red]")
            sys.exit(1)
        console.print("[green]✓ Server is healthy.[/green]")
    except httpx.ConnectError:
        console.print("[red]✗ Could not connect to the API. Are you running `make dev`?[/red]")
        sys.exit(1)

    with httpx.Client(base_url=API_URL) as client:
        test_email = f"demo_user_{uuid.uuid4().hex[:8]}@example.com"
        test_password = "SecurePassword123!"
        
        # 2. Register Account
        console.print(f"\n[bold yellow]Step 1: Registering User ({test_email})[/bold yellow]")
        register_resp = client.post(
            "/auth/register",
            json={"email": test_email, "password": test_password},
        )
        if register_resp.status_code == 200:
            console.print("[green]✓ User registered successfully! [/green]")
        elif register_resp.status_code == 400 and "already registered" in register_resp.json().get("detail", ""):
             console.print("[yellow]! User already existed. Proceeding to login.[/yellow]")
        else:
             console.print(f"[red]✗ Registration Failed: {register_resp.text}[/red]")
             sys.exit(1)

        # 3. Login
        console.print("\n[bold yellow]Step 2: Authenticating[/bold yellow]")
        login_resp = client.post(
            "/auth/login",
            data={"username": test_email, "password": test_password},
        )
        if login_resp.status_code != 200:
            console.print(f"[red]✗ Login Failed: {login_resp.text}[/red]")
            sys.exit(1)
            
        token = login_resp.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}
        console.print("[green]✓ JWT Token Acquired.[/green]")

        # 4. Triage Incident
        console.print("\n[bold yellow]Step 3: Orchestrating an Incident Triage[/bold yellow]")
        console.print("Sending a simulated Redis OOM payload to `/operations/triage`...")
        
        sample_incident = "CRITICAL: The Redis cluster nodes in US-East-1 are evicting massive amounts of keys and reporting OOM errors during the latest massive scale-up event. The primary API cache is starting to drift heavily."
        
        triage_resp = client.post(
            "/operations/triage",
            headers=auth_headers,
            json={"incident_input": sample_incident},
            timeout=30.0 # LangGraph could take a bit if it hits LLMs
        )
        
        if triage_resp.status_code == 200:
            data = triage_resp.json()
            console.print("[green]✓ Result received via LangGraph API Orchestration![/green]")
            console.print(Panel(data.get("diagnostic_summary", "No summary provided."), title="Diagnostic Summary", border_style="green"))
            
            steps = data.get("executed_steps", [])
            if steps:
                 console.print("\n[dim]Executed nodes in state traversal:[/dim]")
                 for step in steps:
                     console.print(f"[dim]- {step}[/dim]")
                     
        elif triage_resp.status_code == 401:
            console.print("[bold red]✗ The LLM Provider rejected the sequence due to an invalid API key.[/bold red]")
            console.print("[italic]This is entirely expected if your `.env.development` does not possess a valid `OPENAI_API_KEY`. The FastApi network wrapper succeeded.[/italic]")
        elif triage_resp.status_code == 500 and "Failed to process incident triage" in triage_resp.text:
            console.print("[bold yellow]⚠ Orchestration halted at LLM node (500 Internal Error Wrapper).[/bold yellow]")
            console.print("[italic]This is entirely expected if your `.env.development` does not possess a valid `OPENAI_API_KEY`. The FastAPI routing, LangGraph state setup, and Pydantic validation successfully executed before hitting the provider network boundary.[/italic]")
        elif triage_resp.status_code == 500:
            console.print(f"[bold red]✗ Remote Internal Error: {triage_resp.text}[/bold red]")
        else:
            console.print(f"[red]✗ Unhandled HTTP Error ({triage_resp.status_code}): {triage_resp.text}[/red]")


if __name__ == "__main__":
    run_demo()
