#!/usr/bin/env python3
"""
Python interface for calling Docker code analyzer
Supports local and remote Docker images
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DockerCodeAnalyzer:
    """Docker code analyzer calling interface"""
    
    def __init__(self, 
                 docker_image: str = "enhanced-code-analyzer:latest",
                 timeout: int = 600,
                 memory_limit: str = "2g",
                 cpu_limit: str = "1.0"):
        """
        Initialize analyzer
        
        Args:
            docker_image: Docker image name
            timeout: Timeout in seconds
            memory_limit: Memory limit
            cpu_limit: CPU limit
        """
        self.docker_image = docker_image
        self.timeout = timeout
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        
        # Verify Docker and image
        self._verify_docker()
        self._verify_image()
    
    def _verify_docker(self):
        """Verify Docker availability"""
        try:
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                raise Exception("Docker not available")
            logger.info(f"✅ Docker available: {result.stdout.strip()}")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            raise Exception("Docker not installed or not in PATH")
    
    def _verify_image(self):
        """Verify Docker image exists"""
        try:
            result = subprocess.run(['docker', 'images', '-q', self.docker_image],
                                  capture_output=True, text=True, timeout=10)
            if not result.stdout.strip():
                logger.warning(f"⚠️  Local image {self.docker_image} not found, attempting to pull...")
                self._pull_image()
            else:
                logger.info(f"✅ Docker image {self.docker_image} found")
        except Exception as e:
            raise Exception(f"Failed to verify Docker image: {e}")
    
    def _pull_image(self):
        """Pull Docker image"""
        try:
            logger.info(f"🔄 Pulling image {self.docker_image}...")
            result = subprocess.run(['docker', 'pull', self.docker_image],
                                  capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                logger.info(f"✅ Image pull successful")
            else:
                raise Exception(f"Pull failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            raise Exception("Image pull timeout")
    
    def analyze_codebase(self, 
                        codebase_path: Union[str, Path],
                        output_path: Optional[Union[str, Path]] = None,
                        exclude_patterns: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Analyze codebase
        
        Args:
            codebase_path: Path to code to analyze
            output_path: Output file path (optional)
            exclude_patterns: File patterns to exclude (optional)
            
        Returns:
            Analysis result dictionary
        """
        codebase_path = Path(codebase_path).resolve()
        
        if not codebase_path.exists():
            raise FileNotFoundError(f"Code path does not exist: {codebase_path}")
        
        task_id = str(uuid.uuid4())[:8]
        logger.info(f"🚀 Starting codebase analysis: {codebase_path}")
        logger.info(f"📋 Task ID: {task_id}")
        
        with tempfile.TemporaryDirectory(prefix=f"analyzer-{task_id}-") as temp_dir:
            temp_output = Path(temp_dir) / "output"
            temp_output.mkdir()
            
            # Run Docker analysis
            start_time = time.time()
            success = self._run_docker_container(codebase_path, temp_output, task_id)
            duration = time.time() - start_time
            
            if not success:
                raise Exception("Docker analysis failed")
            
            # Read results
            result_file = temp_output / "analysis.json"
            if not result_file.exists():
                raise Exception("Analysis result file not generated")
            
            with open(result_file, 'r', encoding='utf-8') as f:
                result = json.load(f)
            
            # Add analysis metadata
            result['analysis_info'] = {
                'task_id': task_id,
                'duration_seconds': round(duration, 2),
                'analyzed_path': str(codebase_path),
                'docker_image': self.docker_image,
                'timestamp': time.time()
            }
            
            # Save to specified path
            if output_path:
                output_path = Path(output_path).resolve()
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                logger.info(f"💾 Results saved to: {output_path}")
            
            # Print statistics
            self._print_summary(result, duration)
            
            return result
    
    def _run_docker_container(self, input_path: Path, output_path: Path, task_id: str) -> bool:
        """Run Docker container"""
        
        container_name = f"analyzer-{task_id}"
        
        docker_cmd = [
            'docker', 'run',
            '--rm',                              # Auto-remove container
            '--name', container_name,            # Container name
            '-v', f'{input_path}:/input:ro',     # Read-only mount input
            '-v', f'{output_path}:/output:rw',   # Read-write mount output
            '--memory', self.memory_limit,       # Memory limit
            '--cpus', self.cpu_limit,           # CPU limit
            '--network', 'none',                 # Run without network
            '--user', 'root',                   # Need write permissions
            self.docker_image,                   # Image name
            '--input', '/input',                # Analyzer parameters
            '--output', '/output/analysis.json' # Output file
        ]
        
        try:
            logger.info(f"🐳 Starting Docker container: {container_name}")
            logger.debug(f"Docker command: {' '.join(docker_cmd)}")
            
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode == 0:
                logger.info("✅ Docker analysis complete")
                if result.stdout.strip():
                    logger.info("📄 Analyzer output:")
                    for line in result.stdout.strip().split('\n'):
                        logger.info(f"   {line}")
                return True
            else:
                logger.error(f"❌ Docker analysis failed (exit code: {result.returncode})")
                if result.stderr:
                    logger.error(f"Error message: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"❌ Docker analysis timeout ({self.timeout} seconds)")
            # Try to stop container
            try:
                subprocess.run(['docker', 'stop', container_name], 
                             capture_output=True, timeout=10)
            except:
                pass
            return False
        except Exception as e:
            logger.error(f"❌ Docker execution error: {e}")
            return False
    
    def _print_summary(self, result: Dict[str, Any], duration: float):
        """Print analysis summary"""
        metadata = result.get('metadata', {})
        
        logger.info("📊 Analysis Summary:")
        logger.info(f"   - Duration: {duration:.2f} seconds")
        logger.info(f"   - Total nodes: {metadata.get('total_nodes', 'N/A')}")
        logger.info(f"   - Total relationships: {metadata.get('total_relationships', 'N/A')}")
        logger.info(f"   - Resolution rate: {metadata.get('resolution_rate', 'N/A'):.1f}%")
        
        node_counts = metadata.get('node_type_counts', {})
        if node_counts:
            logger.info("   - Node types:")
            for node_type, count in node_counts.items():
                logger.info(f"     * {node_type}: {count}")
    
    def analyze_file(self, file_path: Union[str, Path], output_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        """
        Analyze single file
        
        Args:
            file_path: File path to analyze
            output_path: Output file path (optional)
            
        Returns:
            Analysis result dictionary
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File does not exist: {file_path}")
        
        # Create temporary directory containing only this file
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = Path(temp_dir) / file_path.name
            shutil.copy2(file_path, temp_file)
            
            # Analyze the temporary directory
            return self.analyze_codebase(temp_dir, output_path)
    
    def get_functions_with_comments(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get functions with comments"""
        functions_with_comments = []
        for node in result.get('nodes', []):
            if node.get('node_type') == 'function' and node.get('documentation'):
                functions_with_comments.append(node)
        return functions_with_comments
    
    def get_complex_functions(self, result: Dict[str, Any], min_params: int = 3) -> List[Dict[str, Any]]:
        """Get complex functions (with many parameters)"""
        complex_functions = []
        for node in result.get('nodes', []):
            if node.get('node_type') == 'function':
                params = node.get('parameters', [])
                if len(params) >= min_params:
                    complex_functions.append(node)
        return complex_functions
    
    def generate_summary_report(self, result: Dict[str, Any], output_path: Optional[Union[str, Path]] = None) -> str:
        """Generate summary report"""
        
        metadata = result.get('metadata', {})
        nodes = result.get('nodes', [])
        
        # Statistics
        total_nodes = len(nodes)
        node_types = {}
        languages = {}
        
        for node in nodes:
            node_type = node.get('node_type', 'unknown')
            language = node.get('language', 'unknown')
            
            node_types[node_type] = node_types.get(node_type, 0) + 1
            languages[language] = languages.get(language, 0) + 1
        
        # Generate report
        report_lines = [
            "# Code Analysis Summary Report",
            "",
            "## Overview",
            f"- Total nodes: {total_nodes}",
            f"- Total relationships: {metadata.get('total_relationships', 'N/A')}",
            f"- Resolution rate: {metadata.get('resolution_rate', 'N/A'):.1f}%",
            f"- Analyzer version: {metadata.get('analyzer_version', 'N/A')}",
            "",
            "## Node Type Distribution",
        ]
        
        for node_type, count in sorted(node_types.items()):
            percentage = (count / total_nodes * 100) if total_nodes > 0 else 0
            report_lines.append(f"- {node_type}: {count} ({percentage:.1f}%)")
        
        report_lines.extend([
            "",
            "## Language Distribution",
        ])
        
        for language, count in sorted(languages.items()):
            percentage = (count / total_nodes * 100) if total_nodes > 0 else 0
            report_lines.append(f"- {language}: {count} ({percentage:.1f}%)")
        
        # Functions with documentation
        functions_with_docs = self.get_functions_with_comments(result)
        report_lines.extend([
            "",
            "## Documentation Coverage",
            f"- Functions with documentation: {len(functions_with_docs)}",
        ])
        
        # Complex functions
        complex_functions = self.get_complex_functions(result)
        report_lines.extend([
            "",
            "## Complex Functions (3+ parameters)",
            f"- Count: {len(complex_functions)}",
        ])
        
        if complex_functions:
            report_lines.append("- List:")
            for func in complex_functions[:10]:  # Show top 10
                name = func.get('name', 'unknown')
                param_count = len(func.get('parameters', []))
                report_lines.append(f"  * {name} ({param_count} parameters)")
        
        report = "\n".join(report_lines)
        
        # Save to file if specified
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"📄 Summary report saved to: {output_path}")
        
        return report

# Convenience functions
def analyze_code(codebase_path: Union[str, Path], 
                output_path: Optional[Union[str, Path]] = None,
                docker_image: str = "enhanced-code-analyzer:latest") -> Dict[str, Any]:
    """
    Convenience function to analyze codebase
    
    Args:
        codebase_path: Path to code to analyze
        output_path: Output file path (optional)
        docker_image: Docker image to use
        
    Returns:
        Analysis result dictionary
    """
    analyzer = DockerCodeAnalyzer(docker_image=docker_image)
    return analyzer.analyze_codebase(codebase_path, output_path)

def analyze_file(file_path: Union[str, Path],
                output_path: Optional[Union[str, Path]] = None,
                docker_image: str = "enhanced-code-analyzer:latest") -> Dict[str, Any]:
    """
    Convenience function to analyze single file
    
    Args:
        file_path: File path to analyze
        output_path: Output file path (optional)
        docker_image: Docker image to use
        
    Returns:
        Analysis result dictionary
    """
    analyzer = DockerCodeAnalyzer(docker_image=docker_image)
    return analyzer.analyze_file(file_path, output_path)

def main():
    """Command line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Docker Code Analyzer Interface')
    parser.add_argument('path', help='Path to code file or directory to analyze')
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('--image', default='enhanced-code-analyzer:latest', 
                       help='Docker image to use')
    parser.add_argument('--report', help='Generate summary report to specified path')
    parser.add_argument('--timeout', type=int, default=600, help='Timeout in seconds')
    
    args = parser.parse_args()
    
    try:
        # Create analyzer
        analyzer = DockerCodeAnalyzer(
            docker_image=args.image,
            timeout=args.timeout
        )
        
        # Analyze
        path = Path(args.path)
        if path.is_file():
            result = analyzer.analyze_file(path, args.output)
        else:
            result = analyzer.analyze_codebase(path, args.output)
        
        # Generate report if requested
        if args.report:
            analyzer.generate_summary_report(result, args.report)
        
        print("✅ Analysis complete!")
        
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())