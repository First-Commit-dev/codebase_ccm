#!/usr/bin/env python3
"""
Multi-language code analyzer
Supports 20+ programming languages for function, class, and comment analysis
Outputs unified format compliant with CCM (Canonical Code Model) standard
"""

import os
import json
import ast
import re
import argparse
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Union
from dataclasses import dataclass, asdict
from collections import defaultdict
from enum import Enum

# Dynamic import of tree-sitter
TREE_SITTER_MODULES = {}
TREE_SITTER_AVAILABLE = True

try:
    from tree_sitter import Language, Parser, Node
    
    # Try to import all supported languages
    language_imports = {
        'python': 'tree_sitter_python',
        'javascript': 'tree_sitter_javascript', 
        'typescript': 'tree_sitter_typescript',
        'java': 'tree_sitter_java',
        'c': 'tree_sitter_c',
        'cpp': 'tree_sitter_cpp',
        'go': 'tree_sitter_go',
        'rust': 'tree_sitter_rust',
        'ruby': 'tree_sitter_ruby',
        'php': 'tree_sitter_php',
        'csharp': 'tree_sitter_c_sharp',
        'kotlin': 'tree_sitter_kotlin',
        'swift': 'tree_sitter_swift',
        'scala': 'tree_sitter_scala',
        'bash': 'tree_sitter_bash',
    }
    
    for lang, module_name in language_imports.items():
        try:
            module = __import__(module_name)
            TREE_SITTER_MODULES[lang] = module
        except ImportError:
            print(f"⚠️  {lang} tree-sitter module not available")
    
    print(f"✅ Tree-sitter available, supported languages: {list(TREE_SITTER_MODULES.keys())}")
    
except ImportError:
    TREE_SITTER_AVAILABLE = False
    print("⚠️  Tree-sitter not available, using fallback parser")

# CCM enum type definitions
class CCMNodeType(Enum):
    """CCM node type enum"""
    MODULE = "module"
    CLASS = "class"
    INTERFACE = "interface"
    FUNCTION = "function"
    METHOD = "method"
    CONSTRUCTOR = "constructor"
    PROPERTY = "property"
    VARIABLE = "variable"
    PARAMETER = "parameter"
    COMMENT = "comment"
    IMPORT = "import"
    EXPORT = "export"

class CCMVisibility(Enum):
    """CCM visibility enum"""
    PUBLIC = "public"
    PRIVATE = "private"
    PROTECTED = "protected"
    INTERNAL = "internal"
    PACKAGE = "package"

class CCMModifier(Enum):
    """CCM modifier enum"""
    STATIC = "static"
    ABSTRACT = "abstract"
    FINAL = "final"
    ASYNC = "async"
    VIRTUAL = "virtual"
    OVERRIDE = "override"
    READONLY = "readonly"
    CONST = "const"

# CCM core data structures
@dataclass
class CCMLocation:
    """CCM location information"""
    file_path: str
    start_line: int
    end_line: int
    start_column: Optional[int] = None
    end_column: Optional[int] = None

@dataclass
class CCMTypeInfo:
    """CCM type information"""
    name: str
    is_primitive: bool = False
    is_array: bool = False
    is_nullable: bool = False
    generic_parameters: Optional[List[str]] = None
    namespace: Optional[str] = None

@dataclass
class CCMParameter:
    """CCM parameter information"""
    name: str
    type_info: Optional[CCMTypeInfo] = None
    default_value: Optional[str] = None
    is_optional: bool = False
    is_variadic: bool = False

@dataclass
class CCMRelationship:
    """CCM relationship information"""
    type: str  # "calls", "inherits", "implements", "uses", "contains", "imports"
    target_id: str
    target_name: str
    # Optional metadata for storing additional relationship information (e.g., call count, import alias)
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class CCMDocumentation:
    """CCM documentation information"""
    summary: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[Dict[str, str]] = None
    returns: Optional[str] = None
    examples: Optional[List[str]] = None
    tags: Optional[Dict[str, str]] = None

@dataclass
class CCMNode:
    """CCM unified node"""
    id: str  # Unique identifier
    name: str
    node_type: CCMNodeType
    location: CCMLocation
    language: str
    
    # Optional attributes
    visibility: Optional[CCMVisibility] = None
    modifiers: Optional[List[CCMModifier]] = None
    type_info: Optional[CCMTypeInfo] = None
    parameters: Optional[List[CCMParameter]] = None
    return_type: Optional[CCMTypeInfo] = None
    parent_id: Optional[str] = None
    children_ids: Optional[List[str]] = None
    relationships: Optional[List[CCMRelationship]] = None
    documentation: Optional[CCMDocumentation] = None
    
    # Raw information (for debugging and special handling)
    raw_content: Optional[str] = None
    annotations: Optional[Dict[str, Any]] = None

@dataclass
class CCMProject:
    """CCM project information"""
    name: str
    root_path: str
    project_type: str
    languages: List[str]
    
