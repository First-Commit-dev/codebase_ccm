#!/usr/bin/env python3
"""
真正的多语言代码分析器
支持20+编程语言的函数、类、注释分析
输出符合CCM (Canonical Code Model) 标准的统一格式
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

# 动态导入tree-sitter
TREE_SITTER_MODULES = {}
TREE_SITTER_AVAILABLE = True

try:
    from tree_sitter import Language, Parser, Node
    
    # 尝试导入所有支持的语言
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
            print(f"⚠️  {lang} tree-sitter模块不可用")
    
    print(f"✅ Tree-sitter可用，支持语言: {list(TREE_SITTER_MODULES.keys())}")
    
except ImportError:
    TREE_SITTER_AVAILABLE = False
    print("⚠️  Tree-sitter不可用，使用备选解析器")

# CCM 枚举类型定义
class CCMNodeType(Enum):
    """CCM 节点类型枚举"""
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
    """CCM 可见性枚举"""
    PUBLIC = "public"
    PRIVATE = "private"
    PROTECTED = "protected"
    INTERNAL = "internal"
    PACKAGE = "package"

class CCMModifier(Enum):
    """CCM 修饰符枚举"""
    STATIC = "static"
    ABSTRACT = "abstract"
    FINAL = "final"
    ASYNC = "async"
    VIRTUAL = "virtual"
    OVERRIDE = "override"
    READONLY = "readonly"
    CONST = "const"

# CCM 核心数据结构
@dataclass
class CCMLocation:
    """CCM 位置信息"""
    file_path: str
    start_line: int
    end_line: int
    start_column: Optional[int] = None
    end_column: Optional[int] = None

@dataclass
class CCMTypeInfo:
    """CCM 类型信息"""
    name: str
    is_primitive: bool = False
    is_array: bool = False
    is_nullable: bool = False
    generic_parameters: Optional[List[str]] = None
    namespace: Optional[str] = None

@dataclass
class CCMParameter:
    """CCM 参数信息"""
    name: str
    type_info: Optional[CCMTypeInfo] = None
    default_value: Optional[str] = None
    is_optional: bool = False
    is_variadic: bool = False

@dataclass
class CCMRelationship:
    """CCM 关系信息"""
    type: str  # "calls", "inherits", "implements", "uses", "contains", "imports"
    target_id: str
    target_name: str
    # 可选的元数据，用于存储关系的额外信息（如调用次数、导入别名等）
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class CCMDocumentation:
    """CCM 文档信息"""
    summary: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[Dict[str, str]] = None
    returns: Optional[str] = None
    examples: Optional[List[str]] = None
    tags: Optional[Dict[str, str]] = None

@dataclass
class CCMNode:
    """CCM 统一节点"""
    id: str  # 唯一标识符
    name: str
    node_type: CCMNodeType
    location: CCMLocation
    language: str
    
    # 可选属性
    visibility: Optional[CCMVisibility] = None
    modifiers: Optional[List[CCMModifier]] = None
    type_info: Optional[CCMTypeInfo] = None
    parameters: Optional[List[CCMParameter]] = None
    return_type: Optional[CCMTypeInfo] = None
    parent_id: Optional[str] = None
    children_ids: Optional[List[str]] = None
    relationships: Optional[List[CCMRelationship]] = None
    documentation: Optional[CCMDocumentation] = None
    
    # 原始信息（用于调试和特殊处理）
    raw_content: Optional[str] = None
    annotations: Optional[Dict[str, Any]] = None

@dataclass
class CCMProject:
    """CCM 项目信息"""
    name: str
    root_path: str
    project_type: str
    languages: List[str]
    
@dataclass
class CCMAnalysisResult:
    """CCM 分析结果"""
    project: CCMProject
    nodes: List[CCMNode]
    relationships: List[CCMRelationship]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "ccm_version": "1.0.0",
            "project": self._serialize_object(asdict(self.project)),
            "nodes": [self._serialize_object(asdict(node)) for node in self.nodes],
            "global_relationships": [self._serialize_object(asdict(rel)) for rel in self.relationships],
            "metadata": self.metadata
        }
    
    def _serialize_object(self, obj) -> Any:
        """递归序列化对象，处理枚举类型"""
        if isinstance(obj, dict):
            return {key: self._serialize_object(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_object(item) for item in obj]
        elif isinstance(obj, (CCMNodeType, CCMVisibility, CCMModifier)):
            return obj.value
        elif isinstance(obj, Path):
            return str(obj)
        elif hasattr(obj, '__dict__'):
            # 处理其他数据类对象
            return self._serialize_object(asdict(obj))
        else:
            return obj

# 保留原有的数据类以兼容现有代码
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
    """检测文件语言类型"""
    
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
        
        # Java系列
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
        
        # 其他编译型语言
        '.go': 'go',
        '.rs': 'rust',
        '.swift': 'swift',
        '.cs': 'csharp',
        
        # 脚本语言
        '.rb': 'ruby',
        '.php': 'php',
        '.pl': 'perl',
        '.py': 'python',
        
        # Shell
        '.sh': 'bash',
        '.bash': 'bash',
        '.zsh': 'bash',
        
        # 标记语言
        '.html': 'html',
        '.htm': 'html',
        '.css': 'css',
        '.scss': 'css',
        '.sass': 'css',
        
        # 配置文件
        '.json': 'json',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.toml': 'toml',
        '.xml': 'xml',
        '.sql': 'sql',
        
        # 其他
        '.dockerfile': 'dockerfile',
        '.md': 'markdown',
        '.makefile': 'makefile',
    }
    
    @classmethod
    def detect_language(cls, file_path: str) -> Optional[str]:
        """根据文件扩展名检测语言"""
        path = Path(file_path)
        
        # 特殊文件名处理
        if path.name.lower() in ['dockerfile', 'makefile']:
            return path.name.lower()
        
        suffix = path.suffix.lower()
        return cls.LANGUAGE_MAP.get(suffix)

class UniversalTreeSitterAnalyzer:
    """通用Tree-sitter分析器"""
    
    def __init__(self, language: str):
        self.language = language
        self.parser = None
        
        if TREE_SITTER_AVAILABLE and language in TREE_SITTER_MODULES:
            self.parser = self._create_parser(language)
    
    def _create_parser(self, language: str):
        """创建指定语言的解析器"""
        try:
            parser = Parser()
            module = TREE_SITTER_MODULES[language]
            
            if hasattr(Language, '__call__'):
                parser.language = Language(module.language())
            else:
                parser.set_language(Language(module.language()))
            
            return parser
        except Exception as e:
            print(f"创建{language}解析器失败: {e}")
            return None
    
    def analyze_file(self, file_path: str, content: str) -> Optional[Dict[str, Any]]:
        """分析文件"""
        if not self.parser:
            return None
        
        try:
            tree = self.parser.parse(bytes(content, "utf8"))
            return self._extract_info_from_tree(tree, file_path, content)
        except Exception as e:
            print(f"Tree-sitter分析失败 {file_path}: {e}")
            return None
    
    def _extract_info_from_tree(self, tree, file_path: str, content: str) -> Dict[str, Any]:
        """从AST树提取信息"""
        functions = []
        classes = []
        imports = []
        exports = []
        comments = self._extract_comments(content)
        
        # 递归遍历AST
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
        """递归遍历AST节点"""
        # 函数定义节点类型映射
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
        
        # 类定义节点类型映射
        class_types = {
            'class_definition',        # Python
            'class_declaration',       # JavaScript, Java
            'struct_item',            # Rust
            'interface_declaration',   # TypeScript, Java
            'type_declaration',       # Go
        }
        
        # 导入节点类型映射  
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
        
        # 递归处理子节点
        for child in node.children:
            self._traverse_node(child, context)
    
    def _extract_function_info(self, node, context) -> Optional[FunctionInfo]:
        """提取函数信息"""
        try:
            # 获取函数名
            name = self._extract_name_from_node(node)
            if not name:
                name = "anonymous"
            
            # 获取参数
            params = self._extract_parameters_from_node(node)
            
            # 获取函数调用
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
                class_name=None,  # 需要上下文信息
                module_name=Path(context['file_path']).stem,
                language=context['language'],
                docstring=None,
                comments=[],
                is_async=self._is_async_function(node)
            )
        except Exception as e:
            print(f"提取函数信息失败: {e}")
            return None
    
    def _extract_class_info(self, node, context) -> Optional[ClassInfo]:
        """提取类信息"""
        try:
            name = self._extract_name_from_node(node)
            if not name:
                return None
            
            # 获取方法
            methods = []
            self._extract_methods_from_class(node, methods)
            
            return ClassInfo(
                name=name,
                file_path=context['file_path'],
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                methods=methods,
                parent_classes=[],  # 需要进一步解析
                module_name=Path(context['file_path']).stem,
                language=context['language'],
                docstring=None,
                comments=[]
            )
        except Exception as e:
            print(f"提取类信息失败: {e}")
            return None
    
    def _extract_name_from_node(self, node) -> Optional[str]:
        """从节点提取名称"""
        # 尝试通过字段名获取
        name_node = node.child_by_field_name("name")
        if name_node:
            return self._get_node_text(name_node)
        
        # 尝试查找identifier子节点
        for child in node.children:
            if child.type == "identifier":
                return self._get_node_text(child)
        
        return None
    
    def _extract_parameters_from_node(self, node) -> List[str]:
        """从节点提取参数"""
        params = []
        
        # 查找参数列表
        params_node = node.child_by_field_name("parameters")
        if not params_node:
            # 尝试其他字段名
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
        """从节点提取函数调用"""
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
        """从类节点提取方法"""
        for child in class_node.children:
            if child.type in ["function_definition", "method_definition", "method_declaration"]:
                method_name = self._extract_name_from_node(child)
                if method_name:
                    methods.append(method_name)
    
    def _extract_comments(self, content: str) -> List[CommentInfo]:
        """提取注释（通用方法）"""
        comments = []
        lines = content.splitlines()
        
        # 根据语言选择注释模式
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
        """获取注释模式"""
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
        """检查是否是异步函数"""
        # 查找async关键字
        for child in node.children:
            if child.type == "async" or "async" in self._get_node_text(child).lower():
                return True
        return False
    
    def _get_node_text(self, node) -> str:
        """获取节点文本"""
        return node.text.decode('utf8')

class RegexFallbackAnalyzer:
    """正则表达式备选分析器"""
    
    def __init__(self, language: str):
        self.language = language
    
    def analyze_file(self, file_path: str, content: str) -> Optional[Dict[str, Any]]:
        """使用正则表达式分析"""
        
        patterns = self._get_language_patterns()
        if not patterns:
            return None
        
        functions = []
        classes = []
        imports = []
        comments = self._extract_comments_regex(content)
        
        # 提取函数
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
        
        # 提取类
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
        """获取语言特定的正则模式"""
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
        """使用正则提取注释"""
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
    """将传统分析结果转换为CCM格式的转换器"""
    
    def __init__(self):
        self.node_id_counter = 0
        self.id_map = {}  # 用于存储原始对象到ID的映射
    
    def _generate_id(self, prefix: str = "node") -> str:
        """生成唯一ID"""
        self.node_id_counter += 1
        return f"{prefix}_{self.node_id_counter:06d}"
    
    def _get_ccm_visibility(self, visibility: str) -> CCMVisibility:
        """转换可见性"""
        visibility_map = {
            "public": CCMVisibility.PUBLIC,
            "private": CCMVisibility.PRIVATE,
            "protected": CCMVisibility.PROTECTED,
            "internal": CCMVisibility.INTERNAL,
            "package": CCMVisibility.PACKAGE
        }
        return visibility_map.get(visibility.lower(), CCMVisibility.PUBLIC)
    
    def _get_ccm_modifiers(self, function_info: FunctionInfo) -> List[CCMModifier]:
        """转换修饰符"""
        modifiers = []
        if function_info.is_static:
            modifiers.append(CCMModifier.STATIC)
        if function_info.is_async:
            modifiers.append(CCMModifier.ASYNC)
        
        # 处理装饰器
        if function_info.decorators:
            for decorator in function_info.decorators:
                if 'abstract' in decorator.lower():
                    modifiers.append(CCMModifier.ABSTRACT)
                elif 'static' in decorator.lower():
                    modifiers.append(CCMModifier.STATIC)
        
        return modifiers
    
    def _get_ccm_class_modifiers(self, class_info: ClassInfo) -> List[CCMModifier]:
        """转换类修饰符"""
        modifiers = []
        if class_info.is_abstract:
            modifiers.append(CCMModifier.ABSTRACT)
        
        # 处理装饰器
        if class_info.decorators:
            for decorator in class_info.decorators:
                if 'abstract' in decorator.lower():
                    modifiers.append(CCMModifier.ABSTRACT)
                elif 'final' in decorator.lower():
                    modifiers.append(CCMModifier.FINAL)
        
        return modifiers
    
    def _parse_type_info(self, type_str: Optional[str], language: str) -> Optional[CCMTypeInfo]:
        """解析类型信息"""
        if not type_str:
            return None
        
        # 基本类型映射
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
        
        # 检查是否是数组类型
        is_array = False
        if any(marker in type_str for marker in ['[]', 'List[', 'Array<', 'Vec<', 'list[', 'array[']):
            is_array = True
        
        # 检查是否可空
        is_nullable = False
        if any(marker in type_str for marker in ['?', 'Optional[', 'Maybe<', 'Option<']):
            is_nullable = True
        
        # 提取基本类型名
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
        """转换参数信息"""
        ccm_parameters = []
        
        for param in parameters:
            # 解析参数名和默认值
            param_name = param
            default_value = None
            is_optional = False
            is_variadic = False
            
            if '=' in param:
                param_name, default_value = param.split('=', 1)
                param_name = param_name.strip()
                default_value = default_value.strip()
                is_optional = True
            
            # 检查可变参数
            if param_name.startswith('*'):
                is_variadic = True
                param_name = param_name.lstrip('*')
            
            # 获取类型信息
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
        """创建文档信息"""
        if not docstring and not comments:
            return None
        
        # 解析docstring
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
        
        # 从注释中提取额外信息
        comment_text = []
        for comment in comments:
            if comment.comment_type == 'docstring':
                continue  # 已经处理过docstring
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
        """将传统分析结果转换为CCM格式"""
        
        ccm_nodes = []
        node_lookup = {}  # 用于快速查找节点：{name: node_id}
        
        # ===== 第一阶段：创建所有节点 =====
        print("🔄 第一阶段：创建所有节点...")
        
        # 1. 创建模块节点
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
            
            # 注册到查找表
            node_lookup[module.name] = module_id
            node_lookup[f"module:{module.name}"] = module_id
        
        # 2. 创建类节点
        class_nodes = {}
        for class_info in classes:
            class_id = self._generate_id("class")
            class_full_name = f"{class_info.module_name}.{class_info.name}"
            
            # 查找父模块
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
            
            # 注册到查找表（多种可能的名称）
            node_lookup[class_info.name] = class_id
            node_lookup[f"class:{class_info.name}"] = class_id
            node_lookup[class_full_name] = class_id
            node_lookup[f"class:{class_full_name}"] = class_id
        
        # 3. 创建函数节点
        function_nodes = {}
        for function_info in functions:
            function_id = self._generate_id("function")
            
            # 构建函数的完整名称
            if function_info.class_name:
                function_full_name = f"{function_info.module_name}.{function_info.class_name}.{function_info.name}"
                function_class_name = f"{function_info.class_name}.{function_info.name}"
            else:
                function_full_name = f"{function_info.module_name}.{function_info.name}"
                function_class_name = None
            
            # 确定节点类型
            node_type = CCMNodeType.METHOD if function_info.class_name else CCMNodeType.FUNCTION
            if function_info.name in ['__init__', 'constructor', 'init']:
                node_type = CCMNodeType.CONSTRUCTOR
            
            # 查找父节点
            parent_id = None
            if function_info.class_name:
                class_key = f"{function_info.module_name}.{function_info.class_name}"
                if class_key in class_nodes:
                    parent_id = class_nodes[class_key].id
                    class_nodes[class_key].children_ids.append(function_id)
            elif function_info.module_name in module_nodes:
                parent_id = module_nodes[function_info.module_name].id
                module_nodes[function_info.module_name].children_ids.append(function_id)
            
            # 转换参数
            ccm_parameters = self._convert_parameters(
                function_info.parameters, 
                function_info.type_annotations or {}, 
                function_info.language
            )
            
            # 转换返回类型
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
            
            # 注册到查找表（多种可能的名称）
            node_lookup[function_info.name] = function_id
            node_lookup[f"function:{function_info.name}"] = function_id
            node_lookup[function_full_name] = function_id
            node_lookup[f"function:{function_full_name}"] = function_id
            
            if function_class_name:
                node_lookup[function_class_name] = function_id
                node_lookup[f"function:{function_class_name}"] = function_id
            
            # 模块级别的函数名
            module_function_name = f"{function_info.module_name}.{function_info.name}"
            node_lookup[module_function_name] = function_id
            node_lookup[f"function:{module_function_name}"] = function_id
        
        # 4. 创建注释节点
        for comment in comments:
            comment_id = self._generate_id("comment")
            
            ccm_node = CCMNode(
                id=comment_id,
                name=f"comment_{comment.line_number}",
                node_type=CCMNodeType.COMMENT,
                location=CCMLocation(
                    file_path="",  # 注释可能没有文件路径
                    start_line=comment.line_number,
                    end_line=comment.line_number
                ),
                language=comment.language,
                raw_content=comment.content,
                annotations={"comment_type": comment.comment_type}
            )
            ccm_nodes.append(ccm_node)
        
        print(f"✅ 创建了 {len(ccm_nodes)} 个节点")
        print(f"📋 节点查找表包含 {len(node_lookup)} 个条目")
        
        # ===== 第二阶段：处理所有关系 =====
        print("🔗 第二阶段：处理节点关系...")
        
        all_relationships = []
        resolved_count = 0
        unresolved_count = 0
        
        # 1. 处理模块导入关系
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
        
        # 2. 处理类继承关系
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
        
        # 3. 处理函数调用关系
        for function_info in functions:
            if function_info.class_name:
                function_full_name = f"{function_info.module_name}.{function_info.class_name}.{function_info.name}"
            else:
                function_full_name = f"{function_info.module_name}.{function_info.name}"
            
            function_node = function_nodes[function_full_name]
            
            for call in function_info.calls:
                # 过滤掉明显的内置函数或方法调用
                if self._is_likely_builtin_call(call):
                    continue
                    
                target_id = self._find_target_id(call, node_lookup, 
                                               context={
                                                   'module': function_info.module_name,
                                                   'class': function_info.class_name
                                               })
                
                # 只有找到目标ID才创建关系
                if target_id:
                    relationship = CCMRelationship(
                        type="calls",
                        target_id=target_id,
                        target_name=call
                    )
                    
                    function_node.relationships.append(relationship)
                    all_relationships.append(relationship)
                    resolved_count += 1
        
        print(f"✅ 处理了 {len(all_relationships)} 个关系")
        print(f"🎯 解析成功: {resolved_count} 个")
        print(f"❌ 解析失败: {unresolved_count} 个")
        print(f"📊 解析成功率: {(resolved_count / len(all_relationships) * 100):.1f}%" if all_relationships else "N/A")
        
        # 创建项目信息
        project = CCMProject(
            name=project_info.get('name', 'Unknown Project'),
            root_path=project_info.get('root_path', ''),
            project_type=project_info.get('project_type', 'unknown'),
            languages=project_info.get('languages', [])
        )
        
        # 创建元数据
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
        """在节点查找表中查找目标ID - 只查找代码中实际存在的节点"""
        if not target_name:
            return ""
        
        context = context or {}
        
        # 构建搜索候选列表，按优先级排序
        candidates = []
        
        # 1. 精确匹配
        candidates.append(target_name)
        candidates.append(f"function:{target_name}")
        candidates.append(f"class:{target_name}")
        candidates.append(f"module:{target_name}")
        
        # 2. 当前上下文中的匹配
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
        
        # 按优先级查找 - 只在已知节点中查找
        for candidate in candidates:
            if candidate in node_lookup:
                return node_lookup[candidate]
        
        # 如果没找到，说明是外部依赖，直接返回空字符串
        return ""

    def _extract_module_name_from_import(self, import_stmt: str) -> Optional[str]:
        """从导入语句中提取模块名"""
        # 简单的导入语句解析
        import_stmt = import_stmt.strip()
        
        # 处理 "import module" 格式
        if import_stmt.startswith('import '):
            module_name = import_stmt[7:].split('.')[0].split(' as ')[0].strip()
            return module_name
        
        # 处理 "from module import ..." 格式
        elif import_stmt.startswith('from '):
            parts = import_stmt.split(' import ')
            if len(parts) > 0:
                module_name = parts[0][5:].strip()
                return module_name
        
        return None
    
    def _count_relationship_types(self, relationships: List[CCMRelationship]) -> Dict[str, int]:
        """统计关系类型数量"""
        counts = defaultdict(int)
        for rel in relationships:
            counts[rel.type] += 1
        return dict(counts)
    
    def _count_node_types(self, nodes: List[CCMNode]) -> Dict[str, int]:
        """统计节点类型数量"""
        counts = defaultdict(int)
        for node in nodes:
            counts[node.node_type.value] += 1
        return dict(counts)
    
    def _count_languages(self, nodes: List[CCMNode]) -> Dict[str, int]:
        """统计语言分布"""
        counts = defaultdict(int)
        for node in nodes:
            counts[node.language] += 1
        return dict(counts)

    def _is_likely_builtin_call(self, call: str) -> bool:
        """检查是否可能是内置函数或方法调用"""
        
        # 常见的内置函数
        builtin_functions = {
            # Python内置函数
            'print', 'len', 'range', 'str', 'int', 'float', 'bool', 'list', 'dict', 'set', 'tuple',
            'abs', 'all', 'any', 'bin', 'chr', 'dir', 'divmod', 'enumerate', 'eval', 'exec',
            'filter', 'format', 'getattr', 'hasattr', 'hash', 'hex', 'id', 'input', 'isinstance',
            'issubclass', 'iter', 'map', 'max', 'min', 'next', 'oct', 'open', 'ord', 'pow',
            'repr', 'reversed', 'round', 'setattr', 'sorted', 'sum', 'type', 'vars', 'zip',
            
            # JavaScript内置函数
            'console.log', 'parseInt', 'parseFloat', 'isNaN', 'isFinite', 'encodeURI', 'decodeURI',
            'setTimeout', 'setInterval', 'clearTimeout', 'clearInterval',
            
            # 常见方法调用模式
            'append', 'extend', 'insert', 'remove', 'pop', 'clear', 'index', 'count',
            'sort', 'reverse', 'copy', 'get', 'keys', 'values', 'items', 'update',
            'add', 'discard', 'union', 'intersection', 'difference',
            'split', 'join', 'strip', 'replace', 'find', 'startswith', 'endswith',
            'upper', 'lower', 'capitalize', 'title', 'format'
        }
        
        # 检查是否是内置函数
        if call in builtin_functions:
            return True
        
        # 检查是否包含点号（可能是方法调用）
        if '.' in call:
            # 提取方法名
            method_name = call.split('.')[-1]
            # 检查是否是常见的方法名
            if method_name in builtin_functions:
                return True
            
            # 检查是否是常见的对象方法调用模式
            common_patterns = [
                'append', 'extend', 'insert', 'remove', 'pop', 'clear',
                'get', 'set', 'add', 'delete', 'update', 'keys', 'values',
                'push', 'shift', 'unshift', 'slice', 'splice', 'concat',
                'toString', 'valueOf', 'hasOwnProperty'
            ]
            if method_name in common_patterns:
                return True
        
        # 检查是否包含特殊字符（可能是复杂表达式）
        if any(char in call for char in ['(', ')', '[', ']', '{', '}', '+', '-', '*', '/', '=']):
            return True
        
        # 检查是否是单个字符或很短的名称（可能是变量）
        if len(call) <= 2:
            return True
        
        return False

class ComprehensiveMultiLanguageAnalyzer:
    """综合多语言分析器"""
    
    def __init__(self):
        self.supported_languages = {
            'python', 'javascript', 'typescript', 'java', 'c', 'cpp',
            'go', 'rust', 'ruby', 'php', 'csharp', 'kotlin', 'swift',
            'scala', 'bash', 'html', 'css', 'json', 'yaml', 'sql'
        }
        
        # 忽略的文件和目录
        self.ignore_patterns = {
            # 版本控制
            '.git', '.svn', '.hg',
            # 依赖目录
            'node_modules', 'bower_components',
            # Python
            '__pycache__', '.pytest_cache', 'venv', 'env', '.venv',
            'site-packages', '.tox', '.coverage', 'htmlcov',
            # 构建输出
            'dist', 'build', '.next', 'out', 'target', 'bin', 'obj',
            # IDE和编辑器
            '.vscode', '.idea', '.vs', '.eclipse',
            # 临时文件
            'tmp', 'temp', '.tmp',
            # 日志和缓存
            'logs', 'log', '.cache', 'coverage', '.nyc_output',
            # 移动端
            'ios', 'android', '.expo',
            # 其他
            '.terraform', '.serverless'
        }
        
        # 忽略的文件模式（更全面的过滤）
        self.ignore_files = {
            # 压缩和编译文件
            '.min.js', '.min.css', '.bundle.js', '.bundle.css',
            # 测试文件
            'test', 'spec', '.test.', '.spec.',
            # 配置文件
            '.env', '.env.local', '.env.development', '.env.production',
            '.gitignore', '.gitattributes', '.editorconfig',
            # 包管理文件
            'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
            'pipfile.lock', 'poetry.lock', 'requirements.txt',
            'composer.lock', 'gemfile.lock',
            # 文档文件
            'readme', 'license', 'changelog', 'contributing',
            # 配置文件
            '.eslintrc', '.prettierrc', '.babelrc', 'tsconfig.json',
            'webpack.config', 'rollup.config', 'vite.config',
            'jest.config', 'cypress.config', 'playwright.config',
            # 部署文件
            'dockerfile', '.dockerignore', 'docker-compose',
            'k8s', 'kubernetes', '.github', '.gitlab-ci',
            # 数据文件
            '.db', '.sqlite', '.sql', '.csv', '.json', '.xml',
            # 媒体文件
            '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico',
            '.mp4', '.mp3', '.wav', '.pdf',
            # 字体文件
            '.woff', '.woff2', '.ttf', '.eot',
            # 其他
            '.map', '.d.ts', '.backup', '.swp', '.tmp'
        }
        
        # 项目类型特定的忽略规则
        self.project_specific_ignores = {}
        
        print(f"支持的语言: {', '.join(sorted(self.supported_languages))}")
    
    def _detect_project_type(self, repo_path: Path) -> str:
        """检测项目类型以应用特定的忽略规则"""
        
        # 检查标志性文件
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
        """根据项目类型返回特定的忽略模式"""
        
        ignores = {
            "nodejs": {
                # 文件
                'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
                '.npmrc', '.yarnrc', 'babel.config.js', 'webpack.config.js',
                'next.config.js', 'nuxt.config.js', 'vue.config.js',
                # 目录
                'node_modules', '.next', 'out', 'dist', 'build'
            },
            "python": {
                # 文件
                'requirements.txt', 'setup.py', 'setup.cfg', 'pyproject.toml',
                'Pipfile', 'Pipfile.lock', 'poetry.lock', '.flake8',
                'pytest.ini', 'tox.ini', '.coveragerc', 'mypy.ini',
                # 环境文件（重要！）
                '.env', '.env.local', '.env.development', '.env.production',
                '.env.staging', '.env.test',
                # 目录
                '__pycache__', 'venv', 'env', '.venv', '.env',
                'site-packages', '.tox', 'htmlcov', '.coverage'
            },
            "java": {
                # 文件
                'pom.xml', 'build.gradle', 'gradle.properties',
                'application.properties', 'application.yml',
                # 目录
                'target', 'build', '.gradle', 'bin', 'out'
            },
            "go": {
                # 文件
                'go.mod', 'go.sum',
                # 目录
                'vendor'
            },
            "rust": {
                # 文件
                'Cargo.toml', 'Cargo.lock',
                # 目录
                'target'
            },
            "php": {
                # 文件
                'composer.json', 'composer.lock', '.env',
                # 目录
                'vendor'
            },
            "ruby": {
                # 文件
                'Gemfile', 'Gemfile.lock', '.env',
                # 目录
                'vendor', 'bundle'
            }
        }
        
        return ignores.get(project_type, set())
    
    def analyze_repository(self, repo_path: str, output_path: str = "/output/analysis.json"):
        """分析整个代码仓库"""
        repo_path = Path(repo_path)
        
        # 检测项目类型
        project_type = self._detect_project_type(repo_path)
        project_ignores = self._get_project_specific_ignores(project_type)
        
        print(f"🔍 开始分析代码仓库: {repo_path}")
        print(f"📋 检测到项目类型: {project_type}")
        print(f"🚫 应用特定忽略规则: {len(project_ignores)} 项")
        
        # 临时添加项目特定的忽略规则
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
                    
                    print(f"📄 分析文件: {file_path} ({language})")
                    result = self.analyze_file(file_path, language)
                    
                    if result:
                        all_functions.extend(result['functions'])
                        all_classes.extend(result['classes'])
                        all_modules.append(result['module'])
                        
                        # 收集注释
                        module_comments = result['module'].comments if hasattr(result['module'], 'comments') and result['module'].comments else []
                        all_comments.extend(module_comments)
                        
                        language_stats[language] += 1
                        file_count += 1
                        
                except Exception as e:
                    print(f"❌ 分析文件失败 {file_path}: {e}")
                    continue
        
        finally:
            # 恢复原始忽略规则
            self.ignore_files = original_ignore_files
        
        # 构建调用关系
        print("🔗 构建函数调用关系...")
        self._build_call_relationships(all_functions)
        
        # 生成统计信息
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
        
        # 创建 CCM 转换器并生成 CCM 格式结果
        print("🔄 转换为 CCM 格式...")
        ccm_converter = CCMConverter()
        
        # 准备项目信息
        project_info = {
            'name': repo_path.name,
            'root_path': str(repo_path),
            'project_type': project_type,
            'languages': list(language_stats.keys()),
            'stats': stats,
            'timestamp': None  # 可以添加时间戳
        }
        
        # 转换为 CCM 格式
        ccm_result = ccm_converter.convert_to_ccm(
            functions=all_functions,
            classes=all_classes,
            modules=all_modules,
            comments=all_comments,
            project_info=project_info
        )
        
        # 生成两种格式的输出
        # 1. 传统格式（向后兼容）
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
        
        # 2. CCM 格式（新标准）
        ccm_dict = ccm_result.to_dict()
        
        # 保存结果
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 保存 CCM 格式（主要输出）
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(ccm_dict, f, indent=2, ensure_ascii=False)
        
        # 保存传统格式（兼容性）
        legacy_output_path = output_path.replace('.json', '_legacy.json')
        with open(legacy_output_path, 'w', encoding='utf-8') as f:
            json.dump(legacy_result, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ 分析完成!")
        print(f"📊 统计信息:")
        print(f"   - 项目类型: {project_type}")
        print(f"   - 总文件数: {stats['total_files']}")
        print(f"   - 总函数数: {stats['total_functions']}")
        print(f"   - 总类数: {stats['total_classes']}")
        print(f"   - 总注释数: {stats['total_comments']}")
        print(f"   - 支持语言: {list(stats['languages'].keys())}")
        print(f"📁 CCM 格式结果: {output_path}")
        print(f"📁 传统格式结果: {legacy_output_path}")
        print(f"🎯 CCM 节点总数: {ccm_dict['metadata']['total_nodes']}")
        print(f"🔗 关系总数: {ccm_dict['metadata']['total_relationships']}")
        print(f"📈 节点类型分布: {ccm_dict['metadata']['node_type_counts']}")
        
        return ccm_result
    
    def analyze_file(self, file_path: str, language: str) -> Optional[Dict[str, Any]]:
        """分析单个文件"""
        if not os.path.exists(file_path):
            return None
        
        if self._should_ignore_file(Path(file_path)):
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if len(content.strip()) < 10:
                return None
            
            # 优先使用Tree-sitter分析器
            if TREE_SITTER_AVAILABLE and language in TREE_SITTER_MODULES:
                analyzer = UniversalTreeSitterAnalyzer(language)
                result = analyzer.analyze_file(file_path, content)
                if result:
                    return result
            
            # 备选：使用正则表达式分析器
            fallback_analyzer = RegexFallbackAnalyzer(language)
            return fallback_analyzer.analyze_file(file_path, content)
            
        except Exception as e:
            print(f"读取文件失败 {file_path}: {e}")
            return None
    
    def _find_code_files(self, repo_path: Path) -> List[Path]:
        """查找所有代码文件"""
        code_files = []
        
        for root, dirs, files in os.walk(repo_path):
            # 过滤忽略的目录
            dirs[:] = [d for d in dirs if d not in self.ignore_patterns and not d.startswith('.')]
            
            for file in files:
                file_path = Path(root) / file
                
                # 先检查是否应该忽略
                if self._should_ignore_file(file_path):
                    continue
                
                # 检查是否是支持的代码文件
                language = LanguageDetector.detect_language(str(file_path))
                if language and language in self.supported_languages:
                    code_files.append(file_path)
        
        return code_files
    
    def _should_ignore_file(self, file_path: Path) -> bool:
        """检查文件是否应该被忽略"""
        file_name = file_path.name.lower()
        file_stem = file_path.stem.lower()
        
        # 检查完整文件名
        if file_name in {'.env', '.env.local', '.env.development', '.env.production', 
                        '.gitignore', '.dockerignore', 'dockerfile', 'readme.md', 
                        'license', 'changelog.md', 'package.json', 'package-lock.json',
                        'yarn.lock', 'requirements.txt', 'pipfile.lock', 'poetry.lock',
                        'composer.json', 'composer.lock', 'gemfile', 'gemfile.lock'}:
            return True
        
        # 检查文件名模式
        for pattern in self.ignore_files:
            if pattern in file_name or pattern in file_stem:
                return True
        
        # 检查特殊的配置文件模式
        config_patterns = [
            'config', 'conf', '.rc', '.config', 'settings',
            'webpack', 'rollup', 'vite', 'babel', 'eslint', 'prettier',
            'jest', 'cypress', 'playwright', 'tsconfig', 'jsconfig'
        ]
        
        for pattern in config_patterns:
            if pattern in file_name:
                return True
        
        # 检查是否是隐藏文件（以.开头，但排除代码文件）
        if file_name.startswith('.') and file_path.suffix not in {'.py', '.js', '.ts', '.jsx', '.tsx'}:
            return True
        
        # 检查文件大小（排除过大的文件，可能是数据文件）
        try:
            if file_path.stat().st_size > 1024 * 1024:  # 1MB以上
                return True
        except:
            pass
        
        return False
    
    def _build_call_relationships(self, functions: List[FunctionInfo]):
        """构建函数调用关系"""
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
        """清理函数调用名称"""
        if '.' in call:
            return call.split('.')[-1]
        return call
    
    def _convert_paths_to_strings(self, obj):
        """递归转换所有Path对象为字符串"""
        if isinstance(obj, dict):
            return {key: self._convert_paths_to_strings(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_paths_to_strings(item) for item in obj]
        elif isinstance(obj, Path):
            return str(obj)
        else:
            return obj

    def _count_by_language(self, items: List) -> Dict[str, int]:
        """按语言统计数量"""
        counts = defaultdict(int)
        for item in items:
            counts[item.language] += 1
        return dict(counts)
    
    def _count_comments_by_language(self, comments: List[CommentInfo]) -> Dict[str, int]:
        """按语言统计注释数量"""
        counts = defaultdict(int)
        for comment in comments:
            counts[comment.language] += 1
        return dict(counts)

def main():
    """主函数 - Docker容器入口点"""
    parser = argparse.ArgumentParser(description='综合多语言代码分析器')
    parser.add_argument('--input', required=True, help='输入代码目录')
    parser.add_argument('--output', default='/output/analysis.json', help='输出文件路径')
    
    args = parser.parse_args()
    
    # 验证输入目录
    if not os.path.exists(args.input):
        print(f"❌ 输入目录不存在: {args.input}")
        return 1
    
    try:
        # 创建分析器并运行
        analyzer = ComprehensiveMultiLanguageAnalyzer()
        result = analyzer.analyze_repository(args.input, args.output)
        
        print(f"🎉 分析完成! 结果保存在: {args.output}")
        return 0
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())