# YoMo Integration Test Skill

## What this does

Generates curl-based integration test cases for YoMo AI Bridge, runs them against a user-started server, compares provider recordings (JSONL) with actual responses, and writes a Markdown report.

## Install

Copy this directory into your skills folder so the folder name matches the skill name:

```bash
mkdir -p ~/.agents/skills
cp -R . ~/.agents/skills/yomo-integration-test
```
