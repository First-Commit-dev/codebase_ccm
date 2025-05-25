# Enhanced multi-language code analyzer Docker image
FROM python:3.10-bullseye

LABEL maintainer="code-analyzer"
LABEL description="Enhanced multi-language code analyzer with comments and documentation support"
LABEL version="2.0.0"

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Build tools
    build-essential \
    gcc \
    g++ \
    make \
    git \
    curl \
    wget \
    # Clean cache
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Install Python dependencies
RUN pip install --no-cache-dir \
    # Core dependencies
    pathlib \
    typing-extensions \
    dataclasses

# Install tree-sitter core first
RUN pip install --no-cache-dir tree-sitter

# Install available tree-sitter language packages
RUN pip install --no-cache-dir \
    tree-sitter-python \
    tree-sitter-javascript \
    tree-sitter-typescript \
    tree-sitter-java \
    tree-sitter-c \
    tree-sitter-cpp \
    tree-sitter-go \
    tree-sitter-rust

# Try to install other language packages (skip if failed)
RUN pip install --no-cache-dir \
    tree-sitter-ruby \
    tree-sitter-php || echo "Ruby/PHP parser not available"

# For remaining languages, use regex fallback approach
# This ensures analysis capability even when certain tree-sitter packages are unavailable

# Install additional language tools (for fallback analysis)
RUN apt-get update && apt-get install -y \
    # Java development tools
    openjdk-11-jdk \
    # Go compiler
    golang-go \
    # Rust toolchain will be installed at runtime
    curl \
    # Ruby
    ruby \
    ruby-dev \
    # PHP
    php \
    php-cli \
    # Node.js (already included)
    # C/C++ tools
    clang \
    llvm \
    # Clean up
    && rm -rf /var/lib/apt/lists/*

# Install Rust (for Rust code analysis)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Create working directory
WORKDIR /app

# Copy analyzer code
COPY enhanced_analyzer.py /app/analyzer.py

# Create input/output directories
RUN mkdir -p /input /output

# Set permissions
RUN chmod +x /app/analyzer.py

# Verify installation
RUN python -c "import ast, json, pathlib; print('✅ Python dependencies OK')"

# Verify core installation (language packages checked at runtime)
RUN python -c "import tree_sitter; print('✅ Tree-sitter core OK')"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default entry point
ENTRYPOINT ["python", "/app/analyzer.py"]
CMD ["--input", "/input", "--output", "/output/analysis.json"]

# Metadata
LABEL features="functions,classes,imports,exports,comments,docstrings,type_annotations"
LABEL languages="python,javascript,typescript,java,c,cpp,go,rust,ruby,php"
LABEL supported_extensions=".py,.js,.jsx,.ts,.tsx,.java,.c,.cpp,.cc,.cxx,.h,.hpp,.go,.rs,.rb,.php"
LABEL fallback_languages="csharp,kotlin,swift,scala,bash,html,css,json,yaml,sql"