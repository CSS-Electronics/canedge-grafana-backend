from flask import Blueprint

alive = Blueprint('alive', __name__)

@alive.route('/',methods=['GET'])
def alive_view():
    """
    Lets the frontend know that the backend is working
    """
    return "OK"