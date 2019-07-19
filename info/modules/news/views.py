from flask import render_template, current_app, jsonify, abort, request

from info import db
from info.models import News, Comment, CommentLike, User
from info.utils.common import user_login_data
from info.utils.response_code import RET
from . import news_blu
from flask import g


# @news_blu.route('/<int:news_id>')
# def news_detail(news_id):
#     data = {}
#     return render_template('news/detail.html', data=data)


@news_blu.route('/<int:news_id>')
@user_login_data
def news_detail(news_id):
	# ......
    user = g.user
    # if not user:
    #     return jsonify(errno=RET.DATAEXIST,errmsg="g变量获取失败")
    # 查询新闻数据
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
    # 校验报404错误
    if not news:
        # return jsonify(errno=RET.DBERR, errmsg="数据库查询失败")
        abort(404)
    # 进入详情页后要更新新闻的点击次数
    news.clicks += 1

    # 获取当前新闻最新的评论,按时间排序
    comments = []
    comments = Comment.query.filter(Comment.news_id==news_id).order_by(Comment.create_time.desc()).all()
    # 如果用户登陆
    comment_like_ids = []
    if user:
        # 查询当前新闻所有评论ID,按时间排序
        comment_ids = [ Comment.id for comment in comments ]
        # 查询当前新闻所有评论哪些被当前用户点赞
        comment_likes = CommentLike.query.filter(CommentLike.comment_id.in_(comment_ids),CommentLike.user_id==user.id).all()
        # 取出所有被点赞评论ID
        comment_like_ids = [comment_like.comment_id for comment_like in comment_likes ]
    # 遍历评论id,将评论属性赋值
    # 定义列表保存所有评论内容
    comment_dict_li = []
    for comment in comments:
        comment_dict = comment.to_dict()
        # 为评论增加'is_like'字段,判断是否点赞
        comment_dict['is_like'] = False
        # 判断用户是否在点赞评论里
        if comment.id in comment_like_ids:
            comment_dict["is_like"] = True
        comment_dict_li.append(comment_dict)
    # 判断是否收藏该新闻，默认值为 false
    is_collected = False
    # 判断用户是否收藏过该新闻
    if user and news in user.collection_news:
        is_collected = True

    # 右侧新闻排行
    clicks_news = []
    try:
        clicks_news = News.query.order_by(News.clicks.desc()).limit(10).all()
    except Exception as e:
        current_app.logger.error(e)
    clicks_news_li = []
    for news_abj in clicks_news:
        clicks_news_dict = news_abj.to_basic_dict()
        clicks_news_li.append(clicks_news_dict)

    # 当前登录用户是否关注当前新闻作者
    is_followed = False
    # 判断用户是否收藏过该新闻
    if news.user and user:
        if news.user in user.followed:
            is_followed = True
    # 返回数据
    data = {

        # ......
        # "user": g.user.to_dict() if g.user else None,
        "user": user.to_dict() if user else None,
        "news_dict": clicks_news_li,
        "news":news.to_dict(),
        "is_collected":is_collected,
        'is_followed': is_followed,
        "comments":comment_dict_li
    }
    return render_template('news/detail.html', data=data)


# 收藏后端
@news_blu.route("/news_collect", methods=['POST'])
@user_login_data
def news_collect():
    """新闻收藏"""

    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR,errmsg="用户未登录")
    # 获取参数
    action = request.json.get("action")
    news_id = request.json.get("news_id")
    # 判断参数
    if not all([action,news_id]):
        return jsonify(errno=RET.NODATA,errmsg="数据不完整")
    try:
        news_id = int(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR,errmsg="数据错误")
	# action在不在指定的两个值：'collect', 'cancel_collect'内
    if action not in ['collect', 'cancel_collect']:
        return jsonify(errno=RET.DATAERR,errmsg="数据错误")

    # 查询新闻,并判断新闻是否存在
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
    if not news:
        return jsonify(errno=RET.NODATA,errmsg="无此项新闻数据")

    # 收藏/取消收藏
    if action == "cancel_collect":
        # 取消收藏
        if news in user.collection_news:
            user.collection_news.remove(news)
            return jsonify(errno=RET.OK,errmsg="取消收藏成功")

    else:
        # 收藏
        if news not in user.collection_news:
            user.collection_news.append(news)
            return jsonify(errno=RET.OK, errmsg="收藏成功")


