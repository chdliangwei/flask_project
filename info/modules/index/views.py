from . import index_blu
from flask import render_template, session, current_app, request, jsonify
from info.models import User, News, Category
from info.utils.response_code import RET


# 测试
# @index_blu.route('/')
# def index():
#     # return '<h1>index-text</h1>'
#     user_id = session.get("user_id")
#     user = User.query.filter_by(id=user_id).first()
#     data = {
#         "user":user
#     }
#
#     return render_template('news/index.html',data=data)


@index_blu.route('/')
def index():
    # 获取到当前登录用户的id
    user_id = session.get("user_id")
    user = None
    try:
        user = User.query.filter_by(id=user_id).first()
    except Exception as e:
        current_app.logger.error(e)
    # 右侧新闻排行
    clicks_news = []
    try:
        clicks_news = News.query.order_by(News.clicks.desc()).limit(10).all()
    except Exception as e:
        current_app.logger.error(e)
    # 按照点击量排序查询出点击最高的前10条新闻
    # 将对象字典添加到列表中
    clicks_news_li = []
    for news_abj in clicks_news:
        clicks_news_dict = news_abj.to_basic_dict()
        clicks_news_li.append(clicks_news_dict)


    # 获取新闻分类数据
    category_all = Category.query.all()
    # 定义列表保存分类数据
    categories = []
    for category_abj in category_all:
        category_dict = category_abj.to_dict()
        categories.append(category_dict)
    # 拼接内容
	# 返回数据
    data = {
        "user":user,
        "news_dict":clicks_news_li,
        "categories":categories
    }
    return render_template('news/index.html',data=data)


@index_blu.route('/news_list')
def news_list():
    """
    获取首页新闻数据
    :return:
    """

    # 1. 获取参数,并指定默认为最新分类,第一页,一页显示10条数据
    cid = request.args.get("cid",'5')
    page = request.args.get("page",'1')
    per_page = request.args.get("per_page",'10')

    # 2. 校验参数
    try:
        cid,page,per_page = int(cid),int(page),int(per_page)
    except Exception as e:
        return jsonify(errno=RET.DATAERR,errmsg="数据转化错误")

	  # 默认选择最新数据分类
    filters = [News.category_id==5]
    # 3. 查询数据
    if cid > 5:
        filters.append(News.category_id==cid)
    # 按照分类id进行过滤，按新闻发布时间排序，对查询数据进行分类
    paginate = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page,per_page,False)
    # paginate(页数，每页显示多少条，分页异常不报错）
    # 获取分页后的新闻数据模型对象，总页数及当前页数
    news_list = paginate.items  #模型对象
    total_page = paginate.pages  #总页数
    current_page = paginate.page  #当前页数
    # 将模型对象列表转成字典列表
    news_dict_list = []
    for news in news_list:
        news_dict_list.append(news.to_dict())


	#返回数据
    data = {
        "news_dict_list":news_dict_list,
        "cid":cid,
        "total_page":total_page,
        "current_page":current_page

    }
    return jsonify(errno=RET.OK,errmsg="查询成功",data=data)