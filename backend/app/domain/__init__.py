"""Business rules, expressed as pure functions over data.

Nothing here imports FastAPI or opens a database connection. Keeping the rules separate
from the plumbing means they can be tested exhaustively in milliseconds, and read by
someone who wants to know how booking works without learning the web framework first.
"""
