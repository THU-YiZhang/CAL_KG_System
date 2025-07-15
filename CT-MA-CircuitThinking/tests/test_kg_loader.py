"""
Test cases for KG Loader module.
"""

import pytest
import json
import tempfile
from pathlib import Path
import sys

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.core.kg_loader import KGLoader
from src.utils.config_manager import ConfigManager


@pytest.fixture
def sample_kg_data():
    """Sample knowledge graph data for testing."""
    return {
        "title": "Test Knowledge Graph",
        "timestamp": "2024-01-01T00:00:00",
        "nodes": [
            {
                "id": "node_1",
                "label": "基础概念1",
                "node_type": "basic_concept",
                "summary": "这是一个基础概念",
                "keywords": ["概念", "基础"]
            },
            {
                "id": "node_2", 
                "label": "核心技术1",
                "node_type": "core_technology",
                "summary": "这是一个核心技术",
                "keywords": ["技术", "核心"]
            },
            {
                "id": "node_3",
                "label": "电路应用1", 
                "node_type": "circuit_application",
                "summary": "这是一个电路应用",
                "keywords": ["应用", "电路"]
            }
        ],
        "edges": [
            {
                "source_id": "node_1",
                "target_id": "node_2",
                "relationship": "supports",
                "description": "基础概念支持核心技术"
            },
            {
                "source_id": "node_2", 
                "target_id": "node_3",
                "relationship": "enables",
                "description": "核心技术实现电路应用"
            }
        ]
    }


@pytest.fixture
def temp_kg_file(sample_kg_data):
    """Create temporary knowledge graph file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(sample_kg_data, f, ensure_ascii=False, indent=2)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    Path(temp_path).unlink()


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    config_data = {
        "data": {
            "input_kg_path": "test_kg.json"
        }
    }
    
    # Create a simple mock config
    class MockConfig:
        def __init__(self, data):
            self.data = data
        
        def get(self, key, default=None):
            keys = key.split('.')
            value = self.data
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            return value
    
    return MockConfig(config_data)


class TestKGLoader:
    """Test cases for KGLoader class."""
    
    def test_init(self, mock_config):
        """Test KGLoader initialization."""
        loader = KGLoader(mock_config)
        assert loader.config == mock_config
        assert loader.kg_data is None
        assert loader.graph is None
    
    @pytest.mark.asyncio
    async def test_load_knowledge_graph_success(self, mock_config, temp_kg_file, sample_kg_data):
        """Test successful knowledge graph loading."""
        loader = KGLoader(mock_config)
        
        # Load the knowledge graph
        result = await loader.load_knowledge_graph(temp_kg_file)
        
        # Verify results
        assert result is not None
        assert loader.kg_data is not None
        assert loader.graph is not None
        
        # Check data structure
        assert len(result['nodes']) == 3
        assert len(result['edges']) == 2
        assert result['title'] == sample_kg_data['title']
    
    @pytest.mark.asyncio
    async def test_load_knowledge_graph_file_not_found(self, mock_config):
        """Test loading non-existent knowledge graph file."""
        loader = KGLoader(mock_config)
        
        with pytest.raises(FileNotFoundError):
            await loader.load_knowledge_graph("non_existent_file.json")
    
    @pytest.mark.asyncio
    async def test_load_knowledge_graph_invalid_format(self, mock_config):
        """Test loading invalid knowledge graph format."""
        # Create invalid JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            f.write('{"invalid": "format"}')  # Missing required keys
            temp_path = f.name
        
        try:
            loader = KGLoader(mock_config)
            
            with pytest.raises(ValueError):
                await loader.load_knowledge_graph(temp_path)
        finally:
            Path(temp_path).unlink()
    
    def test_get_nodes_by_type(self, mock_config, sample_kg_data):
        """Test getting nodes by type."""
        loader = KGLoader(mock_config)
        loader.kg_data = sample_kg_data
        
        # Test getting basic concepts
        basic_concepts = loader.get_nodes_by_type('basic_concept')
        assert len(basic_concepts) == 1
        assert basic_concepts[0]['label'] == '基础概念1'
        
        # Test getting core technologies
        core_techs = loader.get_nodes_by_type('core_technology')
        assert len(core_techs) == 1
        assert core_techs[0]['label'] == '核心技术1'
        
        # Test getting circuit applications
        circuit_apps = loader.get_nodes_by_type('circuit_application')
        assert len(circuit_apps) == 1
        assert circuit_apps[0]['label'] == '电路应用1'
    
    def test_get_node_by_id(self, mock_config, sample_kg_data):
        """Test getting node by ID."""
        loader = KGLoader(mock_config)
        loader.kg_data = sample_kg_data
        
        # Test existing node
        node = loader.get_node_by_id('node_1')
        assert node is not None
        assert node['label'] == '基础概念1'
        
        # Test non-existent node
        node = loader.get_node_by_id('non_existent')
        assert node is None
    
    def test_get_node_statistics(self, mock_config, sample_kg_data):
        """Test getting node statistics."""
        loader = KGLoader(mock_config)
        loader.kg_data = sample_kg_data
        
        # Build graph first
        loader.graph = loader._build_networkx_graph()
        
        stats = loader.get_node_statistics()
        
        assert stats['total_nodes'] == 3
        assert stats['total_edges'] == 2
        assert 'node_types' in stats
        assert stats['node_types']['basic_concept'] == 1
        assert stats['node_types']['core_technology'] == 1
        assert stats['node_types']['circuit_application'] == 1


if __name__ == "__main__":
    pytest.main([__file__])
