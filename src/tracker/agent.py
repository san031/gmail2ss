from datetime import date

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

load_dotenv()

import sheet
from mail import fetch_recent_emails
from tools import TOOLS

LOG_FILE = Path(__file__).resolve().parents[2] / "logs" / "tracker.log"
log = logging.getLogger("tracker")


def setup_logging() -> None:
    LOG_FILE.parent.mkdir(exist_ok=True)
    handlers = [RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3,
                                    encoding="utf-8")]
    if sys.stderr:  # pythonw (scheduled runs) has no console
        handlers.append(logging.StreamHandler())
    logging.basicConfig(level=logging.INFO, handlers=handlers,
                        format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # hide per-request noise


SYSTEM = f"""You maintain the user's job-application tracker spreadsheet.
Today is {date.today().isoformat()}.

For each email:
1. If it is not about one of the user's job applications (newsletters, job
   alerts, OTPs, promotions), call NO tools and reply "not job related".
2. Otherwise call find_application first.
3. Application confirmation -> add_application (if not already tracked).
4. Interview invite -> add_application first if not tracked, then schedule_interview.
5. Rejection / offer / online test / recruiter call -> update_status.
6. Always pass email_id exactly as given in the email header.
7. Use the short company name without suffixes (Acme, not Acme Corp Pvt Ltd).
8. Resolve relative dates ("next Tuesday") using the email's Date header.
When done, reply with one sentence summarising what you changed."""

llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0).bind_tools(TOOLS)


def call_model(state: MessagesState) -> dict:
    response = llm.invoke([SystemMessage(SYSTEM)] + state["messages"])
    return {"messages": [response]}


def build_graph():
    graph = StateGraph(MessagesState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)  # -> "tools" or END
    graph.add_edge("tools", "agent")
    return graph.compile()


def format_email(m: dict) -> str:
    return (f"email_id: {m['email_id']}\nFrom: {m['from']}\nDate: {m['date']}\n"
            f"Subject: {m['subject']}\n\n{m['body']}")


# if __name__ == "__main__":     # for local run
#     agent = build_graph()
#     for m in fetch_recent_emails(days=7, limit=20):
#         if not m["email_id"] or sheet.is_email_processed(m["email_id"]):
#             print(f"skip (already processed): {m['subject']}")
#             continue

#         print(f"\n=== {m['subject']}")
#         config = {"recursion_limit": 10,
#                   "configurable": {"email_id": m["email_id"]}}
#         try:
#             result = agent.invoke(
#                 {"messages": [HumanMessage(format_email(m))]}, config)
#         except Exception as e:  # one bad email must not stop the run
#             print(f"!! failed, will retry next run: {type(e).__name__}: {e}")
#             continue

#         for msg in result["messages"][1:]:
#             msg.pretty_print()


# for automation
def run_once(days: int = 7, limit: int = 20) -> None:
    agent = build_graph()
    counts = {"skipped": 0, "done": 0, "failed": 0}

    for m in fetch_recent_emails(days=days, limit=limit):
        if not m["email_id"] or sheet.is_email_processed(m["email_id"]):
            counts["skipped"] += 1
            continue

        config = {"recursion_limit": 10,
                  "configurable": {"email_id": m["email_id"]}}
        try:
            result = agent.invoke(
                {"messages": [HumanMessage(format_email(m))]}, config)
        except Exception:
            counts["failed"] += 1
            log.exception("failed: %s", m["subject"])
            continue

        counts["done"] += 1
        for msg in result["messages"]:
            for call in getattr(msg, "tool_calls", None) or []:
                log.info("  tool %s %s", call["name"], call["args"])
        log.info("done: %s -> %s", m["subject"], result["messages"][-1].content)

    log.info("run finished: %s", counts)


if __name__ == "__main__":
    setup_logging()
    try:
        run_once()
    except Exception:  # e.g. no internet, IMAP login failed
        log.exception("run crashed")
        raise SystemExit(1)
