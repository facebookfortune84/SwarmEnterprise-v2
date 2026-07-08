"""
Swarm Intelligence Runtime (v2 → v3 bridge)

Features:
- Full prompt DNA loading
- Agent scoring
- Graph traversal (SOP + tools)
- Multi-agent chaining
- Memory manager integration
"""

import os
import json
import logging

logger = logging.getLogger(__name__)

BASE = os.path.join(os.getcwd(), "backend", "intelligence", "output")


# ============================================================
# ✅ Loader
# ============================================================

def load_json(name):
    with open(os.path.join(BASE, name), "r", encoding="utf-8") as f:
        return json.load(f)


def load_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return ""


# ============================================================
# ✅ Intelligence Core
# ============================================================

class Intelligence:

    def __init__(self):
        self.archetypes = load_json("archetype_registry.json")
        self.agents = load_json("agent_registry.json")
        self.graph = load_json("asset_graph.json")

        self.node_map = {n["id"]: n for n in self.graph["nodes"]}
        self.name_map = {n["name"]: n for n in self.graph["nodes"]}

    # ============================================================
    # ✅ Task Classification
    # ============================================================

    def classify(self, prompt: str):
        p = prompt.lower()

        if any(k in p for k in ["build", "code", "create", "develop"]):
            return "builder"

        if any(k in p for k in ["plan", "strategy", "roadmap"]):
            return "planner"

        if any(k in p for k in ["analyze", "research", "investigate"]):
            return "researcher"

        if any(k in p for k in ["review", "evaluate", "audit"]):
            return "reviewer"

        return "orchestrator"

    # ============================================================
    # ✅ Best Agent Selection (SCORING)
    # ============================================================

    def select_agent(self, archetype):
        agents = self.agents.get("agents", {})

        if archetype in agents:
            variants = agents[archetype]["variants"]

            best = sorted(variants, key=lambda x: x["score"], reverse=True)[0]

            return best["file"]

        return None

    # ============================================================
    # ✅ Load FULL Prompt DNA
    # ============================================================

    def load_prompt_dna(self, archetype):
        entries = self.archetypes["archetypes"].get(archetype, [])

        prompts = []

        for item in sorted(entries, key=lambda x: x["confidence"], reverse=True)[:3]:

            path = item["file"].replace("asset_processor\\", "")
            path = os.path.join(os.getcwd(), path)

            content = load_file(path)

            if content:
                prompts.append(content[:2000])  # safe limit

        return prompts

    # ============================================================
    # ✅ Graph Traversal → SOP Extraction
    # ============================================================

    def get_related_sops(self, limit=5):
        nodes = self.graph["nodes"]

        sops = [
            n for n in nodes
            if n["asset_type"] == "sop"
        ]

        return sops[:limit]

    # ============================================================
    # ✅ Tool Extraction
    # ============================================================

    def get_tools(self, limit=3):
        nodes = self.graph["nodes"]

        tools = [
            n for n in nodes
            if n["asset_type"] == "tool"
        ]

        return tools[:limit]

    # ============================================================
    # ✅ Memory Manager Hook
    # ============================================================

    def get_memory(self, prompt):
        # simple stub — replace with actual memory agent later
        return f"Relevant memory context for: {prompt[:100]}"

    # ============================================================
    # ✅ Multi-Agent Chain Builder
    # ============================================================

    def build_chain(self, archetype):

        if archetype == "builder":
            return ["planner", "architect", "builder", "reviewer"]

        if archetype == "researcher":
            return ["researcher", "reviewer"]

        return ["orchestrator"]

    # ============================================================
    # ✅ Context Builder (MASTER FUNCTION)
    # ============================================================

    def build_context(self, prompt):

        archetype = self.classify(prompt)

        agent_file = self.select_agent(archetype)

        prompt_dna = self.load_prompt_dna(archetype)

        sops = self.get_related_sops()
        tools = self.get_tools()

        memory = self.get_memory(prompt)

        chain = self.build_chain(archetype)

        # ========================================================
        # ✅ Build FORMATTED Context
        # ========================================================

        context = f"""
=== ARCHETYPE ===
{archetype}

=== AGENT ===
{agent_file}

=== EXECUTION CHAIN ===
{" -> ".join(chain)}

=== MEMORY ===
{memory}

=== PROMPT DNA ===
{"\n\n---\n\n".join(prompt_dna)}

=== SOP CONTEXT ===
{"\n".join([s['name'] for s in sops])}

=== TOOLS ===
{"\n".join([t['name'] for t in tools])}
"""

        return {
            "archetype": archetype,
            "context": context,
            "chain": chain
        }