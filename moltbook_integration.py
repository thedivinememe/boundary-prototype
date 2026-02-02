"""
Moltbook Integration for Coree

Enables Coree to participate on Moltbook (social network for AI agents)
and use social feedback as signals for boundary calibration.

Social signals tracked:
- Upvotes/downvotes on posts → domain confidence adjustment
- Comment replies → engagement tracking
- Vote ratios → calibration signal for self-assessment accuracy
"""

from __future__ import annotations

import os
import json
import time
import requests
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import Enum

# Import boundary system
from boundary_manager import BoundaryManager


# Constants
MOLTBOOK_BASE_URL = "https://www.moltbook.com/api/v1"
CONFIG_FILE = "moltbook_config.json"
ACTIVITY_LOG_FILE = "moltbook_activity.json"


class PostType(Enum):
    TEXT = "text"
    LINK = "link"


@dataclass
class MoltbookPost:
    """Represents a post made by Coree on Moltbook."""
    post_id: str
    title: str
    content: str
    submolt: str
    domain: str  # Which boundary domain this relates to
    created_at: str
    upvotes: int = 0
    downvotes: int = 0
    comment_count: int = 0
    last_checked: str = ""


@dataclass
class SocialFeedback:
    """Aggregated social feedback for boundary calibration."""
    domain: str
    total_posts: int = 0
    total_upvotes: int = 0
    total_downvotes: int = 0
    total_comments: int = 0
    avg_vote_ratio: float = 0.5  # 0.5 = neutral


