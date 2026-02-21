#!/usr/bin/env bash
set -euo pipefail

TAG=""
PUSH=0

usage() {
  cat <<'EOF'
Usage: scripts/release.sh --tag vX.Y.Z [--push]

Options:
  --tag    Required semantic version tag (example: v0.2.1)
  --push   Optional: push the tag to origin after creation
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tag)
      TAG="${2:-}"
      shift 2
      ;;
    --push)
      PUSH=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1"
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$TAG" ]]; then
  echo "Error: --tag is required"
  usage
  exit 1
fi

if [[ ! "$TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Error: tag '$TAG' is not strict semver (expected vX.Y.Z)"
  exit 1
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Error: must be run inside a git repository"
  exit 1
fi

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$CURRENT_BRANCH" != "main" ]]; then
  echo "Error: releases must be tagged from 'main' (current branch: $CURRENT_BRANCH)"
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Error: working tree is not clean. Commit/stash changes before tagging."
  exit 1
fi

if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "Error: tag '$TAG' already exists locally"
  exit 1
fi

if git ls-remote --tags origin "refs/tags/$TAG" | grep -q "$TAG"; then
  echo "Error: tag '$TAG' already exists on origin"
  exit 1
fi

# Strip the leading "v" to get the PEP 440 version
VERSION="${TAG#v}"

# Sync the version in pyproject.toml to match the tag
echo "Setting version in pyproject.toml to $VERSION ..."
sed -i "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml

# Stage the version bump so CI sees a clean tree after commit
git add pyproject.toml
git commit -m "chore: bump version to $VERSION"

echo "Running CI-equivalent checks before tagging..."
make ci

echo "Creating tag $TAG"
git tag -a "$TAG" -m "Release $TAG"

if [[ "$PUSH" -eq 1 ]]; then
  echo "Pushing tag $TAG to origin"
  git push origin "$TAG"
  echo "Done. GitHub release workflow should trigger for $TAG."
else
  echo "Tag created locally: $TAG"
  echo "To trigger release workflow: git push origin $TAG"
fi
