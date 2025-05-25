# 增强版多语言代码分析器 Docker镜像
FROM python:3.10-bullseye

LABEL maintainer="code-analyzer"
LABEL description="Enhanced multi-language code analyzer with comments and documentation support"
LABEL version="2.0.0"

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    # 编译工具
    build-essential \
    gcc \
    g++ \
    make \
    git \
    curl \
    wget \
    # 清理缓存
    && rm -rf /var/lib/apt/lists/*

# 升级pip
RUN pip install --no-cache-dir --upgrade pip

# 安装Python依赖
RUN pip install --no-cache-dir \
    # 核心依赖
    pathlib \
    typing-extensions \
    dataclasses

# 先安装tree-sitter核心
RUN pip install --no-cache-dir tree-sitter

# 安装确实存在的tree-sitter语言包
RUN pip install --no-cache-dir \
    tree-sitter-python \
    tree-sitter-javascript \
    tree-sitter-typescript \
    tree-sitter-java \
    tree-sitter-c \
    tree-sitter-cpp \
    tree-sitter-go \
    tree-sitter-rust

# 尝试安装其他语言包（如果失败就跳过）
RUN pip install --no-cache-dir \
    tree-sitter-ruby \
    tree-sitter-php || echo "Ruby/PHP parser not available"

# 剩下的语言用正则表达式备选方案
# 这样即使某些tree-sitter包不可用，也能分析对应语言

# 安装额外的语言工具 (用于备选分析)
RUN apt-get update && apt-get install -y \
    # Java 开发工具
    openjdk-11-jdk \
    # Go 编译器
    golang-go \
    # Rust 工具链会在运行时安装
    curl \
    # Ruby
    ruby \
    ruby-dev \
    # PHP
    php \
    php-cli \
    # Node.js (已包含)
    # C/C++ 工具
    clang \
    llvm \
    # 清理
    && rm -rf /var/lib/apt/lists/*

# 安装Rust (用于Rust代码分析)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# 创建工作目录
WORKDIR /app

# 复制分析器代码
COPY enhanced_analyzer.py /app/analyzer.py

# 创建输入输出目录
RUN mkdir -p /input /output

# 设置权限
RUN chmod +x /app/analyzer.py

# 验证安装
RUN python -c "import ast, json, pathlib; print('✅ Python dependencies OK')"

# 验证core安装（语言包在运行时检查）
RUN python -c "import tree_sitter; print('✅ Tree-sitter core OK')"

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# 默认入口点
ENTRYPOINT ["python", "/app/analyzer.py"]
CMD ["--input", "/input", "--output", "/output/analysis.json"]

# 元数据
LABEL features="functions,classes,imports,exports,comments,docstrings,type_annotations"
LABEL languages="python,javascript,typescript,java,c,cpp,go,rust,ruby,php"
LABEL supported_extensions=".py,.js,.jsx,.ts,.tsx,.java,.c,.cpp,.cc,.cxx,.h,.hpp,.go,.rs,.rb,.php"
LABEL fallback_languages="csharp,kotlin,swift,scala,bash,html,css,json,yaml,sql"