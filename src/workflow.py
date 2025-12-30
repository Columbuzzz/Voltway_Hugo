# src/workflow.py
from langgraph.graph import StateGraph, END
from typing import TypedDict
from src.agents import run_watchdog, run_analyst

class AgentState(TypedDict):
    email_content: str
    extraction: dict
    final_report: str

def watchdog_node(state):
    result = run_watchdog(state["email_content"])
    return {"extraction": result.dict()}

def analyst_node(state):
    from src.schemas import EmailExtraction
    data = EmailExtraction(**state["extraction"])
    report = run_analyst(data)
    return {"final_report": report}

def route(state):
    return "analyst" if state["extraction"]["risk_score"] >= 2 else END

graph = StateGraph(AgentState)
graph.add_node("watchdog", watchdog_node)
graph.add_node("analyst", analyst_node)

graph.set_entry_point("watchdog")
graph.add_conditional_edges("watchdog", route, {"analyst": "analyst", END: END})
graph.add_edge("analyst", END)

app = graph.compile()
