# -*- coding:utf-8 -*-
# @Time : 2020/2/26 12:29
# @Author : TianWei
# @File : web_client.py
# @Software: PyCharm
# @Organization : NJU
# @email : cleverzhangw@qq.com

from flask import Flask, request, redirect, url_for, render_template


app = Flask(__name__)

@app.route('/')
def hello_world():
	return render_template("index.html")

@app.route('/question_answer')
def question_answer():
	return render_template('question_answer.html')


if __name__ == '__main__':
	app.run(host="0.0.0.0",port=8000,debug=True)