@dataclass
class CCMAnalysisResult:
    """CCM analysis result"""
    project: CCMProject
    nodes: List[CCMNode]
    relationships: List[CCMRelationship]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "ccm_version": "1.0.0",
            "project": self._serialize_object(asdict(self.project)),
            "nodes": [self._serialize_object(asdict(node)) for node in self.nodes],
            "global_relationships": [self._serialize_object(asdict(rel)) for rel in self.relationships],
            "metadata": self.metadata
        }
    
    def _serialize_object(self, obj) -> Any:
        """Recursively serialize objects, handling enum types"""
        if isinstance(obj, dict):
            return {key: self._serialize_object(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_object(item) for item in obj]
        elif isinstance(obj, (CCMNodeType, CCMVisibility, CCMModifier)):
            return obj.value
        elif isinstance(obj, Path):
            return str(obj)
        elif hasattr(obj, '__dict__'):
            # Handle other dataclass objects
            return self._serialize_object(asdict(obj))
        else:
            return obj

# Keep original data classes for compatibility with existing code
@dataclass
class CommentInfo:
    content: str
    line_number: int
    comment_type: str  # "line", "block", "docstring"
    language: str

@dataclass
class FunctionInfo:
    name: str
    file_path: str
    start_line: int
    end_line: int
    parameters: List[str]
    return_type: Optional[str]
    calls: List[str]
    called_by: List[str]
    class_name: Optional[str]
    module_name: str
    language: str
    docstring: Optional[str]
    comments: List[CommentInfo]
    is_async: bool = False
    is_static: bool = False
    visibility: str = "public"
    decorators: List[str] = None
    type_annotations: Dict[str, str] = None

@dataclass
class ClassInfo:
    name: str
    file_path: str
    start_line: int
    end_line: int
    methods: List[str]
    parent_classes: List[str]
    module_name: str
    language: str
    docstring: Optional[str]
    comments: List[CommentInfo]
    decorators: List[str] = None
    is_abstract: bool = False
    interfaces: List[str] = None

@dataclass
class ModuleInfo:
    name: str
    file_path: str
    imports: List[str]
    exports: List[str]
    functions: List[str]
    classes: List[str]
    language: str
    comments: List[CommentInfo]
    docstring: Optional[str]

class LanguageDetector:
    """Detect file language type"""
    
    LANGUAGE_MAP = {
        # Python
        '.py': 'python',
        '.pyi': 'python',
        
        # JavaScript/TypeScript
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.mjs': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.d.ts': 'typescript',
        
        # Java family
        '.java': 'java',
        '.kt': 'kotlin',
        '.scala': 'scala',
        
        # C/C++
        '.c': 'c',
        '.h': 'c',
        '.cpp': 'cpp',
        '.cxx': 'cpp',
        '.cc': 'cpp',
        '.hpp': 'cpp',
        '.hxx': 'cpp',
        
        # Other compiled languages
        '.go': 'go',
        '.rs': 'rust',
        '.swift': 'swift',
        '.cs': 'csharp',
        
        # Script languages
        '.rb': 'ruby',
        '.php': 'php',
        '.pl': 'perl',
        '.py': 'python',
        
        # Shell
        '.sh': 'bash',
        '.bash': 'bash',
        '.zsh': 'bash',
        
        # Markup languages
        '.html': 'html',
        '.htm': 'html',
        '.css': 'css',
        '.scss': 'css',
        '.sass': 'css',
        
        # Configuration files
        '.json': 'json',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.toml': 'toml',
        '.xml': 'xml',
        '.sql': 'sql',
        
        # Others
        '.dockerfile': 'dockerfile',
        '.md': 'markdown',
        '.makefile': 'makefile',
    }
    
    @classmethod
    def detect_language(cls, file_path: str) -> Optional[str]:
        """Detect language based on file extension"""
        path = Path(file_path)
        
        # Special filename handling
        if path.name.lower() in ['dockerfile', 'makefile']:
            return path.name.lower()
        
        suffix = path.suffix.lower()
        return cls.LANGUAGE_MAP.get(suffix)

class UniversalTreeSitterAnalyzer:
    """Universal Tree-sitter analyzer"""
    
    def __init__(self, language: str):
        self.language = language
        self.parser = None
        
        if TREE_SITTER_AVAILABLE and language in TREE_SITTER_MODULES:
            self.parser = self._create_parser(language)
    
    def _create_parser(self, language: str):
        """Create parser for specified language"""
        try:
            parser = Parser()
            module = TREE_SITTER_MODULES[language]
            
            if hasattr(Language, '__call__'):
                parser.language = Language(module.language())
            else:
                parser.set_language(Language(module.language()))
            
            return parser
        except Exception as e:
            print(f"Failed to create {language} parser: {e}")
            return None
    
    def analyze_file(self, file_path: str, content: str) -> Optional[Dict[str, Any]]:
        """Analyze file"""
        if not self.parser:
            return None
        
        try:
            tree = self.parser.parse(bytes(content, "utf8"))
            return self._extract_info_from_tree(tree, file_path, content)
        except Exception as e:
            print(f"Tree-sitter analysis failed {file_path}: {e}")
            return None
    
    def _extract_info_from_tree(self, tree, file_path: str, content: str) -> Dict[str, Any]:
        """Extract information from AST tree"""
        functions = []
        classes = []
        imports = []
        exports = []
        comments = self._extract_comments(content)
        
        # Recursively traverse AST
        self._traverse_node(tree.root_node, {
            'functions': functions,
            'classes': classes,
            'imports': imports,
            'exports': exports,
            'file_path': file_path,
            'language': self.language
        })
        
        module_name = Path(file_path).stem
        
        return {
            'functions': functions,
            'classes': classes,
            'module': ModuleInfo(
                name=module_name,
                file_path=file_path,
                imports=imports,
                exports=exports,
                functions=[f.name for f in functions],
                classes=[c.name for c in classes],
                language=self.language,
                comments=comments,
                docstring=None
            )
        }
    
    def _traverse_node(self, node, context):
        """Recursively traverse AST nodes"""
        # Function definition node type mapping
        function_types = {
            'function_definition',      # Python
            'function_declaration',     # JavaScript, C, Go
            'function_expression',      # JavaScript
            'arrow_function',          # JavaScript
            'method_definition',       # JavaScript classes
            'function_item',           # Rust
            'method_declaration',      # Java
            'function_declaration',    # Go
        }
        
        # Class definition node type mapping
        class_types = {
            'class_definition',        # Python
            'class_declaration',       # JavaScript, Java
            'struct_item',            # Rust
            'interface_declaration',   # TypeScript, Java
            'type_declaration',       # Go
        }
        
        # Import node type mapping  
        import_types = {
            'import_statement',        # Python, JavaScript
            'import_from_statement',   # Python
            'import_declaration',      # TypeScript
            'use_declaration',         # Rust
            'import_spec',            # Go
        }
        
        if node.type in function_types:
            func_info = self._extract_function_info(node, context)
            if func_info:
                context['functions'].append(func_info)
        
        elif node.type in class_types:
            class_info = self._extract_class_info(node, context)
            if class_info:
                context['classes'].append(class_info)
        
        elif node.type in import_types:
            import_text = self._get_node_text(node)
            context['imports'].append(import_text)
        
        # Recursively process child nodes
        for child in node.children:
            self._traverse_node(child, context)
    
    def _extract_function_info(self, node, context) -> Optional[FunctionInfo]:
        """Extract function information"""
        try:
            # Get function name
            name = self._extract_name_from_node(node)
            if not name:
                name = "anonymous"
            
            # Get parameters
            params = self._extract_parameters_from_node(node)
            
            # Get function calls
            calls = []
            self._extract_calls_from_node(node, calls)
            
            return FunctionInfo(
                name=name,
                file_path=context['file_path'],
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                parameters=params,
                return_type=None,
                calls=calls,
                called_by=[],
                class_name=None,  # Need context information
                module_name=Path(context['file_path']).stem,
                language=context['language'],
                docstring=None,
                comments=[],
                is_async=self._is_async_function(node)
            )
        except Exception as e:
            print(f"Failed to extract function info: {e}")
            return None
    
    def _extract_class_info(self, node, context) -> Optional[ClassInfo]:
        """Extract class information"""
        try:
            name = self._extract_name_from_node(node)
            if not name:
                return None
            
            # Get methods
            methods = []
            self._extract_methods_from_class(node, methods)
            
            return ClassInfo(
                name=name,
                file_path=context['file_path'],
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                methods=methods,
                parent_classes=[],  # Need further parsing
                module_name=Path(context['file_path']).stem,
                language=context['language'],
                docstring=None,
                comments=[]
            )
        except Exception as e:
            print(f"Failed to extract class info: {e}")
            return None
    
    def _extract_name_from_node(self, node) -> Optional[str]:
        """Extract name from node"""
        # Try to get through field name
        name_node = node.child_by_field_name("name")
        if name_node:
            return self._get_node_text(name_node)
        
        # Try to find identifier child node
        for child in node.children:
            if child.type == "identifier":
                return self._get_node_text(child)
        
        return None
    
    def _extract_parameters_from_node(self, node) -> List[str]:
        """Extract parameters from node"""
        params = []
        
        # Find parameter list
        params_node = node.child_by_field_name("parameters")
        if not params_node:
            # Try other field names
            for field in ["parameter_list", "parameters", "args"]:
                params_node = node.child_by_field_name(field)
                if params_node:
                    break
        
        if params_node:
            for child in params_node.children:
                if child.type in ["identifier", "parameter", "parameter_declaration"]:
                    param_name = self._get_node_text(child)
                    if param_name and param_name not in [',', '(', ')']:
                        params.append(param_name)
        
        return params
    
    def _extract_calls_from_node(self, node, calls: List[str]):
        """Extract function calls from node"""
        call_types = {'call', 'call_expression', 'function_call'}
        
        if node.type in call_types:
            func_node = node.child_by_field_name("function")
            if func_node:
                call_name = self._get_node_text(func_node)
                if call_name:
                    calls.append(call_name)
        
        for child in node.children:
            self._extract_calls_from_node(child, calls)
    
    def _extract_methods_from_class(self, class_node, methods: List[str]):
        """Extract methods from class node"""
        for child in class_node.children:
            if child.type in ["function_definition", "method_definition", "method_declaration"]:
                method_name = self._extract_name_from_node(child)
                if method_name:
                    methods.append(method_name)
    
    def _extract_comments(self, content: str) -> List[CommentInfo]:
        """Extract comments (universal method)"""
        comments = []
        lines = content.splitlines()
        
        # Select comment patterns based on language
        comment_patterns = self._get_comment_patterns()
        
        for i, line in enumerate(lines, 1):
            for pattern, comment_type in comment_patterns:
                match = re.search(pattern, line)
                if match:
                    comment_content = match.group(1).strip()
                    if comment_content:
                        comments.append(CommentInfo(
                            content=comment_content,
                            line_number=i,
                            comment_type=comment_type,
                            language=self.language
                        ))
                    break
        
        return comments
    
    def _get_comment_patterns(self) -> List[tuple]:
        """Get comment patterns"""
        patterns = {
            'python': [(r'#\s*(.*)', 'line')],
            'javascript': [(r'//\s*(.*)', 'line'), (r'/\*\s*(.*?)\s*\*/', 'block')],
            'typescript': [(r'//\s*(.*)', 'line'), (r'/\*\s*(.*?)\s*\*/', 'block')],
            'java': [(r'//\s*(.*)', 'line'), (r'/\*\s*(.*?)\s*\*/', 'block')],
            'c': [(r'//\s*(.*)', 'line'), (r'/\*\s*(.*?)\s*\*/', 'block')],
            'cpp': [(r'//\s*(.*)', 'line'), (r'/\*\s*(.*?)\s*\*/', 'block')],
            'go': [(r'//\s*(.*)', 'line'), (r'/\*\s*(.*?)\s*\*/', 'block')],
            'rust': [(r'//\s*(.*)', 'line'), (r'/\*\s*(.*?)\s*\*/', 'block')],
            'ruby': [(r'#\s*(.*)', 'line')],
            'php': [(r'//\s*(.*)', 'line'), (r'#\s*(.*)', 'line'), (r'/\*\s*(.*?)\s*\*/', 'block')],
            'bash': [(r'#\s*(.*)', 'line')],
        }
        
        return patterns.get(self.language, [(r'#\s*(.*)', 'line')])
    
    def _is_async_function(self, node) -> bool:
        """Check if it's an async function"""
        # Look for async keyword
        for child in node.children:
            if child.type == "async" or "async" in self._get_node_text(child).lower():
                return True
        return False
    
    def _get_node_text(self, node) -> str:
        """Get node text"""
        return node.text.decode('utf8')

class RegexFallbackAnalyzer:
    """Regex fallback analyzer"""
    
    def __init__(self, language: str):
        self.language = language
    
    def analyze_file(self, file_path: str, content: str) -> Optional[Dict[str, Any]]:
        """Analyze using regex"""
        
        patterns = self._get_language_patterns()
        if not patterns:
            return None
        
        functions = []
        classes = []
        imports = []
        comments = self._extract_comments_regex(content)
        
        # Extract functions
        for pattern in patterns.get('functions', []):
            for match in re.finditer(pattern, content, re.MULTILINE):
                func_name = match.group(1) if match.groups() else "unknown"
                line_num = content[:match.start()].count('\n') + 1
                
                functions.append(FunctionInfo(
                    name=func_name,
                    file_path=file_path,
                    start_line=line_num,
                    end_line=line_num,
                    parameters=[],
                    return_type=None,
                    calls=[],
                    called_by=[],
                    class_name=None,
                    module_name=Path(file_path).stem,
                    language=self.language,
                    docstring=None,
                    comments=[]
                ))
        
        # Extract classes
        for pattern in patterns.get('classes', []):
            for match in re.finditer(pattern, content, re.MULTILINE):
                class_name = match.group(1) if match.groups() else "unknown"
                line_num = content[:match.start()].count('\n') + 1
                
                classes.append(ClassInfo(
                    name=class_name,
                    file_path=file_path,
                    start_line=line_num,
                    end_line=line_num,
                    methods=[],
                    parent_classes=[],
                    module_name=Path(file_path).stem,
                    language=self.language,
                    docstring=None,
                    comments=[]
                ))
        
        module_name = Path(file_path).stem
        
        return {
            'functions': functions,
            'classes': classes,
            'module': ModuleInfo(
                name=module_name,
                file_path=file_path,
                imports=imports,
                exports=[],
                functions=[f.name for f in functions],
                classes=[c.name for c in classes],
                language=self.language,
                comments=comments,
                docstring=None
            )
        }
    
    def _get_language_patterns(self) -> Dict[str, List[str]]:
        """Get language-specific regex patterns"""
        patterns = {
            'java': {
                'functions': [
                    r'(?:public|private|protected|static|\s)*\s+\w+\s+(\w+)\s*\([^)]*\)\s*\{',
                ],
                'classes': [
                    r'(?:public|private|protected|\s)*\s*class\s+(\w+)',
                ]
            },
            'c': {
                'functions': [
                    r'\w+\s+(\w+)\s*\([^)]*\)\s*\{',
                ],
                'classes': [
                    r'typedef\s+struct\s+(\w+)',
                ]
            },
            'cpp': {
                'functions': [
                    r'\w+\s+(\w+)\s*\([^)]*\)\s*\{',
                    r'(\w+)::\w+\s*\([^)]*\)\s*\{',
                ],
                'classes': [
                    r'class\s+(\w+)',
                ]
            },
            'go': {
                'functions': [
                    r'func\s+(\w+)\s*\([^)]*\)',
                ],
                'classes': [
                    r'type\s+(\w+)\s+struct',
                ]
            },
            'rust': {
                'functions': [
                    r'fn\s+(\w+)\s*\([^)]*\)',
                ],
                'classes': [
                    r'struct\s+(\w+)',
                    r'enum\s+(\w+)',
                ]
            },
            'ruby': {
                'functions': [
                    r'def\s+(\w+)',
                ],
                'classes': [
                    r'class\s+(\w+)',
                ]
            },
            'php': {
                'functions': [
                    r'function\s+(\w+)\s*\(',
                ],
                'classes': [
                    r'class\s+(\w+)',
                ]
            },
        }
        
        return patterns.get(self.language, {})
    
    def _extract_comments_regex(self, content: str) -> List[CommentInfo]:
        """Extract comments using regex"""
        comments = []
        lines = content.splitlines()
        
        comment_patterns = {
            'java': [r'//\s*(.*)', r'/\*\s*(.*?)\s*\*/'],
            'c': [r'//\s*(.*)', r'/\*\s*(.*?)\s*\*/'],
            'cpp': [r'//\s*(.*)', r'/\*\s*(.*?)\s*\*/'],
            'go': [r'//\s*(.*)', r'/\*\s*(.*?)\s*\*/'],
            'rust': [r'//\s*(.*)', r'/\*\s*(.*?)\s*\*/'],
            'ruby': [r'#\s*(.*)'],
            'php': [r'//\s*(.*)', r'#\s*(.*)', r'/\*\s*(.*?)\s*\*/'],
        }
        
        patterns = comment_patterns.get(self.language, [r'#\s*(.*)'])
        
        for i, line in enumerate(lines, 1):
            for pattern in patterns:
                match = re.search(pattern, line)
                if match:
                    comments.append(CommentInfo(
                        content=match.group(1).strip(),
                        line_number=i,
                        comment_type="line",
                        language=self.language
                    ))
                    break
        
        return comments

class CCMConverter:
    """Converter to transform traditional analysis results to CCM format"""
    
    def __init__(self):
        self.node_id_counter = 0
        self.id_map = {}  # Store mapping from original objects to IDs
    
    def _generate_id(self, prefix: str = "node") -> str:
        """Generate unique ID"""
        self.node_id_counter += 1
        return f"{prefix}_{self.node_id_counter:06d}"
    
    def _get_ccm_visibility(self, visibility: str) -> CCMVisibility:
        """Convert visibility"""
        visibility_map = {
            "public": CCMVisibility.PUBLIC,
            "private": CCMVisibility.PRIVATE,
            "protected": CCMVisibility.PROTECTED,
            "internal": CCMVisibility.INTERNAL,
            "package": CCMVisibility.PACKAGE
        }
        return visibility_map.get(visibility.lower(), CCMVisibility.PUBLIC)
    
    def _get_ccm_modifiers(self, function_info: FunctionInfo) -> List[CCMModifier]:
        """Convert modifiers"""
        modifiers = []
        if function_info.is_static:
            modifiers.append(CCMModifier.STATIC)
        if function_info.is_async:
            modifiers.append(CCMModifier.ASYNC)
        
        # Handle decorators
        if function_info.decorators:
            for decorator in function_info.decorators:
                if 'abstract' in decorator.lower():
                    modifiers.append(CCMModifier.ABSTRACT)
                elif 'static' in decorator.lower():
                    modifiers.append(CCMModifier.STATIC)
        
        return modifiers
    
    def _get_ccm_class_modifiers(self, class_info: ClassInfo) -> List[CCMModifier]:
        """Convert class modifiers"""
        modifiers = []
        if class_info.is_abstract:
            modifiers.append(CCMModifier.ABSTRACT)
        
        # Handle decorators
        if class_info.decorators:
            for decorator in class_info.decorators:
                if 'abstract' in decorator.lower():
                    modifiers.append(CCMModifier.ABSTRACT)
                elif 'final' in decorator.lower():
                    modifiers.append(CCMModifier.FINAL)
        
        return modifiers
    
    def _parse_type_info(self, type_str: Optional[str], language: str) -> Optional[CCMTypeInfo]:
        """Parse type information"""
        if not type_str:
            return None
        
        # Basic type mapping
        primitive_types = {
            'python': {'int', 'float', 'str', 'bool', 'bytes', 'None'},
            'javascript': {'number', 'string', 'boolean', 'undefined', 'null'},
            'typescript': {'number', 'string', 'boolean', 'undefined', 'null', 'void'},
            'java': {'int', 'long', 'float', 'double', 'boolean', 'char', 'byte', 'short', 'void'},
            'c': {'int', 'long', 'float', 'double', 'char', 'void'},
            'cpp': {'int', 'long', 'float', 'double', 'char', 'bool', 'void'},
            'go': {'int', 'int32', 'int64', 'float32', 'float64', 'string', 'bool'},
            'rust': {'i32', 'i64', 'f32', 'f64', 'bool', 'char', 'str'},
        }
        
        lang_primitives = primitive_types.get(language, set())
        
        # Check if it's an array type
        is_array = False
        if any(marker in type_str for marker in ['[]', 'List[', 'Array<', 'Vec<', 'list[', 'array[']):
            is_array = True
        
        # Check if nullable
        is_nullable = False
        if any(marker in type_str for marker in ['?', 'Optional[', 'Maybe<', 'Option<']):
            is_nullable = True
        
        # Extract basic type name
        clean_type = type_str
        for marker in ['[]', '?', 'Optional[', 'List[', 'Array<', 'Vec<', 'Maybe<', 'Option<']:
            clean_type = clean_type.replace(marker, '').replace(']', '').replace('>', '')
        clean_type = clean_type.strip()
        
        return CCMTypeInfo(
            name=clean_type,
            is_primitive=clean_type in lang_primitives,
            is_array=is_array,
            is_nullable=is_nullable
        )
    
    def _convert_parameters(self, parameters: List[str], type_annotations: Dict[str, str], language: str) -> List[CCMParameter]:
        """Convert parameter information"""
        ccm_parameters = []
        
        for param in parameters:
            # Parse parameter name and default value
            param_name = param
            default_value = None
            is_optional = False
            is_variadic = False
            
            if '=' in param:
                param_name, default_value = param.split('=', 1)
                param_name = param_name.strip()
                default_value = default_value.strip()
                is_optional = True
            
            # Check variadic parameters
            if param_name.startswith('*'):
                is_variadic = True
                param_name = param_name.lstrip('*')
            
            # Get type information
            type_info = None
            if type_annotations and param_name in type_annotations:
                type_info = self._parse_type_info(type_annotations[param_name], language)
            
            ccm_parameters.append(CCMParameter(
                name=param_name,
                type_info=type_info,
                default_value=default_value,
                is_optional=is_optional,
                is_variadic=is_variadic
            ))
        
        return ccm_parameters
    
    def _create_documentation(self, docstring: Optional[str], comments: List[CommentInfo]) -> Optional[CCMDocumentation]:
        """Create documentation information"""
        if not docstring and not comments:
            return None
        
        # Parse docstring
        summary = None
        description = None
        parameters = {}
        returns = None
        
        if docstring:
            lines = docstring.strip().split('\n')
            if lines:
                summary = lines[0].strip()
                if len(lines) > 1:
                    description = '\n'.join(lines[1:]).strip()
        
        # Extract additional information from comments
        comment_text = []
        for comment in comments:
            if comment.comment_type == 'docstring':
                continue  # Already processed docstring
            comment_text.append(comment.content)
        
        if comment_text and not description:
            description = '\n'.join(comment_text)
        
        return CCMDocumentation(
            summary=summary,
            description=description,
            parameters=parameters,
            returns=returns
        )
    
    def convert_to_ccm(self, 
                      functions: List[FunctionInfo], 
                      classes: List[ClassInfo], 
                      modules: List[ModuleInfo],
                      comments: List[CommentInfo],
                      project_info: Dict[str, Any]) -> CCMAnalysisResult:
        """Convert traditional analysis results to CCM format"""
        
        ccm_nodes = []
        node_lookup = {}  # For quick node lookup: {name: node_id}
        
        # ===== Phase 1: Create all nodes =====
        print("🔄 Phase 1: Creating all nodes...")
        
        # 1. Create module nodes
        module_nodes = {}
        for module in modules:
            module_id = self._generate_id("module")
            
            ccm_node = CCMNode(
                id=module_id,
                name=module.name,
                node_type=CCMNodeType.MODULE,
                location=CCMLocation(
                    file_path=module.file_path,
                    start_line=1,
                    end_line=1
                ),
                language=module.language,
                documentation=self._create_documentation(module.docstring, module.comments),
                children_ids=[],
                relationships=[]
            )
            ccm_nodes.append(ccm_node)
            module_nodes[module.name] = ccm_node
            
            # Register to lookup table
            node_lookup[module.name] = module_id
            node_lookup[f"module:{module.name}"] = module_id
        
        # 2. Create class nodes
        class_nodes = {}
        for class_info in classes:
            class_id = self._generate_id("class")
            class_full_name = f"{class_info.module_name}.{class_info.name}"
            
            # Find parent module
            parent_id = None
            if class_info.module_name in module_nodes:
                parent_id = module_nodes[class_info.module_name].id
                module_nodes[class_info.module_name].children_ids.append(class_id)
            
            ccm_node = CCMNode(
                id=class_id,
                name=class_info.name,
                node_type=CCMNodeType.CLASS,
                location=CCMLocation(
                    file_path=class_info.file_path,
                    start_line=class_info.start_line,
                    end_line=class_info.end_line
                ),
                language=class_info.language,
                modifiers=self._get_ccm_class_modifiers(class_info),
                parent_id=parent_id,
                children_ids=[],
                relationships=[],
                documentation=self._create_documentation(class_info.docstring, class_info.comments)
            )
            ccm_nodes.append(ccm_node)
            class_nodes[class_full_name] = ccm_node
            
            # Register to lookup table (multiple possible names)
            node_lookup[class_info.name] = class_id
            node_lookup[f"class:{class_info.name}"] = class_id
            node_lookup[class_full_name] = class_id
            node_lookup[f"class:{class_full_name}"] = class_id
        
        # 3. Create function nodes
        function_nodes = {}
        for function_info in functions:
            function_id = self._generate_id("function")
            
            # Build function's full name
            if function_info.class_name:
                function_full_name = f"{function_info.module_name}.{function_info.class_name}.{function_info.name}"
                function_class_name = f"{function_info.class_name}.{function_info.name}"
            else:
                function_full_name = f"{function_info.module_name}.{function_info.name}"
                function_class_name = None
            
            # Determine node type
            node_type = CCMNodeType.METHOD if function_info.class_name else CCMNodeType.FUNCTION
            if function_info.name in ['__init__', 'constructor', 'init']:
                node_type = CCMNodeType.CONSTRUCTOR
            
            # Find parent node
            parent_id = None
            if function_info.class_name:
                class_key = f"{function_info.module_name}.{function_info.class_name}"
                if class_key in class_nodes:
                    parent_id = class_nodes[class_key].id
                    class_nodes[class_key].children_ids.append(function_id)
            elif function_info.module_name in module_nodes:
                parent_id = module_nodes[function_info.module_name].id
                module_nodes[function_info.module_name].children_ids.append(function_id)
            
            # Convert parameters
            ccm_parameters = self._convert_parameters(
                function_info.parameters, 
                function_info.type_annotations or {}, 
                function_info.language
            )
            
            # Convert return type
            return_type = self._parse_type_info(function_info.return_type, function_info.language)
            
            ccm_node = CCMNode(
                id=function_id,
                name=function_info.name,
                node_type=node_type,
                location=CCMLocation(
                    file_path=function_info.file_path,
                    start_line=function_info.start_line,
                    end_line=function_info.end_line
                ),
                language=function_info.language,
                visibility=self._get_ccm_visibility(function_info.visibility),
                modifiers=self._get_ccm_modifiers(function_info),
                parameters=ccm_parameters,
                return_type=return_type,
                parent_id=parent_id,
                relationships=[],
                documentation=self._create_documentation(function_info.docstring, function_info.comments)
            )
            ccm_nodes.append(ccm_node)
            function_nodes[function_full_name] = ccm_node
            
            # Register to lookup table (multiple possible names)
            node_lookup[function_info.name] = function_id
            node_lookup[f"function:{function_info.name}"] = function_id
            node_lookup[function_full_name] = function_id
            node_lookup[f"function:{function_full_name}"] = function_id
            
            if function_class_name:
                node_lookup[function_class_name] = function_id
                node_lookup[f"function:{function_class_name}"] = function_id
            
            # Module-level function name
            module_function_name = f"{function_info.module_name}.{function_info.name}"
            node_lookup[module_function_name] = function_id
            node_lookup[f"function:{module_function_name}"] = function_id
        
        # 4. Create comment nodes
        for comment in comments:
            comment_id = self._generate_id("comment")
            
            ccm_node = CCMNode(
                id=comment_id,
                name=f"comment_{comment.line_number}",
                node_type=CCMNodeType.COMMENT,
                location=CCMLocation(
                    file_path="",  # Comments may not have file path
                    start_line=comment.line_number,
                    end_line=comment.line_number
                ),
                language=comment.language,
                raw_content=comment.content,
                annotations={"comment_type": comment.comment_type}
            )
            ccm_nodes.append(ccm_node)
        
        print(f"✅ Created {len(ccm_nodes)} nodes")
        print(f"📋 Node lookup table contains {len(node_lookup)} entries")
        
        # ===== Phase 2: Process all relationships =====
        print("🔗 Phase 2: Processing node relationships...")
        
        all_relationships = []
        resolved_count = 0
        unresolved_count = 0
        
        # 1. Process module import relationships
        for module in modules:
            module_id = module_nodes[module.name].id
            
            for import_stmt in module.imports:
                imported_module = self._extract_module_name_from_import(import_stmt)
                if imported_module:
                    target_id = self._find_target_id(imported_module, node_lookup)
                    
                    relationship = CCMRelationship(
                        type="imports",
                        target_id=target_id,
                        target_name=imported_module
                    )
                    
                    module_nodes[module.name].relationships.append(relationship)
                    all_relationships.append(relationship)
                    
                    if target_id:
                        resolved_count += 1
                    else:
                        unresolved_count += 1
        
        # 2. Process class inheritance relationships
        for class_info in classes:
            class_full_name = f"{class_info.module_name}.{class_info.name}"
            class_node = class_nodes[class_full_name]
            
            for parent_class in class_info.parent_classes:
                target_id = self._find_target_id(parent_class, node_lookup, 
                                               context={'module': class_info.module_name})
                
                relationship = CCMRelationship(
                    type="inherits",
                    target_id=target_id,
                    target_name=parent_class
                )
                
                class_node.relationships.append(relationship)
                all_relationships.append(relationship)
                
                if target_id:
                    resolved_count += 1
                else:
                    unresolved_count += 1
        
        # 3. Process function call relationships
        for function_info in functions:
            if function_info.class_name:
                function_full_name = f"{function_info.module_name}.{function_info.class_name}.{function_info.name}"
            else:
                function_full_name = f"{function_info.module_name}.{function_info.name}"
            
            function_node = function_nodes[function_full_name]
            
            for call in function_info.calls:
                # Filter out obvious builtin function or method calls
                if self._is_likely_builtin_call(call):
                    continue
                    
                target_id = self._find_target_id(call, node_lookup, 
                                               context={
                                                   'module': function_info.module_name,
                                                   'class': function_info.class_name
                                               })
                
                # Only create relationship if target ID is found
                if target_id:
                    relationship = CCMRelationship(
                        type="calls",
                        target_id=target_id,
                        target_name=call
                    )
                    
                    function_node.relationships.append(relationship)
                    all_relationships.append(relationship)
                    resolved_count += 1
        
        print(f"✅ Processed {len(all_relationships)} relationships")
        print(f"🎯 Successfully resolved: {resolved_count}")
        print(f"❌ Failed to resolve: {unresolved_count}")
        print(f"📊 Resolution success rate: {(resolved_count / len(all_relationships) * 100):.1f}%" if all_relationships else "N/A")
        
        # Create project information
        project = CCMProject(
            name=project_info.get('name', 'Unknown Project'),
            root_path=project_info.get('root_path', ''),
            project_type=project_info.get('project_type', 'unknown'),
            languages=project_info.get('languages', [])
        )
        
        # Create metadata
        metadata = {
            "analysis_timestamp": project_info.get('timestamp'),
            "analyzer_version": "2.1.0-ccm-two-phase",
            "total_nodes": len(ccm_nodes),
            "total_relationships": len(all_relationships),
            "resolved_relationships": resolved_count,
            "unresolved_relationships": unresolved_count,
            "resolution_rate": (resolved_count / len(all_relationships) * 100) if all_relationships else 0,
            "node_type_counts": self._count_node_types(ccm_nodes),
            "language_distribution": self._count_languages(ccm_nodes),
            "relationship_type_counts": self._count_relationship_types(all_relationships),
            "lookup_table_size": len(node_lookup),
            "original_stats": project_info.get('stats', {})
        }
        
        return CCMAnalysisResult(
            project=project,
            nodes=ccm_nodes,
            relationships=all_relationships,
            metadata=metadata
        )
    
    def _find_target_id(self, target_name: str, node_lookup: Dict[str, str], 
                       context: Dict[str, str] = None) -> str:
        """Find target ID in node lookup table - only search for nodes that actually exist in code"""
        if not target_name:
            return ""
        
        context = context or {}
        
        # Build search candidate list, ordered by priority
        candidates = []
        
        # 1. Exact match
        candidates.append(target_name)
        candidates.append(f"function:{target_name}")
        candidates.append(f"class:{target_name}")
        candidates.append(f"module:{target_name}")
        
        # 2. Match in current context
        current_module = context.get('module')
        current_class = context.get('class')
        
        if current_module:
            candidates.append(f"{current_module}.{target_name}")
            candidates.append(f"function:{current_module}.{target_name}")
            candidates.append(f"class:{current_module}.{target_name}")
            
        if current_class:
            candidates.append(f"{current_class}.{target_name}")
            candidates.append(f"function:{current_class}.{target_name}")
            
            if current_module:
                candidates.append(f"{current_module}.{current_class}.{target_name}")
                candidates.append(f"function:{current_module}.{current_class}.{target_name}")
        
        # Search by priority - only in known nodes
        for candidate in candidates:
            if candidate in node_lookup:
                return node_lookup[candidate]
        
        # If not found, it's an external dependency, return empty string
        return ""
    
    def _is_likely_builtin_call(self, call: str) -> bool:
        """Check if it's likely a builtin function or method call"""
        
        # Common builtin functions
        builtin_functions = {
            # Python builtin functions
            'print', 'len', 'range', 'str', 'int', 'float', 'bool', 'list', 'dict', 'set', 'tuple',
            'abs', 'all', 'any', 'bin', 'chr', 'dir', 'divmod', 'enumerate', 'eval', 'exec',
            'filter', 'format', 'getattr', 'hasattr', 'hash', 'hex', 'id', 'input', 'isinstance',
            'issubclass', 'iter', 'map', 'max', 'min', 'next', 'oct', 'open', 'ord', 'pow',
            'repr', 'reversed', 'round', 'setattr', 'sorted', 'sum', 'type', 'vars', 'zip',
            
            # JavaScript builtin functions
            'console.log', 'parseInt', 'parseFloat', 'isNaN', 'isFinite', 'encodeURI', 'decodeURI',
            'setTimeout', 'setInterval', 'clearTimeout', 'clearInterval',
            
            # Common method call patterns
            'append', 'extend', 'insert', 'remove', 'pop', 'clear', 'index', 'count',
            'sort', 'reverse', 'copy', 'get', 'keys', 'values', 'items', 'update',
            'add', 'discard', 'union', 'intersection', 'difference',
            'split', 'join', 'strip', 'replace', 'find', 'startswith', 'endswith',
            'upper', 'lower', 'capitalize', 'title', 'format'
        }
        
        # Check if it's a builtin function
        if call in builtin_functions:
            return True
        
        # Check if it contains dot (possibly method call)
        if '.' in call:
            # Extract method name
            method_name = call.split('.')[-1]
            # Check if it's a common method name
            if method_name in builtin_functions:
                return True
            
            # Check if it's a common object method call pattern
            common_patterns = [
                'append', 'extend', 'insert', 'remove', 'pop', 'clear',
                'get', 'set', 'add', 'delete', 'update', 'keys', 'values',
                'push', 'shift', 'unshift', 'slice', 'splice', 'concat',
                'toString', 'valueOf', 'hasOwnProperty'
            ]
            if method_name in common_patterns:
                return True
        
        # Check if it contains special characters (possibly complex expression)
        if any(char in call for char in ['(', ')', '[', ']', '{', '}', '+', '-', '*', '/', '=']):
            return True
        
        # Check if it's a single character or very short name (possibly variable)
        if len(call) <= 2:
            return True
        
        return False

    def _extract_module_name_from_import(self, import_stmt: str) -> Optional[str]:
        """Extract module name from import statement"""
        # Simple import statement parsing
        import_stmt = import_stmt.strip()
        
        # Handle "import module" format
        if import_stmt.startswith('import '):
            module_name = import_stmt[7:].split('.')[0].split(' as ')[0].strip()
            return module_name
        
        # Handle "from module import ..." format
        elif import_stmt.startswith('from '):
            parts = import_stmt.split(' import ')
            if len(parts) > 0:
                module_name = parts[0][5:].strip()
                return module_name
        
        return None
    
    def _count_relationship_types(self, relationships: List[CCMRelationship]) -> Dict[str, int]:
        """Count relationship type quantities"""
        counts = defaultdict(int)
        for rel in relationships:
            counts[rel.type] += 1
        return dict(counts)
    
    def _count_node_types(self, nodes: List[CCMNode]) -> Dict[str, int]:
        """Count node type quantities"""
        counts = defaultdict(int)
        for node in nodes:
            counts[node.node_type.value] += 1
        return dict(counts)
    
    def _count_languages(self, nodes: List[CCMNode]) -> Dict[str, int]:
        """Count language distribution"""
        counts = defaultdict(int)
        for node in nodes:
            counts[node.language] += 1
        return dict(counts)

class ComprehensiveMultiLanguageAnalyzer:
    """Comprehensive multi-language analyzer"""
    
    def __init__(self):
        self.supported_languages = {
            'python', 'javascript', 'typescript', 'java', 'c', 'cpp',
            'go', 'rust', 'ruby', 'php', 'csharp', 'kotlin', 'swift',
            'scala', 'bash', 'html', 'css', 'json', 'yaml', 'sql'
        }
        
        # Ignored files and directories
        self.ignore_patterns = {
            # Version control
            '.git', '.svn', '.hg',
            # Dependency directories
            'node_modules', 'bower_components',
            # Python
            '__pycache__', '.pytest_cache', 'venv', 'env', '.venv',
            'site-packages', '.tox', '.coverage', 'htmlcov',
            # Build output
            'dist', 'build', '.next', 'out', 'target', 'bin', 'obj',
            # IDE and editors
            '.vscode', '.idea', '.vs', '.eclipse',
            # Temporary files
            'tmp', 'temp', '.tmp',
            # Logs and cache
            'logs', 'log', '.cache', 'coverage', '.nyc_output',
            # Mobile
            'ios', 'android', '.expo',
            # Others
            '.terraform', '.serverless'
        }
        
        # Ignored file patterns (more comprehensive filtering)
        self.ignore_files = {
            # Compressed and compiled files
            '.min.js', '.min.css', '.bundle.js', '.bundle.css',
            # Test files
            'test', 'spec', '.test.', '.spec.',
            # Configuration files
            '.env', '.env.local', '.env.development', '.env.production',
            '.gitignore', '.gitattributes', '.editorconfig',
            # Package management files
            'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
            'pipfile.lock', 'poetry.lock', 'requirements.txt',
            'composer.lock', 'gemfile.lock',
            # Documentation files
            'readme', 'license', 'changelog', 'contributing',
            # Configuration files
            '.eslintrc', '.prettierrc', '.babelrc', 'tsconfig.json',
            'webpack.config', 'rollup.config', 'vite.config',
            'jest.config', 'cypress.config', 'playwright.config',
            # Deployment files
            'dockerfile', '.dockerignore', 'docker-compose',
            'k8s', 'kubernetes', '.github', '.gitlab-ci',
            # Data files
            '.db', '.sqlite', '.sql', '.csv', '.json', '.xml',
            # Media files
            '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico',
            '.mp4', '.mp3', '.wav', '.pdf',
            # Font files
            '.woff', '.woff2', '.ttf', '.eot',
            # Others
            '.map', '.d.ts', '.backup', '.swp', '.tmp'
        }
        
        # Project type specific ignore rules
        self.project_specific_ignores = {}
        
        print(f"Supported languages: {', '.join(sorted(self.supported_languages))}")
    
    def _detect_project_type(self, repo_path: Path) -> str:
        """Detect project type to apply specific ignore rules"""
        
        # Check signature files
        if (repo_path / "package.json").exists():
            return "nodejs"
        elif (repo_path / "requirements.txt").exists() or (repo_path / "setup.py").exists():
            return "python"
        elif (repo_path / "pom.xml").exists() or (repo_path / "build.gradle").exists():
            return "java"
        elif (repo_path / "go.mod").exists():
            return "go"
        elif (repo_path / "Cargo.toml").exists():
            return "rust"
        elif (repo_path / "composer.json").exists():
            return "php"
        elif (repo_path / "Gemfile").exists():
            return "ruby"
        else:
            return "unknown"
    
    def _get_project_specific_ignores(self, project_type: str) -> set:
        """Return specific ignore patterns based on project type"""
        
        ignores = {
            "nodejs": {
                # Files
                'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
                '.npmrc', '.yarnrc', 'babel.config.js', 'webpack.config.js',
                'next.config.js', 'nuxt.config.js', 'vue.config.js',
                # Directories
                'node_modules', '.next', 'out', 'dist', 'build'
            },
            "python": {
                # Files
                'requirements.txt', 'setup.py', 'setup.cfg', 'pyproject.toml',
                'Pipfile', 'Pipfile.lock', 'poetry.lock', '.flake8',
                'pytest.ini', 'tox.ini', '.coveragerc', 'mypy.ini',
                # Environment files (important!)
                '.env', '.env.local', '.env.development', '.env.production',
                '.env.staging', '.env.test',
                # Directories
                '__pycache__', 'venv', 'env', '.venv', '.env',
                'site-packages', '.tox', 'htmlcov', '.coverage'
            },
            "java": {
                # Files
                'pom.xml', 'build.gradle', 'gradle.properties',
                'application.properties', 'application.yml',
                # Directories
                'target', 'build', '.gradle', 'bin', 'out'
            },
            "go": {
                # Files
                'go.mod', 'go.sum',
                # Directories
                'vendor'
            },
            "rust": {
                # Files
                'Cargo.toml', 'Cargo.lock',
                # Directories
                'target'
            },
            "php": {
                # Files
                'composer.json', 'composer.lock', '.env',
                # Directories
                'vendor'
            },
            "ruby": {
                # Files
                'Gemfile', 'Gemfile.lock', '.env',
                # Directories
                'vendor', 'bundle'
            }
        }
        
        return ignores.get(project_type, set())
    
    def analyze_repository(self, repo_path: str, output_path: str = "/output/analysis.json"):
        """Analyze entire code repository"""
        repo_path = Path(repo_path)
        
        # Detect project type
        project_type = self._detect_project_type(repo_path)
        project_ignores = self._get_project_specific_ignores(project_type)
        
        print(f"🔍 Starting code repository analysis: {repo_path}")
        print(f"📋 Detected project type: {project_type}")
        print(f"🚫 Applying specific ignore rules: {len(project_ignores)} items")
        
        # Temporarily add project-specific ignore rules
        original_ignore_files = self.ignore_files.copy()
        self.ignore_files.update(project_ignores)
        
        all_functions = []
        all_classes = []
        all_modules = []
        all_comments = []
        language_stats = defaultdict(int)
        file_count = 0
        ignored_count = 0
        
        try:
            for file_path in self._find_code_files(repo_path):
                try:
                    language = LanguageDetector.detect_language(str(file_path))
                    if not language or language not in self.supported_languages:
                        continue
                    
                    print(f"📄 Analyzing file: {file_path} ({language})")
                    result = self.analyze_file(file_path, language)
                    
                    if result:
                        all_functions.extend(result['functions'])
                        all_classes.extend(result['classes'])
                        all_modules.append(result['module'])
                        
                        # Collect comments
                        module_comments = result['module'].comments if hasattr(result['module'], 'comments') and result['module'].comments else []
                        all_comments.extend(module_comments)
                        
                        language_stats[language] += 1
                        file_count += 1
                        
                except Exception as e:
                    print(f"❌ File analysis failed {file_path}: {e}")
                    continue
        
        finally:
            # Restore original ignore rules
            self.ignore_files = original_ignore_files
        
        # Build call relationships
        print("🔗 Building function call relationships...")
        self._build_call_relationships(all_functions)
        
        # Generate statistics
        stats = {
            'total_files': file_count,
            'total_functions': len(all_functions),
            'total_classes': len(all_classes),
            'total_comments': len(all_comments),
            'languages': dict(language_stats),
            'functions_per_language': self._count_by_language(all_functions),
            'classes_per_language': self._count_by_language(all_classes),
            'comments_per_language': self._count_comments_by_language(all_comments),
            'project_type': project_type
        }
        
        # Create CCM converter and generate CCM format result
        print("🔄 Converting to CCM format...")
        ccm_converter = CCMConverter()
        
        # Prepare project information
        project_info = {
            'name': repo_path.name,
            'root_path': str(repo_path),
            'project_type': project_type,
            'languages': list(language_stats.keys()),
            'stats': stats,
            'timestamp': None  # Can add timestamp
        }
        
        # Convert to CCM format
        ccm_result = ccm_converter.convert_to_ccm(
            functions=all_functions,
            classes=all_classes,
            modules=all_modules,
            comments=all_comments,
            project_info=project_info
        )
        
        # Generate two format outputs
        # 1. Traditional format (backward compatibility)
        legacy_result = {
            'functions': [self._convert_paths_to_strings(asdict(f)) for f in all_functions],
            'classes': [self._convert_paths_to_strings(asdict(c)) for c in all_classes],
            'modules': [self._convert_paths_to_strings(asdict(m)) for m in all_modules],
            'comments': [self._convert_paths_to_strings(asdict(c)) for c in all_comments],
            'stats': stats,
            'repository_path': str(repo_path),
            'analysis_metadata': {
                'analyzer_version': '2.0.0',
                'features': ['functions', 'classes', 'imports', 'comments', 'docstrings', 'type_annotations'],
                'tree_sitter_available': TREE_SITTER_AVAILABLE,
                'supported_languages': list(self.supported_languages),
                'project_type': project_type,
                'files_analyzed': file_count,
                'files_ignored': ignored_count
            }
        }
        
        # 2. CCM format (new standard)
        ccm_dict = ccm_result.to_dict()
        
        # Save results
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save CCM format (main output)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(ccm_dict, f, indent=2, ensure_ascii=False)
        
        # Save traditional format (compatibility)
        legacy_output_path = output_path.replace('.json', '_legacy.json')
        with open(legacy_output_path, 'w', encoding='utf-8') as f:
            json.dump(legacy_result, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Analysis complete!")
        print(f"📊 Statistics:")
        print(f"   - Project type: {project_type}")
        print(f"   - Total files: {stats['total_files']}")
        print(f"   - Total functions: {stats['total_functions']}")
        print(f"   - Total classes: {stats['total_classes']}")
        print(f"   - Total comments: {stats['total_comments']}")
        print(f"   - Supported languages: {list(stats['languages'].keys())}")
        print(f"📁 CCM format result: {output_path}")
        print(f"📁 Traditional format result: {legacy_output_path}")
        print(f"🎯 Total CCM nodes: {ccm_dict['metadata']['total_nodes']}")
        print(f"🔗 Total relationships: {ccm_dict['metadata']['total_relationships']}")
        print(f"📈 Node type distribution: {ccm_dict['metadata']['node_type_counts']}")
        
        return ccm_result
    
    def analyze_file(self, file_path: str, language: str) -> Optional[Dict[str, Any]]:
        """Analyze single file"""
        if not os.path.exists(file_path):
            return None
        
        if self._should_ignore_file(Path(file_path)):
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if len(content.strip()) < 10:
                return None
            
            # Prefer Tree-sitter analyzer
            if TREE_SITTER_AVAILABLE and language in TREE_SITTER_MODULES:
                analyzer = UniversalTreeSitterAnalyzer(language)
                result = analyzer.analyze_file(file_path, content)
                if result:
                    return result
            
            # Fallback: use regex analyzer
            fallback_analyzer = RegexFallbackAnalyzer(language)
            return fallback_analyzer.analyze_file(file_path, content)
            
        except Exception as e:
            print(f"Failed to read file {file_path}: {e}")
            return None
    
    def _find_code_files(self, repo_path: Path) -> List[Path]:
        """Find all code files"""
        code_files = []
        
        for root, dirs, files in os.walk(repo_path):
            # Filter ignored directories
            dirs[:] = [d for d in dirs if d not in self.ignore_patterns and not d.startswith('.')]
            
            for file in files:
                file_path = Path(root) / file
                
                # First check if should be ignored
                if self._should_ignore_file(file_path):
                    continue
                
                # Check if it's a supported code file
                language = LanguageDetector.detect_language(str(file_path))
                if language and language in self.supported_languages:
                    code_files.append(file_path)
        
        return code_files
    
    def _should_ignore_file(self, file_path: Path) -> bool:
        """Check if file should be ignored"""
        file_name = file_path.name.lower()
        file_stem = file_path.stem.lower()
        
        # Check complete filename
        if file_name in {'.env', '.env.local', '.env.development', '.env.production', 
                        '.gitignore', '.dockerignore', 'dockerfile', 'readme.md', 
                        'license', 'changelog.md', 'package.json', 'package-lock.json',
                        'yarn.lock', 'requirements.txt', 'pipfile.lock', 'poetry.lock',
                        'composer.json', 'composer.lock', 'gemfile', 'gemfile.lock'}:
            return True
        
        # Check filename patterns
        for pattern in self.ignore_files:
            if pattern in file_name or pattern in file_stem:
                return True
        
        # Check special configuration file patterns
        config_patterns = [
            'config', 'conf', '.rc', '.config', 'settings',
            'webpack', 'rollup', 'vite', 'babel', 'eslint', 'prettier',
            'jest', 'cypress', 'playwright', 'tsconfig', 'jsconfig'
        ]
        
        for pattern in config_patterns:
            if pattern in file_name:
                return True
        
        # Check if it's a hidden file (starts with ., but exclude code files)
        if file_name.startswith('.') and file_path.suffix not in {'.py', '.js', '.ts', '.jsx', '.tsx'}:
            return True
        
        # Check file size (exclude overly large files, possibly data files)
        try:
            if file_path.stat().st_size > 1024 * 1024:  # Over 1MB
                return True
        except:
            pass
        
        return False
    
    def _build_call_relationships(self, functions: List[FunctionInfo]):
        """Build function call relationships"""
        func_map = {}
        for func in functions:
            func_map[func.name] = func
            if func.class_name:
                func_map[f"{func.class_name}.{func.name}"] = func
                func_map[f"{func.module_name}.{func.class_name}.{func.name}"] = func
            func_map[f"{func.module_name}.{func.name}"] = func
        
        for func in functions:
            for call in func.calls:
                clean_call = self._clean_function_call(call)
                
                called_func = None
                possible_names = [
                    clean_call,
                    f"{func.module_name}.{clean_call}",
                    f"{func.class_name}.{clean_call}" if func.class_name else None,
                    f"{func.module_name}.{func.class_name}.{clean_call}" if func.class_name else None
                ]
                
                for possible_name in possible_names:
                    if possible_name and possible_name in func_map:
                        called_func = func_map[possible_name]
                        break
                
                if called_func and called_func != func:
                    caller_name = f"{func.class_name}.{func.name}" if func.class_name else func.name
                    if caller_name not in called_func.called_by:
                        called_func.called_by.append(caller_name)
    
    def _clean_function_call(self, call: str) -> str:
        """Clean function call name"""
        if '.' in call:
            return call.split('.')[-1]
        return call
    
    def _convert_paths_to_strings(self, obj):
        """Recursively convert all Path objects to strings"""
        if isinstance(obj, dict):
            return {key: self._convert_paths_to_strings(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_paths_to_strings(item) for item in obj]
        elif isinstance(obj, Path):
            return str(obj)
        else:
            return obj

    def _count_by_language(self, items: List) -> Dict[str, int]:
        """Count by language"""
        counts = defaultdict(int)
        for item in items:
            counts[item.language] += 1
        return dict(counts)
    
    def _count_comments_by_language(self, comments: List[CommentInfo]) -> Dict[str, int]:
        """Count comments by language"""
        counts = defaultdict(int)
        for comment in comments:
            counts[comment.language] += 1
        return dict(counts)

def main():
    """Main function - Docker container entry point"""
    parser = argparse.ArgumentParser(description='Comprehensive multi-language code analyzer')
    parser.add_argument('--input', required=True, help='Input code directory')
    parser.add_argument('--output', default='/output/analysis.json', help='Output file path')
    
    args = parser.parse_args()
    
    # Validate input directory
    if not os.path.exists(args.input):
        print(f"❌ Input directory does not exist: {args.input}")
        return 1
    
    try:
        # Create analyzer and run
        analyzer = ComprehensiveMultiLanguageAnalyzer()
        result = analyzer.analyze_repository(args.input, args.output)
        
        print(f"🎉 Analysis complete! Results saved to: {args.output}")
        return 0
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())