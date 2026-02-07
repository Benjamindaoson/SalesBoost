#!/usr/bin/env python3
# -*- coding: utf-8 -*-

persona_html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>客户预演 - 销冠AI系统</title>
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
.content-card{background:#fff;border-radius:12px;padding:24px;box-shadow:0 2px 8px rgba(0,0,0,0.04)}
.persona-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-top:20px}
.persona-card{background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.04);transition:all .3s}
.persona-card:hover{transform:translateY(-4px);box-shadow:0 8px 24px rgba(0,0,0,0.1)}
.persona-header{height:140px;background:linear-gradient(135deg,#667eea,#764ba2);display:flex;align-items:center;justify-content:center}
.persona-avatar{width:80px;height:80px;border-radius:50%;background:rgba(255,255,255,0.2);display:flex;align-items:center;justify-content:center;font-size:40px;border:3px solid rgba(255,255,255,0.3)}
.persona-body{padding:20px}
.persona-name{font-size:16px;font-weight:600;margin-bottom:8px}
.persona-desc{font-size:13px;color:#666;line-height:1.6;margin-bottom:16px;height:40px;overflow:hidden}
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
<div class="menu-item active">👤 客户预演</div>
<div class="menu-item" onclick="location.href='history.html'">📊 历史记录</div>
</div>
<div class="main">
<div class="header">
<div><h1>客户预演</h1><div style="color:#999;font-size:14px">创建个性化客户画像</div></div>
<button class="btn btn-primary">+ 新建预演角色</button>
</div>
<div class="persona-grid">
<div class="persona-card">
<div class="persona-header"><div class="persona-avatar">👨</div></div>
<div class="persona-body">
<div class="persona-name">刘先生</div>
<div class="persona-desc">27岁，互联网行业程序员，商旅需求高</div>
<button class="btn btn-primary" style="width:100%">去预演</button>
</div>
</div>
<div class="persona-card">
<div class="persona-header"><div class="persona-avatar">👩</div></div>
<div class="persona-body">
<div class="persona-name">王女士</div>
<div class="persona-desc">35岁，金融行业，关注子女教育和理财</div>
<button class="btn btn-primary" style="width:100%">去预演</button>
</div>
</div>
<div class="persona-card">
<div class="persona-header"><div class="persona-avatar">👨‍💼</div></div>
<div class="persona-body">
<div class="persona-name">李总</div>
<div class="persona-desc">42岁，企业高管，追求高端服务和品质</div>
<button class="btn btn-primary" style="width:100%">去预演</button>
</div>
</div>
<div class="persona-card">
<div class="persona-header"><div class="persona-avatar">👩‍🎨</div></div>
<div class="persona-body">
<div class="persona-name">张小姐</div>
<div class="persona-desc">29岁，设计师，注重生活品质和消费体验</div>
<button class="btn btn-primary" style="width:100%">去预演</button>
</div>
</div>
<div class="persona-card">
<div class="persona-header"><div class="persona-avatar">👨‍💼</div></div>
<div class="persona-body">
<div class="persona-name">赵经理</div>
<div class="persona-desc">38岁，销售行业，经常出差，追求效率</div>
<button class="btn btn-primary" style="width:100%">去预演</button>
</div>
</div>
<div class="persona-card">
<div class="persona-header"><div class="persona-avatar">👩‍🏫</div></div>
<div class="persona-body">
<div class="persona-name">周女士</div>
<div class="persona-desc">45岁，教育行业，注重子女教育和家庭理财</div>
<button class="btn btn-primary" style="width:100%">去预演</button>
</div>
</div>
</div>
</div>
</div>
</body>
</html>'''

with open('/root/salesboost/webapp/student/persona.html', 'w') as f:
    f.write(persona_html)

print('Persona page created successfully')
