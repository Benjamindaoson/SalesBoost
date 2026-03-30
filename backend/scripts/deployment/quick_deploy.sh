#!/bin/bash

###############################################################################
# SalesBoost 腾讯云快速部署脚本
# 服务器: 106.53.168.252
# 部署方案: 快速开始（自建数据库、本地存储、简单认证）
###############################################################################

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 显示横幅
show_banner() {
    clear
    echo -e "${BLUE}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ███████╗ █████╗ ██╗     ███████╗███████╗               ║
║   ██╔════╝██╔══██╗██║     ██╔════╝██╔════╝               ║
║   ███████╗███████║██║     █████╗  ███████╗               ║
║   ╚════██║██╔══██║██║     ██╔══╝  ╚════██║               ║
║   ███████║██║  ██║███████╗███████╗███████║               ║
║   ╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝               ║
║                                                           ║
║          腾讯云快速部署 - 10分钟上线！                    ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

# 更新系统
update_system() {
    log_info "更新系统包..."
    apt-get update -y
    apt-get upgrade -y
    log_success "系统更新完成"
}

# 安装基础工具
install_basic_tools() {
    log_info "安装基础工具..."
    apt-get install -y \
        curl \
        wget \
        git \
        vim \
        htop \
        net-tools \
        ufw
    log_success "基础工具安装完成"
}

# 安装PostgreSQL
install_postgresql() {
    log_info "安装PostgreSQL..."

    if command -v psql &> /dev/null; then
        log_success "PostgreSQL已安装"
        return
    fi

    apt-get install -y postgresql postgresql-contrib
    systemctl start postgresql
    systemctl enable postgresql

    # 创建数据库和用户
    log_info "配置数据库..."
    sudo -u postgres psql << EOF
CREATE USER salesboost WITH PASSWORD 'salesboost2026';
CREATE DATABASE salesboost OWNER salesboost;
GRANT ALL PRIVILEGES ON DATABASE salesboost TO salesboost;
EOF

    log_success "PostgreSQL安装配置完成"
}

# 安装Redis
install_redis() {
    log_info "安装Redis..."

    if command -v redis-server &> /dev/null; then
        log_success "Redis已安装"
        return
    fi

    apt-get install -y redis-server

    # 配置Redis密码
    sed -i 's/# requirepass foobared/requirepass salesboost2026/' /etc/redis/redis.conf

    systemctl restart redis-server
    systemctl enable redis-server

    log_success "Redis安装配置完成"
}

# 安装Python 3.11
install_python() {
    log_info "安装Python 3.11..."

    if command -v python3.11 &> /dev/null; then
        log_success "Python 3.11已安装"
        return
    fi

    apt-get install -y software-properties-common
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update -y
    apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip

    # 设置默认Python版本
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

    log_success "Python 3.11安装完成"
}

# 安装Node.js
install_nodejs() {
    log_info "安装Node.js..."

    if command -v node &> /dev/null; then
        log_success "Node.js已安装: $(node --version)"
        return
    fi

    curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
    apt-get install -y nodejs

    log_success "Node.js安装完成: $(node --version)"
}

# 安装Nginx
install_nginx() {
    log_info "安装Nginx..."

    if command -v nginx &> /dev/null; then
        log_success "Nginx已安装"
        return
    fi

    apt-get install -y nginx
    systemctl start nginx
    systemctl enable nginx

    log_success "Nginx安装完成"
}

# 配置防火墙
configure_firewall() {
    log_info "配置防火墙..."

    ufw --force enable
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow 22/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw allow 3000/tcp
    ufw allow 8000/tcp

    log_success "防火墙配置完成"
}

# 克隆代码
clone_code() {
    log_info "准备代码..."

    DEPLOY_DIR="/opt/salesboost"

    if [ -d "$DEPLOY_DIR" ]; then
        log_info "代码目录已存在，跳过克隆"
    else
        log_info "创建部署目录..."
        mkdir -p $DEPLOY_DIR

        # 这里假设代码已经在本地，需要上传
        log_warning "请确保代码已上传到 $DEPLOY_DIR"
    fi

    cd $DEPLOY_DIR
    log_success "代码准备完成"
}

# 安装后端依赖
install_backend_deps() {
    log_info "安装后端依赖..."

    cd /opt/salesboost

    # 创建虚拟环境
    python3.11 -m venv venv
    source venv/bin/activate

    # 升级pip
    pip install --upgrade pip

    # 安装依赖
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        log_warning "未找到requirements.txt，跳过依赖安装"
    fi

    log_success "后端依赖安装完成"
}

# 安装前端依赖
install_frontend_deps() {
    log_info "安装前端依赖..."

    cd /opt/salesboost/frontend

    if [ -f "package.json" ]; then
        npm install
        npm run build
    else
        log_warning "未找到package.json，跳过前端构建"
    fi

    log_success "前端依赖安装完成"
}

# 配置环境变量
configure_env() {
    log_info "配置环境变量..."

    cd /opt/salesboost

    # 复制环境变量文件
    if [ -f "env.production" ]; then
        cp env.production .env
        log_success "环境变量配置完成"
    else
        log_error "未找到env.production文件"
        exit 1
    fi
}

# 初始化数据库
init_database() {
    log_info "初始化数据库..."

    cd /opt/salesboost
    source venv/bin/activate

    # 运行数据库迁移（如果有）
    if [ -f "alembic.ini" ]; then
        alembic upgrade head
    fi

    log_success "数据库初始化完成"
}

# 配置systemd服务
configure_systemd() {
    log_info "配置systemd服务..."

    # 后端服务
    cat > /etc/systemd/system/salesboost-backend.service << 'EOF'
[Unit]
Description=SalesBoost Backend API
After=network.target postgresql.service redis-server.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/salesboost
Environment="PATH=/opt/salesboost/venv/bin"
ExecStart=/opt/salesboost/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # 前端服务（使用serve）
    npm install -g serve

    cat > /etc/systemd/system/salesboost-frontend.service << 'EOF'
[Unit]
Description=SalesBoost Frontend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/salesboost/frontend
ExecStart=/usr/bin/serve -s dist -l 3000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # 重载systemd
    systemctl daemon-reload

    # 启动服务
    systemctl start salesboost-backend
    systemctl enable salesboost-backend

    systemctl start salesboost-frontend
    systemctl enable salesboost-frontend

    log_success "systemd服务配置完成"
}

# 配置Nginx反向代理
configure_nginx_proxy() {
    log_info "配置Nginx反向代理..."

    cat > /etc/nginx/sites-available/salesboost << 'EOF'
server {
    listen 80;
    server_name 106.53.168.252;

    # 前端
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # 后端API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;

        # 增加超时时间（用于流式响应）
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
EOF

    # 启用站点
    ln -sf /etc/nginx/sites-available/salesboost /etc/nginx/sites-enabled/

    # 删除默认站点
    rm -f /etc/nginx/sites-enabled/default

    # 测试配置
    nginx -t

    # 重启Nginx
    systemctl restart nginx

    log_success "Nginx配置完成"
}

# 健康检查
health_check() {
    log_info "执行健康检查..."

    sleep 5

    # 检查后端
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log_success "后端API运行正常"
    else
        log_warning "后端API健康检查失败，请检查日志"
    fi

    # 检查前端
    if curl -f http://localhost:3000 > /dev/null 2>&1; then
        log_success "前端运行正常"
    else
        log_warning "前端健康检查失败，请检查日志"
    fi

    # 检查数据库
    if sudo -u postgres psql -d salesboost -c "SELECT 1" > /dev/null 2>&1; then
        log_success "数据库连接正常"
    else
        log_warning "数据库连接失败"
    fi

    # 检查Redis
    if redis-cli -a salesboost2026 ping > /dev/null 2>&1; then
        log_success "Redis连接正常"
    else
        log_warning "Redis连接失败"
    fi
}

# 显示部署信息
show_deployment_info() {
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                           ║${NC}"
    echo -e "${GREEN}║          🎉 部署成功！SalesBoost已上线！                  ║${NC}"
    echo -e "${GREEN}║                                                           ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}访问地址：${NC}"
    echo -e "  前端: ${GREEN}http://106.53.168.252:3000${NC}"
    echo -e "  API:  ${GREEN}http://106.53.168.252:8000${NC}"
    echo -e "  API文档: ${GREEN}http://106.53.168.252:8000/docs${NC}"
    echo ""
    echo -e "${BLUE}默认管理员账号：${NC}"
    echo -e "  邮箱: ${YELLOW}admin@salesboost.local${NC}"
    echo -e "  密码: ${YELLOW}Admin@2026${NC}"
    echo ""
    echo -e "${BLUE}服务管理命令：${NC}"
    echo -e "  查看后端日志: ${YELLOW}journalctl -u salesboost-backend -f${NC}"
    echo -e "  查看前端日志: ${YELLOW}journalctl -u salesboost-frontend -f${NC}"
    echo -e "  重启后端: ${YELLOW}systemctl restart salesboost-backend${NC}"
    echo -e "  重启前端: ${YELLOW}systemctl restart salesboost-frontend${NC}"
    echo ""
    echo -e "${BLUE}数据库信息：${NC}"
    echo -e "  数据库: ${YELLOW}salesboost${NC}"
    echo -e "  用户: ${YELLOW}salesboost${NC}"
    echo -e "  密码: ${YELLOW}salesboost2026${NC}"
    echo ""
    echo -e "${BLUE}下一步：${NC}"
    echo -e "  1. 访问 ${GREEN}http://106.53.168.252:3000${NC}"
    echo -e "  2. 使用管理员账号登录"
    echo -e "  3. 开始使用SalesBoost！"
    echo ""
}

# 主函数
main() {
    show_banner

    log_info "开始快速部署..."
    echo ""

    update_system
    install_basic_tools
    install_postgresql
    install_redis
    install_python
    install_nodejs
    install_nginx
    configure_firewall
    clone_code
    configure_env
    install_backend_deps
    install_frontend_deps
    init_database
    configure_systemd
    configure_nginx_proxy

    log_info "等待服务启动..."
    sleep 10

    health_check
    show_deployment_info
}

# 运行
main "$@"
