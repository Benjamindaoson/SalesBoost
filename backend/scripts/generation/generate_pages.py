#!/usr/bin/env python3
# -*- coding: utf-8 -*-

student_tasks_html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>任务管理 - SalesBoost</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f7fa;color:#333}
.layout{display:flex;min-height:100vh}
.sidebar{width:240px;background:#fff;border-right:1px solid #e8e8e8;padding:20px 0;position:fixed;height:100vh}
.logo{padding:0 20px 30px;display:flex;align-items:center;gap:12px}
.logo-icon{width:44px;height:44px;background:linear-gradient(135deg,#667eea,#764ba2);border-radius:10px;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:bold;font-size:20px}
.menu-item{padding:14px 24px;display:flex;align-items:center;gap:12px;cursor:pointer;transition:all .3s;color:#666;font-size:14px;margin:4px 12px;border-radius:8px}
.menu-item:hover,.menu-item.active{background:#f0f2ff;color:#667eea}
.main{flex:1;margin-left:240px;padding:24px 32px}
.header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:24px}
.header h1{font-size:24px;color:#1a1a1a}
.btn{padding:10px 20px;border-radius:8px;border:none;cursor:pointer;font-size:14px}
.btn-primary{background:#667eea;color:#fff}
.btn-default{background:#fff;border:1px solid #d9d9d9;color:#666}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:20px;margin-bottom:24px}
.stat-card{background:#fff;padding:24px;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.04)}
.stat-value{font-size:36px;font-weight:600;color:#1a1a1a}
.content-card{background:#fff;border-radius:12px;padding:24px;box-shadow:0 2px 8px rgba(0,0,0,0.04)}
table{width:100%;border-collapse:collapse}
th,td{padding:16px 12px;text-align:left;border-bottom:1px solid #f0f0f0;font-size:14px}
th{background:#fafafa;color:#666;font-weight:500}
.tag{display:inline-block;padding:4px 12px;border-radius:4px;font-size:12px;margin-right:6px;background:#e6f7ff;color:#1890ff}
</style>
</head>
<body>
<div class="layout">
<div class="sidebar">
<div class="logo">
<div class="logo-icon">AI</div>
<div><h2 style="font-size:16px">SalesBoost</h2><div style="font-size:12px;color:#999">学员端</div></div>
</div>
<div class="menu-item active">📋 任务管理</div>
<div class="menu-item" onclick="location.href='persona.html'">👤 客户预演</div>
<div class="menu-item" onclick="location.href='history.html'">📊 历史记录</div>
</div>
<div class="main">
<div class="header">
<div><h1>任务管理</h1><div style="color:#999;font-size:14px">查看所有学习任务</div></div>
<div>
<button class="btn btn-default" onclick="location.href='/admin/'">切换到管理端</button>
<button class="btn btn-primary">查看H5版本</button>
</div>
</div>
<div class="stats">
<div class="stat-card"><div style="color:#666;font-size:14px;margin-bottom:12px">全部任务</div><div class="stat-value">5</div></div>
<div class="stat-card"><div style="color:#666;font-size:14px;margin-bottom:12px">进行中</div><div class="stat-value">3</div></div>
<div class="stat-card"><div style="color:#666;font-size:14px;margin-bottom:12px">已完成</div><div class="stat-value">1</div></div>
<div class="stat-card"><div style="color:#666;font-size:14px;margin-bottom:12px">平均分数</div><div class="stat-value">84</div></div>
</div>
<div class="content-card">
<table>
<tr><th>课程名称</th><th>任务信息</th><th>状态</th><th>时间范围</th><th>进度</th><th>操作</th></tr>
<tr>
<td><div style="font-weight:500">新客户开卡场景训练</div><div style="color:#999;font-size:12px">刘先生（27岁，互联网行业）</div></td>
<td><span class="tag">新人培训</span><span class="tag" style="background:#f6ffed;color:#52c41a">必修</span></td>
<td><span class="tag">进行中</span></td>
<td>2024-12-01 至 2024-12-31</td>
<td>完成度 3/5</td>
<td><button class="btn btn-primary" style="padding:6px 12px;font-size:12px">去练习</button></td>
</tr>
<tr>
<td><div style="font-weight:500">异议处理训练</div><div style="color:#999;font-size:12px">王女士（35岁，金融行业）</div></td>
<td><span class="tag" style="background:#fff7e6;color:#fa8c16">技能提升</span></td>
<td><span class="tag" style="background:#f5f5f5;color:#999">未开始</span></td>
<td>2024-12-10 至 2024-12-25</td>
<td>完成度 0/3</td>
<td><button class="btn btn-primary" style="padding:6px 12px;font-size:12px">去练习</button></td>
</tr>
</table>
</div>
</div>
</div>
</body>
</html>'''

with open('/root/salesboost/webapp/student/index.html', 'w') as f:
    f.write(student_tasks_html)

print('Student tasks page created successfully')
