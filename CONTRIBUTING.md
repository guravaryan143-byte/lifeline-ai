# Contributing

Thanks for helping improve LifeLine AI. This is an educational incident-reporting prototype, not an emergency service.

## Development setup

Follow the [README setup guide](./README.md#local-development) to configure the backend and frontend. Keep local `.env` files, database files, uploads, model binaries, and real incident/user data out of commits. Use synthetic or otherwise privacy-safe test data only.

## Before opening a pull request

Run the relevant checks from the backend project directory:

```powershell
python -m pytest -q
```

For frontend changes, run from `life-line-ai frontend/lifeline-ai-frontend`:

```powershell
npm ci
npm run typecheck
npm run build
```

For database changes, include an Alembic migration and tests where practical. Verify the configured database target before applying migrations; never test against production or apply changes to a database you do not own.

## Pull request guidance

- Keep changes focused and explain the user-visible behavior or problem being addressed.
- Include tests for behavior changes and update documentation/configuration examples when needed.
- Do not include credentials, personal information, generated database files, user uploads, or real incident data.
- Describe any operational, privacy, or security implications and list checks that were run.
- Do not represent AI classifications as emergency advice or verified predictions.

By submitting a contribution, you agree that it is provided under the project’s Apache License 2.0.
