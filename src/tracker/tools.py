from langchain_core.tools import tool
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from typing import Literal
load_dotenv()
from langchain_core.runnables import RunnableConfig
import sheet
from pathlib import Path

Status = Literal[sheet.STATUSES]

def _path(config: RunnableConfig) -> Path:
    return Path(config["configurable"].get("sheet_path", sheet.DEFAULT_PATH))


def _email_id(config: RunnableConfig) -> str:
    return config["configurable"]["email_id"]

@tool
def find_application(company: str, role: str,config: RunnableConfig) -> dict:
    """Look up an application by company and role. Call this first to check
    whether the application is already being tracked."""
    row = sheet.find_application(company, role,path=_path(config))
    return row if row else {"found": False}


@tool
def add_application(company: str, role: str, config: RunnableConfig,
                    date_applied: str = "", company_email: str = "",
                    website: str = "") -> dict:
    """Start tracking a NEW application. Use for 'thanks for applying' /
    'application received' emails, or before scheduling an interview for an
    application that is not tracked yet. Dates: YYYY-MM-DD."""
    return sheet.add_application(company, role, email_id=_email_id(config),
                                 date_applied=date_applied,
                                 company_email=company_email, website=website,path=_path(config))

@tool
def update_status(company: str, role: str, status: Status,
                  config: RunnableConfig) -> dict:
    """Change the status of a tracked application, e.g. Rejected, Offer,
    Screening (online test / recruiter call), Interviewed."""
    return sheet.update_status(company, role, status, email_id=_email_id(config),path=_path(config))


@tool
def schedule_interview(company: str, role: str, interview_date: str,
                       config: RunnableConfig,
                       round_number: int | None = None) -> dict:
    """Record an interview invite for a tracked application. interview_date:
    'YYYY-MM-DD HH:MM'. Omit round_number unless the email states it."""
    return sheet.schedule_interview(company, role, interview_date,
                                    email_id=_email_id(config),
                                    round_number=round_number,path=_path(config))


@tool
def update_details(company: str, role: str, config: RunnableConfig,
                   company_email: str | None = None, website: str | None = None,
                   company_review: str | None = None) -> dict:
    """Fill in contact email, company website, or notes about the company."""
    return sheet.update_details(company, role, email_id=_email_id(config),
                                company_email=company_email, website=website,
                                company_review=company_review)


TOOLS = [find_application, add_application, update_status,
         schedule_interview, update_details]
