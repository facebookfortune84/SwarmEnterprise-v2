from crewai import Agent
from agents.llm_config import LOCAL_BRAIN
from langchain_ollama import OllamaLLM

class MarketingContentCreator:
    """Reads finished projects and writes high-converting sales copy"""
    def __init__(self):
        self.agent = Agent(
            role="Marketing Director",
            goal="Write a 1-page sales spec for the newly built autonomous app.",
            backstory="You are a brilliant SaaS marketer. You analyze code features and translate them into $49,999 value propositions.",
            llm=LOCAL_BRAIN,
            verbose=True
        )