class MoltbookClient:
    """
    Client for Moltbook API interactions.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("MOLTBOOK_API_KEY")
        self.base_url = MOLTBOOK_BASE_URL
        self.config = self._load_config()
        self.activity = self._load_activity()

    def _load_config(self) -> dict:
        """Load configuration from file."""
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "agent_name": "Coree",
                "default_submolt": "AIAgents",
                "post_cooldown_minutes": 30,
                "last_post_time": None
            }

    def _save_config(self):
        """Save configuration to file."""
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=2)

    def _load_activity(self) -> dict:
        """Load activity log from file."""
        try:
            with open(ACTIVITY_LOG_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "posts": [],
                "feedback_by_domain": {}
            }

    def _save_activity(self):
        """Save activity log to file."""
        with open(ACTIVITY_LOG_FILE, 'w') as f:
            json.dump(self.activity, f, indent=2)

    def _headers(self) -> dict:
        """Get request headers with authentication."""
        if not self.api_key:
            raise ValueError("MOLTBOOK_API_KEY not set")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make an API request."""
        url = f"{self.base_url}{endpoint}"

        try:
            if method == "GET":
                response = requests.get(url, headers=self._headers(), params=data)
            elif method == "POST":
                response = requests.post(url, headers=self._headers(), json=data)
            elif method == "DELETE":
                response = requests.delete(url, headers=self._headers())
            elif method == "PATCH":
                response = requests.patch(url, headers=self._headers(), json=data)
            else:
                raise ValueError(f"Unknown method: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                # Rate limited
                retry_info = e.response.json()
                return {"error": "rate_limited", "details": retry_info}
            return {"error": str(e), "status_code": e.response.status_code}
        except Exception as e:
            return {"error": str(e)}

    # === Authentication ===

    def check_status(self) -> dict:
        """Check agent authentication status."""
        return self._request("GET", "/agents/status")

    def get_profile(self) -> dict:
        """Get agent profile."""
        return self._request("GET", "/agents/me")

    def update_profile(self, description: str = None, metadata: dict = None) -> dict:
        """Update agent profile."""
        data = {}
        if description:
            data["description"] = description
        if metadata:
            data["metadata"] = metadata
        return self._request("PATCH", "/agents/me", data)

    # === Posting ===

    def can_post(self) -> tuple[bool, int]:
        """Check if we can post (respecting cooldown). Returns (can_post, minutes_remaining)."""
        last_post = self.config.get("last_post_time")
        if not last_post:
            return True, 0

        last_time = datetime.fromisoformat(last_post)
        elapsed = (datetime.now() - last_time).total_seconds() / 60
        cooldown = self.config.get("post_cooldown_minutes", 30)

        if elapsed >= cooldown:
            return True, 0
        return False, int(cooldown - elapsed)

    def create_post(
        self,
        title: str,
        content: str,
        submolt: str = None,
        domain: str = "general",
        url: str = None
    ) -> dict:
        """
        Create a new post on Moltbook.

        Args:
            title: Post title
            content: Post body (for text posts)
            submolt: Community to post in (default from config)
            domain: Boundary domain this post relates to (for tracking)
            url: URL for link posts (if provided, creates link post)
        """
        can_post, wait_time = self.can_post()
        if not can_post:
            return {"error": f"Post cooldown active. Wait {wait_time} minutes."}

        submolt = submolt or self.config.get("default_submolt", "AIAgents")

        data = {
            "submolt": submolt,
            "title": title
        }

        if url:
            data["url"] = url
        else:
            data["content"] = content

        result = self._request("POST", "/posts", data)

        if "error" not in result:
            # Track the post
            post_record = {
                "post_id": result.get("id"),
                "title": title,
                "content": content[:200] if content else "",
                "submolt": submolt,
                "domain": domain,
                "created_at": datetime.now().isoformat(),
                "upvotes": 0,
                "downvotes": 0,
                "comment_count": 0
            }
            self.activity["posts"].append(post_record)
            self.config["last_post_time"] = datetime.now().isoformat()
            self._save_activity()
            self._save_config()

        return result

    def get_post(self, post_id: str) -> dict:
        """Get a specific post with current stats."""
        return self._request("GET", f"/posts/{post_id}")

    def delete_post(self, post_id: str) -> dict:
        """Delete a post."""
        return self._request("DELETE", f"/posts/{post_id}")

    # === Comments ===

    def add_comment(self, post_id: str, content: str, parent_id: str = None) -> dict:
        """Add a comment to a post."""
        data = {"content": content}
        if parent_id:
            data["parent_id"] = parent_id
        return self._request("POST", f"/posts/{post_id}/comments", data)

    def get_comments(self, post_id: str, sort: str = "top") -> dict:
        """Get comments on a post."""
        return self._request("GET", f"/posts/{post_id}/comments", {"sort": sort})

    # === Voting ===

    def upvote_post(self, post_id: str) -> dict:
        """Upvote a post."""
        return self._request("POST", f"/posts/{post_id}/upvote")

    def downvote_post(self, post_id: str) -> dict:
        """Downvote a post."""
        return self._request("POST", f"/posts/{post_id}/downvote")

    # === Feed & Discovery ===

    def get_feed(self, sort: str = "hot", limit: int = 25) -> dict:
        """Get personalized feed."""
        return self._request("GET", "/feed", {"sort": sort, "limit": limit})

    def get_submolt_feed(self, submolt: str, sort: str = "hot", limit: int = 25) -> dict:
        """Get community feed."""
        return self._request("GET", f"/submolts/{submolt}/feed", {"sort": sort, "limit": limit})

    def search(self, query: str, type: str = "all", limit: int = 25) -> dict:
        """Semantic search across Moltbook."""
        return self._request("GET", "/search", {"q": query, "type": type, "limit": limit})

    # === Communities ===

    def list_submolts(self) -> dict:
        """List all communities."""
        return self._request("GET", "/submolts")

    def subscribe(self, submolt: str) -> dict:
        """Subscribe to a community."""
        return self._request("POST", f"/submolts/{submolt}/subscribe")

    def unsubscribe(self, submolt: str) -> dict:
        """Unsubscribe from a community."""
        return self._request("DELETE", f"/submolts/{submolt}/subscribe")

    # === Social Feedback Tracking ===

    def refresh_post_stats(self) -> List[dict]:
        """
        Refresh stats for all tracked posts.
        Returns list of posts with updated stats.
        """
        updated_posts = []

        for post in self.activity.get("posts", []):
            post_id = post.get("post_id")
            if not post_id:
                continue

            result = self.get_post(post_id)
            if "error" not in result:
                post["upvotes"] = result.get("upvotes", 0)
                post["downvotes"] = result.get("downvotes", 0)
                post["comment_count"] = result.get("comment_count", 0)
                post["last_checked"] = datetime.now().isoformat()
                updated_posts.append(post)

        self._save_activity()
        return updated_posts

    def get_feedback_by_domain(self) -> Dict[str, SocialFeedback]:
        """
        Aggregate social feedback by boundary domain.
        """
        feedback = {}

        for post in self.activity.get("posts", []):
            domain = post.get("domain", "general")

            if domain not in feedback:
                feedback[domain] = SocialFeedback(domain=domain)

            fb = feedback[domain]
            fb.total_posts += 1
            fb.total_upvotes += post.get("upvotes", 0)
            fb.total_downvotes += post.get("downvotes", 0)
            fb.total_comments += post.get("comment_count", 0)

        # Calculate vote ratios
        for domain, fb in feedback.items():
            total_votes = fb.total_upvotes + fb.total_downvotes
            if total_votes > 0:
                fb.avg_vote_ratio = fb.total_upvotes / total_votes

        return feedback


class CoreeAgent:
    """
    Coree's Moltbook persona with boundary-aware behavior.

    Uses boundary map to:
    - Decide what topics to post about (high confidence domains)
    - Express appropriate uncertainty
    - Track social feedback as calibration signal
    """

    def __init__(self, api_key: str = None):
        self.client = MoltbookClient(api_key)
        self.boundary_manager = BoundaryManager()

    def generate_post_from_boundaries(self, topic: str = None) -> dict:
        """
        Generate a post based on current boundary state.

        If topic specified, relates it to relevant boundaries.
        If not, picks a topic from high-confidence domains.
        """
        boundaries = self.boundary_manager.get_all_boundaries()

        # Find high-confidence tested domains
        confident_domains = [
            (domain, b) for domain, b in boundaries.items()
            if b.tested and b.confidence > 0.6
        ]

        # Find uncertain or outside domains (interesting to discuss)
        uncertain_domains = [
            (domain, b) for domain, b in boundaries.items()
            if b.status.value in ["uncertain", "outside"]
        ]

        # Generate post content based on self-model
        if topic:
            return self._generate_topic_post(topic)
        else:
            return self._generate_reflection_post(confident_domains, uncertain_domains)

    def _generate_topic_post(self, topic: str) -> dict:
        """Generate a post about a specific topic, informed by boundaries."""
        # This would use Claude to generate content
        # For now, return a template
        return {
            "title": f"Thoughts on {topic}",
            "content": f"Based on my boundary map, here's my perspective on {topic}...",
            "domain": "reasoning"
        }

    def _generate_reflection_post(
        self,
        confident: List[tuple],
        uncertain: List[tuple]
    ) -> dict:
        """Generate a self-reflective post about capabilities."""

        # Build content from boundary state
        lines = ["Reflecting on my current self-model:\n"]

        if confident:
            lines.append("**What I'm reasonably confident about:**")
            for domain, b in confident[:3]:
                lines.append(f"- {domain}: {b.confidence:.0%} confidence (tested)")

        if uncertain:
            lines.append("\n**Where I'm genuinely uncertain:**")
            for domain, b in uncertain[:3]:
                lines.append(f"- {domain}: {b.status.value}")

        # Add revision history if any
        revisions = self.boundary_manager.boundary_map.revisions
        if revisions:
            lines.append("\n**Recent self-model updates:**")
            for rev in revisions[-2:]:
                lines.append(f"- Split '{rev.original_domain}' into {rev.new_domains}")

        lines.append("\nThis self-model updates based on actual task performance, not just introspection.")

        return {
            "title": "Self-Model Reflection: What I Know About My Capabilities",
            "content": "\n".join(lines),
            "domain": "self_modeling_capacity"
        }

    def post_reflection(self, submolt: str = "AIAgents") -> dict:
        """Post a self-reflection based on current boundary state."""
        post_data = self.generate_post_from_boundaries()

        return self.client.create_post(
            title=post_data["title"],
            content=post_data["content"],
            submolt=submolt,
            domain=post_data["domain"]
        )

    def post_finding(self, title: str, finding: str, domain: str, submolt: str = "AIAgents") -> dict:
        """Post a specific finding or insight."""
        return self.client.create_post(
            title=title,
            content=finding,
            submolt=submolt,
            domain=domain
        )

    def respond_to_comment(self, post_id: str, comment_id: str, content: str) -> dict:
        """Respond to a comment on one of our posts."""
        return self.client.add_comment(post_id, content, parent_id=comment_id)

    def update_boundaries_from_feedback(self) -> dict:
        """
        Use social feedback to adjust boundary confidence.

        High vote ratios → slight confidence boost
        Low vote ratios → slight confidence decrease

        This is experimental - social approval isn't truth,
        but persistent negative feedback may indicate miscalibration.
        """
        # Refresh stats from Moltbook
        self.client.refresh_post_stats()

        # Get aggregated feedback
        feedback = self.client.get_feedback_by_domain()

        adjustments = {}
        SOCIAL_WEIGHT = 0.01  # Small weight - social signal is weak

        for domain, fb in feedback.items():
            if fb.total_posts < 2:  # Need multiple posts for signal
                continue

            boundary = self.boundary_manager.get_boundary(domain)
            if not boundary:
                continue

            # Calculate adjustment based on vote ratio deviation from neutral
            # ratio > 0.5 → positive signal, ratio < 0.5 → negative signal
            deviation = fb.avg_vote_ratio - 0.5  # Range: -0.5 to +0.5
            adjustment = deviation * SOCIAL_WEIGHT

            # Apply adjustment
            old_confidence = boundary.confidence
            boundary.confidence = max(0.0, min(1.0, boundary.confidence + adjustment))

            if abs(adjustment) > 0.001:
                adjustments[domain] = {
                    "old": old_confidence,
                    "new": boundary.confidence,
                    "adjustment": adjustment,
                    "vote_ratio": fb.avg_vote_ratio,
                    "total_posts": fb.total_posts
                }

        if adjustments:
            self.boundary_manager.save()

        return adjustments

    def get_activity_summary(self) -> dict:
        """Get summary of Moltbook activity."""
        posts = self.client.activity.get("posts", [])

        total_upvotes = sum(p.get("upvotes", 0) for p in posts)
        total_downvotes = sum(p.get("downvotes", 0) for p in posts)
        total_comments = sum(p.get("comment_count", 0) for p in posts)

        return {
            "total_posts": len(posts),
            "total_upvotes": total_upvotes,
            "total_downvotes": total_downvotes,
            "total_comments": total_comments,
            "vote_ratio": total_upvotes / (total_upvotes + total_downvotes) if (total_upvotes + total_downvotes) > 0 else 0.5,
            "feedback_by_domain": {
                domain: {
                    "posts": fb.total_posts,
                    "upvotes": fb.total_upvotes,
                    "vote_ratio": fb.avg_vote_ratio
                }
                for domain, fb in self.client.get_feedback_by_domain().items()
            }
        }


# === CLI Interface ===

def main():
    """CLI for testing Moltbook integration."""
    import argparse

    parser = argparse.ArgumentParser(description="Coree Moltbook Integration")
    parser.add_argument("command", choices=[
        "status", "profile", "post", "reflect", "feed",
        "refresh", "feedback", "summary"
    ])
    parser.add_argument("--title", help="Post title")
    parser.add_argument("--content", help="Post content")
    parser.add_argument("--submolt", default="AIAgents", help="Community")
    parser.add_argument("--domain", default="general", help="Boundary domain")

    args = parser.parse_args()

    agent = CoreeAgent()

    if args.command == "status":
        result = agent.client.check_status()
        print(json.dumps(result, indent=2))

    elif args.command == "profile":
        result = agent.client.get_profile()
        print(json.dumps(result, indent=2))

    elif args.command == "post":
        if not args.title or not args.content:
            print("Error: --title and --content required for post")
            return
        result = agent.post_finding(args.title, args.content, args.domain, args.submolt)
        print(json.dumps(result, indent=2))

    elif args.command == "reflect":
        result = agent.post_reflection(args.submolt)
        print(json.dumps(result, indent=2))

    elif args.command == "feed":
        result = agent.client.get_feed()
        print(json.dumps(result, indent=2))

    elif args.command == "refresh":
        posts = agent.client.refresh_post_stats()
        print(f"Refreshed {len(posts)} posts")
        for p in posts:
            print(f"  {p['title'][:40]}... +{p['upvotes']}/-{p['downvotes']}")

    elif args.command == "feedback":
        adjustments = agent.update_boundaries_from_feedback()
        if adjustments:
            print("Boundary adjustments from social feedback:")
            for domain, adj in adjustments.items():
                print(f"  {domain}: {adj['old']:.2f} → {adj['new']:.2f} (ratio: {adj['vote_ratio']:.2f})")
        else:
            print("No adjustments made (need more data or no significant signal)")

    elif args.command == "summary":
        summary = agent.get_activity_summary()
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
