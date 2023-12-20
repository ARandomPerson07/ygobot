from flask import Flask

app = Flask(__name__)


@app.route("/")
def hello_world():
    return "<p>Hello, World! Debug</p>"


@app.route("/docs")
def hello_docs():
    return "<p>Hello, endpoint!</p>"
