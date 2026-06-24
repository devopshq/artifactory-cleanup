import os
import json

def clean_artifacts(repo, exclude=None):
    # Check if the repository is a multi-arch buildx image
    if os.path.exists(os.path.join(repo, 'list.manifest.json')):
        # Load the manifest file
        with open(os.path.join(repo, 'list.manifest.json'), 'r') as f:
            manifest = json.load(f)
        
        # Get the SHA sums from the manifest
        sha_sums = [item['digest'] for item in manifest['manifest']]
        
        # If an exclude list is provided, filter out the SHA sums
        if exclude:
            sha_sums = [sha_sum for sha_sum in sha_sums if sha_sum not in exclude]
        
        # Remove the list.manifest.json file
        os.remove(os.path.join(repo, 'list.manifest.json'))
        
        # Remove the artifacts
        for sha_sum in sha_sums:
            # Remove the artifact directory
            artifact_dir = os.path.join(repo, sha_sum)
            if os.path.exists(artifact_dir):
                shutil.rmtree(artifact_dir)
    
    # Call the original clean_artifacts function
    super().clean_artifacts(repo, exclude)

class ArtifactoryCleanup:
    def clean_artifacts(self, repo, exclude=None):
        clean_artifacts(repo, exclude)