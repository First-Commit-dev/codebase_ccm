#!/usr/bin/env python3
"""
Graph Converter for Enhanced Analyzer Output

This module converts the enhanced_analyzer output (CCM format) into a graph structure
suitable for frontend architecture diagram visualization.

The converter transforms the complex CCM format into a simplified graph with nodes and edges
that can be easily consumed by frontend graph visualization libraries like D3.js, Cytoscape.js, etc.
"""

import json
import logging
from typing import Dict, List, Any, Set, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    """Represents a node in the architecture graph"""
    id: str
    name: str
    type: str  # module, class, function, package
    file_path: str
    package: str  # derived from file path
    size: int = 1  # for visualization sizing
    complexity: int = 0  # based on relationships count
    documentation: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class GraphEdge:
    """Represents an edge in the architecture graph"""
    id: str
    source: str
    target: str
    type: str  # imports, calls, inherits, contains
    weight: int = 1  # for visualization thickness
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ArchitectureGraph:
    """Complete architecture graph structure"""
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    packages: List[Dict[str, Any]]  # package hierarchy
    statistics: Dict[str, Any]
    metadata: Dict[str, Any]


class GraphConverter:
    """Converts enhanced_analyzer CCM output to architecture graph"""
    
    def __init__(self):
        self.node_id_mapping = {}  # CCM id -> graph id
        self.package_hierarchy = defaultdict(set)
        self.file_to_package = {}
        
    def convert_analysis_to_graph(self, analysis_file: str, output_file: str = None) -> ArchitectureGraph:
        """
        Convert enhanced_analyzer output to architecture graph
        
        Args:
            analysis_file: Path to the analysis.json file
            output_file: Optional path to save the graph JSON
            
        Returns:
            ArchitectureGraph object
        """
        logger.info(f"Converting analysis file: {analysis_file}")
        
        # Load analysis data
        with open(analysis_file, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        
        # Extract project info
        project_info = analysis_data.get('project', {})
        nodes_data = analysis_data.get('nodes', [])
        
        # Build package hierarchy
        self._build_package_hierarchy(nodes_data)
        
        # Convert nodes
        graph_nodes = self._convert_nodes(nodes_data)
        
        # Convert relationships to edges
        graph_edges = self._convert_relationships(nodes_data)
        
        # Generate packages info
        packages_info = self._generate_packages_info()
        
        # Calculate statistics
        statistics = self._calculate_statistics(graph_nodes, graph_edges, analysis_data)
        
        # Create graph structure
        graph = ArchitectureGraph(
            nodes=graph_nodes,
            edges=graph_edges,
            packages=packages_info,
            statistics=statistics,
            metadata={
                'project_name': project_info.get('name', 'Unknown'),
                'project_type': project_info.get('project_type', 'Unknown'),
                'languages': project_info.get('languages', []),
                'ccm_version': analysis_data.get('ccm_version', '1.0.0'),
                'converter_version': '1.0.0'
            }
        )
        
        # Save to file if specified
        if output_file:
            self._save_graph(graph, output_file)
            
        logger.info(f"Conversion completed: {len(graph_nodes)} nodes, {len(graph_edges)} edges")
        return graph
    
    def _build_package_hierarchy(self, nodes_data: List[Dict]) -> None:
        """Build package hierarchy from file paths"""
        for node in nodes_data:
            location = node.get('location', {})
            file_path = location.get('file_path', '')
            
            if file_path:
                # Normalize path and extract package structure
                path_parts = Path(file_path).parts
                if path_parts:
                    # Remove file name, keep directory structure
                    if len(path_parts) > 1:
                        package_parts = path_parts[:-1]  # Remove filename
                        package_name = '.'.join(package_parts)
                        self.file_to_package[file_path] = package_name
                        
                        # Build hierarchy
                        for i in range(1, len(package_parts) + 1):
                            partial_package = '.'.join(package_parts[:i])
                            if i > 1:
                                parent_package = '.'.join(package_parts[:i-1])
                                self.package_hierarchy[parent_package].add(partial_package)
                            else:
                                self.package_hierarchy['root'].add(partial_package)
    
    def _convert_nodes(self, nodes_data: List[Dict]) -> List[GraphNode]:
        """Convert CCM nodes to graph nodes"""
        graph_nodes = []
        
        for node in nodes_data:
            node_id = node.get('id', '')
            name = node.get('name', 'Unknown')
            node_type = node.get('node_type', 'unknown')
            location = node.get('location', {})
            file_path = location.get('file_path', '')
            
            # Skip comment nodes as they are not useful for architecture visualization
            if node_type == 'comment':
                continue
            
            # Generate simplified node ID
            graph_node_id = f"{node_type}_{len(graph_nodes) + 1:06d}"
            self.node_id_mapping[node_id] = graph_node_id
            
            # Determine package
            package = self.file_to_package.get(file_path, 'root')
            
            # Calculate complexity based on relationships
            relationships = node.get('relationships', []) or []
            complexity = len(relationships)
            
            # Extract documentation
            doc = node.get('documentation', {})
            documentation = None
            if doc:
                doc_parts = []
                if doc.get('summary'):
                    doc_parts.append(doc['summary'])
                if doc.get('description'):
                    doc_parts.append(doc['description'])
                documentation = ' '.join(doc_parts) if doc_parts else None
            
            # Create graph node
            graph_node = GraphNode(
                id=graph_node_id,
                name=name,
                type=node_type,
                file_path=file_path,
                package=package,
                size=max(1, complexity // 5 + 1),  # Size based on complexity
                complexity=complexity,
                documentation=documentation,
                metadata={
                    'original_id': node_id,
                    'language': node.get('language', 'unknown'),
                    'visibility': node.get('visibility'),
                    'modifiers': node.get('modifiers'),
                    'parameters_count': len(node.get('parameters', [])) if node.get('parameters') else 0,
                    'children_count': len(node.get('children_ids', [])) if node.get('children_ids') else 0,
                    'start_line': location.get('start_line'),
                    'end_line': location.get('end_line')
                }
            )
            
            graph_nodes.append(graph_node)
        
        return graph_nodes
    
    def _convert_relationships(self, nodes_data: List[Dict]) -> List[GraphEdge]:
        """Convert CCM relationships to graph edges"""
        graph_edges = []
        edge_counter = 0
        
        for node in nodes_data:
            source_id = node.get('id', '')
            source_graph_id = self.node_id_mapping.get(source_id)
            
            if not source_graph_id:
                continue
                
            relationships = node.get('relationships', []) or []
            
            for rel in relationships:
                rel_type = rel.get('type', 'unknown')
                target_name = rel.get('target_name', '')
                target_id = rel.get('target_id', '')
                
                # Try to find target node
                target_graph_id = None
                if target_id and target_id in self.node_id_mapping:
                    target_graph_id = self.node_id_mapping[target_id]
                else:
                    # Try to find by name (for external dependencies)
                    target_graph_id = self._find_target_by_name(target_name, nodes_data)
                
                if target_graph_id:
                    edge_counter += 1
                    edge_id = f"edge_{edge_counter:06d}"
                    
                    # Determine edge weight based on relationship type
                    weight = self._get_relationship_weight(rel_type)
                    
                    graph_edge = GraphEdge(
                        id=edge_id,
                        source=source_graph_id,
                        target=target_graph_id,
                        type=rel_type,
                        weight=weight,
                        metadata={
                            'target_name': target_name,
                            'original_target_id': target_id,
                            'relationship_metadata': rel.get('metadata')
                        }
                    )
                    
                    graph_edges.append(graph_edge)
        
        return graph_edges
    
    def _find_target_by_name(self, target_name: str, nodes_data: List[Dict]) -> Optional[str]:
        """Find target node by name for external dependencies"""
        for node in nodes_data:
            if node.get('name') == target_name:
                node_id = node.get('id', '')
                return self.node_id_mapping.get(node_id)
        return None
    
    def _get_relationship_weight(self, rel_type: str) -> int:
        """Determine edge weight based on relationship type"""
        weight_map = {
            'imports': 1,
            'calls': 2,
            'inherits': 3,
            'contains': 1,
            'implements': 3,
            'extends': 3,
            'uses': 1
        }
        return weight_map.get(rel_type, 1)
    
    def _generate_packages_info(self) -> List[Dict[str, Any]]:
        """Generate package hierarchy information"""
        packages = []
        
        for parent, children in self.package_hierarchy.items():
            if parent != 'root':
                packages.append({
                    'id': parent,
                    'name': parent.split('.')[-1],
                    'full_name': parent,
                    'children': list(children),
                    'type': 'package'
                })
        
        return packages
    
    def _calculate_statistics(self, nodes: List[GraphNode], edges: List[GraphEdge], 
                            analysis_data: Dict) -> Dict[str, Any]:
        """Calculate graph statistics"""
        # Node statistics
        node_types = defaultdict(int)
        languages = defaultdict(int)
        packages = defaultdict(int)
        
        for node in nodes:
            node_types[node.type] += 1
            languages[node.metadata.get('language', 'unknown')] += 1
            packages[node.package] += 1
        
        # Edge statistics
        edge_types = defaultdict(int)
        for edge in edges:
            edge_types[edge.type] += 1
        
        # Complexity analysis
        complexities = [node.complexity for node in nodes]
        avg_complexity = sum(complexities) / len(complexities) if complexities else 0
        max_complexity = max(complexities) if complexities else 0
        
        # Original metadata
        original_metadata = analysis_data.get('metadata', {})
        
        return {
            'total_nodes': len(nodes),
            'total_edges': len(edges),
            'total_packages': len(packages),
            'node_types': dict(node_types),
            'edge_types': dict(edge_types),
            'languages': dict(languages),
            'packages': dict(packages),
            'complexity': {
                'average': round(avg_complexity, 2),
                'maximum': max_complexity,
                'distribution': self._get_complexity_distribution(complexities)
            },
            'original_analysis': {
                'total_nodes': original_metadata.get('total_nodes'),
                'total_relationships': original_metadata.get('total_relationships'),
                'resolution_rate': original_metadata.get('resolution_rate'),
                'analyzer_version': original_metadata.get('analyzer_version')
            }
        }
    
    def _get_complexity_distribution(self, complexities: List[int]) -> Dict[str, int]:
        """Get complexity distribution buckets"""
        distribution = {
            'low': 0,      # 0-5
            'medium': 0,   # 6-15
            'high': 0,     # 16-30
            'very_high': 0 # 30+
        }
        
        for complexity in complexities:
            if complexity <= 5:
                distribution['low'] += 1
            elif complexity <= 15:
                distribution['medium'] += 1
            elif complexity <= 30:
                distribution['high'] += 1
            else:
                distribution['very_high'] += 1
        
        return distribution
    
    def _save_graph(self, graph: ArchitectureGraph, output_file: str) -> None:
        """Save graph to JSON file"""
        graph_dict = {
            'nodes': [asdict(node) for node in graph.nodes],
            'edges': [asdict(edge) for edge in graph.edges],
            'packages': graph.packages,
            'statistics': graph.statistics,
            'metadata': graph.metadata
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(graph_dict, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Graph saved to: {output_file}")


def main():
    """Command line interface for the graph converter"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert enhanced_analyzer output to architecture graph')
    parser.add_argument('input', help='Input analysis.json file')
    parser.add_argument('-o', '--output', help='Output graph.json file', 
                       default='architecture_graph.json')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Convert analysis to graph
    converter = GraphConverter()
    try:
        graph = converter.convert_analysis_to_graph(args.input, args.output)
        print(f"✅ Conversion successful!")
        print(f"📊 Generated {len(graph.nodes)} nodes and {len(graph.edges)} edges")
        print(f"📦 Found {len(graph.packages)} packages")
        print(f"💾 Output saved to: {args.output}")
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        raise


if __name__ == '__main__':
    main() 