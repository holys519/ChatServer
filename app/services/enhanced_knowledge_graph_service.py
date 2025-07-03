"""
Enhanced Knowledge Graph Service
Advanced knowledge graph processing with clustering and concept mapping
"""

import json
import re
import math
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
from collections import defaultdict, Counter

from app.models.knowledge_graph_schemas import (
    EnhancedEntity, EnhancedRelation, TopicCluster, ConceptMap,
    KnowledgeGraphQuery, KnowledgeGraphStats, EntityType, RelationType,
    EntityMention
)

# Firebase imports
try:
    from app.services.firebase_service import firebase_service
    FIREBASE_AVAILABLE = True
except ImportError:
    firebase_service = None
    FIREBASE_AVAILABLE = False

# Gemini service for advanced extraction
try:
    from app.services.gemini_service import gemini_service
    GEMINI_AVAILABLE = True
except ImportError:
    gemini_service = None
    GEMINI_AVAILABLE = False

# Clustering libraries
try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans, DBSCAN
    from sklearn.manifold import TSNE
    from sklearn.metrics.pairwise import cosine_similarity
    CLUSTERING_AVAILABLE = True
except ImportError:
    np = None
    TfidfVectorizer = None
    KMeans = None
    DBSCAN = None
    TSNE = None
    cosine_similarity = None
    CLUSTERING_AVAILABLE = False

