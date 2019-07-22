from flask import render_template, g, request, jsonify, redirect, current_app, abort

from info import db, constants
from info.models import Category, News, User
from info.modules.profile import profile_blu
from info.utils.common import user_login_data
from info.utils.image_storage import storage
from info.utils.response_code import RET


@profile_blu.route('/info')
@user_login_data
def user_info():
    # 如果用户登陆则进入个人中心
    user = g.user
    # 如果没有登陆,跳转主页
    if not user:
        return redirect("/")
    # 返回用户数据
    else:
        data = {"user":user.to_dict()}
        return render_template('news/user.html',data=data)


@profile_blu.route('/base_info', methods=["GET", "POST"])
@user_login_data
def base_info():
    user = g.user
    # 不同的请求方式，做不同的事情
    # 获取请求方式
    method = request.method
    # 如果是GET请求,返回用户数据
    if method == "GET":
        return render_template('news/user_base_info.html')
    else:
        # 修改用户数据
        # 获取传入参数
        signature = request.json.get("signature")
        nick_name = request.json.get("nick_name")
        gender = request.json.get("gender")
    # 校验参数
        if not all([signature, nick_name, gender]):
            return jsonify(errno=RET.NODATA, errmsg="数据不全")
        if gender not in ['MAN','WOMAN']:
            return jsonify(errno=RET.DATAERR, errmsg="数据错误")
	# 修改用户数据
        user.signature = signature
        user.nick_name = nick_name
        user.gender = gender
        try:
            db.session.add(user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(e)
            return jsonify(errno=RET.DATAERR,errmsg="数据添加失败")
        else:
            # 返回
            return jsonify(errno=RET.OK,errmsg="修改信息成功")


@profile_blu.route('/pic_info', methods=["GET", "POST"])
@user_login_data
def pic_info():
    # 如果是GET请求,返回用户数据
    user = g.user
    method = request.method
    if method == "GET":
        return render_template('news/user_pic_info.html', data={"user_info": user.to_dict()})
    else:
        # 如果是POST请求表示修改头像
        # 1. 获取到上传的图片
        picture = request.files.get('pic')
    # 2. 上传头像
        # 使用自已封装的storage方法去进行图片上传
        try:
            index_image_data = picture.read()
            # 上传到七牛云
            key = storage(index_image_data)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.PARAMERR, errmsg="参数有误")
    # 3. 保存头像地址
        avatar_url = key
        data = {"avatar_url":avatar_url}
    # 拼接url并返回数据
        return jsonify(errno=RET.OK,errmsg="头像上传成功")


@profile_blu.route('/pass_info', methods=["GET", "POST"])
@user_login_data
def pass_info():
    user = g.user
    # GET请求,返回
    if request.method == "GET":
        return render_template('news/user_pass_info.html')
    else:
        # 1. 获取参数
        old_password = request.json.get("old_password")
        new_password = request.json.get("new_password")

    # 2. 校验参数
    if not all([old_password,new_password]):
        return jsonify(errno=RET.DATAERR,errmsg="密码数据不全")
    # 3. 判断旧密码是否正确
    if not user.check_password(old_password):
        return jsonify(errno=RET.PWDERR,errmsg="密码输入错误")

    # 4. 设置新密码
    user.password = new_password
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
    else:
        # 返回
        return jsonify(errno=RET.OK,errmsg="密码修改成功")


@profile_blu.route('/collection')
@user_login_data
def user_collection():
    # 1. 获取参数
    user = g.user
    page = request.args.get("p",'1')
    # 2. 判断参数
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    # 3. 查询用户指定页数的收藏的新闻
    collect_news = user.collection_news.paginate(page,constants.USER_COLLECTION_MAX_NEWS,False)

        # 进行分页数据查询
    # 生成模型对象
    collections_li = collect_news.items
        # 当前页数
    current_page = collect_news.page
        # 总页数
    total_page = collect_news.pages
        # 总数据
    news_collect_li = []
    for news in collections_li:
        news_collect_li.append(news.to_review_dict())

    # 收藏列表
    data = {
        "collections":news_collect_li,
        "current_page":current_page,
        "total_page":total_page
    }
	# 返回数据
    return render_template('news/user_collection.html',data=data)


