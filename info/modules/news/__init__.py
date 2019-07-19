from flask import Blueprint

news_blu = Blueprint('news_blu',__name__,url_prefix="/news")

from . import views