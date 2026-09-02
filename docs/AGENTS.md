# Documentation project instructions

## About this project

- This is the Russian documentation site for [JacRed](https://github.com/jacred-fdb/jacred).
- The site uses Mintlify. Pages are MDX files with YAML frontmatter.
- Site configuration and navigation live in `docs.json`.
- The parent repository is the product source of truth.
- `openapi/openapi.yaml` and branded images are deployment copies of canonical files under `../web/public/`.
- Update the copies manually when their canonical `web/public` files change. Do not add a synchronization script or workflow.
- Use the Mintlify docs MCP server to verify current components and configuration.

## Terminology

- Write the product name as “JacRed”.
- Use “трекер”, “раздача”, “FileDB”, “поисковый API”, and “веб-интерфейс”.
- Keep API names in English: Jackett, Torznab, Prowlarr, OpenAPI.
- Use `apikey` for search access and `devkey` for administrative access.

## Style preferences

- Write in Russian using active voice and second person (“вы”).
- Keep sentences concise. Use one idea per sentence.
- Use sentence case for headings.
- Bold UI labels: нажмите **Настройки**.
- Use code formatting for file names, commands, paths, options, and endpoints.
- Use root-relative internal links without extensions.
- Add `title`, `sidebarTitle`, `description`, and useful `keywords` to pages.
- Prefer Mintlify components when they improve scanning, not for decoration.

## Content boundaries

- Never publish real API keys, tokens, passwords, cookies, wallet secrets, or private URLs.
- Treat `../web/public/openapi.yaml`, `../Data/crontab`, `../Configuration/Schema/ConfigSchema.cs`, and `../Infrastructure/Security/` as authoritative.
- Document `/dev/*` and destructive maintenance actions as operator-only features with warnings.
- Do not describe retired tracker icons as active trackers.
- Keep generated OpenAPI reference separate from task-focused guides.
- Do not invent defaults. Verify them in source code or the canonical config.
