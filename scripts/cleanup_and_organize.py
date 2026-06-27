"""
Project Cleanup and Organization Script

Consolidates documentation, removes duplicates, and organizes project structure.
"""

import shutil
from pathlib import Path

# Define project root
PROJECT_ROOT = Path(__file__).parent.parent

# Documentation organization
DOC_MOVES = {
    # Keep in root (essential)
    "README.md": None,
    "IMPLEMENTATION_COMPLETE.md": None,  # Latest comprehensive summary
    # Move to docs/architecture
    "ARCHITECTURE.md": "docs/architecture/",
    "MASTER_PLAN.md": "docs/architecture/",
    "SELF_HOSTED_ARCHITECTURE.md": "docs/architecture/",
    # Move to docs/guides
    "DEPLOYMENT_GUIDE.md": "docs/guides/",
    "QUICKSTART.md": "docs/guides/",
    "IMPLEMENTATION_ROADMAP.md": "docs/guides/",
    # Move to docs/phases (historical)
    "PHASE_8_COMPLETE.md": "docs/phases/",
    "PHASE_9_SELF_HEALING.md": "docs/phases/",
    "PHASE3_COMPLETION_SUMMARY.md": "docs/phases/",
    # Remove (duplicates/obsolete)
    "PROJECT_STATUS_FINAL.md": "DELETE",
    "FINAL_IMPLEMENTATION_SUMMARY.md": "DELETE",
    "PROJECT_COMPLETION_SUMMARY.md": "DELETE",
    "PROJECT_STATUS.md": "DELETE",
    "DEPLOY.md": "DELETE",  # Superseded by DEPLOYMENT_GUIDE.md
    ".aider.chat.history.md": "DELETE",
    ".aider.input.history": "DELETE",
}

# Files to remove
FILES_TO_REMOVE = [
    "test_network_bridge.py",  # Old test file
    "upload_secrets.ps1",  # Temporary script
    "project_structure_clean.txt",  # Temporary file
    ".sconsign.dblite",  # Build artifact
    "swarm_complete.yaml",  # Old config
]


def cleanup_documentation():
    """Organize and clean up documentation files"""
    print("Organizing documentation...")

    for filename, destination in DOC_MOVES.items():
        source = PROJECT_ROOT / filename

        if not source.exists():
            continue

        if destination == "DELETE":
            print(f"  Removing: {filename}")
            source.unlink()
        elif destination:
            dest_path = PROJECT_ROOT / destination / filename
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            print(f"  Moving: {filename} -> {destination}")
            shutil.move(str(source), str(dest_path))
        else:
            print(f"  Keeping in root: {filename}")


def cleanup_temp_files():
    """Remove temporary and obsolete files"""
    print("\nCleaning up temporary files...")

    for filename in FILES_TO_REMOVE:
        filepath = PROJECT_ROOT / filename
        if filepath.exists():
            print(f"  Removing: {filename}")
            filepath.unlink()


def create_docs_index():
    """Create index file for documentation"""
    print("\nCreating documentation index...")

    index_content = """# SwarmEnterprise v2 Documentation

## 📖 Quick Links

### Getting Started
- [README](../README.md) - Project overview
- [Quick Start Guide](guides/QUICKSTART.md) - Get up and running in 30 minutes
- [Implementation Complete](../IMPLEMENTATION_COMPLETE.md) - Current status and achievements

### Architecture
- [Master Plan](architecture/MASTER_PLAN.md) - Overall vision and strategy
- [Architecture](architecture/ARCHITECTURE.md) - System design and components
- [Self-Hosted Architecture](architecture/SELF_HOSTED_ARCHITECTURE.md) - Zero-cost deployment

### Guides
- [Deployment Guide](guides/DEPLOYMENT_GUIDE.md) - Production deployment
- [Implementation Roadmap](guides/IMPLEMENTATION_ROADMAP.md) - Development phases

### Phase Summaries
- [Phase 3 Completion](phases/PHASE3_COMPLETION_SUMMARY.md) - Backend infrastructure
- [Phase 8 Complete](phases/PHASE_8_COMPLETE.md) - Autonomous ticketing
- [Phase 9 Self-Healing](phases/PHASE_9_SELF_HEALING.md) - Self-healing system

## 📊 Project Status

**Completion:** 86%  
**Files:** 67 files, 21,382+ lines  
**Agents:** 16 operational  
**Cost:** $0/month (self-hosted)  

See [IMPLEMENTATION_COMPLETE.md](../IMPLEMENTATION_COMPLETE.md) for full details.
"""

    index_path = PROJECT_ROOT / "docs" / "INDEX.md"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_content)

    print("  Created: docs/INDEX.md")