@news_blu.route('/news_comment', methods=["POST"])
@user_login_data
def add_news_comment():
    """添加评论"""

    # 用户是否登陆
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")
    # 获取参数
    news_id = request.json.get("news_id")
    comment = request.json.get("comment")
    parent_id = request.json.get("parent_id")

    # 判断参数是否正确
    if not all([news_id,comment]):
        return jsonify(errno=RET.NODATA,errmsg="数据不完整")
    try:
        news_id = int(news_id)
        if parent_id:
            parent_id = int(parent_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR,errmsg="数据错误")
    # 查询新闻是否存在并校验
    try:
        news = News.query.get(news_id)
        print(news)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")
    if not news:
        return jsonify(errno=RET.NODATA, errmsg="无此项新闻数据")
    # 初始化评论模型，保存数据
    try:
        comment_abj = Comment()
        comment_abj.user_id = user.id
        comment_abj.news_id = news_id
        comment_abj.content = comment
        if parent_id:
            comment_abj.parent_id = parent_id
        db.session.add(comment_abj)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="数据库存储错误")

    # 配置文件设置了自动提交,自动提交要在return返回结果以后才执行commit命令,如果有回复
    # 评论,先拿到回复评论id,在手动commit,否则无法获取回复评论内容
    # 返回响应
    data = {
        "user":user.to_dict(),
        "content":comment,
        "news_id":news_id
    }
    return jsonify(errno=RET.OK,errmsg="评论成功",data=data)


@news_blu.route('/comment_like', methods=["POST"])
@user_login_data
def comment_like():
    """
    评论点赞
    :return:
    """
    # 用户是否登陆
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")
    # 取到请求参数
    comment_id = request.json.get("comment_id")
    print(comment_id)
    action = request.json.get("action")
    # 判断参数
    if not all([comment_id,action]):
        return jsonify(errno=RET.NODATA,errmsg="数据不全")
    try:
        comment_id = int(comment_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR,errmsg="数据类型错误")
    if action not in ["add","remove"]:
        return jsonify(errno=RET.DATAERR, errmsg="数据不在范围内")
    # 获取到要被点赞的评论模型
    try:
        comment = Comment.query.get(comment_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="数据库查询错误")
    # # 查询当前评论所有点赞
    # try:
    #     comment_likes = CommentLike.query.filter(CommentLike.id==comment_id).all()
    # except Exception as e:
    #     current_app.logger.error(e)
    #     return jsonify(errno=RET.DBERR,errmsg="数据库查询错误")
	# action的状态,如果点赞,则查询后将用户id和评论id添加到数据库

    if action == "add":
        comment_like = CommentLike.query.filter(CommentLike.user_id==user.id,
                                                CommentLike.comment_id==comment_id).first()
        if not comment_like:
            comment_like = CommentLike()
            comment_like.comment_id = comment_id
            comment_like.user_id = user.id
            db.session.add(comment_like)
            db.session.commit()

            # 点赞评论
            # 更新点赞次数
            comment.like_count +=1
            return jsonify(errno=RET.OK,errmsg="点赞成功")
        # 取消点赞评论,查询数据库,如果以点在,则删除点赞信息
    else:
        comment_like = CommentLike.query.filter(CommentLike.user_id == user.id,
                                                CommentLike.comment_id == comment_id).first()
        if comment_like:
            db.session.delete(comment_like)
            # 更新点赞次数
            comment.like_count -= 1
            # 返回结果
            return jsonify(errno=RET.OK, errmsg="点赞成功")


@news_blu.route('/followed_user', methods=["POST"])
@user_login_data
def followed_user():
    """关注或者取消关注用户"""

    # 获取自己登录信息
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="未登录")

    # 获取参数
    user_id = request.json.get("user_id")
    action = request.json.get("action")

    # 判断参数
    if not all([user_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    if action not in ("follow", "unfollow"):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 获取要被关注的用户
    try:
        other = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")

    if not other:
        return jsonify(errno=RET.NODATA, errmsg="未查询到数据")

    if other.id == user.id:
        return jsonify(errno=RET.PARAMERR, errmsg="请勿关注自己")

    # 根据要执行的操作去修改对应的数据
    if action == "follow":
        if other not in user.followed:
            # 当前用户的关注列表添加一个值
            user.followed.append(other)
        else:
            return jsonify(errno=RET.DATAEXIST, errmsg="当前用户已被关注")
    else:
        # 取消关注
        if other in user.followed:
            user.followed.remove(other)
        else:
            return jsonify(errno=RET.DATAEXIST, errmsg="当前用户未被关注")

    return jsonify(errno=RET.OK, errmsg="操作成功")

