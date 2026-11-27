# KotoLagbe Week 4 implementation summary

Base source: GitHub ZIP commit `21584caae7ab225e553f5ef8169908a6ee89e281`.

## Work completed

- Extended the existing `places` app with `PlacePhoto` and migration `0006_placephoto`.
- Added authenticated photo uploads tied to the selected place and the authenticated contributor.
- Added image checks for valid JPEG, PNG and WebP content, matching file extensions, a 5 MB size limit and a 25-megapixel dimension limit.
- Added public photo retrieval that returns approved photos only.
- Added an authenticated endpoint for contributors to view their own photo submission statuses and rejection reasons.
- Added staff-only photo moderation endpoints with approval, required rejection reasons, own-submission protection and activity logging.
- Stored uploaded photos in a private media directory and served them through a permission-checked image endpoint. Approved photos are public; pending/rejected photos can be previewed by the contributor and staff through short-lived signed image URLs.
- Added `MEDIA_ROOT` / `MEDIA_URL` settings for local filesystem storage.
- Extended the existing AdminPanel with Place items, Item prices, Reviews and Photos moderation tabs.
- Added a rejection-reason dialog for item, price, review and photo moderation.
- Added item-status visibility in price moderation and disabled price approval until the parent item is approved.
- Added create-place support to the existing Places admin section.
- Connected PlaceDetails to the existing item suggestion and item-price submission APIs.
- Added public photo display, photo upload and contributor photo status to PlaceDetails.
- Added dashboard counts for pending reviews and photos.

## New photo API routes

- `GET /api/places/{place_id}/photos/` — approved photos for a place.
- `POST /api/places/{place_id}/photos/` — authenticated multipart upload. Fields: `image_upload` (required) and `caption` (optional). New submissions start as `pending`.
- `GET /api/places/{place_id}/photos/mine/` — authenticated contributor's photo submissions for that place.
- `GET /api/places/photos/{photo_id}/image/` — serves approved photos publicly; pending/rejected photos require the contributor/staff or a short-lived signed preview URL returned to them.
- `GET /api/admin/photos/` — staff-only moderation list; supports `?status=pending|approved|rejected` and search.
- `POST /api/admin/photos/{photo_id}/approve/` — approve a photo.
- `POST /api/admin/photos/{photo_id}/reject/` — reject a photo; JSON body must include a non-empty `reason`.

## Existing contribution APIs connected in PlaceDetails

- `POST /api/places/items/suggest/` — suggest an item and its initial price for the current place.
- `POST /api/places/items/{item_id}/prices/` — suggest a price for an approved item.
- Existing review submission and moderation routes remain in use.

## Setup

1. Install backend dependencies with `pip install -r backend/requirements.txt` (Pillow was added for image validation).
2. Configure `backend/.env` using the existing `.env.example` database settings.
3. Run `python manage.py migrate` from `backend/` to create the photo table.
4. Run the Django server. Photo files are stored under the configured `MEDIA_ROOT` and delivered through the permission-checked photo image endpoint, not a public `/media/` directory.
5. In production, configure persistent media storage. Keep the private upload directory outside any publicly served static/media path; the application endpoint checks photo status and access before returning a file.

## Verification performed

- `python manage.py check --settings=config.test_settings` — passed.
- `python manage.py makemigrations --check --dry-run --settings=config.test_settings` — no model changes missing from migrations.
- `python manage.py test --settings=config.test_settings` — 96 tests passed using SQLite in-memory test settings.
- Frontend ESLint — passed.
- Vite production build — not completed in this environment because the uploaded Windows `node_modules` did not contain the Linux Rolldown native binding, and package installation could not reach the network. Re-run `npm ci`, `npm run lint` and `npm run build` on the development machine.

## Manual browser checks still required

- Sign in as a normal user and upload a valid image to a place.
- Confirm it appears in the contributor's own photo submissions as pending but is not public yet.
- Sign in as a staff user, open Admin > Photos, inspect the thumbnail and approve it.
- Confirm the approved image appears in the place photo gallery.
- Upload another image and reject it with a reason; confirm the contributor sees the reason and the image stays hidden publicly.
- Test a non-image, mismatched/unsupported image extension and an image larger than 5 MB.
- Confirm direct pending/rejected image requests return 403 to other users and anonymous visitors; contributor/admin preview URLs should work until their 15-minute signature expires.
- Test item and price submissions from PlaceDetails and approve the item before approving its price.

## Deployment note

Local file uploads use Django's filesystem storage. For a deployed environment, `MEDIA_ROOT` must be on persistent storage and uploaded media must be served securely. Do not deploy with `DEBUG=True`.

## Files changed

- `backend/places/models.py`
- `backend/places/migrations/0006_placephoto.py`
- `backend/places/serializers.py`
- `backend/places/views.py`
- `backend/places/urls.py`
- `backend/places/test_photos.py`
- `backend/administration/serializers.py`
- `backend/administration/views.py`
- `backend/administration/urls.py`
- `backend/administration/test_photo_moderation.py`
- `backend/config/settings.py`
- `backend/config/test_settings.py`
- `backend/requirements.txt`
- `frontend/src/AdminPanel.jsx`
- `frontend/src/AdminPanel.css`
- `frontend/src/PlaceDetails.jsx`
- `frontend/src/PlaceDetails.css`
- `WEEK4_IMPLEMENTATION_SUMMARY.md`
