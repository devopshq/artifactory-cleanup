import logging
import re
from collections import defaultdict
from typing import List, Dict, Set

from artifactory_cleanup.rules.base import Rule, ArtifactsList

logger = logging.getLogger(__name__)


class DockerRule(Rule):
    """
    Rule for Docker repositories.
    Handles both regular Docker images and multi-arch buildx images.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.manifest_references = defaultdict(set)  # Track which manifests reference which layers
        self.protected_manifests = set()  # Manifests that should not be deleted

    def _is_manifest_list(self, artifact) -> bool:
        """Check if artifact is a manifest list (multi-arch image)."""
        return artifact.name == "list.manifest.json"

    def _parse_manifest_list(self, artifact) -> Set[str]:
        """Parse manifest list and return set of referenced SHA digests."""
        try:
            content = self.artifactory.download(artifact.path)
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            
            import json
            manifest_data = json.loads(content)
            
            shas = set()
            # Handle Docker manifest list format
            if 'manifests' in manifest_data:
                for manifest in manifest_data['manifests']:
                    if 'digest' in manifest:
                        # Extract SHA from digest (format: sha256:xxxxx)
                        digest = manifest['digest']
                        if ':' in digest:
                            sha = digest.split(':', 1)[1]
                            shas.add(sha)
            
            return shas
        except Exception as e:
            logger.warning(f"Failed to parse manifest list {artifact.path}: {e}")
            return set()

    def _collect_manifest_references(self, artifacts: ArtifactsList):
        """Collect all manifest list references before filtering."""
        self.manifest_references.clear()
        self.protected_manifests.clear()
        
        for artifact in artifacts:
            if self._is_manifest_list(artifact):
                # Get parent path (tag directory)
                tag_path = artifact.path.rsplit('/', 1)[0]
                referenced_shas = self._parse_manifest_list(artifact)
                
                if referenced_shas:
                    self.manifest_references[tag_path].update(referenced_shas)
                    logger.debug(f"Manifest list at {tag_path} references SHAs: {referenced_shas}")

    def _is_protected_by_manifest(self, artifact, protected_tags: Set[str]) -> bool:
        """Check if artifact SHA is referenced by a protected manifest list."""
        # Extract SHA from artifact path
        # Typical path: repo/image/tag/sha256__<sha>/manifest.json
        path_parts = artifact.path.split('/')
        
        for part in path_parts:
            if part.startswith('sha256__'):
                sha = part.replace('sha256__', '')
                
                # Check if this SHA is referenced by any protected tag's manifest list
                for tag_path in protected_tags:
                    if sha in self.manifest_references.get(tag_path, set()):
                        logger.debug(f"Artifact {artifact.path} protected by manifest list at {tag_path}")
                        return True
        
        return False

    def filter(self, artifacts: ArtifactsList) -> ArtifactsList:
        """
        Filter Docker artifacts, handling multi-arch manifest lists.
        """
        # First pass: collect all manifest list references
        self._collect_manifest_references(artifacts)
        
        # Identify protected tags (tags we want to keep)
        protected_tag_paths = set()
        for artifact in artifacts:
            if hasattr(artifact, 'keep') and artifact.keep:
                # Get the tag directory path
                if '/' in artifact.path:
                    tag_path = artifact.path.rsplit('/', 1)[0]
                    protected_tag_paths.add(tag_path)
        
        # Second pass: filter artifacts
        result = ArtifactsList()
        
        for artifact in artifacts:
            # Keep artifacts explicitly marked to keep
            if hasattr(artifact, 'keep') and artifact.keep:
                result.append(artifact)
                continue
            
            # Check if this is a manifest list
            if self._is_manifest_list(artifact):
                tag_path = artifact.path.rsplit('/', 1)[0]
                if tag_path in protected_tag_paths:
                    # Keep manifest list if tag is protected
                    result.append(artifact)
                    continue
            
            # Check if artifact is referenced by a protected manifest list
            if self._is_protected_by_manifest(artifact, protected_tag_paths):
                result.append(artifact)
                continue
            
            # Apply standard filtering
            result.append(artifact)
        
        return result

    def delete(self, artifacts: ArtifactsList) -> int:
        """
        Delete Docker artifacts, handling manifest lists properly.
        """
        # Collect manifest references to understand dependencies
        self._collect_manifest_references(artifacts)
        
        # Group artifacts by tag to handle manifest lists with their referenced layers
        tag_groups = defaultdict(list)
        standalone_artifacts = []
        
        for artifact in artifacts:
            if '/' in artifact.path:
                # Try to extract tag path
                parts = artifact.path.split('/')
                # Look for tag directory (usually before sha256__ or manifest files)
                tag_path = None
                for i, part in enumerate(parts):
                    if part.startswith('sha256__') or part in ['manifest.json', 'list.manifest.json']:
                        if i > 0:
                            tag_path = '/'.join(parts[:i])
                            break
                
                if tag_path:
                    tag_groups[tag_path].append(artifact)
                else:
                    standalone_artifacts.append(artifact)
            else:
                standalone_artifacts.append(artifact)
        
        deleted_count = 0
        
        # Delete tag groups (manifest lists with their layers)
        for tag_path, tag_artifacts in tag_groups.items():
            # Check if this tag has a manifest list
            has_manifest_list = any(self._is_manifest_list(a) for a in tag_artifacts)
            
            if has_manifest_list:
                # For multi-arch images, delete all artifacts in the tag together
                logger.info(f"Deleting multi-arch tag: {tag_path}")
                for artifact in tag_artifacts:
                    try:
                        self.artifactory.delete(artifact.path)
                        deleted_count += 1
                        logger.debug(f"Deleted {artifact.path}")
                    except Exception as e:
                        logger.error(f"Failed to delete {artifact.path}: {e}")
            else:
                # Regular tag, delete artifacts individually
                for artifact in tag_artifacts:
                    try:
                        self.artifactory.delete(artifact.path)
                        deleted_count += 1
                        logger.debug(f"Deleted {artifact.path}")
                    except Exception as e:
                        logger.error(f"Failed to delete {artifact.path}: {e}")
        
        # Delete standalone artifacts
        for artifact in standalone_artifacts:
            try:
                self.artifactory.delete(artifact.path)
                deleted_count += 1
                logger.debug(f"Deleted {artifact.path}")
            except Exception as e:
                logger.error(f"Failed to delete {artifact.path}: {e}")
        
        return deleted_count
