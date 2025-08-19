import logging
import json
import hashlib
import time
import os
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from datetime import datetime
import numpy as np

from ..models.database import File, FAISSIndexMetadata, FileStatus
from .essentia_analyzer import essentia_analyzer, safe_json_serialize

# FAISS for efficient vector similarity search
try:
    import faiss
    FAISS_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("FAISS is available for vector indexing")
except ImportError:
    FAISS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("FAISS not available. Install with: pip install faiss-cpu or faiss-gpu")

class FAISSService:
    """
    Service for managing FAISS vector indexing and similarity search with database integration.
    
    Handles vector storage, index building, similarity search, and persistence.
    """
    
    def __init__(self, index_name: str = None):
        # Get index name from configuration if not provided
        if index_name is None:
            try:
                from ..core.config_loader import config_loader
                app_config = config_loader.get_app_settings()
                self.index_name = app_config.get("faiss", {}).get("index_name", "music_library")
            except Exception:
                self.index_name = "music_library"
        else:
            self.index_name = index_name
            
        self.faiss_index = None
        self.vector_dimension = None
        self.track_paths = []
        self.index_metadata = None
        
    def build_index_from_database(self, db: Session, include_tensorflow: bool = True, 
                                include_faiss: bool = True, force_rebuild: bool = False) -> Dict[str, Any]:
        """
        Build FAISS index from analyzed tracks in database.
        
        Args:
            db: Database session
            include_tensorflow: Whether to include MusiCNN features
            force_rebuild: Whether to force rebuild existing index
            
        Returns:
            Build results
        """
        if not FAISS_AVAILABLE:
            return {"error": "FAISS not available"}
        
        try:
            # Check if FAISS is enabled in configuration
            try:
                from ..core.analysis_config import analysis_config_loader
                config = analysis_config_loader.get_config()
                if not config.algorithms.enable_faiss:
                    return {"error": "FAISS indexing is disabled in configuration"}
            except Exception as e:
                logger.warning(f"Failed to check FAISS configuration: {e}")
                # Continue with default behavior if config check fails
            
            start_time = time.time()
            
            # Load vector analysis configuration
            try:
                from ..core.analysis_config import analysis_config_loader
                config = analysis_config_loader.get_config()
                # Use default values since vector_analysis config is not in the dataclass
                index_type_config = "IVFFlat"
                nlist_config = 100
                normalize_enabled = True
                normalize_method = "l2"
            except Exception as e:
                logger.warning(f"Failed to load vector analysis config: {e}, using defaults")
                index_type_config = "IVFFlat"
                nlist_config = 100
                normalize_enabled = True
                normalize_method = "l2"
            
            # Check if index already exists
            existing_metadata = db.query(FAISSIndexMetadata).filter(
                FAISSIndexMetadata.index_name == self.index_name,
                FAISSIndexMetadata.is_active == True
            ).first()
            
            if existing_metadata and not force_rebuild:
                logger.info(f"Index {self.index_name} already exists, loading...")
                return self.load_index_from_database(db)
            
            # Get all analyzed files (both complete and essentia_complete)
            # Note: AudioAnalysis table has been replaced with independent analyzer tables
            # This method needs to be updated to use the new schema
            analyzed_files = db.query(File).filter(
                File.analysis_status.in_(["complete", "essentia_complete"]),
                File.is_active == True
            ).all()
            
            if not analyzed_files:
                return {"error": "No analyzed files found in database"}
            
            logger.info(f"Building index for {len(analyzed_files)} analyzed files")
            
            # Extract feature vectors
            vectors = []
            track_paths = []
            vector_records = []
            
            for file_record in analyzed_files:
                try:
                    # Extract feature vector
                    vector = essentia_analyzer.extract_feature_vector(
                        file_record.file_path, 
                        include_tensorflow=include_tensorflow
                    )
                    
                    # Apply normalization if enabled
                    if normalize_enabled:
                        if normalize_method == "l2":
                            norm = np.linalg.norm(vector)
                            if norm > 0:
                                vector = vector / norm
                        elif normalize_method == "l1":
                            norm = np.sum(np.abs(vector))
                            if norm > 0:
                                vector = vector / norm
                    
                    vectors.append(vector)
                    track_paths.append(file_record.file_path)
                    
                    # Create vector record
                    vector_hash = self._compute_vector_hash(vector)
                    vector_record = VectorIndex(
                        file_id=file_record.id,
                        vector_dimension=len(vector),
                        vector_data=json.dumps(vector.tolist()),
                        vector_hash=vector_hash,
                        includes_tensorflow=include_tensorflow,
                        is_normalized=normalize_enabled
                    )
                    vector_records.append(vector_record)
                    
                except Exception as e:
                    logger.warning(f"Failed to extract vector for {file_record.file_path}: {e}")
                    continue
            
            if not vectors:
                return {"error": "No valid vectors extracted"}
            
            # Build FAISS index
            self.vector_dimension = len(vectors[0])
            self.track_paths = track_paths
            
            # Choose index type based on configuration and dataset size
            num_vectors = len(vectors)
            if index_type_config == "IndexFlatIP" or num_vectors < 1000:
                index_type = "IndexFlatIP"
                self.faiss_index = faiss.IndexFlatIP(self.vector_dimension)
            elif index_type_config == "IndexIVFFlat" or num_vectors < 10000:
                index_type = "IndexIVFFlat"
                nlist = min(nlist_config, num_vectors // 10)
                quantizer = faiss.IndexFlatIP(self.vector_dimension)
                self.faiss_index = faiss.IndexIVFFlat(quantizer, self.vector_dimension, nlist)
            else:
                index_type = "IndexIVFPQ"
                nlist = min(nlist_config, num_vectors // 10)
                m = 8
                bits = 8
                quantizer = faiss.IndexFlatIP(self.vector_dimension)
                self.faiss_index = faiss.IndexIVFPQ(quantizer, self.vector_dimension, nlist, m, bits)
            
            # Add vectors to index
            vectors_array = np.array(vectors, dtype=np.float32)
            self.faiss_index.add(vectors_array)
            
            # Store vector records in database
            for i, vector_record in enumerate(vector_records):
                vector_record.index_type = index_type
                vector_record.index_position = i
                db.add(vector_record)
            
            # Create or update index metadata
            build_time = time.time() - start_time
            
            if existing_metadata:
                existing_metadata.total_vectors = num_vectors
                existing_metadata.index_type = index_type
                existing_metadata.vector_dimension = self.vector_dimension
                existing_metadata.build_time = build_time
                existing_metadata.last_rebuild = datetime.utcnow()
                existing_metadata.updated_at = datetime.utcnow()
            else:
                index_metadata = FAISSIndexMetadata(
                    index_name=self.index_name,
                    index_type=index_type,
                    vector_dimension=self.vector_dimension,
                    total_vectors=num_vectors,
                    build_time=build_time,
                    is_active=True
                )
                db.add(index_metadata)
            
            db.commit()
            
            # Save index to disk
            self.save_index_to_disk()
            
            logger.info(f"FAISS index built successfully: {num_vectors} vectors, {build_time:.2f}s")
            
            return {
                "success": True,
                "total_vectors": num_vectors,
                "vector_dimension": self.vector_dimension,
                "index_type": index_type,
                "build_time": build_time
            }
            
        except Exception as e:
            logger.error(f"Failed to build FAISS index: {e}")
            db.rollback()
            return {"error": str(e)}
    
    def load_index_from_database(self, db: Session) -> Dict[str, Any]:
        """
        Load FAISS index from database.
        
        Args:
            db: Database session
            
        Returns:
            Load results
        """
        if not FAISS_AVAILABLE:
            return {"error": "FAISS not available"}
        
        try:
            # Get index metadata
            metadata = db.query(FAISSIndexMetadata).filter(
                FAISSIndexMetadata.index_name == self.index_name,
                FAISSIndexMetadata.is_active == True
            ).first()
            
            if not metadata:
                return {"error": f"Index {self.index_name} not found in database"}
            
            # Load index from disk if exists
            index_file = f"{self.index_name}.faiss"
            if os.path.exists(index_file):
                self.faiss_index = faiss.read_index(index_file)
                self.vector_dimension = metadata.vector_dimension
                
                # Load track paths
                vector_records = db.query(VectorIndex).filter(
                    VectorIndex.index_type == metadata.index_type
                ).order_by(VectorIndex.index_position).all()
                
                self.track_paths = [record.file.file_path for record in vector_records]
                
                logger.info(f"Loaded FAISS index: {len(self.track_paths)} vectors")
                return {
                    "success": True,
                    "total_vectors": len(self.track_paths),
                    "vector_dimension": self.vector_dimension,
                    "index_type": metadata.index_type
                }
            else:
                return {"error": f"Index file {index_file} not found"}
                
        except Exception as e:
            logger.error(f"Failed to load FAISS index: {e}")
            return {"error": str(e)}
    
    def add_track_to_index(self, db: Session, file_path: str, include_tensorflow: bool = True) -> Dict[str, Any]:
        """
        Add a single track to the FAISS index.
        
        Args:
            db: Database session
            file_path: Path to audio file
            include_tensorflow: Whether to include MusiCNN features
            
        Returns:
            Add results
        """
        if not FAISS_AVAILABLE:
            return {"error": "FAISS not available"}
        
        try:
            # Check if FAISS is enabled in configuration
            try:
                from ..core.analysis_config import analysis_config_loader
                config = analysis_config_loader.get_config()
                if not config.algorithms.enable_faiss:
                    return {"error": "FAISS indexing is disabled in configuration"}
            except Exception as e:
                logger.warning(f"Failed to check FAISS configuration: {e}")
                # Continue with default behavior if config check fails
            
            # Get file record
            file_record = db.query(File).filter(File.file_path == file_path).first()
            if not file_record:
                return {"error": f"File not found in database: {file_path}"}
            
            # Check if already indexed
            existing_vector = db.query(VectorIndex).filter(
                VectorIndex.file_id == file_record.id
            ).first()
            
            if existing_vector:
                logger.info(f"Track {file_path} already indexed")
                return {"success": True, "already_indexed": True}
            
            # Extract feature vector
            vector = essentia_analyzer.extract_feature_vector(file_path, include_tensorflow)
            
            # Add to FAISS index if it exists
            if self.faiss_index is not None:
                vector_array = vector.reshape(1, -1).astype(np.float32)
                self.faiss_index.add(vector_array)
                index_position = len(self.track_paths)
                self.track_paths.append(file_path)
            else:
                index_position = None
            
            # Store in database
            vector_hash = self._compute_vector_hash(vector)
            vector_record = VectorIndex(
                file_id=file_record.id,
                vector_dimension=len(vector),
                vector_data=json.dumps(vector.tolist()),
                vector_hash=vector_hash,
                index_position=index_position,
                includes_tensorflow=include_tensorflow,
                is_normalized=True
            )
            
            db.add(vector_record)
            
            # Update file status to FAISS_ANALYZED
            file_record.status = FileStatus.FAISS_ANALYZED
            
            db.commit()
            
            logger.info(f"Added track {file_path} to FAISS index")
            return {"success": True, "vector_dimension": len(vector)}
            
        except Exception as e:
            logger.error(f"Failed to add track to index: {e}")
            db.rollback()
            return {"error": str(e)}
    
    def find_similar_tracks(self, db: Session, query_path: str, top_n: int = 5) -> List[Tuple[str, float]]:
        """
        Find similar tracks using FAISS index.
        
        Args:
            db: Database session
            query_path: Path to query audio file
            top_n: Number of similar tracks to return
            
        Returns:
            List of (track_path, similarity_score) tuples
        """
        if not FAISS_AVAILABLE or self.faiss_index is None:
            return self._fallback_similarity_search(db, query_path, top_n)
        
        try:
            # Extract query vector
            query_vector = essentia_analyzer.extract_feature_vector(query_path, include_tensorflow=True)
            
            # Search FAISS index
            query_array = query_vector.reshape(1, -1).astype(np.float32)
            similarities, indices = self.faiss_index.search(query_array, min(top_n, len(self.track_paths)))
            
            # Convert to results
            results = []
            for idx, sim in zip(indices[0], similarities[0]):
                if idx != -1 and idx < len(self.track_paths):
                    results.append((self.track_paths[idx], float(sim)))
            
            return results
            
        except Exception as e:
            logger.error(f"FAISS search failed: {e}, falling back to basic search")
            return self._fallback_similarity_search(db, query_path, top_n)
    
    def find_similar_by_vector(self, db: Session, query_vector: np.ndarray, top_n: int = 5) -> List[Tuple[str, float]]:
        """
        Find similar tracks using a pre-computed feature vector.
        
        Args:
            db: Database session
            query_vector: Pre-computed feature vector
            top_n: Number of similar tracks to return
            
        Returns:
            List of (track_path, similarity_score) tuples
        """
        if not FAISS_AVAILABLE or self.faiss_index is None:
            return self._fallback_vector_search(db, query_vector, top_n)
        
        try:
            # Search FAISS index
            query_array = query_vector.reshape(1, -1).astype(np.float32)
            similarities, indices = self.faiss_index.search(query_array, min(top_n, len(self.track_paths)))
            
            # Convert to results
            results = []
            for idx, sim in zip(indices[0], similarities[0]):
                if idx != -1 and idx < len(self.track_paths):
                    results.append((self.track_paths[idx], float(sim)))
            
            return results
            
        except Exception as e:
            logger.error(f"FAISS vector search failed: {e}, falling back to basic search")
            return self._fallback_vector_search(db, query_vector, top_n)
    
    def get_index_statistics(self, db: Session) -> Dict[str, Any]:
        """
        Get statistics about the FAISS index.
        
        Args:
            db: Database session
            
        Returns:
            Index statistics
        """
        try:
            # Get metadata
            metadata = db.query(FAISSIndexMetadata).filter(
                FAISSIndexMetadata.index_name == self.index_name,
                FAISSIndexMetadata.is_active == True
            ).first()
            
            if not metadata:
                return {"error": f"Index {self.index_name} not found"}
            
            # Get vector statistics
            total_vectors = db.query(VectorIndex).count()
            indexed_vectors = db.query(VectorIndex).filter(
                VectorIndex.index_position.isnot(None)
            ).count()
            
            # Get file statistics
            total_files = db.query(File).count()
            analyzed_files = db.query(File).filter(File.analysis_status == "complete").count()
            indexed_files = db.query(File).join(VectorIndex).count()
            
            stats = {
                "index_name": metadata.index_name,
                "index_type": metadata.index_type,
                "vector_dimension": metadata.vector_dimension,
                "total_vectors": total_vectors,
                "indexed_vectors": indexed_vectors,
                "total_files": total_files,
                "analyzed_files": analyzed_files,
                "indexed_files": indexed_files,
                "index_coverage": (indexed_files / analyzed_files * 100) if analyzed_files > 0 else 0,
                "build_time": metadata.build_time,
                "last_rebuild": metadata.last_rebuild.isoformat() if metadata.last_rebuild else None,
                "faiss_available": FAISS_AVAILABLE,
                "index_loaded": self.faiss_index is not None
            }
            
            if self.faiss_index is not None:
                stats["faiss_index_size"] = self.faiss_index.ntotal
                stats["faiss_index_type"] = type(self.faiss_index).__name__
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get index statistics: {e}")
            return {"error": str(e)}
    
    def index_exists(self) -> bool:
        """
        Check if FAISS index exists and is loaded.
        
        Returns:
            True if index exists and is loaded, False otherwise
        """
        try:
            # Check if FAISS index is loaded in memory
            if self.faiss_index is not None:
                return True
            
            # Check if index exists in database
            from ..models.database import get_db_session, FAISSIndexMetadata
            db = get_db_session()
            try:
                existing_metadata = db.query(FAISSIndexMetadata).filter(
                    FAISSIndexMetadata.index_name == self.index_name,
                    FAISSIndexMetadata.is_active == True
                ).first()
                return existing_metadata is not None
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Failed to check if index exists: {e}")
            return False
    
    def save_index_to_disk(self, base_path: str = ".") -> bool:
        """
        Save FAISS index to disk.
        
        Args:
            base_path: Base path for saving index files
            
        Returns:
            True if successful
        """
        if not FAISS_AVAILABLE or self.faiss_index is None:
            return False
        
        try:
            # Save FAISS index
            faiss_path = os.path.join(base_path, f"{self.index_name}.faiss")
            faiss.write_index(self.faiss_index, faiss_path)
            
            # Save metadata
            metadata_path = os.path.join(base_path, f"{self.index_name}.json")
            metadata = {
                'track_paths': self.track_paths,
                'vector_dimension': self.vector_dimension,
                'index_name': self.index_name
            }
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Saved FAISS index to {faiss_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save FAISS index: {e}")
            return False
    
    def _compute_vector_hash(self, vector: np.ndarray) -> str:
        """Compute hash of vector for change detection"""
        try:
            from ..core.analysis_config import analysis_config_loader
            config = analysis_config_loader.get_config()
            # Use default hash algorithm since vector_analysis config is not in the dataclass
            hash_algorithm = "md5"
        except Exception:
            hash_algorithm = "md5"
        
        if hash_algorithm == "md5":
            return hashlib.md5(vector.tobytes()).hexdigest()
        elif hash_algorithm == "sha1":
            return hashlib.sha1(vector.tobytes()).hexdigest()
        elif hash_algorithm == "sha256":
            return hashlib.sha256(vector.tobytes()).hexdigest()
        else:
            # Default to MD5
            return hashlib.md5(vector.tobytes()).hexdigest()
    
    def _fallback_similarity_search(self, db: Session, query_path: str, top_n: int) -> List[Tuple[str, float]]:
        """Fallback similarity search using database"""
        try:
            # Get query vector
            query_vector = essentia_analyzer.extract_feature_vector(query_path, include_tensorflow=True)
            
            # Get all indexed vectors from database
            vector_records = db.query(VectorIndex).all()
            
            similarities = []
            for record in vector_records:
                try:
                    vector_data = json.loads(record.vector_data)
                    vector = np.array(vector_data, dtype=np.float32)
                    
                    # Compute cosine similarity
                    sim = np.dot(query_vector, vector) / (np.linalg.norm(query_vector) * np.linalg.norm(vector))
                    similarities.append((record.file.file_path, float(sim)))
                    
                except Exception as e:
                    logger.warning(f"Failed to compute similarity for {record.file.file_path}: {e}")
                    continue
            
            # Sort by similarity and return top N
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:top_n]
            
        except Exception as e:
            logger.error(f"Fallback similarity search failed: {e}")
            return []
    
    def _fallback_vector_search(self, db: Session, query_vector: np.ndarray, top_n: int) -> List[Tuple[str, float]]:
        """Fallback vector search using database"""
        try:
            # Get all indexed vectors from database
            vector_records = db.query(VectorIndex).all()
            
            similarities = []
            for record in vector_records:
                try:
                    vector_data = json.loads(record.vector_data)
                    vector = np.array(vector_data, dtype=np.float32)
                    
                    # Compute cosine similarity
                    sim = np.dot(query_vector, vector) / (np.linalg.norm(query_vector) * np.linalg.norm(vector))
                    similarities.append((record.file.file_path, float(sim)))
                    
                except Exception as e:
                    logger.warning(f"Failed to compute similarity for {record.file.file_path}: {e}")
                    continue
            
            # Sort by similarity and return top N
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:top_n]
            
        except Exception as e:
            logger.error(f"Fallback vector search failed: {e}")
            return []

# Global instance
faiss_service = FAISSService()
