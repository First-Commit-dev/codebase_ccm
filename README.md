# Repos Service - Multi-Language Code Analyzer

A comprehensive code analysis service that supports 20+ programming languages and outputs unified format compliant with CCM (Canonical Code Model) standard. This service can analyze codebases to extract functions, classes, imports, relationships, and documentation for building code knowledge graphs.

## 🚀 Features

### Multi-Language Support
- **Tree-sitter based parsing** for accurate syntax analysis
- **20+ programming languages** including:
  - Python, JavaScript, TypeScript
  - Java, C, C++, Go, Rust
  - Ruby, PHP, C#, Kotlin, Swift, Scala
  - Bash, HTML, CSS, JSON, YAML, SQL
- **Fallback regex parsing** when tree-sitter modules are unavailable

### Code Analysis Capabilities
- **Function extraction**: Parameters, return types, decorators, visibility
- **Class analysis**: Methods, inheritance, interfaces, abstract classes
- **Module analysis**: Imports, exports, dependencies
- **Comment extraction**: Line comments, block comments, docstrings
- **Relationship mapping**: Function calls, class inheritance, module imports
- **Type annotation support**: Full type information extraction

### Output Formats
- **CCM (Canonical Code Model)** compliant output for standardized processing
- **Traditional format** for backward compatibility
- **JSON output** with comprehensive metadata and statistics

### Deployment Options
- **Docker containerized** for easy deployment and isolation
- **Python interface** for direct integration
- **Command-line interface** for batch processing

## 📋 Requirements

### System Requirements
- Python 3.10+
- Docker (for containerized deployment)
- 2GB+ RAM (recommended for large codebases)

### Python Dependencies
Core dependencies are automatically installed via Docker or can be installed manually:

```bash
# Core dependencies
pip install tree-sitter pathlib typing-extensions dataclasses

# Language-specific tree-sitter modules
pip install tree-sitter-python tree-sitter-javascript tree-sitter-typescript
pip install tree-sitter-java tree-sitter-c tree-sitter-cpp
pip install tree-sitter-go tree-sitter-rust tree-sitter-ruby tree-sitter-php
```

## 🛠 Installation & Setup

### Option 1: Docker Deployment (Recommended)

1. **Build the Docker image:**
```bash
cd backend/repos-service
docker build -t enhanced-code-analyzer:latest .
```

2. **Verify installation:**
```bash
docker run --rm enhanced-code-analyzer:latest --help
```

### Option 2: Local Python Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Install tree-sitter language modules:**
```bash
# Install available language parsers
pip install tree-sitter-python tree-sitter-javascript tree-sitter-typescript
# Add more languages as needed
```

## 📖 Usage

### Docker Interface (Recommended)

#### Analyze a codebase using Python interface:
```python
from docker_analyzer import analyze_code

# Analyze entire codebase
result = analyze_code("./my-project", "./analysis.json")
print(f"Found {len(result['nodes'])} code elements")

# Analyze single file
from docker_analyzer import analyze_file
result = analyze_file("./my-file.py", "./file-analysis.json")
```

#### Command line usage:
```bash
# Analyze codebase
python docker_analyzer.py ./my-project --output ./analysis.json

# Generate summary report
python docker_analyzer.py ./my-project --output ./analysis.json --report ./summary.md

# Custom Docker image
python docker_analyzer.py ./my-project --image my-custom-analyzer:latest
```

#### Direct Docker usage:
```bash
# Analyze codebase
docker run --rm \
  -v /path/to/code:/input:ro \
  -v /path/to/output:/output:rw \
  enhanced-code-analyzer:latest \
  --input /input --output /output/analysis.json

# With resource limits
docker run --rm \
  --memory 2g --cpus 1.0 \
  -v /path/to/code:/input:ro \
  -v /path/to/output:/output:rw \
  enhanced-code-analyzer:latest
```

### Direct Python Usage

```python
from enhanced_analyzer import ComprehensiveMultiLanguageAnalyzer

# Create analyzer instance
analyzer = ComprehensiveMultiLanguageAnalyzer()

# Analyze repository
analyzer.analyze_repository("./my-project", "./analysis.json")

# The output will contain both CCM format and traditional format
```

## 📊 Output Format

### CCM (Canonical Code Model) Format

The service outputs standardized CCM format for interoperability:

```json
{
  "ccm_version": "1.0.0",
  "project": {
    "name": "my-project",
    "root_path": "/path/to/project",
    "project_type": "python",
    "languages": ["python", "javascript"]
  },
  "nodes": [
    {
      "id": "node_001",
      "name": "my_function",
      "node_type": "function",
      "location": {
        "file_path": "src/main.py",
        "start_line": 10,
        "end_line": 25
      },
      "language": "python",
      "parameters": [...],
      "return_type": {...},
      "relationships": [...],
      "documentation": {...}
    }
  ],
  "global_relationships": [...],
  "metadata": {
    "total_nodes": 150,
    "total_relationships": 89,
    "resolution_rate": 75.2,
    "analyzer_version": "2.0.0"
  }
}
```

