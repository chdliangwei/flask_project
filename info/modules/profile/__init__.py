from flask import Blueprint

profile_blu = Blueprint('profile_blu',__name__,url_prefix="/profile")

from . import views