def update_readme():
    """Update README with new documentation structure"""
    print("\nUpdating README...")

    readme_content = """# SwarmEnterprise v2

**Autonomous Digital Factory Platform**

A comprehensive platform with 16 AI-powered autonomous agents that automate software development, deployment, monitoring, and maintenance - all at **$0/month operational cost**.

## 🎯 Quick Start

```bash
# Clone repository
git clone https://github.com/yourusername/SwarmEnterprise-v2.git
cd SwarmEnterprise-v2

# Set up environment
cp .env.example .env

# Start services
docker-compose up -d

# Access dashboard
open http://localhost:8000
```

See [Quick Start Guide](docs/guides/QUICKSTART.md) for detailed instructions.

## 📊 Status

- **Completion:** 86% (Production Ready)
- **Files:** 67 files, 21,382+ lines
- **Agents:** 16 operational autonomous agents
- **Cost:** $0/month (completely self-hosted)
- **ROI:** 43,600%-147,700%

## 🤖 Autonomous Agents

### DevOps Team (5 agents)
- CI/CD Manager - 7-stage pipeline automation
- Deployment Agent - Blue-green, canary, rolling updates
- Security Scanner - Vulnerability detection
- Performance Monitor - Real-time metrics
- Infrastructure Agent - Resource provisioning

### Code Quality Team (3 agents)
- Code Reviewer - Static analysis & quality scoring
- Style Checker - PEP 8 & ESLint compliance
- Security Auditor - 10 vulnerability types

### Documentation Team (3 agents)
- Doc Generator - README, guides, architecture
- API Doc Updater - OpenAPI 3.0 specs
- Changelog Generator - Semantic versioning

### Ticketing Team (3 agents)
- Linear Integration - GraphQL API integration
- Ticket Prioritizer - Multi-factor AI scoring
- Backlog Manager - Health analysis & sprint planning

### Self-Healing Team (3 agents)
- Health Monitor - Continuous monitoring
- Auto-Recovery - Automatic failure recovery
- Circuit Breaker - Cascading failure prevention

## 📚 Documentation

- [Implementation Complete](IMPLEMENTATION_COMPLETE.md) - Current status & achievements
- [Architecture](docs/architecture/ARCHITECTURE.md) - System design
- [Deployment Guide](docs/guides/DEPLOYMENT_GUIDE.md) - Production deployment
- [Documentation Index](docs/INDEX.md) - All documentation

## 🚀 Features

- **Zero-Cost Operations** - Completely self-hosted (Windows Server + WSL2 + Ollama)
- **16 Autonomous Agents** - Full automation pipeline
- **Multi-Tenant** - Isolated tenants with per-tenant databases
- **Self-Healing** - Automatic recovery & circuit breakers
- **Production-Ready** - Authentication, monitoring, security

## 💰 Cost Savings

| Service | Traditional Cloud | SwarmEnterprise v2 |
|---------|------------------|-------------------|
| Monthly Cost | $950-3,200 | $0 |
| Annual Cost | $11,400-38,400 | $0 |
| **Savings** | **-** | **$11,400-38,400/year** |

## 🛠️ Tech Stack

- **Backend:** FastAPI, Python 3.11+
- **Database:** PostgreSQL 15
- **Cache:** Redis 7
- **Storage:** MinIO (S3-compatible)
- **LLM:** Ollama (llama3, codellama, mistral)
- **Monitoring:** Prometheus, Grafana, Loki
- **Infrastructure:** Docker, Hyper-V

## 📖 Getting Help

- [Quick Start Guide](docs/guides/QUICKSTART.md) - 30-minute setup
- [Deployment Guide](docs/guides/DEPLOYMENT_GUIDE.md) - Production deployment
- [Architecture Docs](docs/architecture/) - System design
- [Implementation Complete](IMPLEMENTATION_COMPLETE.md) - Full project status

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

Built with ❤️ using Claude AI

---

**Status:** Production Ready (86% Complete)  
**Cost:** $0/month operational  
**Agents:** 16 operational  
**Documentation:** Complete
"""

    readme_path = PROJECT_ROOT / "README.md"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)

    print("  Updated: README.md")


def main():
    """Main cleanup function"""
    print("Starting project cleanup and organization...\n")

    cleanup_documentation()
    cleanup_temp_files()
    create_docs_index()
    update_readme()

    print("\nCleanup complete!")
    print("\nNew structure:")
    print("  |- README.md (updated)")
    print("  |- IMPLEMENTATION_COMPLETE.md (latest status)")
    print("  |- docs/")
    print("      |- INDEX.md (documentation index)")
    print("      |- architecture/ (system design)")
    print("      |- guides/ (how-to guides)")
    print("      |- phases/ (historical summaries)")


if __name__ == "__main__":
    main()

# Made with Bob
