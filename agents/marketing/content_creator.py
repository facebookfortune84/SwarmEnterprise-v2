from agents.llm_config import get_local_brain_instance


class MarketingContentCreator:
    """Reads finished projects and writes high-converting sales copy"""

    def __init__(self):
        try:
            from crewai import Agent
        except ImportError:
            raise RuntimeError(
                "crewai package required to construct Agent objects. Install or mock for tests."
            )

        brain = get_local_brain_instance()
        self.agent = Agent(
            role="Marketing Director",
            goal="Write a 1-page sales spec for the newly built autonomous app.",
            backstory="You are a brilliant SaaS marketer. You analyze code features and translate them into $49,999 value propositions.",
            llm=brain,
            verbose=True,
        )
