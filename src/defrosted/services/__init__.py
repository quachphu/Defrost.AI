"""Application services: orchestrate domain objects + repositories.

Services contain business rules and transaction boundaries. They never touch
HTTP (that's the API layer) and never write SQL (that's the repository layer).
"""
