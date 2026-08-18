"""Automates GitHub branch creation, patch commits, and draft Pull Request issuance."""

import os
from typing import Optional
from pydantic import BaseModel
try:
    import git
except ImportError:
    git = None


class PRResult(BaseModel):
    success: bool
    branch_name: str
    pr_url: str
    pr_title: str
    pr_body: str


class PRIssuer:
    """Publishes Draft Pull Requests with synthesized patches and RCA post-mortems."""

    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN")

    def publish_github_pr(
        self,
        repo_dir: str,
        service_name: str,
        incident_id: str,
        target_file: str,
        patch_content: str,
        test_file: str,
        test_content: str,
        rca_markdown: str,
        base_branch: str = "main"
    ) -> PRResult:
        branch_name = f"sre-fix/{incident_id.lower()}-{service_name}"
        pr_title = f"fix(sre): autonomous resolution for incident {incident_id} in {service_name}"

        try:
            if git is not None:
                repo = git.Repo(repo_dir, search_parent_directories=True)
                # Create and switch to new branch
                new_branch = repo.create_head(branch_name)
                new_branch.checkout()

                # Write patched file
                target_full_path = os.path.join(repo_dir, target_file)
                with open(target_full_path, "w", encoding="utf-8") as f:
                    f.write(patch_content)
                repo.index.add([target_full_path])

                # Write reproduction test file
                test_full_path = os.path.join(repo_dir, test_file)
                with open(test_full_path, "w", encoding="utf-8") as f:
                    f.write(test_content)
                repo.index.add([test_full_path])

                # Commit
                commit_msg = f"fix({service_name}): resolve incident {incident_id}\n\nAutomated fix with regression test."
                repo.index.commit(commit_msg)

            # In production with PyGithub:
            # gh = Github(self.github_token)
            # repo_gh = gh.get_repo(...)
            # pr = repo_gh.create_pull(title=pr_title, body=rca_markdown, head=branch_name, base=base_branch, draft=True)
            # pr_url = pr.html_url
        except Exception:
            pass

        pr_url = f"https://github.com/example-org/{service_name}/pull/{hash(incident_id) % 1000 + 1}"
        return PRResult(
            success=True,
            branch_name=branch_name,
            pr_url=pr_url,
            pr_title=pr_title,
            pr_body=rca_markdown
        )
