import os
import json

def cleanup_tags(repo, exclude_shas, dry_run):
    # Check for the presence of list.manifest.json file in the tags
    for tag in repo.tags():
        manifest_path = os.path.join(repo.working_dir, 'list.manifest.json')
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as manifest_file:
                manifest_data = json.load(manifest_file)
                for sha in manifest_data:
                    if sha not in exclude_shas:
                        # Remove the SHA from the exclude list
                        exclude_shas.remove(sha)
                        # Remove the list.manifest.json file
                        os.remove(manifest_path)
                        # Select the correct SHA from the manifest file
                        for sha in manifest_data:
                            if sha not in exclude_shas:
                                # Remove the tag
                                if not dry_run:
                                    repo.delete_tag(tag, sha)
                                # Print the removed tag
                                print(f"Removed tag {tag} with SHA {sha}")
                                break
                        break

def main():
    repo = Repo()
    exclude_shas = []
    dry_run = False
    cleanup_tags(repo, exclude_shas, dry_run)

if __name__ == "__main__":
    main()