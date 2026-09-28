import {
  FormEvent,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  createAdminUser,
  getAdminRoles,
  getAdminUsers,
  updateAdminUser,
  updateRolePermissions,
} from "./api";

import type {
  AdminRole,
  AdminUser,
  AdminUserCreatePayload,
  AdminUserUpdatePayload,
} from "./types";

import "./admin.css";


type AdminTab =
  | "users"
  | "roles";


const EMPTY_CREATE: AdminUserCreatePayload = {
  login_id: "",
  name: "",
  email: "",
  role_id: "",
  temp_password: "",
};


export default function AdminUsersPage() {
  const [
    tab,
    setTab,
  ] = useState<AdminTab>(
    "users",
  );

  const [
    users,
    setUsers,
  ] = useState<AdminUser[]>([]);

  const [
    roles,
    setRoles,
  ] = useState<AdminRole[]>([]);

  const [
    count,
    setCount,
  ] = useState(0);

  const [
    page,
    setPage,
  ] = useState(1);

  const [
    search,
    setSearch,
  ] = useState("");

  const [
    roleFilter,
    setRoleFilter,
  ] = useState("");

  const [
    activeFilter,
    setActiveFilter,
  ] = useState("");

  const [
    loading,
    setLoading,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState("");

  const [
    message,
    setMessage,
  ] = useState("");

  const [
    revision,
    setRevision,
  ] = useState(0);

  const [
    createOpen,
    setCreateOpen,
  ] = useState(false);

  const [
    createForm,
    setCreateForm,
  ] = useState<
    AdminUserCreatePayload
  >(EMPTY_CREATE);

  const [
    editingUser,
    setEditingUser,
  ] = useState<
    AdminUser | null
  >(null);

  const [
    editForm,
    setEditForm,
  ] = useState<
    AdminUserUpdatePayload
  >({});

  const [
    selectedRoleId,
    setSelectedRoleId,
  ] = useState("");

  const [
    permissionDraft,
    setPermissionDraft,
  ] = useState<Set<string>>(
    new Set(),
  );


  const params = useMemo(
    () => {
      const value =
        new URLSearchParams();

      value.set(
        "page",
        String(page),
      );

      if (search.trim()) {
        value.set(
          "search",
          search.trim(),
        );
      }

      if (roleFilter) {
        value.set(
          "role",
          roleFilter,
        );
      }

      if (activeFilter) {
        value.set(
          "is_active",
          activeFilter,
        );
      }

      return value;
    },
    [
      page,
      search,
      roleFilter,
      activeFilter,
    ],
  );


  useEffect(
    () => {
      let active = true;

      setLoading(true);
      setError("");

      Promise.all([
        getAdminUsers(params),
        getAdminRoles(),
      ])
        .then(
          ([
            userResponse,
            roleResponse,
          ]) => {
            if (!active) {
              return;
            }

            setUsers(
              userResponse.results,
            );

            setCount(
              userResponse.count,
            );

            setRoles(
              roleResponse.roles,
            );

            if (
              !selectedRoleId
              && roleResponse
                .roles.length > 0
            ) {
              setSelectedRoleId(
                roleResponse
                  .roles[0].id,
              );
            }
          },
        )
        .catch(
          (requestError) => {
            if (!active) {
              return;
            }

            setError(
              requestError instanceof Error
                ? requestError.message
                : (
                    "관리자 정보를 "
                    + "불러오지 못했습니다."
                  ),
            );
          },
        )
        .finally(
          () => {
            if (active) {
              setLoading(false);
            }
          },
        );

      return () => {
        active = false;
      };
    },
    [
      params,
      revision,
    ],
  );


  const selectedRole =
    roles.find(
      (item) =>
        item.id === selectedRoleId,
    ) ?? null;


  useEffect(
    () => {
      if (!selectedRole) {
        setPermissionDraft(
          new Set(),
        );

        return;
      }

      setPermissionDraft(
        new Set(
          selectedRole.permissions.map(
            (permission) =>
              permission.code,
          ),
        ),
      );
    },
    [
      selectedRoleId,
      roles,
    ],
  );


  const permissions =
    useMemo(
      () => {
        const map = new Map<
          string,
          {
            code: string;
            name: string;
            domain: string;
          }
        >();

        roles.forEach(
          (role) => {
            role.permissions.forEach(
              (permission) => {
                map.set(
                  permission.code,
                  permission,
                );
              },
            );
          },
        );

        return Array.from(
          map.values(),
        ).sort(
          (a, b) =>
            (
              a.domain
              + a.code
            ).localeCompare(
              b.domain
              + b.code,
            ),
        );
      },
      [
        roles,
      ],
    );


  const permissionGroups =
    useMemo(
      () => {
        const grouped =
          new Map<
            string,
            typeof permissions
          >();

        permissions.forEach(
          (permission) => {
            const current =
              grouped.get(
                permission.domain,
              ) ?? [];

            current.push(
              permission,
            );

            grouped.set(
              permission.domain,
              current,
            );
          },
        );

        return Array.from(
          grouped.entries(),
        );
      },
      [
        permissions,
      ],
    );


  const totalPages =
    Math.max(
      1,
      Math.ceil(
        count / 20,
      ),
    );


  const creatableRoles =
    roles.filter(
      (role) =>
        role.code
        !== "SYSTEM_ADMIN",
    );


  function refresh(
    successMessage?: string,
  ) {
    if (successMessage) {
      setMessage(
        successMessage,
      );
    }

    setRevision(
      (value) =>
        value + 1,
    );
  }


  async function handleCreate(
    event: FormEvent,
  ) {
    event.preventDefault();

    setError("");
    setMessage("");

    try {
      await createAdminUser({
        ...createForm,
        email:
          createForm.email?.trim()
          || null,
      });

      setCreateOpen(false);
      setCreateForm(
        EMPTY_CREATE,
      );

      setPage(1);

      refresh(
        "사용자 계정을 생성했습니다.",
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "사용자 생성에 실패했습니다.",
      );
    }
  }


  function openEdit(
    user: AdminUser,
  ) {
    setEditingUser(
      user,
    );

    const role = roles.find(
      (item) =>
        item.code
        === user.role.code,
    );

    setEditForm({
      name: user.name,
      email:
        user.email ?? "",
      role_id:
        role?.id,
      is_active:
        user.is_active,
    });

    setError("");
    setMessage("");
  }


  async function handleUpdate(
    event: FormEvent,
  ) {
    event.preventDefault();

    if (!editingUser) {
      return;
    }

    const payload = {
      ...editForm,
      email:
        typeof editForm.email
        === "string"
          ? (
              editForm.email.trim()
              || null
            )
          : editForm.email,
    };


    /*
     * SYSTEM_ADMIN은 프로젝트의 단일
     * 운영 관리자이므로 UI에서
     * Role 변경/비활성화를 막는다.
     */
    if (
      editingUser.role.code
      === "SYSTEM_ADMIN"
    ) {
      delete payload.role_id;
      delete payload.is_active;
    }


    setError("");
    setMessage("");

    try {
      await updateAdminUser(
        editingUser.id,
        payload,
      );

      setEditingUser(
        null,
      );

      refresh(
        "사용자 정보를 수정했습니다.",
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "사용자 수정에 실패했습니다.",
      );
    }
  }


  function togglePermission(
    code: string,
  ) {
    setPermissionDraft(
      (current) => {
        const next =
          new Set(current);

        if (next.has(code)) {
          next.delete(code);
        } else {
          next.add(code);
        }

        return next;
      },
    );
  }


  async function savePermissions() {
    if (!selectedRole) {
      return;
    }

    if (
      selectedRole.code
      === "SYSTEM_ADMIN"
    ) {
      setError(
        (
          "SYSTEM_ADMIN 권한은 "
          + "관리자 잠금 방지를 위해 "
          + "화면에서 변경하지 않습니다."
        ),
      );

      return;
    }

    setError("");
    setMessage("");

    try {
      await updateRolePermissions(
        selectedRole.id,
        Array.from(
          permissionDraft,
        ).sort(),
      );

      refresh(
        "Role Permission을 변경했습니다.",
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "권한 변경에 실패했습니다.",
      );
    }
  }


  return (
    <section
      className="clinical-page admin-page"
    >
      <header
        className="clinical-page__heading"
      >
        <div>
          <h2>
            사용자 · 권한 관리
          </h2>

          <p>
            계정 생성·수정·활성화와
            Role Permission을 관리합니다.
          </p>
        </div>

        {tab === "users" && (
          <button
            type="button"
            className="
              admin-action
              admin-action--primary
            "
            onClick={
              () => {
                setCreateForm(
                  EMPTY_CREATE,
                );
                setCreateOpen(
                  true,
                );
                setError("");
                setMessage("");
              }
            }
          >
            사용자 생성
          </button>
        )}
      </header>


      <div className="admin-tabs">
        <button
          type="button"
          className={
            tab === "users"
              ? "is-active"
              : ""
          }
          onClick={
            () =>
              setTab("users")
          }
        >
          사용자 관리
        </button>

        <button
          type="button"
          className={
            tab === "roles"
              ? "is-active"
              : ""
          }
          onClick={
            () =>
              setTab("roles")
          }
        >
          Role · Permission
        </button>
      </div>


      {message && (
        <div className="admin-message">
          {message}
        </div>
      )}

      {error && (
        <div
          className="
            admin-message
            admin-message--error
          "
        >
          {error}
        </div>
      )}


      {tab === "users" ? (
        <>
          <div
            className="
              clinical-toolbar
              admin-filter-grid
            "
          >
            <label>
              사용자 검색

              <input
                value={search}
                onChange={
                  (event) => {
                    setSearch(
                      event.target.value,
                    );
                    setPage(1);
                  }
                }
                placeholder={
                  "이름 또는 로그인 ID"
                }
              />
            </label>

            <label>
              Role

              <select
                value={roleFilter}
                onChange={
                  (event) => {
                    setRoleFilter(
                      event.target.value,
                    );
                    setPage(1);
                  }
                }
              >
                <option value="">
                  전체
                </option>

                {roles.map(
                  (role) => (
                    <option
                      key={role.id}
                      value={role.code}
                    >
                      {role.name}
                    </option>
                  ),
                )}
              </select>
            </label>

            <label>
              상태

              <select
                value={activeFilter}
                onChange={
                  (event) => {
                    setActiveFilter(
                      event.target.value,
                    );
                    setPage(1);
                  }
                }
              >
                <option value="">
                  전체
                </option>

                <option value="true">
                  활성
                </option>

                <option value="false">
                  비활성
                </option>
              </select>
            </label>
          </div>


          <div
            className="
              clinical-card
              clinical-table-wrap
            "
          >
            <table
              className="clinical-table"
            >
              <thead>
                <tr>
                  <th>이름</th>
                  <th>로그인 ID</th>
                  <th>이메일</th>
                  <th>Role</th>
                  <th>상태</th>
                  <th>최근 로그인</th>
                  <th>관리</th>
                </tr>
              </thead>

              <tbody>
                {loading ? (
                  <tr>
                    <td
                      colSpan={7}
                      className="admin-table-empty"
                    >
                      조회 중...
                    </td>
                  </tr>
                ) : users.length === 0 ? (
                  <tr>
                    <td
                      colSpan={7}
                      className="admin-table-empty"
                    >
                      사용자가 없습니다.
                    </td>
                  </tr>
                ) : (
                  users.map(
                    (user) => (
                      <tr key={user.id}>
                        <td>
                          {user.name}
                        </td>

                        <td>
                          {user.login_id}
                        </td>

                        <td>
                          {user.email ?? "-"}
                        </td>

                        <td>
                          {user.role.name}
                        </td>

                        <td>
                          {user.is_active
                            ? "활성"
                            : "비활성"}
                        </td>

                        <td>
                          {user.last_login
                            ? new Date(
                                user.last_login,
                              )
                                .toLocaleString()
                            : "-"}
                        </td>

                        <td>
                          <button
                            type="button"
                            className="admin-action"
                            onClick={
                              () =>
                                openEdit(
                                  user,
                                )
                            }
                          >
                            수정
                          </button>
                        </td>
                      </tr>
                    ),
                  )
                )}
              </tbody>
            </table>
          </div>


          <div className="admin-pagination">
            <button
              type="button"
              className="admin-action"
              disabled={
                page <= 1
              }
              onClick={
                () =>
                  setPage(
                    (current) =>
                      Math.max(
                        1,
                        current - 1,
                      ),
                  )
              }
            >
              이전
            </button>

            <span>
              {page} / {totalPages}
              {" · "}
              총 {count}명
            </span>

            <button
              type="button"
              className="admin-action"
              disabled={
                page >= totalPages
              }
              onClick={
                () =>
                  setPage(
                    (current) =>
                      Math.min(
                        totalPages,
                        current + 1,
                      ),
                  )
              }
            >
              다음
            </button>
          </div>
        </>
      ) : (
        <div className="admin-role-layout">
          <section className="clinical-card">
            <div
              className="clinical-card__title"
            >
              <h3>Role</h3>
            </div>

            <div className="admin-role-list">
              {roles.map(
                (role) => (
                  <button
                    type="button"
                    key={role.id}
                    className={
                      (
                        "admin-role-item "
                        + (
                          selectedRoleId
                          === role.id
                            ? "is-active"
                            : ""
                        )
                      )
                    }
                    onClick={
                      () =>
                        setSelectedRoleId(
                          role.id,
                        )
                    }
                  >
                    <strong>
                      {role.name}
                    </strong>

                    <span>
                      {role.code}
                    </span>
                  </button>
                ),
              )}
            </div>
          </section>


          <section className="clinical-card">
            <div
              className="clinical-card__title"
            >
              <div>
                <h3>
                  Permission
                </h3>

                <p>
                  {selectedRole
                    ? (
                        selectedRole.name
                        + " · "
                        + selectedRole.code
                      )
                    : "-"}
                </p>
              </div>

              <button
                type="button"
                className="
                  admin-action
                  admin-action--primary
                "
                disabled={
                  !selectedRole
                  || selectedRole.code
                    === "SYSTEM_ADMIN"
                }
                onClick={
                  () =>
                    void savePermissions()
                }
              >
                권한 저장
              </button>
            </div>


            {selectedRole?.code
              === "SYSTEM_ADMIN"
              && (
                <div className="admin-message">
                  SYSTEM_ADMIN은 단일
                  운영 관리자이므로
                  권한 변경을 잠급니다.
                </div>
              )}


            <div className="admin-permission-groups">
              {permissionGroups.map(
                ([
                  domain,
                  items,
                ]) => (
                  <fieldset
                    key={domain}
                    className="admin-permission-group"
                  >
                    <legend>
                      {domain}
                    </legend>

                    {items.map(
                      (permission) => (
                        <label
                          key={
                            permission.code
                          }
                          className="admin-permission-item"
                        >
                          <input
                            type="checkbox"
                            checked={
                              permissionDraft
                                .has(
                                  permission.code,
                                )
                            }
                            disabled={
                              selectedRole
                                ?.code
                              === "SYSTEM_ADMIN"
                            }
                            onChange={
                              () =>
                                togglePermission(
                                  permission.code,
                                )
                            }
                          />

                          <span>
                            <strong>
                              {permission.name}
                            </strong>

                            <small>
                              {permission.code}
                            </small>
                          </span>
                        </label>
                      ),
                    )}
                  </fieldset>
                ),
              )}
            </div>
          </section>
        </div>
      )}


      {createOpen && (
        <div className="admin-modal-backdrop">
          <form
            className="admin-modal"
            onSubmit={
              handleCreate
            }
          >
            <div className="admin-modal__header">
              <h3>사용자 생성</h3>

              <button
                type="button"
                className="admin-action"
                onClick={
                  () =>
                    setCreateOpen(
                      false,
                    )
                }
              >
                닫기
              </button>
            </div>

            <div className="admin-form-grid">
              <label>
                로그인 ID
                <input
                  required
                  value={
                    createForm.login_id
                  }
                  onChange={
                    (event) =>
                      setCreateForm(
                        (current) => ({
                          ...current,
                          login_id:
                            event.target.value,
                        }),
                      )
                  }
                />
              </label>

              <label>
                이름
                <input
                  required
                  value={
                    createForm.name
                  }
                  onChange={
                    (event) =>
                      setCreateForm(
                        (current) => ({
                          ...current,
                          name:
                            event.target.value,
                        }),
                      )
                  }
                />
              </label>

              <label>
                이메일
                <input
                  type="email"
                  value={
                    createForm.email
                    ?? ""
                  }
                  onChange={
                    (event) =>
                      setCreateForm(
                        (current) => ({
                          ...current,
                          email:
                            event.target.value,
                        }),
                      )
                  }
                />
              </label>

              <label>
                Role
                <select
                  required
                  value={
                    createForm.role_id
                  }
                  onChange={
                    (event) =>
                      setCreateForm(
                        (current) => ({
                          ...current,
                          role_id:
                            event.target.value,
                        }),
                      )
                  }
                >
                  <option value="">
                    선택
                  </option>

                  {creatableRoles.map(
                    (role) => (
                      <option
                        key={role.id}
                        value={role.id}
                      >
                        {role.name}
                      </option>
                    ),
                  )}
                </select>
              </label>

              <label className="admin-form-wide">
                임시 비밀번호
                <input
                  required
                  type="password"
                  autoComplete="new-password"
                  value={
                    createForm.temp_password
                  }
                  onChange={
                    (event) =>
                      setCreateForm(
                        (current) => ({
                          ...current,
                          temp_password:
                            event.target.value,
                        }),
                      )
                  }
                />
              </label>
            </div>

            <div className="admin-modal__actions">
              <button
                type="submit"
                className="
                  admin-action
                  admin-action--primary
                "
              >
                계정 생성
              </button>
            </div>
          </form>
        </div>
      )}


      {editingUser && (
        <div className="admin-modal-backdrop">
          <form
            className="admin-modal"
            onSubmit={
              handleUpdate
            }
          >
            <div className="admin-modal__header">
              <div>
                <h3>사용자 수정</h3>

                <p>
                  {editingUser.login_id}
                </p>
              </div>

              <button
                type="button"
                className="admin-action"
                onClick={
                  () =>
                    setEditingUser(
                      null,
                    )
                }
              >
                닫기
              </button>
            </div>

            <div className="admin-form-grid">
              <label>
                이름
                <input
                  required
                  value={
                    editForm.name ?? ""
                  }
                  onChange={
                    (event) =>
                      setEditForm(
                        (current) => ({
                          ...current,
                          name:
                            event.target.value,
                        }),
                      )
                  }
                />
              </label>

              <label>
                이메일
                <input
                  type="email"
                  value={
                    editForm.email ?? ""
                  }
                  onChange={
                    (event) =>
                      setEditForm(
                        (current) => ({
                          ...current,
                          email:
                            event.target.value,
                        }),
                      )
                  }
                />
              </label>

              <label>
                Role
                <select
                  value={
                    editForm.role_id ?? ""
                  }
                  disabled={
                    editingUser.role.code
                    === "SYSTEM_ADMIN"
                  }
                  onChange={
                    (event) =>
                      setEditForm(
                        (current) => ({
                          ...current,
                          role_id:
                            event.target.value,
                        }),
                      )
                  }
                >
                  {roles.map(
                    (role) => (
                      <option
                        key={role.id}
                        value={role.id}
                      >
                        {role.name}
                      </option>
                    ),
                  )}
                </select>
              </label>

              <label className="admin-checkbox-label">
                <input
                  type="checkbox"
                  checked={
                    editForm.is_active
                    ?? false
                  }
                  disabled={
                    editingUser.role.code
                    === "SYSTEM_ADMIN"
                  }
                  onChange={
                    (event) =>
                      setEditForm(
                        (current) => ({
                          ...current,
                          is_active:
                            event.target.checked,
                        }),
                      )
                  }
                />

                활성 계정
              </label>
            </div>

            {editingUser.role.code
              === "SYSTEM_ADMIN"
              && (
                <div className="admin-message">
                  SYSTEM_ADMIN은 단일
                  관리자이므로 Role과
                  활성 상태를 변경하지
                  않습니다.
                </div>
              )}

            <div className="admin-modal__actions">
              <button
                type="submit"
                className="
                  admin-action
                  admin-action--primary
                "
              >
                저장
              </button>
            </div>
          </form>
        </div>
      )}
    </section>
  );
}
