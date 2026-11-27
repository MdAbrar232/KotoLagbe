# KotoLagbe Administration Module

Staff-only management and moderation, in `backend/administration` (API) and `frontend/src/AdminPanel.jsx` (page).
All `/api/admin/` routes require an active staff account and a JWT access token. A guest receives HTTP 401, and a signed-in member receives HTTP 403.

## Admin Panel sections
The existing React panel includes Places, Users, Locations, Transport modes, Fare moderation, Place items, Item prices, Reviews, Photos, and Activity log. Dashboard counts include pending submissions in each moderation queue.

## Endpoints
| Method | Endpoint | Purpose |
|---|---|---|
| GET, POST, PATCH, DELETE | `/api/admin/places/`, `/api/admin/places/{id}/` | List, create, search, edit, and delete places, including their transport location and parent place |
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
| GET | `/api/admin/items/`, `/api/admin/item-prices/`, `/api/admin/reviews/`, `/api/admin/photos/` | Search submissions and filter by `status` |
| POST | Append `{id}/approve/` or `{id}/reject/` to a moderation queue | Items, prices, reviews, and photos require a JSON `reason` on rejection. Their contributors cannot moderate their own submissions. |
| GET | `/api/admin/activity/` | Log of admin actions |
| GET | `/api/admin/stats/` | Dashboard counts (also tells the site whether the user is staff) |

## Workflows
- **Locations:** a logged-in user can submit one; it is saved as `pending` and is not public until an admin approves it. Admin-created locations are `approved`.
- **Transport modes:** only active modes are listed publicly, and fares cannot be submitted on an inactive mode. Mode names are unique ignoring capital letters.
- **Fares:** user submissions are `pending`. The public fare list shows only `approved` fares whose mode is active and whose origin and destination are approved.
- **Migration:** `transport.0002` adds `TransportMode.is_active` and `Location.submitted_by`, `submitted_at`, `status`. Existing locations become `approved` and existing modes stay active.

## Public API contracts

| UI | API | Relevant response or request fields |
|---|---|---|
| Transport locations and fares | `/api/transport/locations/`, `/api/transport/fares/` | Authenticated POST, public GET. Fare rows contain origin, destination and mode IDs. The client resolves their names from the approved stops and active modes. |
| Route summary | `/api/transport/fares/summary/?origin={id}&destination={id}` | Read `transport_options` with minimum, maximum, average and submission count per mode. Direction matters. |
| Place items | `GET /api/places/items/?place={id}`, `POST /api/places/items/suggest/` | Send `place`, `name`, `category`, and initial `price`. The item and its first price enter separate queues. |
| Item prices | `/api/places/items/{item_id}/prices/` | Authenticated POST with `price`. Public GET lists approved reports on approved items. Item rows carry the average of approved prices. |
| Reviews | `/api/places/{id}/reviews/`, `reviews/mine/` under the same place | Public lists and place rating totals use approved reviews. An owner can read their rejection reason. Editing returns a review to pending. |
| Photos | `/api/places/{id}/photos/` | POST multipart `image` and optional `caption`. The URL selects the place, and the JWT identifies the owner. Rows include `image_url`, `username`, `status`, and `can_delete`. |
| Photo bytes and removal | `GET /api/places/{id}/photos/{pk}/content/`, `DELETE /api/places/{id}/photos/{pk}/` | Everyone can see approved photos. Only staff and the uploader can read pending or rejected photos or remove a photo. Removing the user or place also removes its photo files after commit. |
| Profile history | `GET /api/accounts/submissions/` | The current user's location, fare, item and price contributions, with moderation status. Review decisions appear on the place page, as do photo decisions. |

A rejected transport location is hidden from public place details, fare lists, and route choices. Its place link stays in the database and becomes visible again if staff approve it.

The panel reads `contributor` for items and prices and `username` for reviews and photos. Item prices also carry `item_status`. Approve the item before its prices. Place creation requires staff, and parent selections use the same circular-reference validation in the public and administration serializers.

## Setup for this update

From the project root in Windows PowerShell, run these commands with your existing local PostgreSQL configuration.

```powershell
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\backend\.venv\Scripts\python.exe backend\manage.py migrate
```

The new migration is `places.0006_place_photo`. Store uploaded images in a persistent, private directory. Django defaults to `backend/media/` and accepts an override in `DJANGO_MEDIA_ROOT`. Serve them through the photo content endpoint so staff decisions apply to image bytes as well as gallery listings. The uploader accepts still JPEG, PNG and WebP up to 5 MiB and 16 megapixels, and stores a normalized JPEG.

The frontend uses `http://127.0.0.1:8000/api` by default. Set Vite's `VITE_API_BASE_URL` for another API host. Django accepts the local Vite origins on port 5173 by default. Set `DJANGO_CORS_ALLOWED_ORIGINS` to a comma-separated list for other origins.

## Run the checks
```
cd backend
python manage.py migrate
python manage.py test
cd ../frontend
npm run lint
npm run build
```


`administration/test_workflows.py` covers real JWT permissions, blocking, place relationships, and the public contribution → staff decision → public result for locations, fares, items, prices, and reviews. `places/test_photos.py` covers validation, owner and staff access, publication, file cleanup, rollback, and storage errors.

## Browser integration test (optional)

The browser test starts Django with a disposable test database and opens separate member, staff, and guest sessions in Chromium. It exercises the actual React build. From the repository root in PowerShell:

```powershell
.\backend\.venv\Scripts\python.exe -m pip install playwright
.\backend\.venv\Scripts\python.exe -m playwright install chromium
Push-Location frontend
$env:VITE_API_BASE_URL = '/api'
npm ci
npm run build
Remove-Item Env:VITE_API_BASE_URL
Pop-Location
.\backend\.venv\Scripts\python.exe backend\manage.py test administration.browser_workflow
```

The same-origin build above lets the test choose a free port. During local development, `npm run dev` uses the normal API default. An optional `KOTOLAGBE_TEST_DIST` selects another build directory, and `KOTOLAGBE_TEST_CHROMIUM` selects an installed Chromium executable.
