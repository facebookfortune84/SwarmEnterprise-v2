import asyncio
import logging
from backend.services.company_generator import CompanyGenerator, CompanyRequest, TechStack

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AutonomousLoop")

async def trigger_autonomous_generation():
    """
    Sets the autonomous sovereign factory workflow into action.
    This triggers a full 'Vibe-to-Code' cycle.
    """
    generator = CompanyGenerator()
    
    # Define a realistic request for a full system generation
    request = CompanyRequest(
        name="SovereignDashboard",
        description="A lightweight, self-hosted dashboard for managing local Docker services.",
        tech_stack=TechStack.FASTAPI_REACT_POSTGRES,
        features=["authentication", "docker-container-monitoring", "cost-tracking"],
        user_id="SYSTEM_ROOT"
    )
    
    logger.info("🚀 Sovereign Factory Loop: INITIATED")
    try:
        result = await generator.generate_company(request)
        logger.info(f"✅ Sovereign Factory Loop: COMPLETED | Result: {result}")
    except Exception as e:
        logger.error(f"❌ Sovereign Factory Loop: FAILED | Error: {e}")

if __name__ == "__main__":
    asyncio.run(trigger_autonomous_generation())
