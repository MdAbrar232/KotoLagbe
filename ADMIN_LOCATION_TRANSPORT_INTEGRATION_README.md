# KotoLagbe Complete Administration Extension

This package combines the transport administration extension with user-submitted location moderation.

## Admin Panel sections
- Places
- Users (including existing profile/account editing)
- Locations (list, status filters, approve/reject, edit/delete)
- Transport modes (add/edit/delete/activate/deactivate)
- Fare moderation (pending/approved/rejected filters, approve/reject)
- Activity log

## Location workflow
- Public GET locations returns approved locations only.
- Authenticated users can POST a location; it is saved as pending.
- Admins can review and approve/reject locations.
- Admin-created locations are created as approved.
- Existing locations are migrated as approved to preserve current route data.

## Public transportation workflow
- Only active transport modes are listed publicly.
- Public fare listings include only approved fares using active modes and approved locations.
- User fare submissions are pending until moderated.

## Migration
A single transport migration `0002_admin_location_and_mode_moderation.py` adds:
- `TransportMode.is_active`
- `Location.submitted_by`, `submitted_at`, and `status`

Run:
```powershell
cd backend
.\\venv\\Scripts\\python.exe manage.py migrate
.\\venv\\Scripts\\python.exe manage.py check
.\\venv\\Scripts\\python.exe manage.py test administration transport
```

Then:
```powershell
cd frontend
npm.cmd run lint
npm.cmd run build
```

The tests/build must be run in your local environment before pushing. This package has been source-integrated but not executed against your local PostgreSQL database.
