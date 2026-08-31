#!/bin/bash
# 母库推送前必跑（用户指令 2026-08-31：后续推送线上之前务必本地做完）
# 用法: bash scripts/pre-push-check.sh  （全绿才允许 git push）
cd "$(dirname "$0")/.."
RED='\033[0;31m'; GREEN='\033[0;32m'; NC='\033[0m'
PASS=0; FAIL=0
run() {
  local name="$1"; shift
  local out rc
  out=$("$@" 2>&1) || true; rc=$?
  local fails=$(echo "$out" | grep -ciE "FAIL:|BLOCK:|CASE_FAILURE" || true)
  if [ $rc -eq 0 ] && [ "$fails" -eq 0 ]; then
    echo -e "${GREEN}✔ $name${NC}"; PASS=$((PASS+1))
  else
    echo -e "${RED}✘ $name (${fails} failures)${NC}"
    echo "$out" | grep -E "FAIL:|BLOCK:|CASE_FAILURE" | head -5 | sed 's/^/    /'
    FAIL=$((FAIL+1))
  fi
}
echo "=== 母库推送前全量检查（7 步）==="
run "governance-tests"    node scripts/run-governance-tests.mjs --timeout-ms 120000
run "validate-indexes"    node scripts/validate-indexes.mjs --check
run "validate-links"      node scripts/validate-links.mjs
run "validate-document-ids" node scripts/validate-document-ids.mjs
run "validate-logs"       node scripts/validate-logs.mjs
run "knowledge-chain"     node scripts/validate-knowledge-chain.mjs
run "mother-library"      node scripts/validate-mother-library.mjs
echo ""
echo "=== 结果: $PASS 通过 / $FAIL 失败 ==="
[ $FAIL -eq 0 ] && echo -e "${GREEN}允许推送${NC}" || { echo -e "${RED}禁止推送：先修复上述失败${NC}"; exit 1; }
