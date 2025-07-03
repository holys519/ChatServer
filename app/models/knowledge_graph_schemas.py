"""
Enhanced Knowledge Graph Schemas
Defines advanced structures for knowledge graph, concept maps, and topic clustering
"""

from typing import List, Dict, Any, Optional, Set, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import uuid

class EntityType(str, Enum):
    """Types of entities in the knowledge graph"""
    PERSON = "person"
    ORGANIZATION = "organization"
    CONCEPT = "concept"
    TECHNOLOGY = "technology"
    METHOD = "method"
    LOCATION = "location"
    DATE = "date"
    PRODUCT = "product"
    PROCESS = "process"
    METRIC = "metric"
    CATEGORY = "category"
    KEYWORD = "keyword"

class RelationType(str, Enum):
    """Types of relationships between entities"""
    # Hierarchical relationships
    IS_A = "is_a"
    PART_OF = "part_of"
    CONTAINS = "contains"
    SUBCATEGORY_OF = "subcategory_of"
    
    # Causal relationships
    CAUSES = "causes"
    LEADS_TO = "leads_to"
    RESULTS_IN = "results_in"
    ENABLES = "enables"
    
    # Associative relationships
    RELATED_TO = "related_to"
    SIMILAR_TO = "similar_to"
    OPPOSITE_TO = "opposite_to"
    COMPARED_WITH = "compared_with"
    
    # Temporal relationships
    BEFORE = "before"
    AFTER = "after"
    DURING = "during"
    CONCURRENT_WITH = "concurrent_with"
    
    # Functional relationships
    USES = "uses"
    IMPLEMENTS = "implements"
    APPLIES = "applies"
    DEPENDS_ON = "depends_on"
    
    # Quantitative relationships
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    EQUAL_TO = "equal_to"
    PROPORTIONAL_TO = "proportional_to"

class EntityMention(BaseModel):
    """Reference to where an entity appears in documents"""
    document_id: str
    document_name: str
    chunk_id: str
    page_number: int
    context: str = Field(..., description="Surrounding text context")
    confidence: float = Field(..., ge=0.0, le=1.0)
    start_offset: Optional[int] = None
    end_offset: Optional[int] = None

class EnhancedEntity(BaseModel):
    """Enhanced entity with rich metadata and relationships"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Primary name of the entity")
    type: EntityType = Field(..., description="Type classification")
    aliases: List[str] = Field(default_factory=list, description="Alternative names")
    description: str = Field(..., description="Entity description")
    
    # Confidence and validation
    confidence: float = Field(..., ge=0.0, le=1.0)
    validation_status: str = Field(default="auto_extracted", description="manual_verified, auto_extracted, disputed")
    
    # Document references
    mentions: List[EntityMention] = Field(default_factory=list)
    source_documents: Set[str] = Field(default_factory=set)
    mention_count: int = Field(default=0)
    
    # Metadata
    properties: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    category: Optional[str] = None
    subcategory: Optional[str] = None
    
    # Graph metrics
    centrality_score: float = Field(default=0.0, description="Centrality in knowledge graph")
    importance_score: float = Field(default=0.0, description="Calculated importance")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    user_id: str = Field(..., description="User who owns this entity")

class EnhancedRelation(BaseModel):
    """Enhanced relationship with context and metadata"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_entity_id: str = Field(..., description="Source entity ID")
    target_entity_id: str = Field(..., description="Target entity ID")
    relation_type: RelationType = Field(..., description="Type of relationship")
    
    # Relationship metadata
    strength: float = Field(default=1.0, ge=0.0, le=1.0, description="Relationship strength")
    confidence: float = Field(..., ge=0.0, le=1.0)
    direction: str = Field(default="directed", description="directed, undirected, bidirectional")
    
    # Evidence and context
    evidence_text: str = Field(..., description="Text that supports this relationship")
    context_chunks: List[str] = Field(default_factory=list, description="Chunk IDs providing context")
    source_documents: Set[str] = Field(default_factory=set)
    
    # Properties
    properties: Dict[str, Any] = Field(default_factory=dict)
    temporal_info: Optional[Dict[str, str]] = Field(None, description="When this relationship was valid")
    
    # Validation
    validation_status: str = Field(default="auto_extracted")
    validation_notes: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    user_id: str = Field(..., description="User who owns this relation")