class EnhancedKnowledgeGraphService:
    """
    Advanced knowledge graph service with clustering and concept mapping
    """
    
    def __init__(self):
        self.firestore_client = None
        
        # Initialize Firestore
        if FIREBASE_AVAILABLE and firebase_service and firebase_service.is_available():
            self.firestore_client = firebase_service.get_firestore_client()
            print("✅ Enhanced Knowledge Graph service initialized with Firestore")
        else:
            print("⚠️ Firestore not available for Enhanced Knowledge Graph service")
    
    async def extract_enhanced_knowledge_graph(
        self, 
        text: str, 
        chunks: List[Dict[str, Any]], 
        user_id: str,
        document_id: str,
        document_name: str
    ) -> Dict[str, Any]:
        """
        Extract enhanced knowledge graph with relationships and context
        """
        print(f"🧠 Enhanced knowledge graph extraction for document: {document_name}")
        
        if not GEMINI_AVAILABLE or not gemini_service:
            print("⚠️ Gemini service not available, using basic extraction")
            return await self._basic_knowledge_extraction(text, chunks, user_id, document_id, document_name)
        
        try:
            # Advanced extraction with Gemini
            extraction_result = await self._gemini_enhanced_extraction(text, chunks, document_name)
            
            # Process and enhance the extracted knowledge
            entities = await self._process_extracted_entities(
                extraction_result.get('entities', []), 
                user_id, document_id, document_name, chunks
            )
            
            relations = await self._process_extracted_relations(
                extraction_result.get('relations', []), 
                entities, user_id, document_id, document_name
            )
            
            # Calculate graph metrics
            await self._calculate_entity_metrics(entities, relations)
            
            # Save to Firestore
            await self._save_enhanced_entities(entities)
            await self._save_enhanced_relations(relations)
            
            print(f"✅ Enhanced extraction: {len(entities)} entities, {len(relations)} relations")
            
            return {
                'entities': [entity.dict() for entity in entities],
                'relations': [relation.dict() for relation in relations],
                'extraction_method': 'gemini_enhanced'
            }
            
        except Exception as e:
            print(f"❌ Enhanced knowledge extraction error: {str(e)}")
            return await self._basic_knowledge_extraction(text, chunks, user_id, document_id, document_name)
    
    async def _gemini_enhanced_extraction(
        self, 
        text: str, 
        chunks: List[Dict[str, Any]], 
        document_name: str
    ) -> Dict[str, Any]:
        """Use Gemini for advanced knowledge extraction"""
        
        # Prepare enhanced prompt for knowledge extraction
        prompt = f"""
あなたは高度な知識抽出エンジンです。以下の文書から詳細な知識グラフを構築してください。

文書名: {document_name}

以下の要素を抽出してください：

1. エンティティ（実体）:
   - 人物、組織、概念、技術、手法、場所、日付、製品、プロセス、指標など
   - 各エンティティのタイプ、説明、重要度を含める

2. 関係性（リレーション）:
   - エンティティ間の具体的な関係
   - 階層関係（is_a, part_of）、因果関係（causes, leads_to）、機能関係（uses, implements）など
   - 関係の強度と信頼度を評価

3. 文脈情報:
   - 各エンティティ・関係が言及される文脈
   - 文書内での重要度と出現頻度

文書内容:
{text[:4000]}{"..." if len(text) > 4000 else ""}

JSON形式で回答してください：
{{
  "entities": [
    {{
      "name": "エンティティ名",
      "type": "person|organization|concept|technology|method|location|date|product|process|metric|category",
      "description": "詳細説明",
      "confidence": 0.0-1.0,
      "importance": 0.0-1.0,
      "aliases": ["別名1", "別名2"],
      "properties": {{"key": "value"}},
      "mentions": [
        {{
          "context": "文脈テキスト",
          "confidence": 0.0-1.0
        }}
      ]
    }}
  ],
  "relations": [
    {{
      "source": "ソースエンティティ名",
      "target": "ターゲットエンティティ名",
      "type": "is_a|part_of|causes|uses|related_to|etc",
      "description": "関係の説明",
      "confidence": 0.0-1.0,
      "strength": 0.0-1.0,
      "evidence": "関係を示すテキスト証拠",
      "direction": "directed|undirected|bidirectional"
    }}
  ],
  "topics": [
    {{
      "name": "トピック名",
      "keywords": ["キーワード1", "キーワード2"],
      "entities": ["関連エンティティ1", "関連エンティティ2"],
      "description": "トピック説明"
    }}
  ]
}}
"""
        
        try:
            response = await gemini_service.send_message(prompt)
            
            # Extract JSON from response
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                json_match = re.search(r'(\{.*\})', response, re.DOTALL)
                if json_match:
                    json_text = json_match.group(1)
                else:
                    raise ValueError("No JSON found in response")
            
            extraction_result = json.loads(json_text)
            
            # Validate structure
            if 'entities' not in extraction_result:
                extraction_result['entities'] = []
            if 'relations' not in extraction_result:
                extraction_result['relations'] = []
            if 'topics' not in extraction_result:
                extraction_result['topics'] = []
            
            return extraction_result
            
        except Exception as e:
            print(f"❌ Gemini extraction error: {str(e)}")
            raise e
    
    async def _process_extracted_entities(
        self,
        raw_entities: List[Dict[str, Any]],
        user_id: str,
        document_id: str,
        document_name: str,
        chunks: List[Dict[str, Any]]
    ) -> List[EnhancedEntity]:
        """Process raw entities into EnhancedEntity objects"""
        
        enhanced_entities = []
        
        for raw_entity in raw_entities:
            try:
                # Create entity mentions
                mentions = []
                for mention_data in raw_entity.get('mentions', []):
                    mention = EntityMention(
                        document_id=document_id,
                        document_name=document_name,
                        chunk_id=f"{document_id}_chunk_0",  # TODO: map to actual chunks
                        page_number=1,  # TODO: get from chunk metadata
                        context=mention_data.get('context', ''),
                        confidence=mention_data.get('confidence', 0.8)
                    )
                    mentions.append(mention)
                
                # Map entity type
                entity_type_str = raw_entity.get('type', 'concept').lower()
                try:
                    entity_type = EntityType(entity_type_str)
                except ValueError:
                    entity_type = EntityType.CONCEPT
                
                # Create enhanced entity
                entity = EnhancedEntity(
                    name=raw_entity.get('name', ''),
                    type=entity_type,
                    aliases=raw_entity.get('aliases', []),
                    description=raw_entity.get('description', ''),
                    confidence=raw_entity.get('confidence', 0.8),
                    mentions=mentions,
                    source_documents={document_id},
                    mention_count=len(mentions),
                    properties=raw_entity.get('properties', {}),
                    importance_score=raw_entity.get('importance', 0.5),
                    user_id=user_id
                )
                
                enhanced_entities.append(entity)
                
            except Exception as e:
                print(f"⚠️ Error processing entity {raw_entity.get('name', 'unknown')}: {str(e)}")
                continue
        
        return enhanced_entities
    
    async def _process_extracted_relations(
        self,
        raw_relations: List[Dict[str, Any]],
        entities: List[EnhancedEntity],
        user_id: str,
        document_id: str,
        document_name: str
    ) -> List[EnhancedRelation]:
        """Process raw relations into EnhancedRelation objects"""
        
        # Create entity name to ID mapping
        entity_map = {entity.name.lower(): entity.id for entity in entities}
        
        # Add aliases to mapping
        for entity in entities:
            for alias in entity.aliases:
                entity_map[alias.lower()] = entity.id
        
        enhanced_relations = []
        
        for raw_relation in raw_relations:
            try:
                source_name = raw_relation.get('source', '').lower()
                target_name = raw_relation.get('target', '').lower()
                
                # Find entity IDs
                source_id = entity_map.get(source_name)
                target_id = entity_map.get(target_name)
                
                if not source_id or not target_id:
                    print(f"⚠️ Could not find entities for relation: {source_name} -> {target_name}")
                    continue
                
                # Map relation type
                relation_type_str = raw_relation.get('type', 'related_to').lower()
                try:
                    relation_type = RelationType(relation_type_str)
                except ValueError:
                    relation_type = RelationType.RELATED_TO
                
                # Create enhanced relation
                relation = EnhancedRelation(
                    source_entity_id=source_id,
                    target_entity_id=target_id,
                    relation_type=relation_type,
                    strength=raw_relation.get('strength', 0.7),
                    confidence=raw_relation.get('confidence', 0.8),
                    direction=raw_relation.get('direction', 'directed'),
                    evidence_text=raw_relation.get('evidence', ''),
                    source_documents={document_id},
                    user_id=user_id
                )
                
                enhanced_relations.append(relation)
                
            except Exception as e:
                print(f"⚠️ Error processing relation: {str(e)}")
                continue
        
        return enhanced_relations
    
    async def _calculate_entity_metrics(
        self,
        entities: List[EnhancedEntity],
        relations: List[EnhancedRelation]
    ):
        """Calculate centrality and importance metrics for entities"""
        
        if not entities or not relations:
            return
        
        # Build adjacency map
        entity_connections = defaultdict(int)
        entity_ids = {entity.id for entity in entities}
        
        for relation in relations:
            if relation.source_entity_id in entity_ids:
                entity_connections[relation.source_entity_id] += 1
            if relation.target_entity_id in entity_ids:
                entity_connections[relation.target_entity_id] += 1
        
        # Calculate simple centrality (degree centrality)
        max_connections = max(entity_connections.values()) if entity_connections else 1
        
        for entity in entities:
            connections = entity_connections.get(entity.id, 0)
            entity.centrality_score = connections / max_connections if max_connections > 0 else 0
            
            # Calculate importance as combination of centrality and mention count
            normalized_mentions = entity.mention_count / 10.0  # Normalize to 0-1 range
            entity.importance_score = (entity.centrality_score * 0.6 + 
                                     min(normalized_mentions, 1.0) * 0.4)
    
    async def _save_enhanced_entities(self, entities: List[EnhancedEntity]):
        """Save enhanced entities to Firestore"""
        if not self.firestore_client or not entities:
            return
        
        try:
            batch = self.firestore_client.batch()
            
            for entity in entities:
                doc_ref = self.firestore_client.collection('enhanced_entities').document(entity.id)
                batch.set(doc_ref, entity.dict())
            
            batch.commit()
            print(f"💾 Saved {len(entities)} enhanced entities to Firestore")
            
        except Exception as e:
            print(f"❌ Error saving enhanced entities: {str(e)}")
    
    async def _save_enhanced_relations(self, relations: List[EnhancedRelation]):
        """Save enhanced relations to Firestore"""
        if not self.firestore_client or not relations:
            return
        
        try:
            batch = self.firestore_client.batch()
            
            for relation in relations:
                doc_ref = self.firestore_client.collection('enhanced_relations').document(relation.id)
                batch.set(doc_ref, relation.dict())
            
            batch.commit()
            print(f"💾 Saved {len(relations)} enhanced relations to Firestore")
            
        except Exception as e:
            print(f"❌ Error saving enhanced relations: {str(e)}")
    
    async def _basic_knowledge_extraction(
        self,
        text: str,
        chunks: List[Dict[str, Any]],
        user_id: str,
        document_id: str,
        document_name: str
    ) -> Dict[str, Any]:
        """Basic knowledge extraction fallback"""
        
        print("🔧 Using basic knowledge extraction (Gemini unavailable)")
        
        # Simple entity extraction using keywords
        entities = []
        relations = []
        
        # Basic keyword-based entity extraction
        common_patterns = {
            EntityType.PERSON: [r'\b[A-Z][a-z]+ [A-Z][a-z]+\b'],
            EntityType.ORGANIZATION: [r'\b[A-Z][A-Z0-9&\s]{2,20}\b'],
            EntityType.CONCEPT: [r'\b(?:システム|手法|方法|技術|アプローチ)\b'],
            EntityType.DATE: [r'\b\d{4}年?\b', r'\b\d{1,2}月\b']
        }
        
        for entity_type, patterns in common_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    entity_name = match.group().strip()
                    if len(entity_name) > 2:  # Filter very short matches
                        entity = EnhancedEntity(
                            name=entity_name,
                            type=entity_type,
                            description=f"自動抽出された{entity_type.value}",
                            confidence=0.6,
                            source_documents={document_id},
                            mention_count=1,
                            user_id=user_id
                        )
                        entities.append(entity)
        
        # Limit entities to avoid spam
        entities = entities[:50]
        
        return {
            'entities': [entity.dict() for entity in entities],
            'relations': relations,
            'extraction_method': 'basic_pattern'
        }
    
    async def create_topic_clusters(
        self, 
        user_id: str, 
        min_cluster_size: int = 3,
        max_clusters: int = 10
    ) -> List[TopicCluster]:
        """Create topic-based document clusters"""
        
        if not CLUSTERING_AVAILABLE:
            print("⚠️ Clustering libraries not available")
            return []
        
        if not self.firestore_client:
            print("⚠️ Firestore not available for clustering")
            return []
        
        try:
            print(f"🎯 Creating topic clusters for user {user_id}")
            
            # Get all enhanced chunks for user
            chunks_ref = self.firestore_client.collection('enhanced_vector_chunks')
            query = chunks_ref.where('user_id', '==', user_id).limit(1000)
            
            chunks_data = []
            for doc in query.stream():
                chunk_data = doc.to_dict()
                if 'text' in chunk_data and chunk_data['text'].strip():
                    chunks_data.append(chunk_data)
            
            if len(chunks_data) < min_cluster_size:
                print(f"⚠️ Not enough chunks for clustering: {len(chunks_data)}")
                return []
            
            # Extract text for clustering
            texts = [chunk['text'] for chunk in chunks_data]
            
            # TF-IDF vectorization
            vectorizer = TfidfVectorizer(
                max_features=500,
                stop_words=None,  # Handle Japanese text
                ngram_range=(1, 2),
                min_df=2,
                max_df=0.8
            )
            
            tfidf_matrix = vectorizer.fit_transform(texts)
            feature_names = vectorizer.get_feature_names_out()
            
            # Determine optimal number of clusters
            n_clusters = min(max_clusters, max(2, len(chunks_data) // 5))
            
            # K-means clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(tfidf_matrix)
            
            # Create topic clusters
            clusters = []
            for cluster_id in range(n_clusters):
                cluster_chunks = [chunks_data[i] for i, label in enumerate(cluster_labels) if label == cluster_id]
                
                if len(cluster_chunks) < min_cluster_size:
                    continue
                
                # Extract cluster keywords
                cluster_indices = [i for i, label in enumerate(cluster_labels) if label == cluster_id]
                cluster_tfidf = tfidf_matrix[cluster_indices]
                
                # Get top keywords for this cluster
                mean_tfidf = np.mean(cluster_tfidf.toarray(), axis=0)
                top_indices = np.argsort(mean_tfidf)[-10:][::-1]
                keywords = [feature_names[i] for i in top_indices if mean_tfidf[i] > 0.01]
                
                # Create cluster
                cluster = TopicCluster(
                    name=f"トピック {cluster_id + 1}",
                    description=f"キーワード: {', '.join(keywords[:5])}",
                    keywords=keywords,
                    document_ids={chunk['job_id'] for chunk in cluster_chunks},
                    chunk_ids={chunk['id'] for chunk in cluster_chunks},
                    size=len(cluster_chunks),
                    coherence_score=float(np.mean([mean_tfidf[i] for i in top_indices[:5]])),
                    user_id=user_id
                )
                
                clusters.append(cluster)
            
            # Save clusters to Firestore
            await self._save_topic_clusters(clusters)
            
            print(f"✅ Created {len(clusters)} topic clusters")
            return clusters
            
        except Exception as e:
            print(f"❌ Topic clustering error: {str(e)}")
            return []
    
    async def _save_topic_clusters(self, clusters: List[TopicCluster]):
        """Save topic clusters to Firestore"""
        if not self.firestore_client or not clusters:
            return
        
        try:
            batch = self.firestore_client.batch()
            
            for cluster in clusters:
                doc_ref = self.firestore_client.collection('topic_clusters').document(cluster.id)
                batch.set(doc_ref, cluster.dict())
            
            batch.commit()
            print(f"💾 Saved {len(clusters)} topic clusters to Firestore")
            
        except Exception as e:
            print(f"❌ Error saving topic clusters: {str(e)}")
    
    async def query_knowledge_graph(
        self,
        query: KnowledgeGraphQuery,
        user_id: str
    ) -> Dict[str, Any]:
        """Query the knowledge graph with advanced filtering"""
        
        if not self.firestore_client:
            return {"entities": [], "relations": [], "clusters": []}
        
        try:
            results = {
                "entities": [],
                "relations": [],
                "clusters": [],
                "stats": {}
            }
            
            # Query entities
            if query.query_type in ["entity_search", "all"]:
                entities = await self._query_entities(query, user_id)
                results["entities"] = [entity.dict() for entity in entities]
            
            # Query relations
            if query.query_type in ["relation_search", "all"]:
                relations = await self._query_relations(query, user_id)
                results["relations"] = [relation.dict() for relation in relations]
            
            # Query clusters
            if query.include_clusters:
                clusters = await self._query_clusters(query, user_id)
                results["clusters"] = [cluster.dict() for cluster in clusters]
            
            # Calculate stats
            if query.include_metrics:
                results["stats"] = await self._calculate_graph_stats(user_id)
            
            return results
            
        except Exception as e:
            print(f"❌ Knowledge graph query error: {str(e)}")
            return {"entities": [], "relations": [], "clusters": []}
    
    async def _query_entities(
        self,
        query: KnowledgeGraphQuery,
        user_id: str
    ) -> List[EnhancedEntity]:
        """Query entities with filtering"""
        
        entities_ref = self.firestore_client.collection('enhanced_entities')
        base_query = entities_ref.where('user_id', '==', user_id)
        
        # Apply filters
        if query.entity_types:
            type_values = [t.value for t in query.entity_types]
            base_query = base_query.where('type', 'in', type_values)
        
        if query.min_confidence > 0:
            base_query = base_query.where('confidence', '>=', query.min_confidence)
        
        # Execute query
        docs = base_query.limit(query.max_results).stream()
        
        entities = []
        for doc in docs:
            try:
                entity_data = doc.to_dict()
                entity = EnhancedEntity(**entity_data)
                
                # Text search filtering
                if query.search_terms:
                    entity_text = f"{entity.name} {entity.description} {' '.join(entity.aliases)}"
                    if not any(term.lower() in entity_text.lower() for term in query.search_terms):
                        continue
                
                entities.append(entity)
                
            except Exception as e:
                print(f"⚠️ Error loading entity {doc.id}: {str(e)}")
                continue
        
        return entities
    
    async def _query_relations(
        self,
        query: KnowledgeGraphQuery,
        user_id: str
    ) -> List[EnhancedRelation]:
        """Query relations with filtering"""
        
        relations_ref = self.firestore_client.collection('enhanced_relations')
        base_query = relations_ref.where('user_id', '==', user_id)
        
        # Apply filters
        if query.relation_types:
            type_values = [t.value for t in query.relation_types]
            base_query = base_query.where('relation_type', 'in', type_values)
        
        if query.min_confidence > 0:
            base_query = base_query.where('confidence', '>=', query.min_confidence)
        
        # Execute query
        docs = base_query.limit(query.max_results).stream()
        
        relations = []
        for doc in docs:
            try:
                relation_data = doc.to_dict()
                relation = EnhancedRelation(**relation_data)
                relations.append(relation)
                
            except Exception as e:
                print(f"⚠️ Error loading relation {doc.id}: {str(e)}")
                continue
        
        return relations
    
    async def _query_clusters(
        self,
        query: KnowledgeGraphQuery,
        user_id: str
    ) -> List[TopicCluster]:
        """Query topic clusters"""
        
        clusters_ref = self.firestore_client.collection('topic_clusters')
        base_query = clusters_ref.where('user_id', '==', user_id)
        
        docs = base_query.limit(20).stream()
        
        clusters = []
        for doc in docs:
            try:
                cluster_data = doc.to_dict()
                cluster = TopicCluster(**cluster_data)
                clusters.append(cluster)
                
            except Exception as e:
                print(f"⚠️ Error loading cluster {doc.id}: {str(e)}")
                continue
        
        return clusters
    
    async def _calculate_graph_stats(self, user_id: str) -> KnowledgeGraphStats:
        """Calculate knowledge graph statistics"""
        
        stats = KnowledgeGraphStats()
        
        try:
            # Count entities
            entities_ref = self.firestore_client.collection('enhanced_entities')
            entity_count = len(list(entities_ref.where('user_id', '==', user_id).limit(1000).stream()))
            stats.total_entities = entity_count
            
            # Count relations
            relations_ref = self.firestore_client.collection('enhanced_relations')
            relation_count = len(list(relations_ref.where('user_id', '==', user_id).limit(1000).stream()))
            stats.total_relations = relation_count
            
            # Count clusters
            clusters_ref = self.firestore_client.collection('topic_clusters')
            cluster_count = len(list(clusters_ref.where('user_id', '==', user_id).limit(100).stream()))
            stats.total_clusters = cluster_count
            
            # Calculate basic metrics
            if stats.total_entities > 0:
                stats.average_entity_connections = stats.total_relations / stats.total_entities * 2
                stats.graph_density = stats.total_relations / (stats.total_entities * (stats.total_entities - 1) / 2) if stats.total_entities > 1 else 0
            
        except Exception as e:
            print(f"❌ Error calculating graph stats: {str(e)}")
        
        return stats

# Global service instance
enhanced_knowledge_graph_service = EnhancedKnowledgeGraphService()