"""Minimal Flask entry point for AUTO-MAIL."""

from flask import Flask


app = Flask(__name__)


@app.get("/")
def index():
    """Provide a simple boot check while the application is scaffolded."""
    return "AUTO-MAIL is running."


if __name__ == "__main__":
    app.run(debug=True)
