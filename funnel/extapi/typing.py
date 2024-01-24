"""Common types and data structures."""

from typing import TypedDict

__all__ = ['ExtTicketsDict']


class ExtTicketsDict(TypedDict):
    fullname: str
    email: str
    phone: str
    twitter: str | None
    job_title: str
    company: str
    city: str
    ticket_no: str
    ticket_type: str
    order_no: str
    status: str | None
