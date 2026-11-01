# Emergency rollback

1. In GitHub, open your repository **Commits** history.
2. Find the commit before `WATCH VNext clean rebuild`.
3. Revert the code-change commit, or restore `index.html`, `app.js`, and `brand.css`/workflow from that commit, then commit again.
4. **Do not delete `catalog.json`.** Existing videos are preserved in that file or in its Git history.
5. If a refreshed catalog was accidentally modified, recover `catalog-before.json` from the `watch-refresh-audit-backup` artifact of the corresponding import run, or view the previous `catalog.json` in Git history and restore it.
6. Confirm Pages source is **GitHub Actions** and verify the deployment.

Keep the repo's history rather than deleting the entire repository. A destructive reset would make recovery harder.
