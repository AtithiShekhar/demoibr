from langchain.agents import initialize_agent, AgentType
from langchain.tools import Tool
from core.llm import GeminiLLM
from agent.tools import med_info_tool

def build_agent():
    """
    Build a LangChain agent that registers med_info_tool.
    The main flow will orchestrate calls explicitly; agent exists per senior's requirement.
    """
    llm = GeminiLLM(model_name="gemini-2.0-flash", temperature=0.2, max_output_tokens=2300)

    med_tool = Tool(
        name="med_info_tool",
        func=med_info_tool,
        description="Given a medication name, returns structured info from the dummy DB."
    )

    agent = initialize_agent(
        tools=[med_tool],
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=False
    )
    return agent
