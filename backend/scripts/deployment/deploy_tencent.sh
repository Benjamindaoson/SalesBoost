#!/bin/bash

###############################################################################
# SalesBoost 腾讯云自动化部署脚本
#
# 功能：一键部署SalesBoost到腾讯云生产环境
# 作者：Claude (Anthropic)
# 日期：2026-02-05
###############################################################################

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示横幅
show_banner() {
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
║   ██████╗  ██████╗  ██████╗ ███████╗████████╗            ║
║   ██╔══██╗██╔═══██╗██╔═══██╗██╔════╝╚══██╔══╝            ║
║   ██████╔╝██║   ██║██║   ██║███████╗   ██║               ║
║   ██╔══██╗██║   ██║██║   ██║╚════██║   ██║               ║
║   ██████╔╝╚██████╔╝╚██████╔╝███████║   ██║               ║
║   ╚═════╝  ╚═════╝  ╚═════╝ ╚══════╝   ╚═╝               ║
║                                                           ║
║          腾讯云自动化部署脚本 v2.0.0                      ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

# 检查配置文件
check_config() {
    log_info "检查配置文件..."

    if [ ! -f ".env.production" ]; then
        log_error "未找到 .env.production 配置文件"
        log_info "请先创建配置文件，参考 .env.example"
        exit 1
    fi

    # 加载环境变量
    source .env.production

    # 检查必需的环境变量
    required_vars=(
        "DATABASE_URL"
        "SUPABASE_URL"
        "SUPABASE_KEY"
        "SUPABASE_JWT_SECRET"
    )

    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            log_error "缺少必需的环境变量: $var"
            exit 1
        fi
    done

    # 检查至少有一个LLM API密钥
    if [ -z "$OPENAI_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$GEMINI_API_KEY" ]; then
        log_error "至少需要配置一个LLM API密钥 (OPENAI_API_KEY, ANTHROPIC_API_KEY, 或 GEMINI_API_KEY)"
        exit 1
    fi

    log_success "配置文件检查通过"
}

# 检查系统环境
check_system() {
    log_info "检查系统环境..."

    # 检查操作系统
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
        log_info "操作系统: $OS $VER"
    else
        log_error "无法识别操作系统"
        exit 1
    fi

    # 检查是否为root用户
    if [ "$EUID" -ne 0 ]; then
        log_warning "建议使用root用户运行此脚本"
        log_info "如果遇到权限问题，请使用: sudo bash deploy.sh"
    fi

    log_success "系统环境检查通过"
}

# 安装Docker
install_docker() {
    log_info "检查Docker安装状态..."

    if command -v docker &> /dev/null; then
        log_success "Docker已安装: $(docker --version)"
        return
    fi

    log_info "开始安装Docker..."

    # 更新包索引
    apt-get update -y

    # 安装依赖
    apt-get install -y \
        ca-certificates \
        curl \
        gnupg \
        lsb-release

    # 添加Docker官方GPG密钥
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    # 设置Docker仓库
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    # 安装Docker Engine
    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # 启动Docker服务
    systemctl start docker
    systemctl enable docker

    log_success "Docker安装完成: $(docker --version)"
}

# 安装Docker Compose
install_docker_compose() {
    log_info "检查Docker Compose安装状态..."

    if command -v docker-compose &> /dev/null; then
        log_success "Docker Compose已安装: $(docker-compose --version)"
        return
    fi

    log_info "开始安装Docker Compose..."

    # 下载Docker Compose
    curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

    # 添加执行权限
    chmod +x /usr/local/bin/docker-compose

    log_success "Docker Compose安装完成: $(docker-compose --version)"
}

# 安装Nginx
install_nginx() {
    log_info "检查Nginx安装状态..."

    if command -v nginx &> /dev/null; then
        log_success "Nginx已安装: $(nginx -v 2>&1)"
        return
    fi

    log_info "开始安装Nginx..."

    apt-get update -y
    apt-get install -y nginx

    # 启动Nginx服务
    systemctl start nginx
    systemctl enable nginx

    log_success "Nginx安装完成"
}

# 配置防火墙
configure_firewall() {
    log_info "配置防火墙规则..."

    # 检查ufw是否安装
    if ! command -v ufw &> /dev/null; then
        log_info "安装ufw防火墙..."
        apt-get install -y ufw
    fi

    # 配置防火墙规则
    ufw --force enable
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow 22/tcp    # SSH
    ufw allow 80/tcp    # HTTP
    ufw allow 443/tcp   # HTTPS

    log_success "防火墙配置完成"
}

# 克隆代码仓库
clone_repository() {
    log_info "准备代码仓库..."

    DEPLOY_DIR="/opt/salesboost"

    if [ -d "$DEPLOY_DIR" ]; then
        log_info "代码目录已存在，拉取最新代码..."
        cd $DEPLOY_DIR
        git pull origin main
    else
        log_info "克隆代码仓库..."
        git clone https://github.com/yourusername/salesboost.git $DEPLOY_DIR
        cd $DEPLOY_DIR
    fi

    log_success "代码准备完成"
}

# 配置环境变量
configure_environment() {
    log_info "配置环境变量..."

    # 复制环境变量文件
    cp .env.production $DEPLOY_DIR/.env

    log_success "环境变量配置完成"
}

# 构建Docker镜像
build_images() {
    log_info "构建Docker镜像..."

    cd $DEPLOY_DIR

    # 构建后端镜像
    log_info "构建后端镜像..."
    docker build -t salesboost-backend:latest -f Dockerfile.backend .

    # 构建前端镜像
    log_info "构建前端镜像..."
    docker build -t salesboost-frontend:latest -f Dockerfile.frontend .

    log_success "Docker镜像构建完成"
}

# 启动服务
start_services() {
    log_info "启动服务容器..."

    cd $DEPLOY_DIR

    # 停止旧容器
    docker-compose down

    # 启动新容器
    docker-compose up -d

    log_success "服务启动完成"
}

# 初始化数据库
init_database() {
    log_info "初始化数据库..."

    # 等待数据库就绪
    sleep 5

    # 运行数据库迁移
    docker-compose exec -T backend alembic upgrade head

    log_success "数据库初始化完成"
}

# 配置Nginx反向代理
configure_nginx() {
    log_info "配置Nginx反向代理..."

    # 创建Nginx配置文件
    cat > /etc/nginx/sites-available/salesboost << 'EOF'
# 前端配置
server {
    listen 80;
    server_name ${FRONTEND_DOMAIN};

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}

# 后端API配置
server {
    listen 80;
    server_name ${API_DOMAIN};

    location / {
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

    # 替换域名变量
    sed -i "s/\${FRONTEND_DOMAIN}/$FRONTEND_URL/g" /etc/nginx/sites-available/salesboost
    sed -i "s/\${API_DOMAIN}/$API_URL/g" /etc/nginx/sites-available/salesboost

    # 启用站点
    ln -sf /etc/nginx/sites-available/salesboost /etc/nginx/sites-enabled/

    # 测试Nginx配置
    nginx -t

    # 重启Nginx
    systemctl reload nginx

    log_success "Nginx配置完成"
}

# 配置SSL证书
configure_ssl() {
    log_info "配置SSL证书..."

    # 安装Certbot
    if ! command -v certbot &> /dev/null; then
        log_info "安装Certbot..."
        apt-get install -y certbot python3-certbot-nginx
    fi

    # 申请SSL证书
    log_info "申请SSL证书（前端域名）..."
    certbot --nginx -d $FRONTEND_URL --non-interactive --agree-tos --email admin@$FRONTEND_URL

    log_info "申请SSL证书（API域名）..."
    certbot --nginx -d $API_URL --non-interactive --agree-tos --email admin@$API_URL

    # 配置自动续期
    (crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet") | crontab -

    log_success "SSL证书配置完成"
}

# 配置监控
configure_monitoring() {
    log_info "配置监控和日志..."

    # 创建日志目录
    mkdir -p /var/log/salesboost

    # 配置日志轮转
    cat > /etc/logrotate.d/salesboost << 'EOF'
/var/log/salesboost/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 root root
    sharedscripts
    postrotate
        docker-compose -f /opt/salesboost/docker-compose.yml restart
    endscript
}
EOF

    log_success "监控配置完成"
}

# 健康检查
health_check() {
    log_info "执行健康检查..."

    # 检查后端API
    log_info "检查后端API..."
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log_success "后端API运行正常"
    else
        log_error "后端API健康检查失败"
        return 1
    fi

    # 检查前端
    log_info "检查前端..."
    if curl -f http://localhost:3000 > /dev/null 2>&1; then
        log_success "前端运行正常"
    else
        log_error "前端健康检查失败"
        return 1
    fi

    # 检查数据库连接
    log_info "检查数据库连接..."
    if docker-compose exec -T backend python -c "from app.infra.database import engine; engine.connect()" > /dev/null 2>&1; then
        log_success "数据库连接正常"
    else
        log_error "数据库连接失败"
        return 1
    fi

    log_success "所有健康检查通过"
}

# 显示部署信息
show_deployment_info() {
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                           ║${NC}"
    echo -e "${GREEN}║              🎉 部署成功！SalesBoost已上线！              ║${NC}"
    echo -e "${GREEN}║                                                           ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}访问地址：${NC}"
    echo -e "  前端: ${GREEN}https://$FRONTEND_URL${NC}"
    echo -e "  API:  ${GREEN}https://$API_URL${NC}"
    echo ""
    echo -e "${BLUE}管理命令：${NC}"
    echo -e "  查看日志: ${YELLOW}docker-compose logs -f${NC}"
    echo -e "  重启服务: ${YELLOW}docker-compose restart${NC}"
    echo -e "  停止服务: ${YELLOW}docker-compose down${NC}"
    echo -e "  更新代码: ${YELLOW}git pull && docker-compose up -d --build${NC}"
    echo ""
    echo -e "${BLUE}监控地址：${NC}"
    echo -e "  系统监控: ${GREEN}http://$SERVER_IP:9090${NC} (Prometheus)"
    echo -e "  日志查看: ${GREEN}/var/log/salesboost/${NC}"
    echo ""
    echo -e "${BLUE}下一步：${NC}"
    echo -e "  1. 访问前端地址，测试功能"
    echo -e "  2. 创建管理员账号"
    echo -e "  3. 配置团队成员"
    echo -e "  4. 开始使用！"
    echo ""
}

# 主函数
main() {
    show_banner

    log_info "开始自动化部署..."
    echo ""

    # 执行部署步骤
    check_config
    check_system
    install_docker
    install_docker_compose
    install_nginx
    configure_firewall
    clone_repository
    configure_environment
    build_images
    start_services
    init_database
    configure_nginx

    # 询问是否配置SSL
    read -p "是否配置SSL证书？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        configure_ssl
    fi

    configure_monitoring

    # 等待服务启动
    log_info "等待服务启动..."
    sleep 10

    # 健康检查
    if health_check; then
        show_deployment_info
        exit 0
    else
        log_error "部署失败，请检查日志"
        exit 1
    fi
}

# 运行主函数
main "$@"
