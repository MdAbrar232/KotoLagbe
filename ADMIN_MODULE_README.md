# KotoLagbe Administration Module

Staff-only management and moderation, in `backend/administration` (API) and `frontend/src/AdminPanel.jsx` (page).
Every endpoint below needs a logged-in staff user (`is_staff=True`) and a Bearer access token; other users get 403.

## Admin Panel sections
Places, Users, Locations, Transport modes, Fare moderation, Activity log, plus dashboard counts.

## Endpoints
| Method | Endpoint | Purpose |
|---|---|---|
| GET, PATCH, DELETE | `/api/admin/places/`, `/api/admin/places/{id}/` | List, search, edit, delete places |
| GET, PATCH, DELETE | `/api/admin/users/`, `/api/admin/users/{id}/` | List, search, edit information, delete users |
| POST | `/api/admin/users/{id}/block/` and `/unblock/` | Switch an account off or on |
| GET, POST | `/api/admin/locations/` | List (filter `?status=`) or create (created as approved) |
| PATCH, DELETE | `/api/admin/locations/{id}/` | Edit or delete a location (409 if fares use it) |
| POST | `/api/admin/locations/{id}/approve/` and `/reject/` | Moderate a submitted location |
| GET, POST | `/api/admin/transport-modes/` | List (filter `?active=`) or add a mode |
| PATCH, DELETE | `/api/admin/transport-modes/{id}/` | Edit or delete a mode (409 if fares use it) |
| POST | `/api/admin/transport-modes/{id}/activate/` and `/deactivate/` | Switch a mode on or off |
| GET | `/api/admin/fares/` (filter `?status=pending\|approved\|rejected`) | Fare submissions with origin, destination, mode, fare, contributor, date |
| POST | `/api/admin/fares/{id}/approve/` and `/reject/` | Moderate a fare |
| GET | `/api/admin/activity/` | Log of admin actions |
| GET | `/api/admin/stats/` | Dashboard counts (also tells the site whether the user is staff) |

## Workflows
- **Locations:** a logged-in user can submit one; it is saved as `pending` and is not public until an admin approves it. Admin-created locations are `approved`.
- **Transport modes:** only active modes are listed publicly, and fares cannot be submitted on an inactive mode. Mode names are unique ignoring capital letters.
- **Fares:** user submissions are `pending`. The public fare list shows only `approved` fares whose mode is active and whose origin and destination are approved.
- **Migration:** `transport.0002` adds `TransportMode.is_active` and `Location.submitted_by`, `submitted_at`, `status`. Existing locations become `approved` and existing modes stay active.

## Run the checks
```
cd backend
python manage.py migrate
python manage.py test
cd ../frontend
npm run lint
npm run build
```