@profile_blu.route('/news_release', methods=["GET", "POST"])
@user_login_data
def news_release():
    user = g.user
    method = request.method
    # GET请求
    if method == "GET":
    # 1. 加载新闻分类数据
        category_all = Category.query.all()
    # 2. 移除最新分类
        category_all.pop(0)
    # 返回数据
        categories = []
        for category_abj in category_all:
            categories.append(category_abj.to_dict())
        data = {
            "categories":categories
        }
        return render_template('news/user_news_release.html',data=data)
    else:
        # 1. 获取要提交的数据
        title = request.form.get("title")
        category_id = request.form.get("category_id")
        digest = request.form.get("digest")
        content = request.form.get("content")
        print(title,category_id,digest,content)
        # index_image = request.files.get("index_image")
        # 校验参数
        if not all([title,category_id,digest,content]):
            return jsonify(errno=RET.NODATA,errmsg="接收数据不全")
        try:
            category_id = int(category_id)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DATAERR,errmsg="数据类型错误")

    # 3.取到图片，将图片上传到七牛云
    # try:
    #     index_image_data = index_image.read()
    #     # 上传到七牛云
    #     key = storage(index_image_data)
    # except Exception as e:
    #     current_app.logger.error(e)
    #     return jsonify(errno=RET.PARAMERR, errmsg="参数有误")

        # 保存数据
        news = News()
        news.title = title
        news.category_id = category_id
        news.digest = digest
        news.content = content
        # news.index_image_url = key
        news.source = "个人发布"
        # 新闻状态,将新闻设置为1代表待审核状态
        news.status = 1
        news.user_id=user.id

        # 手动设置新闻状态,在返回前commit提交
        try:
            db.session.add(news)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR,errmsg="数据库存储错误")
    # 返回
    #     print(news.to_dict())
        return jsonify(errno=RET.OK,errmsg="发布成功")


# @profile_blu.route('/news_list')
# @user_login_data
# def user_news_list():
#     return render_template('news/user_news_list.html')

@profile_blu.route('/news_list')
@user_login_data
def user_news_list():
	# 查询数据
    user = g.user
    page = request.args.get("g","1")
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR,errmsg="数据类型错误")
    release_news = News.query.filter(News.user_id==user.id).paginate(page,10,False)
    release_news_li = release_news.items
    current_page = release_news.page
    total_page = release_news.pages
    # 返回数据
    news_list = []
    for news in release_news_li:
        news_list.append(news.to_dict())
    data = {
        "news_list":news_list,
        "current_page":current_page,
        "total_page":total_page
    }
    return render_template('news/user_news_list.html',data=data)

@profile_blu.route('/user_follow')
@user_login_data
def user_follow():
    # 获取页数
    p = request.args.get("p", 1)
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1

    user = g.user

    follows = []
    current_page = 1
    total_page = 1
    try:
        paginate = user.followed.paginate(p, constants.USER_FOLLOWED_MAX_COUNT, False)
        # 获取当前页数据
        follows = paginate.items
        # 获取当前页
        current_page = paginate.page
        # 获取总页数
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    user_dict_li = []

    for follow_user in follows:
        user_dict_li.append(follow_user.to_dict())
    data = {"users": user_dict_li, "total_page": total_page, "current_page": current_page}
    return render_template('news/user_follow.html', data=data)


@profile_blu.route('/other_info')
@user_login_data
def other_info():
    user = g.user

    # 去查询其他人的用户信息
    other_id = request.args.get("user_id")
    print(other_id)

    if not other_id:
        abort(404)

    # 查询指定id的用户信息
    other = None
    try:
        other = User.query.get(other_id)
    except Exception as e:
        current_app.logger.error(e)

    if not other:
        abort(404)

    # 判断当前登录用户是否关注过该用户
    is_followed = False
    if other and user:
        if other in user.followed:
            is_followed = True

    data = {
        "is_followed": is_followed,
        "user": g.user.to_dict() if g.user else None,
        "other_info": other.to_dict()
    }
    return render_template('news/other.html', data=data)


@profile_blu.route('/other_news_list')
def other_news_list():
    """返回指定用户的发布的新闻"""

    # 1. 取参数
    other_id = request.args.get("user_id")
    page = request.args.get("p", 1)
    print(other_id)
    # 2. 判断参数
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        other = User.query.get(other_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询失败")

    if not other:
        return jsonify(errno=RET.NODATA, errmsg="当前用户不存在")

    try:
        paginate = other.news_list.paginate(page, constants.USER_COLLECTION_MAX_NEWS, False)
        # 获取当前页数据
        news_li = paginate.items
        # 获取当前页
        current_page = paginate.page
        # 获取总页数
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询失败")

    news_dict_list = []
    for news_item in news_li:
        news_dict_list.append(news_item.to_basic_dict())

    data = {
        "news_list": news_dict_list,
        "total_page": total_page,
        "current_page": current_page
    }
    return jsonify(errno=RET.OK, errmsg="OK", data=data)





