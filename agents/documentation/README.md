# Documentation Agent Team

Autonomous documentation agents for automated documentation creation and maintenance.

## Agents

### 1. Documentation Generator (`doc_generator.py`)
**Purpose:** Automated documentation creation

**Capabilities:**
- README generation from project analysis
- API documentation extraction
- User guide creation
- Architecture documentation
- Docstring generation for missing documentation
- AI-powered content generation

**Key Methods:**
- `generate_readme()` - Generate comprehensive README.md
- `generate_api_docs()` - Extract and document API
- `generate_user_guide()` - Create user-friendly guides
- `generate_architecture_doc()` - Document system architecture
- `update_docstrings()` - Generate missing docstrings

**Usage:**
```python
from agents.documentation.doc_generator import DocGenerator

generator = DocGenerator()

# Generate README
result = await generator.generate_readme(
    project_path="/path/to/project",
    project_name="MyProject",
    description="A Python project for X"
)

# Generate API docs
api_docs = await generator.generate_api_docs(
    project_path="/path/to/project",
    output_format="markdown"
)

# Generate user guide
user_guide = await generator.generate_user_guide(
    project_name="MyProject",
    features=["Feature 1", "Feature 2"],
    examples=[
        {
            "title": "Basic Usage",
            "description": "How to use the API",
            "code": "import myproject\nmyproject.run()"
        }
    ]
)
```

### 2. API Documentation Updater (`api_doc_updater.py`)
**Purpose:** Automated API documentation maintenance

**Capabilities:**
- OpenAPI/Swagger spec generation
- Endpoint documentation extraction from FastAPI routes
- Request/response example generation
- Authentication documentation
- Postman collection generation
- AI-powered endpoint descriptions

**Key Methods:**
- `update_openapi_spec()` - Generate OpenAPI 3.0 spec
- `generate_endpoint_docs()` - Create endpoint documentation
- `generate_postman_collection()` - Export Postman collection

**Usage:**
```python
from agents.documentation.api_doc_updater import APIDocUpdater

updater = APIDocUpdater()

# Generate OpenAPI spec
spec = await updater.update_openapi_spec(
    api_path="backend/api",
    title="My API",
    version="1.0.0"
)

# Save spec
with open("openapi.json", "w") as f:
    f.write(spec.content)

# Generate endpoint docs
docs = await updater.generate_endpoint_docs("backend/api")

# Generate Postman collection
collection = await updater.generate_postman_collection(
    api_path="backend/api",
    collection_name="My API Collection"
)
```

### 3. Changelog Generator (`changelog_generator.py`)
**Purpose:** Automated changelog and release notes generation

**Capabilities:**
- Git commit analysis
- Conventional commits parsing
- Semantic versioning support
- Release notes generation
- Breaking changes detection
- AI-powered release summaries

**Key Methods:**
- `generate_changelog()` - Generate full changelog
- `generate_release_notes()` - Create release notes for version

**Usage:**
```python
from agents.documentation.changelog_generator import ChangelogGenerator

generator = ChangelogGenerator()

# Generate changelog
changelog = await generator.generate_changelog(
    repo_path="/path/to/repo",
    since_tag="v1.0.0",
    output_format="markdown"
)

# Generate release notes
notes = await generator.generate_release_notes(
    repo_path="/path/to/repo",
    version="v2.0.0",
    since_tag="v1.0.0"
)
```

## Integration

### Complete Documentation Workflow

```python
from agents.documentation import DocGenerator, APIDocUpdater, ChangelogGenerator

async def full_documentation_update(project_path: str, version: str):
    """Complete documentation update workflow"""
    
    # 1. Generate README
    doc_gen = DocGenerator()
    readme = await doc_gen.generate_readme(
        project_path=project_path,
        project_name="SwarmEnterprise",
        description="Autonomous digital factory platform"
    )
    
    with open(f"{project_path}/README.md", "w") as f:
        f.write(readme.content)
    
    # 2. Update API documentation
    api_updater = APIDocUpdater()
    openapi_spec = await api_updater.update_openapi_spec(
        api_path=f"{project_path}/backend/api",
        title="SwarmEnterprise API",
        version=version
    )
    
    with open(f"{project_path}/docs/openapi.json", "w") as f:
        f.write(openapi_spec.content)
    
    # 3. Generate changelog
    changelog_gen = ChangelogGenerator()
    changelog = await changelog_gen.generate_changelog(
        repo_path=project_path,
        since_tag=f"v{version}",
        output_format="markdown"
    )
    
    with open(f"{project_path}/CHANGELOG.md", "w") as f:
        f.write(changelog)
    
    # 4. Generate release notes
    release_notes = await changelog_gen.generate_release_notes(
        repo_path=project_path,
        version=version,
        since_tag=f"v{version}"
    )
    
    return {
        "readme": readme,
        "api_docs": openapi_spec,
        "changelog": changelog,
        "release_notes": release_notes
    }
```

