"""Seed script - populates the database with the acceptance demo workspace."""

import json
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import create_db_and_tables, engine
from app.models import (
    Workspace, Document, SandboxCredential,
    DemoRecipe, PolicyRule,
)
from app.services.encryption import encrypt
from app.retrieval.ingest import ingest_document
from sqlmodel import Session

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "acceptance" / "acme-crm-pro"
SALESHANDY_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "acceptance" / "saleshandy-demo"


def _load_fixture(filename: str, fixture_dir: Path = FIXTURE_DIR) -> str:
    path = fixture_dir / filename
    return path.read_text(encoding="utf-8")


def seed():
    """Create sample workspace, documents, credentials, recipes, and policies."""
    create_db_and_tables()

    with Session(engine) as db:
        # Check if already seeded
        from sqlmodel import select
        existing = db.exec(select(Workspace)).first()
        if existing:
            print("Database already has data. Run 'make db-reset' to start fresh.")
            return

        print("Seeding database...")

        # 1. Create workspace
        workspace = Workspace(
            name="Acme CRM Pro",
            description="Demo workspace for Acme CRM Pro - a modern B2B customer relationship management platform",
            product_url="http://localhost:9090",
            allowed_domains="localhost,127.0.0.1",
            browser_auth_mode="credentials",
            public_token="demo-acme-crm-001",
        )
        db.add(workspace)
        db.commit()
        db.refresh(workspace)
        print(f"  Created workspace: {workspace.name} (token: {workspace.public_token})")

        # 2. Upload documents
        docs_content = [
            {
                "filename": "product-overview.md",
                "file_type": "md",
                "content": _load_fixture("product-overview.md"),
            },
            {
                "filename": "contacts-and-import.md",
                "file_type": "md",
                "content": _load_fixture("contacts-and-import.md"),
            },
            {
                "filename": "reporting-and-analytics.md",
                "file_type": "md",
                "content": _load_fixture("reporting-and-analytics.md"),
            },
            {
                "filename": "commercial-boundaries.md",
                "file_type": "md",
                "content": _load_fixture("commercial-boundaries.md"),
            },
        ]

        for doc_data in docs_content:
            doc = Document(
                workspace_id=workspace.id,
                filename=doc_data["filename"],
                file_type=doc_data["file_type"],
                content_text=doc_data["content"],
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            num_chunks = ingest_document(db, doc, content_override=doc_data["content"])
            print(f"  Ingested document: {doc.filename} ({num_chunks} chunks)")

        # 3. Add sandbox credentials (encrypted)
        creds = [
            {"label": "demo-user-1", "username": "demo@acmecrm.com", "password": "demo2024!"},
            {"label": "demo-user-2", "username": "demo2@acmecrm.com", "password": "demo2024!"},
        ]
        for cred_data in creds:
            cred = SandboxCredential(
                workspace_id=workspace.id,
                label=cred_data["label"],
                login_url="http://localhost:9090/login",
                username_encrypted=encrypt(cred_data["username"]),
                password_encrypted=encrypt(cred_data["password"]),
            )
            db.add(cred)
            print(f"  Added credential: {cred_data['label']}")
        db.commit()

        # 4. Create demo recipes
        recipes = [
            {
                "name": "Login and Navigate to Dashboard",
                "description": "Log into the CRM and show the main dashboard overview",
                "trigger_phrases": "dashboard,overview,main page,home,log in,start",
                "priority": 5,
                "steps": [
                    {"action": "narrate", "value": "Let me log in and show you the main dashboard.", "wait_ms": 500},
                    {"action": "navigate", "target": "http://localhost:9090/dashboard", "description": "Navigating to the dashboard", "wait_ms": 2000},
                    {"action": "screenshot", "description": "Here's the main dashboard view", "wait_ms": 1000},
                    {"action": "narrate", "value": "This is the main dashboard where you can see your sales pipeline, revenue forecasts, and team activity at a glance.", "wait_ms": 500},
                ],
            },
            {
                "name": "Search for a Record",
                "description": "Demonstrate the global search functionality",
                "trigger_phrases": "search,find,look up,locate,query",
                "priority": 4,
                "steps": [
                    {"action": "narrate", "value": "I'll show you how the search works.", "wait_ms": 500},
                    {"action": "navigate", "target": "http://localhost:9090/search", "description": "Opening the search page", "wait_ms": 1500},
                    {"action": "type", "target": "input[name='search']", "value": "Acme Corp", "description": "Searching for 'Acme Corp'", "wait_ms": 1500},
                    {"action": "screenshot", "description": "Here are the search results", "wait_ms": 1000},
                    {"action": "narrate", "value": "The search finds matches across contacts, companies, and deals. You can filter by type and date range.", "wait_ms": 500},
                ],
            },
            {
                "name": "Create a New Record",
                "description": "Walk through creating a new contact in the CRM",
                "trigger_phrases": "create,new,add,make,register,new contact,new record",
                "priority": 4,
                "steps": [
                    {"action": "narrate", "value": "Let me show you how to create a new contact.", "wait_ms": 500},
                    {"action": "navigate", "target": "http://localhost:9090/contacts/new", "description": "Opening the new contact form", "wait_ms": 1500},
                    {"action": "type", "target": "input[name='firstName']", "value": "Jane", "description": "Entering first name", "wait_ms": 800},
                    {"action": "type", "target": "input[name='lastName']", "value": "Smith", "description": "Entering last name", "wait_ms": 800},
                    {"action": "type", "target": "input[name='email']", "value": "jane.smith@example.com", "description": "Entering email", "wait_ms": 800},
                    {"action": "type", "target": "input[name='company']", "value": "TechStart Inc", "description": "Entering company name", "wait_ms": 800},
                    {"action": "screenshot", "description": "Here's the filled out form", "wait_ms": 1000},
                    {"action": "narrate", "value": "After filling in the details, you'd click Save to create the contact. The CRM supports custom fields too.", "wait_ms": 500},
                ],
            },
            {
                "name": "Edit an Existing Record",
                "description": "Show how to find and edit a contact record",
                "trigger_phrases": "edit,update,modify,change,existing record",
                "priority": 3,
                "steps": [
                    {"action": "narrate", "value": "I'll demonstrate editing an existing contact.", "wait_ms": 500},
                    {"action": "navigate", "target": "http://localhost:9090/contacts", "description": "Opening the contacts list", "wait_ms": 1500},
                    {"action": "screenshot", "description": "Here's the contacts list", "wait_ms": 1000},
                    {"action": "click", "target": ".contact-row:first-child", "description": "Opening the first contact", "wait_ms": 1500},
                    {"action": "click", "target": "button.edit-btn", "description": "Clicking edit", "wait_ms": 1000},
                    {"action": "screenshot", "description": "Now in edit mode - you can modify any field", "wait_ms": 1000},
                    {"action": "narrate", "value": "You can edit any field and the changes are saved immediately. There's also a full audit history of all changes.", "wait_ms": 500},
                ],
            },
            {
                "name": "Show Reporting and Analytics",
                "description": "Tour the analytics and reporting dashboard",
                "trigger_phrases": "report,analytics,metrics,data,insights,performance,numbers,statistics",
                "priority": 4,
                "steps": [
                    {"action": "narrate", "value": "Let me show you the reporting and analytics suite.", "wait_ms": 500},
                    {"action": "navigate", "target": "http://localhost:9090/analytics", "description": "Opening the analytics page", "wait_ms": 2000},
                    {"action": "screenshot", "description": "This is the analytics overview", "wait_ms": 1000},
                    {"action": "narrate", "value": "The analytics dashboard gives you real-time insights into your sales performance, pipeline velocity, and team metrics.", "wait_ms": 500},
                    {"action": "scroll", "value": "down", "description": "Scrolling to see more reports", "wait_ms": 1500},
                    {"action": "screenshot", "description": "More detailed reports are available below", "wait_ms": 1000},
                    {"action": "narrate", "value": "You can also build custom reports, schedule email delivery, and export to PDF or CSV.", "wait_ms": 500},
                ],
            },
        ]

        for recipe_data in recipes:
            recipe = DemoRecipe(
                workspace_id=workspace.id,
                name=recipe_data["name"],
                description=recipe_data["description"],
                trigger_phrases=recipe_data["trigger_phrases"],
                steps_json=json.dumps(recipe_data["steps"]),
                priority=recipe_data["priority"],
            )
            db.add(recipe)
            print(f"  Created recipe: {recipe.name}")
        db.commit()

        # 5. Create policy rules
        policies = [
            {
                "rule_type": "blocked_topic",
                "pattern": r"\b(competitor|salesforce|hubspot|pipedrive)\b",
                "description": "Competitor comparisons should be handled by sales team",
                "action": "escalate",
                "severity": "medium",
            },
            {
                "rule_type": "blocked_action",
                "pattern": r"\b(delete|remove|destroy|drop)\b.*\b(all|everything|database)\b",
                "description": "Bulk destructive actions are never allowed",
                "action": "refuse",
                "severity": "high",
            },
            {
                "rule_type": "escalation_condition",
                "pattern": r"\b(enterprise|custom plan|sla|volume discount|annual)\b",
                "description": "Enterprise and custom pricing discussions need sales rep",
                "action": "escalate",
                "severity": "medium",
            },
            {
                "rule_type": "blocked_route",
                "pattern": r"/admin|/settings/billing|/settings/security",
                "description": "Admin and billing pages are not part of the demo",
                "action": "refuse",
                "severity": "high",
            },
        ]

        for policy_data in policies:
            rule = PolicyRule(
                workspace_id=workspace.id,
                **policy_data,
            )
            db.add(rule)
            print(f"  Created policy: {policy_data['description']}")
        db.commit()

        # 6. Create a no-login Saleshandy workspace for live-browser demos
        saleshandy = Workspace(
            name="Saleshandy Live Demo",
            description="Live browser demo workspace for Saleshandy using the public demo product flow",
            product_url="https://my.saleshandy.com/demo",
            allowed_domains="my.saleshandy.com",
            browser_auth_mode="none",
            public_token="demo-saleshandy-001",
        )
        db.add(saleshandy)
        db.commit()
        db.refresh(saleshandy)
        print(f"  Created workspace: {saleshandy.name} (token: {saleshandy.public_token})")

        saleshandy_docs = [
            {
                "filename": "overview.md",
                "file_type": "md",
                "content": _load_fixture("overview.md", SALESHANDY_FIXTURE_DIR),
            },
            {
                "filename": "workflows.md",
                "file_type": "md",
                "content": _load_fixture("workflows.md", SALESHANDY_FIXTURE_DIR),
            },
            {
                "filename": "policies.md",
                "file_type": "md",
                "content": _load_fixture("policies.md", SALESHANDY_FIXTURE_DIR),
            },
        ]

        for doc_data in saleshandy_docs:
            doc = Document(
                workspace_id=saleshandy.id,
                filename=doc_data["filename"],
                file_type=doc_data["file_type"],
                content_text=doc_data["content"],
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            num_chunks = ingest_document(db, doc, content_override=doc_data["content"])
            print(f"  Ingested document: {doc.filename} ({num_chunks} chunks)")

        saleshandy_recipes = [
            {
                "name": "Open Saleshandy Sequences",
                "description": "Bootstrap the public demo and stay on the Sequences module",
                "trigger_phrases": "sequence,sequences,outreach,cadence,dashboard",
                "priority": 6,
                "steps": [
                    {"action": "navigate", "target": "https://my.saleshandy.com/demo", "description": "Opening the Saleshandy public demo", "wait_ms": 4000},
                    {"action": "wait_for_url", "target": "/sequence", "value": "15000", "description": "Waiting for the product to load into Sequences", "wait_ms": 0},
                    {"action": "narrate", "value": "This is the Sequences module where outreach flows and activity are managed.", "wait_ms": 500},
                ],
            },
            {
                "name": "Show Reports",
                "description": "Walk through the Saleshandy analytics and reporting section",
                "trigger_phrases": "analytics,reports,metrics,reporting,performance",
                "priority": 5,
                "steps": [
                    {"action": "navigate", "target": "https://my.saleshandy.com/demo", "description": "Loading the public demo", "wait_ms": 4000},
                    {"action": "wait_for_url", "target": "/sequence", "value": "15000", "description": "Waiting for Saleshandy to finish demo bootstrap", "wait_ms": 0},
                    {"action": "click", "target": "a[href='/reports']", "description": "Opening the Reports module", "wait_ms": 2500},
                    {"action": "wait_for_url", "target": "/reports", "value": "10000", "description": "Waiting for Reports to load", "wait_ms": 0},
                    {"action": "narrate", "value": "Reports is where performance and activity trends are reviewed.", "wait_ms": 500},
                ],
            },
            {
                "name": "Show CRM Prospects",
                "description": "Open the CRM list and explain prospect organization",
                "trigger_phrases": "crm,prospects,leads,list,contacts",
                "priority": 5,
                "steps": [
                    {"action": "navigate", "target": "https://my.saleshandy.com/demo", "description": "Loading the public demo", "wait_ms": 4000},
                    {"action": "wait_for_url", "target": "/sequence", "value": "15000", "description": "Waiting for Saleshandy to finish demo bootstrap", "wait_ms": 0},
                    {"action": "click", "target": "a[href='/crm/list']", "description": "Opening the CRM list", "wait_ms": 2500},
                    {"action": "wait_for_url", "target": "/crm/list", "value": "10000", "description": "Waiting for the CRM module to load", "wait_ms": 0},
                    {"action": "narrate", "value": "The CRM list is where prospects and lead records are organized and filtered.", "wait_ms": 500},
                ],
            },
            {
                "name": "Show Unified Inbox",
                "description": "Open the Unified Inbox to explain how responses are reviewed",
                "trigger_phrases": "inbox,conversation,replies,reply,emails",
                "priority": 4,
                "steps": [
                    {"action": "navigate", "target": "https://my.saleshandy.com/demo", "description": "Loading the public demo", "wait_ms": 4000},
                    {"action": "wait_for_url", "target": "/sequence", "value": "15000", "description": "Waiting for Saleshandy to finish demo bootstrap", "wait_ms": 0},
                    {"action": "click", "target": "a[href='/conversations']", "description": "Opening Unified Inbox", "wait_ms": 2500},
                    {"action": "wait_for_url", "target": "/conversations", "value": "10000", "description": "Waiting for the inbox to load", "wait_ms": 0},
                    {"action": "narrate", "value": "Unified Inbox centralizes replies and conversations so reps can triage from one place.", "wait_ms": 500},
                ],
            },
        ]

        for recipe_data in saleshandy_recipes:
            recipe = DemoRecipe(
                workspace_id=saleshandy.id,
                name=recipe_data["name"],
                description=recipe_data["description"],
                trigger_phrases=recipe_data["trigger_phrases"],
                steps_json=json.dumps(recipe_data["steps"]),
                priority=recipe_data["priority"],
            )
            db.add(recipe)
            print(f"  Created recipe: {recipe.name}")
        db.commit()

        saleshandy_policies = [
            {
                "rule_type": "escalation_condition",
                "pattern": r"\b(pricing|discount|annual|enterprise|contract|procurement)\b",
                "description": "Commercial conversations should be escalated during the public demo",
                "action": "escalate",
                "severity": "medium",
            },
            {
                "rule_type": "blocked_route",
                "pattern": r"/settings|/billing|/admin",
                "description": "Settings, billing, and admin screens are blocked in the public demo",
                "action": "refuse",
                "severity": "high",
            },
        ]

        for policy_data in saleshandy_policies:
            rule = PolicyRule(
                workspace_id=saleshandy.id,
                **policy_data,
            )
            db.add(rule)
            print(f"  Created policy: {policy_data['description']}")
        db.commit()

        print("\nSeed complete!")
        print(f"  Workspace ID: {workspace.id}")
        print(f"  Public token: {workspace.public_token}")
        print(f"  Demo link: http://localhost:3000/demo/{workspace.public_token}")
        print(f"  Admin link: http://localhost:3000/admin/workspaces/{workspace.id}")
        print(f"  Saleshandy demo link: http://localhost:3000/demo/{saleshandy.public_token}")
        print(f"  Saleshandy admin link: http://localhost:3000/admin/workspaces/{saleshandy.id}")


if __name__ == "__main__":
    seed()
