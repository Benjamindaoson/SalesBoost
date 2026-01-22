I have researched the current state of User Management and the requirements for the Admin System.

**Status Analysis:**

1. **Backend (`app/api/endpoints/admin_modules/users.py`)**:

   * Exists but only supports listing (`GET /`) and status updates (`PATCH /{id}/status`).

   * **Missing**: Create User (`POST /`), Delete User (`DELETE /`), and Password Hashing (currently plaintext MVP).

   * **Role Management**: No dedicated API for roles; roles are just strings in the `User` model.
2. **Frontend (`pages/Admin/`)**:

   * `UserManagementPage.tsx` (Student Management) exists.

   * **Missing**: Unified "Account & Permission" page with tabs, Admin creation modal, Role configuration UI.
3. **Authentication**:

   * Currently uses plaintext comparison. I should upgrade this to use `passlib` for production readiness as requested ("production environment requirements").

**Implementation Plan:**

**Phase 1: Backend Core Upgrades**

1. **Security Upgrade**: Install `passlib[bcrypt]` and implement `get_password_hash` and `verify_password` utilities in `app/core/security.py`. Update `auth.py` to use these.
2. **Admin User API**: Enhance `users.py` to support:

   * `POST /` (Create User): Support creating Admins/Students with roles.

   * `PUT /{id}` (Update User): Support updating profile/role.

   * `DELETE /{id}` (Delete User).
3. **Role API**: Create `app/api/endpoints/admin_modules/roles.py` (Mock/Simple implementation) to list and configure role permissions (e.g., menu access).

**Phase 2: Frontend "Account & Permission" Module**

1. **Container Page**: Create `pages/Admin/AccountAndPermissions/index.tsx` using a Tab component (Shadcn UI Tabs).

   * **Tab 1: Admin Management**: List admins, Add/Edit modal.

   * **Tab 2: Student Management**: Refactor existing `UserManagementPage` here.

   * **Tab 3: Role Permissions**: List roles, Configure Permissions modal (visual tree selector).
2. **API Integration**: Update `frontend/src/services/api.ts` to include new endpoints.

**Phase 3: Data & System Modules (MVP/Placeholder)**

1. **Data Dashboard**: Enhance `AdminDashboard` with more charts (using Recharts mock data) to satisfy "Data Management".
2. **System Config**: Create `pages/Admin/SystemConfig.tsx` with basic form fields (Site Name, Theme Toggle, Language - mock).

**Phase 4: Tests & Docs**

1. **Tests**: Add `tests/test_admin_users.py` to verify CRUD and RBAC.
2. **Docs**: Generate a `ADMIN_SYSTEM_MANUAL.md`.

I will focus on Phase 1 & 2 immediately as they are the core request.

**Dependencies to Install:**

* `passlib`

* `bcrypt`

