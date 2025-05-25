#!/usr/bin/env python3
"""
Python接口调用Docker代码分析器
支持本地和远程Docker镜像
"""

import os
import json
import subprocess
import tempfile
import shutil
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DockerCodeAnalyzer:
    """Docker代码分析器调用接口"""
    
    def __init__(self, 
                 docker_image: str = "enhanced-code-analyzer:latest",
                 timeout: int = 600,
                 memory_limit: str = "2g",
                 cpu_limit: str = "1.0"):
        """
        初始化分析器
        
        Args:
            docker_image: Docker镜像名
            timeout: 超时时间(秒)
            memory_limit: 内存限制
            cpu_limit: CPU限制
        """
        self.docker_image = docker_image
        self.timeout = timeout
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        
        # 验证Docker和镜像
        self._verify_docker()
        self._verify_image()
    
    def _verify_docker(self):
        """验证Docker是否可用"""
        try:
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                raise Exception("Docker不可用")
            logger.info(f"✅ Docker可用: {result.stdout.strip()}")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            raise Exception("Docker未安装或不在PATH中")
    
    def _verify_image(self):
        """验证Docker镜像是否存在"""
        try:
            result = subprocess.run(['docker', 'images', '-q', self.docker_image],
                                  capture_output=True, text=True, timeout=10)
            if not result.stdout.strip():
                logger.warning(f"⚠️  本地镜像 {self.docker_image} 不存在，尝试拉取...")
                self._pull_image()
            else:
                logger.info(f"✅ Docker镜像 {self.docker_image} 已找到")
        except Exception as e:
            raise Exception(f"验证Docker镜像失败: {e}")
    
    def _pull_image(self):
        """拉取Docker镜像"""
        try:
            logger.info(f"🔄 正在拉取镜像 {self.docker_image}...")
            result = subprocess.run(['docker', 'pull', self.docker_image],
                                  capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                logger.info(f"✅ 镜像拉取成功")
            else:
                raise Exception(f"拉取失败: {result.stderr}")
        except subprocess.TimeoutExpired:
            raise Exception("镜像拉取超时")
    
    def analyze_codebase(self, 
                        codebase_path: Union[str, Path],
                        output_path: Optional[Union[str, Path]] = None,
                        exclude_patterns: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        分析代码库
        
        Args:
            codebase_path: 要分析的代码路径
            output_path: 输出文件路径（可选）
            exclude_patterns: 排除的文件模式（可选）
            
        Returns:
            分析结果字典
        """
        codebase_path = Path(codebase_path).resolve()
        
        if not codebase_path.exists():
            raise FileNotFoundError(f"代码路径不存在: {codebase_path}")
        
        task_id = str(uuid.uuid4())[:8]
        logger.info(f"🚀 开始分析代码库: {codebase_path}")
        logger.info(f"📋 任务ID: {task_id}")
        
        with tempfile.TemporaryDirectory(prefix=f"analyzer-{task_id}-") as temp_dir:
            temp_output = Path(temp_dir) / "output"
            temp_output.mkdir()
            
            # 运行Docker分析
            start_time = time.time()
            success = self._run_docker_container(codebase_path, temp_output, task_id)
            duration = time.time() - start_time
            
            if not success:
                raise Exception("Docker分析失败")
            
            # 读取结果
            result_file = temp_output / "analysis.json"
            if not result_file.exists():
                raise Exception("分析结果文件未生成")
            
            with open(result_file, 'r', encoding='utf-8') as f:
                result = json.load(f)
            
            # 添加分析元数据
            result['analysis_info'] = {
                'task_id': task_id,
                'duration_seconds': round(duration, 2),
                'analyzed_path': str(codebase_path),
                'docker_image': self.docker_image,
                'timestamp': time.time()
            }
            
            # 保存到指定路径
            if output_path:
                output_path = Path(output_path).resolve()
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                logger.info(f"💾 结果已保存到: {output_path}")
            
            # 打印统计信息
            self._print_summary(result, duration)
            
            return result
    
    def _run_docker_container(self, input_path: Path, output_path: Path, task_id: str) -> bool:
        """运行Docker容器"""
        
        container_name = f"analyzer-{task_id}"
        
        docker_cmd = [
            'docker', 'run',
            '--rm',                              # 自动删除容器
            '--name', container_name,            # 容器名称
            '-v', f'{input_path}:/input:ro',     # 只读挂载输入
            '-v', f'{output_path}:/output:rw',   # 可写挂载输出
            '--memory', self.memory_limit,       # 内存限制
            '--cpus', self.cpu_limit,           # CPU限制
            '--network', 'none',                 # 断网运行
            '--user', 'root',                   # 需要写入权限
            self.docker_image,                   # 镜像名
            '--input', '/input',                # 分析器参数
            '--output', '/output/analysis.json' # 输出文件
        ]
        
        try:
            logger.info(f"🐳 启动Docker容器: {container_name}")
            logger.debug(f"Docker命令: {' '.join(docker_cmd)}")
            
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode == 0:
                logger.info("✅ Docker分析完成")
                if result.stdout.strip():
                    logger.info("📄 分析器输出:")
                    for line in result.stdout.strip().split('\n'):
                        logger.info(f"   {line}")
                return True
            else:
                logger.error(f"❌ Docker分析失败 (退出码: {result.returncode})")
                if result.stderr:
                    logger.error(f"错误信息: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"❌ Docker分析超时 ({self.timeout}秒)")
            # 尝试停止容器
            try:
                subprocess.run(['docker', 'stop', container_name], 
                             capture_output=True, timeout=10)
                logger.info(f"🛑 已停止超时容器: {container_name}")
            except:
                pass
            return False
            
        except Exception as e:
            logger.error(f"❌ 运行Docker容器失败: {e}")
            return False
    
    def _print_summary(self, result: Dict[str, Any], duration: float):
        """打印分析摘要"""
        stats = result.get('stats', {})
        
        logger.info(f"\n📊 分析完成摘要:")
        logger.info(f"   ⏱️  耗时: {duration:.2f}秒")
        logger.info(f"   📁 文件数: {stats.get('total_files', 0)}")
        logger.info(f"   🔧 函数数: {stats.get('total_functions', 0)}")
        logger.info(f"   📦 类数: {stats.get('total_classes', 0)}")
        logger.info(f"   💬 注释数: {stats.get('total_comments', 0)}")
        
        languages = stats.get('languages', {})
        if languages:
            logger.info(f"   🌍 语言分布:")
            for lang, count in languages.items():
                logger.info(f"      - {lang}: {count} 个文件")
    
    def analyze_file(self, file_path: Union[str, Path], output_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        """
        分析单个文件
        
        Args:
            file_path: 文件路径
            output_path: 输出路径（可选）
            
        Returns:
            分析结果
        """
        file_path = Path(file_path).resolve()
        
        if not file_path.is_file():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 创建临时目录，包含这个文件
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_input = Path(temp_dir) / "input"
            temp_input.mkdir()
            
            # 复制文件到临时目录
            shutil.copy2(file_path, temp_input / file_path.name)
            
            # 分析临时目录
            return self.analyze_codebase(temp_input, output_path)
    
    def get_functions_with_comments(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取包含注释的函数"""
        functions_with_comments = []
        for func in result.get('functions', []):
            if func.get('docstring') or (func.get('comments') and len(func['comments']) > 0):
                functions_with_comments.append(func)
        return functions_with_comments
    
    def get_complex_functions(self, result: Dict[str, Any], min_params: int = 3) -> List[Dict[str, Any]]:
        """获取复杂函数（参数较多）"""
        complex_functions = []
        for func in result.get('functions', []):
            if len(func.get('parameters', [])) >= min_params:
                complex_functions.append(func)
        return complex_functions
    
    def generate_summary_report(self, result: Dict[str, Any], output_path: Optional[Union[str, Path]] = None) -> str:
        """生成摘要报告"""
        stats = result.get('stats', {})
        
        report = f"""
# 代码分析报告

## 基本统计
- **总文件数**: {stats.get('total_files', 0)}
- **总函数数**: {stats.get('total_functions', 0)}
- **总类数**: {stats.get('total_classes', 0)}
- **总注释数**: {stats.get('total_comments', 0)}
- **分析时间**: {result.get('analysis_info', {}).get('duration_seconds', 0)}秒

## 语言分布
"""
        
        languages = stats.get('languages', {})
        for lang, count in languages.items():
            report += f"- **{lang}**: {count} 个文件\n"
        
        # 添加函数统计
        functions_with_docs = self.get_functions_with_comments(result)
        complex_functions = self.get_complex_functions(result)
        
        report += f"""
## 代码质量
- **有文档的函数**: {len(functions_with_docs)} 个
- **复杂函数(3+参数)**: {len(complex_functions)} 个
- **文档覆盖率**: {len(functions_with_docs)/max(stats.get('total_functions', 1), 1)*100:.1f}%

## 示例函数
"""
        
        # 显示前几个有文档的函数
        for i, func in enumerate(functions_with_docs[:5], 1):
            report += f"""
### {i}. {func['name']} ({func['language']})
- **文件**: {func['file_path']}
- **参数**: {', '.join(func.get('parameters', []))}
- **文档**: {func.get('docstring', 'N/A')[:100]}...
"""
        
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"📄 报告已保存到: {output_path}")
        
        return report

# 便捷函数
def analyze_code(codebase_path: Union[str, Path], 
                output_path: Optional[Union[str, Path]] = None,
                docker_image: str = "enhanced-code-analyzer:latest") -> Dict[str, Any]:
    """
    一键代码分析
    
    Args:
        codebase_path: 代码路径
        output_path: 输出路径（可选）
        docker_image: Docker镜像名
        
    Returns:
        分析结果
    """
    analyzer = DockerCodeAnalyzer(docker_image)
    return analyzer.analyze_codebase(codebase_path, output_path)

def analyze_file(file_path: Union[str, Path],
                output_path: Optional[Union[str, Path]] = None,
                docker_image: str = "enhanced-code-analyzer:latest") -> Dict[str, Any]:
    """
    一键文件分析
    
    Args:
        file_path: 文件路径
        output_path: 输出路径（可选）
        docker_image: Docker镜像名
        
    Returns:
        分析结果
    """
    analyzer = DockerCodeAnalyzer(docker_image)
    return analyzer.analyze_file(file_path, output_path)

# 使用示例和测试
def main():
    """示例用法"""
    import sys
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  python docker_analyzer.py <代码路径> [输出路径]")
        print("\n示例:")
        print("  python docker_analyzer.py ./my-project")
        print("  python docker_analyzer.py ./src ./analysis.json")
        print("  python docker_analyzer.py single_file.py")
        return
    
    code_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        # 检查是文件还是目录
        path = Path(code_path)
        if path.is_file():
            print(f"📄 分析单个文件: {code_path}")
            result = analyze_file(code_path, output_path)
        else:
            print(f"📁 分析代码库: {code_path}")
            result = analyze_code(code_path, output_path)
        
        # 创建分析器实例以使用额外功能
        analyzer = DockerCodeAnalyzer()
        
        # 显示有文档的函数
        documented_functions = analyzer.get_functions_with_comments(result)
        if documented_functions:
            print(f"\n📚 找到 {len(documented_functions)} 个有文档的函数:")
            for func in documented_functions[:3]:  # 显示前3个
                print(f"   - {func['name']}: {func.get('docstring', 'No docstring')[:50]}...")
        
        # 显示复杂函数
        complex_functions = analyzer.get_complex_functions(result)
        if complex_functions:
            print(f"\n🔧 找到 {len(complex_functions)} 个复杂函数:")
            for func in complex_functions[:3]:  # 显示前3个
                params = ', '.join(func.get('parameters', []))
                print(f"   - {func['name']}({params})")
        
        # 生成报告
        if output_path:
            report_path = str(output_path).replace('.json', '_report.md')
            analyzer.generate_summary_report(result, report_path)
        
        print(f"\n✅ 分析完成!")
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        return 1

if __name__ == "__main__":
    main()