### Analysis Statistics

The output includes comprehensive metadata:

- **Node counts** by type (functions, classes, modules)
- **Language distribution** across the codebase
- **Relationship resolution rate** for code connections
- **Documentation coverage** statistics
- **Complex function analysis** (functions with many parameters)

## 🔧 Configuration

### Docker Configuration

Customize the Docker container behavior:

```python
from docker_analyzer import DockerCodeAnalyzer

analyzer = DockerCodeAnalyzer(
    docker_image="enhanced-code-analyzer:latest",
    timeout=600,           # 10 minutes timeout
    memory_limit="2g",     # 2GB memory limit
    cpu_limit="1.0"        # 1 CPU core limit
)
```

### Analysis Options

Configure analysis behavior:

```python
# Exclude patterns
result = analyzer.analyze_codebase(
    "./my-project",
    exclude_patterns=["*.test.js", "node_modules/*", "__pycache__/*"]
)
```

## 🏗 Architecture

### Core Components

1. **Enhanced Analyzer** (`enhanced_analyzer.py`)
   - Multi-language code parsing
   - CCM format conversion
   - Relationship resolution

2. **Docker Interface** (`docker_analyzer.py`)
   - Docker container management
   - Python API wrapper
   - Result processing

3. **Language Detectors**
   - File extension mapping
   - Content-based detection
   - Fallback mechanisms

### Analysis Pipeline

```
Input Code → Language Detection → Tree-sitter/Regex Parsing → 
CCM Conversion → Relationship Resolution → JSON Output
```

## 🐳 Docker Details

### Image Features
- **Multi-language support**: Pre-installed parsers for 20+ languages
- **Lightweight**: Based on Python 3.10 Bullseye
- **Secure**: Runs without network access
- **Resource controlled**: Memory and CPU limits
- **Health checks**: Built-in container health monitoring

### Image Labels
```dockerfile
LABEL features="functions,classes,imports,exports,comments,docstrings,type_annotations"
LABEL languages="python,javascript,typescript,java,c,cpp,go,rust,ruby,php"
LABEL supported_extensions=".py,.js,.jsx,.ts,.tsx,.java,.c,.cpp,.cc,.cxx,.h,.hpp,.go,.rs,.rb,.php"
```

## 📈 Performance

### Benchmarks
- **Small projects** (< 100 files): 5-15 seconds
- **Medium projects** (100-1000 files): 30-120 seconds  
- **Large projects** (1000+ files): 2-10 minutes

### Resource Usage
- **Memory**: 500MB - 2GB depending on codebase size
- **CPU**: Single-threaded analysis, benefits from higher clock speeds
- **Storage**: Minimal, only for temporary processing

## 🔍 Use Cases

### Code Knowledge Graphs
Build comprehensive code knowledge graphs for:
- **Code navigation** and exploration
- **Impact analysis** for changes
- **Dependency mapping** and visualization
- **Code quality** assessment

### Documentation Generation
Extract and organize:
- **API documentation** from code comments
- **Function signatures** and parameters
- **Class hierarchies** and relationships
- **Module dependencies** and imports

### Code Analysis Tools
Support for:
- **Static analysis** tools
- **Code review** automation
- **Refactoring** assistance
- **Architecture** visualization

## 🚨 Troubleshooting

### Common Issues

**Tree-sitter module not found:**
```bash
# Install missing language modules
pip install tree-sitter-python tree-sitter-javascript
```

**Docker image not found:**
```bash
# Build the image locally
docker build -t enhanced-code-analyzer:latest .
```

**Memory issues with large codebases:**
```bash
# Increase Docker memory limit
docker run --memory 4g enhanced-code-analyzer:latest
```

**Permission issues:**
```bash
# Ensure proper volume permissions
chmod -R 755 /path/to/code
```

### Debug Mode

Enable verbose logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

analyzer = DockerCodeAnalyzer()
result = analyzer.analyze_codebase("./my-project")
```

## 🤝 Contributing

### Development Setup
1. Clone the repository
2. Install development dependencies
3. Run tests with sample codebases
4. Submit pull requests with improvements

### Adding Language Support
1. Install tree-sitter language module
2. Add language mapping in `LanguageDetector`
3. Test with sample code files
4. Update documentation

## 📄 License

MIT


For more information, see the example usage in `example.py` or run the analyzer with `--help` for command-line options. 