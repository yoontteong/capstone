from flask import Blueprint

community = Blueprint("community", __name__)

from . import posts
from . import reviews
from . import matches