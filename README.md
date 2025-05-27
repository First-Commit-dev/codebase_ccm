# Codebase CCM - Multi-Language Code Architecture Analyzer

A comprehensive code analysis service that supports 20+ programming languages and outputs unified format compliant with CCM (Canonical Code Model) standard. This service can analyze codebases to extract functions, classes, imports, relationships, and documentation for building code knowledge graphs and architecture visualization.

<img src="https://github.com/user-attachments/assets/67177f3d-0313-4f51-a98a-31b0e14b49bf" width="350"/>
<img src="https://github.com/user-attachments/assets/96c85c3e-9067-4ef4-b702-ae788db1826a" width="350"/>

## 🚀 Core Features

### Multi-Language Support
- **Tree-sitter based parsing** for accurate syntax analysis
- **20+ programming languages**: Python, JavaScript, TypeScript, Java, C, C++, Go, Rust, Ruby, PHP, C#, Kotlin, Swift, Scala, Bash, HTML, CSS, JSON, YAML, SQL, etc.
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
- **Architecture graph format**: Suitable for frontend visualization
- **JSON output** with comprehensive metadata and statistics

## 📖 Quick Start - Two-Step Usage Workflow

### Step 1: Code Architecture Analysis
Use `docker_analyzer.analyze_code` to analyze codebase and extract architecture dependencies:

```python
from docker_analyzer import analyze_code

# Analyze entire codebase to get architecture dependencies
result = analyze_code("./my-project", "./analysis.json")
print(f"Found {len(result['nodes'])} code elements")
print(f"Found {len(result.get('global_relationships', []))} relationships")
```

**Output**: Generates `analysis.json` file containing all code elements and dependencies (CCM format)

### Step 2: Convert to Architecture Graph
Use `graph_converter` to convert CCM format to language-agnostic architecture graph format:

```python
from graph_converter import GraphConverter

# Create converter instance
converter = GraphConverter()

# Convert analysis result to architecture graph
graph = converter.convert_analysis_to_graph(
    analysis_file="analysis.json",
    output_file="architecture_graph.json"
)

print(f"Nodes: {len(graph.nodes)}")
print(f"Edges: {len(graph.edges)}")
print(f"Packages: {len(graph.packages)}")
```

**Output**: Generates `architecture_graph.json` file suitable for frontend visualization

### Complete Workflow Example

```python
# Complete two-step analysis workflow
from docker_analyzer import analyze_code
from graph_converter import GraphConverter

# Step 1: Analyze code architecture
print("🔍 Step 1: Analyzing code architecture...")
analysis_result = analyze_code(
    codebase_path="./my-project",
    output_path="./analysis.json"
)

# Step 2: Convert to architecture graph
print("🔄 Step 2: Converting to architecture graph...")
converter = GraphConverter()
graph = converter.convert_analysis_to_graph(
    analysis_file="./analysis.json",
    output_file="./architecture_graph.json"
)

print("✅ Analysis complete!")
print(f"📊 Statistics:")
print(f"   - Code elements: {len(analysis_result['nodes'])}")
print(f"   - Architecture nodes: {len(graph.nodes)}")
print(f"   - Relationships: {len(graph.edges)}")
print(f"   - Package structure: {len(graph.packages)}")
```

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

1. **Clone the repository:**
```bash
git clone https://github.com/First-Commit-dev/codebase_ccm.git
cd codebase_ccm
```

2. **Build the Docker image:**
```bash
docker build -t enhanced-code-analyzer:latest .
```

3. **Verify installation:**
```bash
docker run --rm enhanced-code-analyzer:latest --help
```

### Option 2: Local Python Setup

1. **Clone the repository:**
```bash
git clone https://github.com/First-Commit-dev/codebase_ccm.git
cd codebase_ccm
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Install tree-sitter language modules:**
```bash
# Install available language parsers
pip install tree-sitter-python tree-sitter-javascript tree-sitter-typescript
# Add more languages as needed
```

## 📊 Output Format Details

### Step 1 Output: CCM Format (analysis.json)

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

### Step 2 Output: Architecture Graph Format (architecture_graph.json)

```json
{
  "nodes": [
    {
      "id": "module_000001",
      "name": "my_module",
      "type": "module",
      "file_path": "/path/to/file.py",
      "package": "com.example.package",
      "size": 2,
      "complexity": 5,
      "documentation": "Module description"
    }
  ],
  "edges": [
    {
      "id": "edge_000001",
      "source": "function_000001",
      "target": "function_000002",
      "type": "calls",
      "weight": 2
    }
  ],
  "packages": [
    {
      "id": "com.example",
      "name": "example",
      "full_name": "com.example",
      "children": ["com.example.subpackage"],
      "type": "package"
    }
  ],
  "statistics": {
    "total_nodes": 304,
    "total_edges": 272,
    "total_packages": 11,
    "node_types": {
      "module": 52,
      "function": 199,
      "class": 33,
      "constructor": 20
    },
    "complexity": {
      "average": 1.85,
      "maximum": 22,
      "distribution": {
        "low": 276,
        "medium": 24,
        "high": 4,
        "very_high": 0
      }
    }
  }
}
```

## 🔧 Advanced Usage

### Docker Interface Configuration

```python
from docker_analyzer import DockerCodeAnalyzer

analyzer = DockerCodeAnalyzer(
    docker_image="enhanced-code-analyzer:latest",
    timeout=600,           # 10 minutes timeout
    memory_limit="2g",     # 2GB memory limit
    cpu_limit="1.0"        # 1 CPU core limit
)

# Exclude specific file patterns
result = analyzer.analyze_codebase(
    "./my-project",
    exclude_patterns=["*.test.js", "node_modules/*", "__pycache__/*"]
)
```

### Command Line Usage

```bash
# Analyze codebase
python docker_analyzer.py ./my-project --output ./analysis.json

# Convert to architecture graph
python graph_converter.py analysis.json -o architecture_graph.json

# Generate summary report
python docker_analyzer.py ./my-project --output ./analysis.json --report ./summary.md
```

### Direct Docker Usage

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

## 🏗 Architecture Design

### Core Components

1. **Enhanced Analyzer** (`enhanced_analyzer.py`)
   - Multi-language code parsing
   - CCM format conversion
   - Relationship resolution

2. **Docker Interface** (`docker_analyzer.py`)
   - Docker container management
   - Python API wrapper
   - Result processing

3. **Graph Converter** (`graph_converter.py`)
   - CCM to architecture graph conversion
   - Package hierarchy extraction
   - Frontend-friendly format output

### Analysis Pipeline

```
Input Code → Language Detection → Tree-sitter/Regex Parsing → 
CCM Conversion → Relationship Resolution → JSON Output → Graph Conversion → Visualization Format
```

## 📈 Performance Benchmarks

### Processing Time
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

### Architecture Visualization
Support for:
- **Architecture diagram** generation
- **Dependency relationship** visualization
- **Module structure** display
- **Code complexity** analysis

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

---

For more information, see the example usage in `example.py` or run the analyzer with `--help` for command-line options.

For detailed graph_converter usage, see the docstrings and examples in `graph_converter.py`.
