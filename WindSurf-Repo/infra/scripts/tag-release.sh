#!/usr/bin/env bash
# Tag release script for production deployment
# Usage: ./tag-release.sh [version] [message] [--force|--force-branch]

set -euo pipefail

VERSION=${1:-$(date +%Y%m%d)}
MESSAGE=${2:-"Production-ready release: Autonomous Backend Orchestration & Edge Architecture"}

# Get current directory (should be backend root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$BACKEND_DIR"

# Check if git repo
if [ ! -d .git ]; then
    echo "Error: Not a git repository"
    exit 1
fi

# Check if working directory is clean
if [ -n "$(git status --porcelain)" ]; then
    echo "Warning: Working directory has uncommitted changes"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
FORCE_BRANCH_FLAG="${3:-}"
FORCE_FLAG="${4:-}"
# Check all args for flags
for arg in "$@"; do
    if [[ "$arg" == "--force-branch" ]]; then
        FORCE_BRANCH_FLAG="--force-branch"
    fi
    if [[ "$arg" == "--force" ]]; then
        FORCE_FLAG="--force"
    fi
done

if [[ "$CURRENT_BRANCH" != "main" && "$CURRENT_BRANCH" != "master" ]]; then
    if [[ "$FORCE_BRANCH_FLAG" != "--force-branch" ]]; then
        echo "Error: Not on main/master branch (current: $CURRENT_BRANCH)"
        echo "Use --force-branch to override"
        exit 1
    fi
fi

# Format version tag
if [[ ! $VERSION =~ ^v ]]; then
    VERSION="v$VERSION"
fi

# Check if tag already exists
if git rev-parse "$VERSION" >/dev/null 2>&1; then
    if [[ "$FORCE_FLAG" != "--force" ]]; then
        echo "Error: Tag $VERSION already exists"
        echo "Use --force to overwrite"
        exit 1
    fi
    echo "Warning: Overwriting existing tag $VERSION"
    git tag -d "$VERSION" || true
fi

# Create annotated tag
echo "Creating tag: $VERSION"
git tag -a "$VERSION" -m "$MESSAGE"

# Show tag info
echo ""
echo "Tag created successfully:"
git show "$VERSION" --no-patch

echo ""
echo "To push the tag to remote:"
echo "  git push origin $VERSION"
echo ""
echo "Or push all tags:"
echo "  git push --tags"
