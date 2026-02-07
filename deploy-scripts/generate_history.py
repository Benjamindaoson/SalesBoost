#!/usr/bin/env python3
# -*- coding: utf-8 -*-

history_html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>历史记录 - 销冠AI系统</title>
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
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:20px;margin-bottom:24px}
.stat-card{background:#fff;padding:24px;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.04)}
.stat-value{font-size:36px;font-weight:600;color:#1a1a1a}
.content-card{background:#fff;border-radius:12px;padding:24px;box-shadow:0 2px 8px rgba(0,0,0,0.04)}
table{width:100%;border-collapse:collapse}
th,td{padding:16px 12px;text-align:left;border-bottom:1px solid #f0f0f0;font-size:14px}
th{background:#fafafa;color:#666;font-weight:500}
.tag{display:inline-block;padding:4px 12px;border-radius:4px;font-size:12px;margin-right:6px;background:#e6f7ff;color:#1890ff}
.score{font-size:24px;font-weight:600}
.score-high{color:#52c41a}
.score-mid{color:#fa8c16}
</style>
</head>
<body>
<div class="layout">
<div class="sidebar">
<div class="logo">
<div class="logo-icon">AI</div>
<div><h2 style="font-size:16px">销冠AI系统</h2><div style="font-size:12px;color:#999">学员端</div></div>
</div>
<div class="menu-item" onclick="location.href='index.html'">📋 任务管理</div>
<div class="menu-item" onclick="location.href='persona.html'">👤 客户预演</div>
<div class="menu-item active">📊 历史记录</div>
</div>
<div class="main">
<div class="header">
<div><h1>历史记录</h1><div style="color:#999;font-size:14px">查看所有陪练记录</div></div>
</div>
<div class="stats">
<div class="stat-card"><div style="color:#666;font-size:14px;margin-bottom:12px">总陪练次数</div><div class="stat-value">8</div></div>
<div class="stat-card"><div style="color:#666;font-size:14px;margin-bottom:12px">平均分数</div><div class="stat-value">82</div></div>
<div class="stat-card"><div style="color:#666;font-size:14px;margin-bottom:12px">最高分数</div><div class="stat-value">92</div></div>
<div class="stat-card"><div style="color:#666;font-size:14px;margin-bottom:12px">总练习时长</div><div class="stat-value">120</div><div style="font-size:12px;color:#999">分钟</div></div>
</div>
<div class="content-card">
<table>
<tr><th>日期时间</th><th>课程信息</th><th>客户角色</th><th>类别</th><th>时长</th><th>得分</th><th>操作</th></tr>
<tr>
<td>2024-12-21<br>14:30</td>
<td>新客户开卡场景训练</td>
<td>刘先生<br>27岁·互联网行业</td>
<td><span class="tag">新客户开卡</span></td>
<td>15分32秒</td>
<td><span class="score score-high">85</span></td>
<td><button style="padding:6px 12px;border:1px solid #d9d9d9;background:#fff;border-radius:4px;cursor:pointer">查看详情</button></td>
</tr>
<tr>
<td>2024-12-20<br>10:15</td>
<td>异议处理训练</td>
<td>王女士<br>35岁·金融行业</td>
<td><span class="tag" style="background:#fff7e6;color:#fa8c16">异议处理</span></td>
<td>18分20秒</td>
<td><span class="score score-mid">78</span></td>
<td><button style="padding:6px 12px;border:1px solid #d9d9d9;background:#fff;border-radius:4px;cursor:pointer">查看详情</button></td>
</tr>
<tr>
<td>2024-12-19<br>16:45</td>
<td>权益推荐场景</td>
<td>李总<br>42岁·企业高管</td>
<td><span class="tag" style="background:#f6ffed;color:#52c41a">权益推荐</span></td>
<td>12分08秒</td>
<td><span class="score score-high">92</span></td>
<td><button style="padding:6px 12px;border:1px solid #d9d9d9;background:#fff;border-radius:4px;cursor:pointer">查看详情</button></td>
</tr>
<tr>
<td>2024-12-18<br>09:30</td>
<td>合规话术训练</td>
<td>张小姐<br>29岁·设计师</td>
<td><span class="tag" style="background:#f9f0ff;color:#722ed1">合规话术</span></td>
<td>14分15秒</td>
<td><span class="score score-high">82</span></td>
<td><button style="padding:6px 12px;border:1px solid #d9d9d9;background:#fff;border-radius:4px;cursor:pointer">查看详情</button></td>
</tr>
</table>
</div>
</div>
</div>
</body>
</html>'''

with open('/root/salesboost/webapp/student/history.html', 'w') as f:
    f.write(history_html)

print('History page created successfully')
