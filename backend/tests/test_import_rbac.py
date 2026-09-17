"""Security and Multi-Tenant RBAC isolation tests for Data Import pipeline."""

import io
import uuid

from fastapi.testclient import TestClient

from backend.app.core.constants import ImportJobStatus
from backend.app.models.university import University
from backend.app.models.user import User
from backend.tests.test_people import create_test_user, get_user_headers
from backend.tests.test_users import get_admin_headers


def test_unauthenticated_and_unauthorized_import_endpoints(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify unauthenticated calls are 401 and student/lecturer calls are 403."""
    admin_headers = get_admin_headers(client, test_admin_user, test_university)

    # Create Student user
    stu_uid, stu_uname, stu_pwd = create_test_user(client, admin_headers, prefix="stu_rbac")
    stu_headers = get_user_headers(client, stu_uname, stu_pwd, str(test_university.id))

    # Create Lecturer user
    lec_uid, lec_uname, lec_pwd = create_test_user(client, admin_headers, prefix="lec_rbac")
    # Assign Lecturer role
    roles_res = client.get("/api/v1/roles", headers=admin_headers)
    lec_role_id = next(r["id"] for r in roles_res.json()["data"] if r["code"] == "LECTURER")
    client.post(
        f"/api/v1/users/{lec_uid}/role-assignments",
        headers=admin_headers,
        json={
            "role_id": lec_role_id,
            "scope_type": "UNIVERSITY",
            "scope_id": str(test_university.id),
        },
    )
    lec_headers = get_user_headers(client, lec_uname, lec_pwd, str(test_university.id))

    csv_data = b"student_number,first_name,last_name\nSTU-01,Ali,Ahmadi\n"

    # 1. Unauthenticated -> 401
    unauth_res = client.post(
        "/api/v1/imports/preview",
        data={"import_type": "STUDENTS"},
        files={"file": ("test.csv", io.BytesIO(csv_data), "text/csv")},
    )
    assert unauth_res.status_code == 401

    # 2. Student -> 403 FORBIDDEN
    stu_res = client.post(
        "/api/v1/imports/preview",
        headers=stu_headers,
        data={"import_type": "STUDENTS"},
        files={"file": ("test.csv", io.BytesIO(csv_data), "text/csv")},
    )
    assert stu_res.status_code == 403

    # Student cannot list jobs
    stu_list = client.get("/api/v1/imports", headers=stu_headers)
    assert stu_list.status_code == 403

    # 3. Lecturer -> 403 FORBIDDEN
    lec_res = client.post(
        "/api/v1/imports/preview",
        headers=lec_headers,
        data={"import_type": "STUDENTS"},
        files={"file": ("test.csv", io.BytesIO(csv_data), "text/csv")},
    )
    assert lec_res.status_code == 403

    lec_list = client.get("/api/v1/imports", headers=lec_headers)
    assert lec_list.status_code == 403


def test_import_cross_tenant_isolation(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
    second_university: University,
    second_admin_user: User,
) -> None:
    """Verify University A import jobs are invisible and inaccessible to University B."""
    headers_a = get_admin_headers(client, test_admin_user, test_university)
    headers_b = get_admin_headers(client, second_admin_user, second_university)

    prefix = uuid.uuid4().hex[:6]
    csv_data = f"code,name\nCS-{prefix},Cross Tenant Course\n".encode()

    # University A creates preview job
    res_a = client.post(
        "/api/v1/imports/preview",
        headers=headers_a,
        data={"import_type": "COURSES"},
        files={"file": ("courses.csv", io.BytesIO(csv_data), "text/csv")},
    )
    assert res_a.status_code == 201
    job_a_id = res_a.json()["data"]["job"]["id"]

    # University B caller attempts to read University A's job -> 404 NOT_FOUND
    get_res = client.get(f"/api/v1/imports/{job_a_id}", headers=headers_b)
    assert get_res.status_code == 404
    assert get_res.json()["error"]["code"] == "NOT_FOUND"

    # University B caller attempts to list rows of University A's job -> 404 NOT_FOUND
    rows_res = client.get(f"/api/v1/imports/{job_a_id}/rows", headers=headers_b)
    assert rows_res.status_code == 404

    # University B caller attempts to commit University A's job -> 404 NOT_FOUND
    commit_res = client.post(f"/api/v1/imports/{job_a_id}/commit", headers=headers_b, json={})
    assert commit_res.status_code == 404

    # University B caller attempts to cancel University A's job -> 404 NOT_FOUND
    cancel_res = client.post(f"/api/v1/imports/{job_a_id}/cancel", headers=headers_b)
    assert cancel_res.status_code == 404

    # University B listing jobs must NOT include job_a_id
    list_b = client.get("/api/v1/imports", headers=headers_b)
    assert list_b.status_code == 200
    b_job_ids = [j["id"] for j in list_b.json()["data"]["items"]]
    assert job_a_id not in b_job_ids


def test_import_job_cancellation_lifecycle(
    client: TestClient,
    test_university: University,
    test_admin_user: User,
) -> None:
    """Verify admin can cancel an uncommitted import job and cancelled job cannot be committed."""
    headers = get_admin_headers(client, test_admin_user, test_university)
    prefix = uuid.uuid4().hex[:6]
    csv_data = f"code,name\nCS-CANCEL-{prefix},Cancel Course\n".encode()

    # 1. Preview
    res = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        data={"import_type": "COURSES"},
        files={"file": ("courses.csv", io.BytesIO(csv_data), "text/csv")},
    )
    assert res.status_code == 201
    job_id = res.json()["data"]["job"]["id"]

    # 2. Cancel
    cancel_res = client.post(f"/api/v1/imports/{job_id}/cancel", headers=headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["data"]["status"] == ImportJobStatus.CANCELLED.value

    # 3. Commit attempt on cancelled job rejected
    commit_res = client.post(f"/api/v1/imports/{job_id}/commit", headers=headers, json={})
    assert commit_res.status_code == 409
