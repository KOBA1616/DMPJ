#!/usr/bin/env bash
# 取得データを cards-data ブランチへ保存する（コミット → 最新を取り込み → push、4回まで再試行）。
# 実行中の定期保存と、最後の保存の両方で使う。途中で落ちても、ここまでの分は残る。
# 作業ツリーを先にコミットで片付けるので、他の保存（変換など）が先に push していても rebase で止まらない（merge で取り込む）。
set -u
git config user.name "github-actions"; git config user.email "actions@users.noreply.github.com"
git add -f data/cards/catalog
if [ -d data/cards/raw/by_product ]; then git add -f data/cards/raw/by_product; fi
git commit -qm "cards-data: auto $(date -u +%FT%TZ)" || echo "no changes"
for i in 1 2 3 4; do
  if git fetch -q origin cards-data 2>/dev/null; then
    git merge -q --no-edit -X ours origin/cards-data >/dev/null 2>&1 || git merge --abort >/dev/null 2>&1
  fi
  if git push -q origin HEAD:cards-data; then echo "saved (try $i)"; exit 0; fi
  sleep $((i * 5))
done
echo "保存に失敗（artifact に残る）" >&2
exit 1