class TopicCluster(BaseModel):
    """Topic-based document clustering"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Topic cluster name")
    description: str = Field(..., description="Topic description")
    
    # Topic characteristics
    keywords: List[str] = Field(default_factory=list)
    key_entities: List[str] = Field(default_factory=list, description="Important entity IDs")
    key_concepts: List[str] = Field(default_factory=list)
    
    # Documents in this cluster
    document_ids: Set[str] = Field(default_factory=set)
    chunk_ids: Set[str] = Field(default_factory=set)
    
    # Cluster metrics
    coherence_score: float = Field(default=0.0, description="Internal coherence")
    size: int = Field(default=0, description="Number of documents")
    density: float = Field(default=0.0, description="Relationship density")
    
    # Hierarchical clustering
    parent_cluster_id: Optional[str] = None
    child_cluster_ids: List[str] = Field(default_factory=list)
    cluster_level: int = Field(default=0, description="Hierarchy level")
    
    # Color and visualization
    color: str = Field(default="#3498db", description="Visualization color")
    position: Optional[Dict[str, float]] = Field(None, description="x, y coordinates for visualization")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    user_id: str = Field(..., description="User who owns this cluster")

class ConceptMap(BaseModel):
    """Concept map structure"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Concept map name")
    description: str = Field(..., description="Map description")
    
    # Map content
    entities: List[str] = Field(default_factory=list, description="Entity IDs in this map")
    relations: List[str] = Field(default_factory=list, description="Relation IDs in this map")
    clusters: List[str] = Field(default_factory=list, description="Topic cluster IDs")
    
    # Map configuration
    layout_type: str = Field(default="force_directed", description="Layout algorithm")
    zoom_level: float = Field(default=1.0)
    center_point: Dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})
    
    # Filtering and focus
    entity_types_shown: List[EntityType] = Field(default_factory=list)
    relation_types_shown: List[RelationType] = Field(default_factory=list)
    min_confidence: float = Field(default=0.5)
    max_entities: int = Field(default=100)
    
    # Map metadata
    scope: str = Field(default="document", description="document, topic, custom")
    focus_entity_id: Optional[str] = Field(None, description="Central entity for focused maps")
    depth_level: int = Field(default=2, description="Relationship depth to include")
    
    # Sharing and collaboration
    is_public: bool = Field(default=False)
    shared_with: List[str] = Field(default_factory=list, description="User IDs with access")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    user_id: str = Field(..., description="User who owns this map")

class KnowledgeGraphQuery(BaseModel):
    """Query structure for knowledge graph exploration"""
    query_type: str = Field(..., description="entity_search, relation_search, path_finding, clustering")
    
    # Search parameters
    search_terms: List[str] = Field(default_factory=list)
    entity_types: List[EntityType] = Field(default_factory=list)
    relation_types: List[RelationType] = Field(default_factory=list)
    
    # Graph traversal
    start_entity_id: Optional[str] = None
    end_entity_id: Optional[str] = None
    max_depth: int = Field(default=3)
    max_results: int = Field(default=50)
    
    # Filtering
    min_confidence: float = Field(default=0.5)
    min_importance: float = Field(default=0.0)
    document_filter: List[str] = Field(default_factory=list)
    date_range: Optional[Dict[str, str]] = None
    
    # Grouping and aggregation
    group_by: Optional[str] = Field(None, description="entity_type, topic, document")
    include_clusters: bool = Field(default=False)
    include_metrics: bool = Field(default=True)

class KnowledgeGraphStats(BaseModel):
    """Statistics about the knowledge graph"""
    total_entities: int = 0
    total_relations: int = 0
    total_clusters: int = 0
    
    # Entity breakdown
    entities_by_type: Dict[str, int] = Field(default_factory=dict)
    
    # Relation breakdown  
    relations_by_type: Dict[str, int] = Field(default_factory=dict)
    
    # Graph metrics
    average_entity_connections: float = 0.0
    graph_density: float = 0.0
    largest_component_size: int = 0
    num_isolated_entities: int = 0
    
    # Quality metrics
    average_confidence: float = 0.0
    verified_entities_count: int = 0
    verified_relations_count: int = 0
    
    # Document coverage
    documents_with_entities: int = 0
    documents_with_relations: int = 0
    average_entities_per_document: float = 0.0
    
    # Temporal info
    last_updated: datetime = Field(default_factory=datetime.now)
    extraction_version: str = "3.0"

class GraphVisualizationConfig(BaseModel):
    """Configuration for graph visualization"""
    width: int = Field(default=800)
    height: int = Field(default=600)
    
    # Layout settings
    layout_algorithm: str = Field(default="force_directed")
    node_spacing: float = Field(default=50.0)
    edge_length: float = Field(default=100.0)
    
    # Visual styling
    node_size_by: str = Field(default="importance", description="importance, connections, mentions")
    edge_width_by: str = Field(default="strength", description="strength, confidence")
    color_by: str = Field(default="entity_type", description="entity_type, cluster, confidence")
    
    # Interaction
    enable_zoom: bool = Field(default=True)
    enable_pan: bool = Field(default=True)
    enable_selection: bool = Field(default=True)
    show_labels: bool = Field(default=True)
    show_edge_labels: bool = Field(default=False)
    
    # Filtering UI
    show_filter_panel: bool = Field(default=True)
    show_minimap: bool = Field(default=True)
    show_legend: bool = Field(default=True)
    
    # Performance
    max_visible_nodes: int = Field(default=200)
    max_visible_edges: int = Field(default=500)
    use_clustering: bool = Field(default=True)

class ConceptMapTemplate(BaseModel):
    """Template for common concept map types"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    category: str = Field(..., description="academic, business, research, etc.")
    
    # Template structure
    required_entity_types: List[EntityType] = Field(default_factory=list)
    suggested_relations: List[RelationType] = Field(default_factory=list)
    layout_hints: Dict[str, Any] = Field(default_factory=dict)
    
    # Usage
    use_count: int = Field(default=0)
    is_public: bool = Field(default=True)
    created_by: str = Field(..., description="Creator user ID")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)