### CI/CD Integration

```yaml
# .github/workflows/docs.yml
name: Update Documentation

on:
  push:
    branches: [main]
  release:
    types: [published]

jobs:
  update-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Update documentation
        run: |
          python -c "
          import asyncio
          from agents.documentation import DocGenerator, APIDocUpdater
          
          async def main():
              # Update README
              doc_gen = DocGenerator()
              await doc_gen.generate_readme('.', 'SwarmEnterprise')
              
              # Update API docs
              api_updater = APIDocUpdater()
              await api_updater.update_openapi_spec('backend/api', 'API', '1.0.0')
          
          asyncio.run(main())
          "
      
      - name: Commit changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add README.md docs/
          git commit -m "docs: auto-update documentation" || echo "No changes"
          git push
```

### Pre-release Hook

```python
# scripts/pre_release.py
import asyncio
from agents.documentation import ChangelogGenerator

async def prepare_release(version: str):
    """Prepare release documentation"""
    
    generator = ChangelogGenerator()
    
    # Generate release notes
    notes = await generator.generate_release_notes(
        repo_path=".",
        version=version,
        since_tag=None  # All commits
    )
    
    # Save release notes
    with open(f"releases/v{version}.md", "w") as f:
        f.write(notes)
    
    print(f"Release notes generated: releases/v{version}.md")

if __name__ == "__main__":
    import sys
    version = sys.argv[1] if len(sys.argv) > 1 else "1.0.0"
    asyncio.run(prepare_release(version))
```

## Configuration

### Environment Variables

```bash
# Ollama LLM
OLLAMA_URL=http://192.168.1.100:11434
OLLAMA_MODEL=llama3

# Documentation settings
DOC_OUTPUT_DIR=./docs
DOC_FORMAT=markdown  # markdown, rst, html
```

### Conventional Commits

The changelog generator supports conventional commits format:

```
feat: Add new feature
fix: Fix bug
docs: Update documentation
refactor: Refactor code
test: Add tests
chore: Update dependencies
perf: Improve performance
```

Breaking changes:
```
feat!: Breaking change
feat: Add feature

BREAKING CHANGE: Description
```

## Output Formats

### README Structure

```markdown
# Project Title

Description

## Features
- Feature 1
- Feature 2

## Installation
```bash
pip install project
```

## Quick Start
```python
import project
project.run()
```

## API Reference
...

## Contributing
...

## License
MIT
```

### OpenAPI Spec

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "API Title",
    "version": "1.0.0"
  },
  "paths": {
    "/endpoint": {
      "get": {
        "summary": "Description",
        "responses": {
          "200": {
            "description": "Success"
          }
        }
      }
    }
  }
}
```

### Changelog Format

```markdown
# Changelog

## ⚠️ BREAKING CHANGES
- Breaking change description

## ✨ Features
- New feature 1
- New feature 2

## 🐛 Bug Fixes
- Fix 1
- Fix 2

## 🔒 Security
- Security update

## ⚡ Performance
- Performance improvement
```

## Best Practices

1. **Keep documentation up-to-date** - Run agents on every release
2. **Use conventional commits** - Enables better changelog generation
3. **Add docstrings** - Improves API documentation quality
4. **Review AI-generated content** - Validate before committing
5. **Version documentation** - Tag docs with releases
6. **Automate in CI/CD** - Keep docs synchronized with code

## Testing

```bash
# Run documentation agent tests
pytest tests/unit/agents/documentation/ -v

# Test README generation
python -c "
import asyncio
from agents.documentation import DocGenerator

async def test():
    gen = DocGenerator()
    result = await gen.generate_readme('.', 'Test', 'Test project')
    print(result.content[:200])

asyncio.run(test())
"

# Test API docs
python -c "
import asyncio
from agents.documentation import APIDocUpdater

async def test():
    updater = APIDocUpdater()
    result = await updater.generate_endpoint_docs('backend/api')
    print(f'Documented {result.endpoints_documented} endpoints')

asyncio.run(test())
"
```

## Troubleshooting

### Common Issues

1. **Git command fails**
   - Ensure git is installed and in PATH
   - Check repository has commits
   - Verify git config is set

2. **Ollama connection fails**
   - Check Ollama is running
   - Verify OLLAMA_URL
   - Test with simple prompt

3. **Missing docstrings**
   - Run `update_docstrings()` to generate
   - Review and edit generated docstrings
   - Commit changes

4. **OpenAPI spec incomplete**
   - Add type hints to functions
   - Use Pydantic models for request/response
   - Add docstrings to endpoints

## Future Enhancements

- [ ] Support for more languages (Java, Go, Rust)
- [ ] Diagram generation (architecture, sequence)
- [ ] Video tutorial generation
- [ ] Interactive documentation
- [ ] Multi-language documentation
- [ ] Documentation quality scoring
- [ ] Automated screenshot generation
- [ ] API client SDK generation

## License

MIT License - See LICENSE file for details