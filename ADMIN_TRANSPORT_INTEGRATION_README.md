# KotoLagbe Administration: Location & Transportation Extension

This package extends the existing Administration app and the Transport module already present in this repository. It does not create duplicate `Location`, `TransportMode`, or `FareSubmission` models.

## Included administration features

- Existing Places and Users administration retained.
- Location list, create, edit, and delete.
- Transport mode list, create, edit, activate/deactivate, and delete.
- Fare submission moderation with pending/approved/rejected filters and approve/reject actions.
- Fare table includes origin, destination, mode, amount, contributor, submission date, and status.
- Admin dashboard transport statistics.
- Admin activity log for administrative changes.
- Admin API endpoints protected by the existing `IsAdmin` permission (`is_staff=True`).
- Public transport mode listing hides inactive modes.
- Public fare listing continues to show only approved fares and now also hides fares for inactive transport modes.
- Fare submissions using inactive transport modes are rejected.
- Referenced locations/modes cannot be deleted while fare submissions depend on them; the API responds with HTTP 409 rather than an unhandled server error.

## Important model coordination note

Rizwan's supplied `Location` model has no submission status or location-submission workflow. The public location API is read-only and there is no user-submitted-location endpoint in this source tree. Therefore, this package provides location administration CRUD but does **not** add approve/reject buttons for locations. That workflow should only be added after the team agrees on a location status field and submission API.

The supplied `TransportMode` model also had no active/inactive field. This package adds one additive field, `is_active` (default `True`), with migration `transport.0002_transportmode_is_active`. Existing seeded modes remain active after migration. Please tell Rizwan about this additive model change before merging if he is still modifying the same model.

## Apply the changes

From PowerShell:

```powershell
cd C:\Users\User\Downloads\KotoLagbe
```

Extract/merge this package into the existing repository, preserving your local `.env` file. Then run:

```powershell
cd backend
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py test administration transport
```

In another terminal:

```powershell
cd C:\Users\User\Downloads\KotoLagbe\frontend
npm.cmd run lint
npm.cmd run build
```

Start the backend and frontend normally after checks pass. Do not replace your `.env` file with `.env.example`.

## New admin endpoints

All endpoints below require an authenticated staff account and a Bearer access token.

| Method | Endpoint | Purpose |
|---|---|---|
| GET/POST | `/api/admin/locations/` | List/create locations |
| GET/PATCH/PUT/DELETE | `/api/admin/locations/{id}/` | Retrieve/edit/delete location |
| GET/POST | `/api/admin/transport-modes/` | List/create transport modes |
| GET/PATCH/PUT/DELETE | `/api/admin/transport-modes/{id}/` | Retrieve/edit/delete mode |
| POST | `/api/admin/transport-modes/{id}/activate/` | Activate mode |
| POST | `/api/admin/transport-modes/{id}/deactivate/` | Deactivate mode |
| GET | `/api/admin/fares/` | List fare submissions |
| GET | `/api/admin/fares/?status=pending` | Filter fare status (also `approved`, `rejected`) |
| POST | `/api/admin/fares/{id}/approve/` | Approve fare |
| POST | `/api/admin/fares/{id}/reject/` | Reject fare |
| GET | `/api/admin/activity/` | Read admin activity log |
| GET | `/api/admin/stats/` | Dashboard counts |

The existing Places and Users endpoints remain unchanged.

## Suggested manual verification

1. Sign in as a staff user and open the Admin Panel.
2. Create a test location and a test transport mode; edit each one.
3. Deactivate a mode and confirm it disappears from the public Transport mode selector/list endpoint. Reactivate it.
4. Submit a fare using a normal account. Confirm it appears as pending in Fare Moderation but not in public approved fares.
5. Approve it and confirm it appears in the public fare list.
6. Reject it and confirm it disappears from the public fare list again.
7. Open Activity Log and verify the moderation action is recorded.
8. Sign in as a normal user and confirm `/api/admin/locations/`, `/api/admin/transport-modes/`, and `/api/admin/fares/` return HTTP 403.

## Scope note

This ZIP is a code integration package based on the uploaded repository snapshot. Run the migrations, automated tests, frontend lint, and frontend build on your machine before committing. No changes have been pushed to GitHub.
