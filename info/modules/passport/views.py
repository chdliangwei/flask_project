from datetime import datetime
from flask import request, current_app, make_response, jsonify, abort, session
from info.models import User
from info.utils.response_code import RET
from info import redis_store, constants, db
from . import passport_blu
from info.utils.captcha.captcha import captcha
import random
import re


@passport_blu.route('/image_code')
def get_image_code():
    '''
    生成图片验证码
    :return:
    '''
    # 1. 获取参数
    image_code = request.args.get('image_Code')
    print(image_code)
    # 2. 校验参数
    if not image_code:
        # 返回错误类型
        abort("403")
    # 3. 生成图片验证码
    name,text,image = captcha.generate_captcha()
    print(name)
    print(text)
    # 4. 保存图片验证码
    redis_store.setex('image_code_'+image_code,constants.IMAGE_CODE_REDIS_EXPIRES,text)
    # 5.返回图片验证码
    res = make_response(image)
    # res.headers["Content-Type"] = "image/jpg"
    res.content_type = 'image/jpg'
    return res


@passport_blu.route('/sms_code', methods=["POST"])
def send_sms_code():
    """
    发送短信的逻辑
    :return:
    """
    # 1.将前端参数转为字典
    mobile = request.json.get("mobile")
    image_code = request.json.get("image_code")
    image_code_id = request.json.get("image_code_id")
    print(mobile)
    print(image_code)
    # 2. 校验参数(参数是否符合规则，判断是否有值)
    # 判断参数是否有值
    if not all([mobile,image_code,image_code_id]):
        return jsonify(errno=RET.PARAMERR,errmsg="信息不全")
    if not re.match("^1[34578][0-9]{9}$", mobile):
        return jsonify(errno=RET.USERERR,errmsg="手机号输入错误")
    # 3. 先从redis中取出真实的验证码内容
    try:
        real_image_code = redis_store.get('image_code_' + image_code_id)
        print(real_image_code)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="数据库查询错误")
    if not real_image_code:
        return jsonify(errno=RET.DATAEXIST,errmsg="验证码已过期")
    # 4. 与用户的验证码内容进行对比，如果对比不一致，那么返回验证码输入错误
    if image_code != real_image_code:
        return jsonify(errno=RET.DATAERR,errmsg="验证码输入错误")
    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")

    if user:
        return jsonify(errno=RET.DATAEXIST, errmsg="该手机号已经被注册")
    # 5. 如果一致，生成短信验证码的内容(随机数据)
    number = random.randint(0,999999)
    sms_code = "%06d"%number
    print("短信验证码为：%s"%sms_code)
    # 6. 发送短信验证码

    # 保存验证码内容到redis
    redis_store.setex("SMS_"+mobile,constants.SMS_CODE_REDIS_EXPIRES,sms_code)
    # 7. 告知发送结果
    return jsonify(errno=RET.OK,errmsg="发送成功")


@passport_blu.route('/register', methods=["POST"])
def register():
    """
    注册功能
    :return:
    """

    # 1. 获取参数和判断是否有值
    mobile = request.json.get("mobile")
    sms_code = request.json.get("smscode")
    password = request.json.get("password")
    print(mobile)
    print(sms_code)
    print(password)
    if not all([mobile,sms_code,password]):
        return jsonify(errno=RET.PARAMERR,errmsg="信息不全")
    # 2. 从redis中获取指定手机号对应的短信验证码的
    try:
        real_sms_code = redis_store.get("SMS_"+mobile)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR,errmsg="数据库读取错误")
    if not real_sms_code:
        return jsonify(errno=RET.DATAEXIST,errmsg="验证码已过期")
    # 3. 校验验证码
    if sms_code != real_sms_code:
        return jsonify(errno=RET.DATAERR,errmsg="验证码输入错误")


    # 4. 初始化 user 模型，并设置数据并添加到数据库
    try:
        user = User()
        user.mobile = mobile
        user.nick_name = mobile
        user.password = password
        user.last_login = datetime.now()

        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="数据库存储错误")

    # 5. 保存用户登录状态
    session["user_id"] = user.id
    # session['mobile'] = user.mobile
    # session['password']=user.password
    # 6. 返回注册结果
    return jsonify(errno=RET.OK,errmsg="注册成功")


@passport_blu.route('/login', methods=["POST"])
def login():
    """
    登陆功能
    :return:
    """

    # 1. 获取参数和判断是否有值
    mobile = request.json.get("mobile")
    password = request.json.get("password")
    print(mobile)
    print(password)
    if not all([mobile,password]):
        return jsonify(errno=RET.DATAEXIST,errmsg="数据不全")
    # 2. 从数据库查询出指定的用户
    # user = User.query.filter_by(mobile=mobile).first()
    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg="数据库查询失败")
    print(user)
    if not user:
        return jsonify(errno=RET.DATAEXIST,errmsg="用户不存在")
    # 3. 校验密码
    # if password != user.password:
    if not user.check_password(password):
        return jsonify(errno=RET.LOGINERR,errmsg="密码输入错误")
    # 4. 保存用户登录状态
    session["user_id"] = user.id
    # 5. 登录成功返回
    return jsonify(errno=RET.OK,errmsg="登录成功")


@passport_blu.route("/logout", methods=['POST'])
def logout():
    """
    清除session中的对应登录之后保存的信息
    :return:
    """
    # 返回结果
    session.pop('user_id', None)
    return jsonify(errno=RET.OK,errmsg="已退出")