#!/bin/bash

REPO="microsoft/AI_Agents_Hackathon"
JSON_FILE="copilot-issues.json"

cat "$JSON_FILE" | jq -c '.[]' | while read -r item; do
  ISSUE_NUMBER=$(echo "$item" | jq '.number')
  LABELS=$(echo "$item" | jq -r '.labels | join(",")')
  
  echo "Labeling issue #$ISSUE_NUMBER with labels: $LABELS"
  
  gh issue edit "$ISSUE_NUMBER" -R "$REPO" --add-label "$LABELS"
done